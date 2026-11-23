"""
Documentos privados (escrituras, cédulas, mandatos, certificados...).
Se guardan fuera de MEDIA_ROOT y solo se descargan desde el CRM con permiso.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from core.models import Auditado
from core.validators import (
    EXTENSIONES_DOCUMENTO,
    TamanoMaximoValidator,
    almacenamiento_privado,
    nombre_aleatorio,
)


def ruta_documento(instancia, nombre):
    if instancia.operacion_id:
        carpeta = f"operaciones/{instancia.operacion_id}"
    elif instancia.propiedad_id:
        carpeta = f"propiedades/{instancia.propiedad_id}"
    else:
        carpeta = f"contactos/{instancia.contacto_id}"
    return f"{carpeta}/{nombre_aleatorio(nombre)}"


class Documento(Auditado):
    nombre = models.CharField("nombre del documento", max_length=150)
    archivo = models.FileField(
        upload_to=ruta_documento,
        storage=almacenamiento_privado,
        validators=[FileExtensionValidator(EXTENSIONES_DOCUMENTO), TamanoMaximoValidator(settings.MAX_DOCUMENTO_MB)],
    )
    contacto = models.ForeignKey("contactos.Contacto", on_delete=models.CASCADE, null=True, blank=True,
                                 related_name="documentos")
    propiedad = models.ForeignKey("propiedades.Propiedad", on_delete=models.CASCADE, null=True, blank=True,
                                  related_name="documentos")
    operacion = models.ForeignKey("comercial.Operacion", on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="documentos",
                                  help_text="Promesa, escritura, contrato de arriendo, comprobante de pago...")

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return self.nombre

    def clean(self):
        if not (self.contacto_id or self.propiedad_id or self.operacion_id):
            raise ValidationError("El documento debe asociarse a un contacto, una propiedad o una operación.")

    @property
    def duenio(self):
        """Ficha a la que pertenece el documento."""
        return self.operacion or self.propiedad or self.contacto