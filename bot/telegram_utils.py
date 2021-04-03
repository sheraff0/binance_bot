import asyncio
from multiprocessing import Process
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
from .binance_utils import BinanceAccount


class ProfileMixin:
    profiles = {}

    def get_profile_db(self, chat_id):
        return Profile.objects.get_or_create(telegram_chat_id=chat_id)

    def get_binance_account(self, profile):
        chat_id = profile.get('telegram_chat_id')
        api_key = profile.get('binance_api_key')
        secret_key = profile.get('binance_secret_key')
        notifications = profile.get('notifications')
        if not (api_key and secret_key):
            return
        binance = BinanceAccount(self.bot, chat_id, api_key, secret_key)
        if binance.account_status and notifications:
            binance.start_user_socket()
        return binance

    def dump_profiles(self):
        profiles = [*Profile.objects.standard_values()]
        self.profiles = {x['telegram_chat_id']: x for x in profiles}
        for chat_id, profile in self.profiles.items():
            self.profiles[chat_id][
                'binance_account'] = self.get_binance_account(profile)


class BinanceMixin(ProfileMixin):
    (
        ROOT_ACTION,
        ADD_API_KEY, ADD_SECRET_KEY,
        EDIT_NOTIFICATIONS
    ) = range(4)  # conversation state codes
    START_OPTIONS = {
        'NEW': ['Добавить пару ключей'],
        'EXISTING': ['Заменить пару ключей', 'Настроить уведомления'],
    }
    NOTIFICATIONS_OPTIONS = ['Включить', 'Отключить']

    def __init__(self, *args):
        super().__init__(*args)
        self.dump_profiles()

    def update_profile(self, chat_id, obj_dict):
        self.profiles[chat_id] = {
            **self.profiles.get(chat_id, {}), **obj_dict}

    def options_list_buttons(self, list_):
        return [InlineKeyboardButton(
            value, callback_data=key
        ) for key, value in enumerate(list_)]

    def shredder(self, chat_id, message):
        self.bot.delete_message(chat_id, message.message_id)

    def start(self, update: Updater, context: CallbackContext) -> int:
        chat_id, text, from_user = self.get_message_details(update)
        chat_id = str(chat_id)
        profile_db, new = self.get_profile_db(chat_id)
        if new:
            self.profiles[chat_id] = {'telegram_chat_id': chat_id}
        api_key = profile_db.binance_api_key
        start_options = self.START_OPTIONS[
            'NEW' if new or not api_key else 'EXISTING']
        reply_keyboard = [self.options_list_buttons(start_options)]
        reply_markup = InlineKeyboardMarkup(reply_keyboard)
        update.message.reply_text(
            '\n'.join([
                f"Здравствуйте, {from_user.first_name}!",
                "Выберите действие:"
            ]), reply_markup=reply_markup)
        return self.ROOT_ACTION

    def root_action(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        action, from_user = int(query.data), query.from_user
        if action == 0:
            query.edit_message_text(text="Введите API-ключ:")
            return self.ADD_API_KEY
        elif action == 1:
            reply_keyboard = [self.options_list_buttons(
                self.NOTIFICATIONS_OPTIONS)]
            reply_markup = InlineKeyboardMarkup(reply_keyboard)
            query.edit_message_text(
                '\n'.join([
                    "Настройка уведомлений:"
                ]), reply_markup=reply_markup)
            return self.EDIT_NOTIFICATIONS

    def add_api_key(self, update: Update, context: CallbackContext) -> int:
        chat_id, text, from_user = self.get_message_details(update)
        chat_id = str(chat_id)
        message = update.message
        api_key = text
        self.update_profile(chat_id, {'binance_api_key': api_key})
        self.shredder(chat_id, message)
        update.message.reply_text(
            text="API-ключ принят.\nВведите секретный ключ:")
        return self.ADD_SECRET_KEY

    def add_secret_key(self, update: Update, context: CallbackContext) -> int:
        chat_id, text, from_user = self.get_message_details(update)
        chat_id = str(chat_id)
        message = update.message
        secret_key = text
        self.update_profile(chat_id, {'binance_secret_key': secret_key})
        api_key = self.profiles[chat_id].get('binance_api_key')
        binance = self.profiles[chat_id].get('binance_account')
        if binance:
            binance.stop_user_socket()
            del binance
            self.update_profile(chat_id, {'binance_account': None})
        binance = self.get_binance_account(self.profiles[chat_id])
        if binance.account_status:
            profile_db, new = self.get_profile_db(chat_id)
            profile_db.binance_api_key = api_key
            profile_db.binance_secret_key = secret_key
            profile_db.save()
            self.update_profile(chat_id, {
                'binance_account': binance,
                'notifications': True
            })
            self.shredder(chat_id, message)
            message.reply_text(
                text=f"Пара ключей принята. Веб-сокет открыт.")
            return ConversationHandler.END
        else:
            update.message.reply_text(
                text="Введите верную пару ключей!\nВведите API-ключ:")
            return self.ADD_API_KEY

    def edit_notifications(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        action = int(query.data)
        chat_id = str(query.message.chat_id)
        notifications_state = self.profiles[chat_id].get('notifications')
        notifications = action == 0
        self.update_profile(chat_id, {'notifications': notifications})
        if not notifications_state and notifications:
            binance = self.get_binance_account(self.profiles[chat_id])
            self.update_profile(chat_id, {'binance_account': binance})
        elif notifications_state and not notifications:
            binance = self.profiles[chat_id].get('binance_account')
            binance.stop_user_socket()
            del binance
            self.update_profile(chat_id, {'binance_account': None})
        profile_db, new = self.get_profile_db(chat_id)
        profile_db.notifications = notifications
        profile_db.save()
        query.edit_message_text(
            text=f"Уведомления {'включены' if notifications else 'отключены'}!")
        return ConversationHandler.END

    def cancel(self, update: Update, context: CallbackContext) -> int:
        update.message.reply_text("Введите /start и выберите действие.")
        return ConversationHandler.END

    def get_handler(self):
        command_handlers = [
            CommandHandler('start', self.start),
            CommandHandler('cancel', self.cancel)
        ]
        return ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                self.ROOT_ACTION: [CallbackQueryHandler(self.root_action)],
                self.ADD_API_KEY: [
                    MessageHandler(Filters.text, self.add_api_key),
                    *command_handlers
                ],
                self.ADD_SECRET_KEY: [
                    MessageHandler(Filters.text, self.add_secret_key),
                    *command_handlers
                ],
                self.EDIT_NOTIFICATIONS: [CallbackQueryHandler(
                    self.edit_notifications)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )


class TelegramBot:
    def __init__(self, state):
        self.create_bot()
        self.state = state
        self.state['listen_keys'] = set()

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
        updater.dispatcher.add_handler(
            self.get_handler_echo())
        updater.start_polling()
        updater.idle()

    def get_handler_echo(self):
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
            text=f"""{chat_id}

{text}
{from_user.first_name}
{update.message.chat.type}""")


class BinanceBot(BinanceMixin, TelegramBot):
    pass
