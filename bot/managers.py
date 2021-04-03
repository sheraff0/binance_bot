from django.db.models import QuerySet


class ProfileQueryset(QuerySet):
    def standard_values(self):
        return self.values(
            'telegram_chat_id', 'binance_api_key', 'binance_secret_key')
