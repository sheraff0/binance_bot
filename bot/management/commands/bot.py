import asyncio
from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand, CommandError

from bot.telegram_utils import BinanceBot
from bot.binance_utils import BinanceAccountsManager


class Command(BaseCommand):
    help = 'Configures and initiates Telegram Bot'

    def add_arguments(self, parser):
        # parser.add_argument('poll_ids', nargs='+', type=int)
        pass

    async def run_bot(self, loop, queue):
        bot = BinanceBot(loop, queue)
        with ThreadPoolExecutor() as pool:
            await loop.run_in_executor(
                pool, bot.set_updater)

    async def run_manager(self, loop, queue):
        manager = BinanceAccountsManager(queue)
        loop.create_task(manager.subscribe())

    def main(self):
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()
        loop.create_task(self.run_bot(loop, queue))
        loop.create_task(self.run_manager(loop, queue))
        loop.run_forever()

    def handle(self, *args, **options):
        self.main()
