from django.db import models


class Profile(models.Model):
    telegram_id = models.CharField(
        max_length=128,
        verbose_name="ID пользователя",
        null=True, blank=True,
    )
    binance_api_key = models.CharField(
        max_length=128,
        verbose_name="API ключ Binance",
        null=True, blank=True,
    )
