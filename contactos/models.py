
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.urls import reverse

from core.models import Auditado
from core.validators import normalizar_rut, validar_rut


class Contacto(Auditado):
    rut = models.CharField(
        "RUT", max_length=12, unique=True, null=True, blank=True,
        validators=[validar_rut],
        help_text="Ej.: 12.345.678-5. Obligatorio para propietarios.",
    )
    nombre = models.CharField("nombre completo", max_length=150)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    email = models.EmailField("correo electrónico", blank=True)
    informacion_adicional = models.TextField(
        "información de contacto adicional", blank=True,
        help_text="Otro teléfono, horario preferido, dirección de contacto, etc.",
    )
    es_propietario = models.BooleanField("propietario", default=False)
    es_arrendatario = models.BooleanField("arrendatario", default=False)
    es_interesado = models.BooleanField("interesado / comprador", default=False)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "contacto"

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("contactos:detalle", args=[self.pk])

    @property
    def roles(self):
        r = []
        if self.es_propietario:
            r.append("Propietario")
        if self.es_arrendatario:
            r.append("Arrendatario")
        if self.es_interesado:
            r.append("Interesado")
        return r

    def clean(self):
        self.rut = normalizar_rut(self.rut) or None
        if not (self.es_propietario or self.es_arrendatario or self.es_interesado):
            raise ValidationError("Marca al menos un rol para el contacto.")
        if self.es_propietario and not self.rut:
            raise ValidationError({"rut": "El RUT es obligatorio para un propietario."})

    def save(self, *args, **kwargs):
        self.rut = normalizar_rut(self.rut) or None
        super().save(*args, **kwargs)


