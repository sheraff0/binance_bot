from binance.client import Client
from binance.websockets import BinanceSocketManager
from binance.exceptions import BinanceAPIException


class BinanceAccount:
    def __init__(self, bot, chat_id, api_key, secret_key):
        self.bot, self.chat_id = bot, chat_id
        self.api_key, self.secret_key = api_key, secret_key
        try:
            self.client = Client(api_key=api_key, api_secret=secret_key)
            self.account_status = self.client.get_account_status()
            print(self.account_status)
            self.socket_manager = BinanceSocketManager(self.client)
        except (KeyError, BinanceAPIException) as e:
            print(e)
            self.account_status = None

    def start_user_socket(self):
        print("Starting...")
        self.conn_key = self.socket_manager.start_user_socket(
            self.process_msg)
        self.socket_manager.start()
        print("Started!")
        self.bot.send_message(self.chat_id, "Веб-сокет открыт.")

    def stop_user_socket(self):
        print("Stopping...")
        try:
            self.socket_manager.stop_socket(self.conn_key)
            print("Stopped!")
            self.bot.send_message(self.chat_id, "Веб-сокет закрыт.")
        except Exception as e:
            print(e)

    def process_msg(self, msg):
        self.bot.send_message(self.chat_id, msg)
