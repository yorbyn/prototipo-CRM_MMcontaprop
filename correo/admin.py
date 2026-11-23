from django.contrib import admin

from .models import Mensaje, PlantillaCorreo

admin.site.register(PlantillaCorreo)
admin.site.register(Mensaje)
