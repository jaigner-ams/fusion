from django.db import models
from django.conf import settings

class Dentist(models.Model):
    name = models.CharField(max_length=128)
    lab = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

class DefaultPriceList(models.Model):
    lab = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    applied_after = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

class PriceList(models.Model):
    dentist = models.ForeignKey(Dentist, on_delete=models.CASCADE)
    applied_after = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

