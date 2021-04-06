import asyncio
import websockets
from aiohttp import ClientSession


class ConnectionManager:
    async def request(self, url, method='get', **kwargs):
        async with ClientSession() as session:
            async with getattr(session, method)(url, **kwargs) as response:
                return await response.text()

    async def ws_client(self, url, callback=print):
        async with websockets.connect(url) as ws:
            async for msg in ws:
                callback(msg)
