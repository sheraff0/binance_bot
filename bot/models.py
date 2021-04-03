from django.db import models
from .managers import ProfileQueryset


class Profile(models.Model):
    telegram_chat_id = models.CharField(
        max_length=128,
        verbose_name="ID пользователя",
        null=True, blank=True,
    )
    binance_api_key = models.CharField(
        max_length=128,
        verbose_name="API ключ Binance",
        null=True, blank=True,
    )
    binance_secret_key = models.CharField(
        max_length=128,
        verbose_name="Секретный ключ Binance",
        null=True, blank=True,
    )

    objects = ProfileQueryset.as_manager()
