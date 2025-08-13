from django.contrib import admin
from .models import Dentist, DefaultPriceList, PriceList

admin.site.register(Dentist)
admin.site.register(DefaultPriceList)
admin.site.register(PriceList)
