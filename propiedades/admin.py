from django.contrib import admin

from .models import FotoPropiedad, Propiedad, TipoPropiedad

admin.site.register(TipoPropiedad)
admin.site.register(Propiedad)
admin.site.register(FotoPropiedad)
