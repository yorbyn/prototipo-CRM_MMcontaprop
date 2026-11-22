from django.contrib import admin

from .models import Oferta, Operacion, Oportunidad

admin.site.register(Oportunidad)
admin.site.register(Oferta)
admin.site.register(Operacion)
