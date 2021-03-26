import datetime
from telegram import (
    Bot, Update, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    MessageHandler, ConversationHandler, CommandHandler,
    Updater, Filters, CallbackContext, CallbackQueryHandler,
)
from telegram.utils.request import Request
from telegram.error import BadRequest

from django.conf import settings as _
from bot.models import Profile
from .binance import BinanceAccount


class ProfileMixin:
    def get_profile(self, user_id):
        return Profile.objects.get_or_create(telegram_id=user_id)


class BinanceMixin(ProfileMixin):
    ROOT_ACTION, ADD_API_KEY, ADD_LISTEN_KEY, EDIT_NOTIFICATIONS = range(4)  # conversation state codes
    START_OPTIONS = {
        'NEW': ['Добавить ключ'],
        'EXISTING': ['Заменить ключ', 'Получить ключ WSS Binance', 'Настроить уведомления'],
    }

    def options_list_buttons(self, list_):
        return [InlineKeyboardButton(
            value, callback_data=key
        ) for key, value in enumerate(list_)]

    def start(self, update: Updater, context: CallbackContext) -> int:
        chat_id, text, from_user = self.get_message_details(update)
        profile, new = self.get_profile(from_user['id'])
        api_key = profile.binance_api_key
        start_options = self.START_OPTIONS[
            'NEW' if new or not api_key else 'EXISTING']
        reply_keyboard = [self.options_list_buttons(start_options)]
        reply_markup = InlineKeyboardMarkup(reply_keyboard)
        update.message.reply_text(
            '\n'.join([
                *(['Добро пожаловать!'] if new else [
                    f"Ваш ключ: {api_key or '___'}"]),
                "Выберите действие"
            ]), reply_markup=reply_markup)
        return self.ROOT_ACTION

    def root_action(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        action, from_user = int(query.data), query.from_user
        if action == 0:
            query.edit_message_text(text="Введите ключ:")
            return self.ADD_API_KEY
        elif action == 1:
            return self.add_listen_key(query)
        elif action == 2:
            query.edit_message_text(text="Настроить уведомления:")
            return self.EDIT_NOTIFICATIONS

    def add_api_key(self, update: Update, context: CallbackContext) -> int:
        chat_id, text, from_user = self.get_message_details(update)
        api_key = text
        profile, new = self.get_profile(from_user['id'])
        binance = BinanceAccount(api_key)
        listen_key = binance.get_listen_key()
        if listen_key:
            profile.binance_api_key = api_key
            profile.save()
            update.message.reply_text(
                text=f"Получен listenKey для подключения к WSS Binance: {listen_key}")
            return ConversationHandler.END
        else:
            update.message.reply_text(
                text="Введите верный ключ apiKey:")
            return self.ADD_API_KEY

    def add_listen_key(self, query):
        from_user = query.from_user
        profile, new = self.get_profile(from_user['id'])
        binance = BinanceAccount(profile.binance_api_key)
        listen_key = binance.get_listen_key()
        if listen_key:
            query.edit_message_text(
                text=f"Получен listenKey для подключения к WSS Binance: {listen_key}")
            return ConversationHandler.END
        else:
            query.edit_message_text(
                text="Введите верный ключ apiKey:")
            return ConversationHandler.ADD_KEY

    def edit_notifications(self, update: Update, context: CallbackContext) -> int:
        chat_id, text, from_user = self.get_message_details(update)
        update.message.reply_text(
            text=f"Уведомления настроены!")
        return ConversationHandler.END

    def cancel(self, update: Update, context: CallbackContext) -> int:
        update.message.reply_text("Введите /start и выберите действие.")
        return ConversationHandler.END

    def get_handler(self):
        return ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                self.ROOT_ACTION: [CallbackQueryHandler(self.root_action)],
                self.ADD_API_KEY: [MessageHandler(
                    Filters.text, self.add_api_key)],
                self.ADD_LISTEN_KEY: [MessageHandler(
                    Filters.text, self.add_api_key)],
                self.EDIT_NOTIFICATIONS: [MessageHandler(
                    Filters.text, self.edit_notifications)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )


class TelegramBot:
    def __init__(self):
        self.create_bot()
        self.set_updater()

    def create_bot(self):
        request = Request(
            connect_timeout=1.5,
            read_timeout=1.5,
            con_pool_size=8
        )
        self.bot = Bot(
            request=request,
            token=_.TELEGRAM_BOT_TOKEN,
            # base_url=_.TELEGRAM_PROXY_URL,
        )

    def set_updater(self):
        updater = Updater(bot=self.bot)
        updater.dispatcher.add_handler(
            self.get_handler())
        updater.start_polling()
        updater.idle()

    def get_handler(self):
        # Echo as default
        return MessageHandler(Filters.text, self.do_echo)

    def get_message_details(self, update):
        return (
            update.message.chat_id,
            update.message.text,
            update.message.from_user
        )

    def do_echo(self, update: Update, context: CallbackContext):
        chat_id, text, from_user = self.get_message_details(update)
        update.message.reply_text(
            text=f"{chat_id}\n\n{text}\n{from_user.first_name}")


class BinanceBot(BinanceMixin, TelegramBot):
    pass
