import asyncio
import uvloop
import websockets
import requests
import json

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


class BinanceAccount:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = Client(api_key)
        self.socket_manager = BinanceSocketManager(self.client)

    def get_api_key_header(self):
        return {"X-MBX-APIKEY": self.api_key}

    def get_listen_key(self):
        response = requests.post(
            f'{BASE_URL}{DATA_STREAM}',
            headers=self.get_api_key_header()
        )
        try:
            self.listen_key = json.loads(response._content).get('listenKey')
            return self.listen_key
        except Exception as e:
            print(e)

    def run_ws_client(self, bot, chat_id):
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        asyncio.run(self.ws_client(bot, chat_id))

    async def ws_client(self, bot, chat_id, callback=print):
        async with websockets.connect(
            f'{WSS_URL}{self.listen_key}'
        ) as ws:
            print("Connection established!")
            async for msg in ws:
                callback(msg)
