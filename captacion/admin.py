from django.contrib import admin

from .models import Encargo, FotoSolicitud, SolicitudCaptacion

admin.site.register(SolicitudCaptacion)
admin.site.register(Encargo)
admin.site.register(FotoSolicitud)
