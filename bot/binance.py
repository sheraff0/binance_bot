import requests
import json

BASE_URL = 'https://api.binance.com'
DATA_STREAM = '/api/v3/userDataStream'


class BinanceAccount:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_api_key_header(self):
        return {"X-MBX-APIKEY": self.api_key}

    def get_listen_key(self):
        response = requests.post(
            f'{BASE_URL}{DATA_STREAM}',
            headers=self.get_api_key_header()
        )
        try:
            return json.loads(response._content).get('listenKey')
        except Exception as e:
            print(e)
