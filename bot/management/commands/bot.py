import asyncio
from multiprocessing import Process, Manager
from django.core.management.base import BaseCommand, CommandError

from bot.telegram_utils import BinanceBot


class Command(BaseCommand):
    help = 'Configures and initiates Telegram Bot'

    def add_arguments(self, parser):
        # parser.add_argument('poll_ids', nargs='+', type=int)
        pass

    def run_bot(self, state):
        bot = BinanceBot(state)
        bot.set_updater()

    def handle(self, *args, **options):
        m = Manager()
        state = m.dict()
        ps = [Process(target=x, args=(state, ), daemon=True) for x in (
            self.run_bot,
        )]
        [p.start() for p in ps]
        [p.join() for p in ps]
