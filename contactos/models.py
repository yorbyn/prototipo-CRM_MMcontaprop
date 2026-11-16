
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.urls import reverse

from core.models import Auditado
from core.validators import normalizar_rut, validar_rut
from propiedades.models import Propiedad

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

class PreferenciaBusqueda(Auditado):
    """Qué busca un interesado. Un contacto puede tener varias (por ejemplo, casa en
    venta en el norte y departamento en arriendo en el centro). Los campos vacíos
    significan «cualquiera». Se usarán en el cruce de propiedades (etapa 3)."""
    contacto = models.ForeignKey(Contacto, on_delete=models.CASCADE, related_name="preferencias")
    operacion = models.CharField("operación", max_length=10, choices=Propiedad.Operacion.choices)
    tipo = models.CharField("tipo de inmueble", max_length=20, blank=True, choices=Propiedad.Tipo.choices)
    zona = models.CharField(max_length=10, blank=True, choices=Propiedad.Zona.choices)
    moneda = models.CharField(max_length=3, default="CLP", choices=Propiedad.Moneda.choices)
    precio_min = models.DecimalField("precio desde", max_digits=14, decimal_places=2, null=True, blank=True,
                                     validators=[MinValueValidator(0)])
    precio_max = models.DecimalField("precio hasta", max_digits=14, decimal_places=2, null=True, blank=True,
                                     validators=[MinValueValidator(1)])
    dormitorios_min = models.PositiveSmallIntegerField("dormitorios (mínimo)", null=True, blank=True,
                                                       validators=[MaxValueValidator(20)])

    class Meta:
        ordering = ["id"]
        verbose_name = "preferencia de búsqueda"
        verbose_name_plural = "preferencias de búsqueda"

    def __str__(self):
        return f"Preferencia de {self.contacto}"

    def clean(self):
        if self.precio_min is not None and self.precio_max is not None and self.precio_min > self.precio_max:
            raise ValidationError({"precio_max": "El precio máximo debe ser mayor o igual al mínimo."})

    @property
    def tiene_precio(self):
        return self.precio_min is not None or self.precio_max is not None
