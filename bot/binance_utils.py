import asyncio
import json

from .core import ConnectionManager

BASE_URL = 'https://api.binance.com'
DATA_STREAM = '/api/v3/userDataStream'
WSS_URL = 'wss://stream.binance.com:9443/ws/'
SUBSCRIBE = {
  "method": "SUBSCRIBE",
  "params": [
    "btcusdt@aggTrade",
    "btcusdt@depth"
  ],
  "id": 1
}
LISTEN_KEY_TIMEOUT = 30 * 60
WS_CONNECTION_TIMEOUT = 24 * 60 * 60


class BinanceAccount(ConnectionManager):
    listen_key = None

    def __init__(self, bot, chat_id, api_key, notifications):
        self.bot = bot.bot
        self.chat_id = chat_id
        self.api_key = api_key
        self.notifications = notifications

    def get_api_key_header(self):
        return {"X-MBX-APIKEY": self.api_key or ''}

    async def get_listen_key(self):
        response = await self.request(
            f'{BASE_URL}{DATA_STREAM}',
            method='post',
            headers=self.get_api_key_header()
        )
        try:
            self.listen_key = json.loads(response).get('listenKey')
            print(f"Received listenKey {self.listen_key}")
            return self.listen_key
        except Exception as e:
            print(e)

    async def keep_alive_listen_key(self):
        while True:
            await asyncio.sleep(LISTEN_KEY_TIMEOUT)
            await self.get_listen_key()

    async def user_stream(self, callback=print):
        await self.ws_client(
            f'{WSS_URL}{self.listen_key}',
            callback=self.process_msg
        )

    async def persistent_user_stream(self):
        while True:
            try:
                self.bot.send_message(self.chat_id, "Веб-сокет открыт.")
                await asyncio.wait_for(
                    self.user_stream(),
                    WS_CONNECTION_TIMEOUT
                )
            except asyncio.TimeoutError:
                self.bot.send_message(
                    self.chat_id, "Веб-сокет закрыт. Перезапуск...")

    def process_msg(self, msg):
        self.bot.send_message(self.chat_id, msg)


class BinanceAccountsManager:
    def __init__(self, queue):
        self.queue = queue
        self.accounts = {}

    def parse_profile(self, profile):
        chat_id = profile.get('telegram_chat_id')
        api_key = profile.get('binance_api_key')
        notifications = profile.get('notifications')
        return chat_id, api_key, notifications

    def cancel_tasks(self, chat_id, bot):
        _, *tasks = self.accounts.get(chat_id, (None, None))
        if tasks and tasks[0]:
            bot.bot.send_message(chat_id, "Веб-сокет закрыт.")
            print(f"CANCELLING TASKS for {chat_id}")
            print(tasks)
            [task.cancel() for task in tasks if task]

    async def activate_account(self, msg):
        profile, bot = msg
        parsed_profile = self.parse_profile(profile)
        chat_id, api_key, notifications = parsed_profile
        account = BinanceAccount(bot, *parsed_profile)
        # Write to database
        await bot.save_profile_db(chat_id, api_key, None, notifications)
        self.cancel_tasks(chat_id, bot)
        if notifications:
            if account.api_key:
                await account.get_listen_key()
            if account.listen_key:
                tasks = [asyncio.create_task(task()) for task in [
                    account.persistent_user_stream,
                    account.keep_alive_listen_key,
                ]]
                self.accounts[chat_id] = [account, *tasks]
            else:
                self.accounts[chat_id] = None, None
                bot.bot.send_message(chat_id, "Неверный ключ.")

    async def subscribe(self):
        while True:
            msg = await self.queue.get()
            print(f"Received profile data: {msg}")
            self.queue.task_done()
            await self.activate_account(msg)
