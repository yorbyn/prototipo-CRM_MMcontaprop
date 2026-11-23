from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import ComprobantePago, FotoPropiedad, Propiedad, TipoPropiedad

admin.site.register(TipoPropiedad)
admin.site.register(Propiedad)
admin.site.register(FotoPropiedad)


@admin.register(ComprobantePago)
class ComprobantePagoAdmin(admin.ModelAdmin):
    """La imagen es privada y no tiene URL pública, por eso el admin no muestra el campo de archivo
    (se caería al pedir su URL): muestra un enlace a la vista protegida del CRM. Se agregan desde la ficha."""
    list_display = ["nombre", "fecha", "propiedad"]
    exclude = ["imagen"]
    readonly_fields = ["ver_imagen"]

    @admin.display(description="imagen")
    def ver_imagen(self, comprobante):
        return format_html('<a href="{}" target="_blank">Ver imagen</a>',
                           reverse("propiedades:comprobante_ver", args=[comprobante.pk]))

    def has_add_permission(self, request):
        return False
