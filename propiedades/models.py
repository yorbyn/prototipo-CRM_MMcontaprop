from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.urls import reverse
# Create your models here.

from core.models import Auditado
from core.validators import EXTENSIONES_FOTO, TamanoMaximoValidator, nombre_aleatorio


class Propiedad(Auditado):
    class Tipo(models.TextChoices):
        CASA = "casa", "Casa"
        DEPARTAMENTO = "departamento", "Departamento"
        TERRENO = "terreno", "Terreno"
        PARCELA = "parcela", "Parcela"
        OFICINA = "oficina", "Oficina"
        LOCAL = "local", "Local comercial"
        BODEGA = "bodega", "Bodega"

    class Operacion(models.TextChoices):
        VENTA = "venta", "Venta"
        ARRIENDO = "arriendo", "Arriendo"

    class ModalidadArriendo(models.TextChoices):
        PERMANENTE = "permanente", "Permanente / largo plazo"
        TEMPORAL = "temporal", "Temporal"

    class Moneda(models.TextChoices):
        CLP = "CLP", "Pesos (CLP)"
        UF = "UF", "UF"

    class Zona(models.TextChoices):
        NORTE = "norte", "Norte"
        CENTRO = "centro", "Centro"
        SUR = "sur", "Sur"

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        DISPONIBLE = "disponible", "Disponible (publicada)"
        ARRENDADA = "arrendada", "Arrendada"
        VENDIDA = "vendida", "Vendida"
        ANULADA = "anulada", "Anulada"

    # --- Identificación ---
    codigo = models.CharField("código", max_length=12, unique=True, null=True, editable=False)
    titulo = models.CharField("título comercial", max_length=120,
                              help_text="Ej.: Casa amplia con patio en sector norte")
    tipo = models.CharField("tipo de inmueble", max_length=20, choices=Tipo.choices)
    operacion = models.CharField("operación", max_length=10, choices=Operacion.choices)
    modalidad_arriendo = models.CharField("modalidad de arriendo", max_length=12,
                                          choices=ModalidadArriendo.choices, blank=True)

    # --- Precio ---
    precio = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True,
                                 validators=[MinValueValidator(1)],
                                 help_text="Obligatorio para publicar.")
    moneda = models.CharField(max_length=3, choices=Moneda.choices, default=Moneda.CLP)

    # --- Características ---
    descripcion = models.TextField("descripción comercial", blank=True)
    dormitorios = models.PositiveSmallIntegerField(null=True, blank=True)
    banos = models.PositiveSmallIntegerField("baños", null=True, blank=True)
    estacionamientos = models.PositiveSmallIntegerField(null=True, blank=True)
    superficie_util = models.DecimalField("superficie útil (m²)", max_digits=10, decimal_places=2,
                                          null=True, blank=True)
    superficie_total = models.DecimalField("superficie total (m²)", max_digits=10, decimal_places=2,
                                           null=True, blank=True)
    caracteristicas = models.TextField("otras características", blank=True,
                                       help_text="Una por línea. Ej.: Bodega, Logia, Piscina.")
    video_url = models.URLField("enlace de video (opcional)", blank=True)

    # --- Ubicación ---
    zona = models.CharField(max_length=10, choices=Zona.choices)
    comuna = models.CharField(max_length=80, help_text="Se muestra en el portal.")
    sector_publico = models.CharField("referencia pública", max_length=120, blank=True,
                                      help_text="Se muestra en el portal. Ej.: Cerca de av. principal. "
                                                "No escribir la dirección exacta.")
    direccion_exacta = models.CharField("dirección exacta (privada)", max_length=200,
                                        help_text="Nunca se muestra en el portal.")

    # --- Relaciones privadas ---
    propietario = models.ForeignKey("contactos.Contacto", on_delete=models.PROTECT,
                                    related_name="propiedades")
    arrendatario = models.ForeignKey("contactos.Contacto", on_delete=models.SET_NULL,
                                     related_name="arriendos", null=True, blank=True,
                                     help_text="Arrendatario actual, si corresponde.")

    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.BORRADOR)
    publicada_desde = models.DateTimeField("publicada desde", null=True, blank=True, editable=False,
                                           help_text="Primera publicación en el portal (para días en mercado).")

    class Meta:
        ordering = ["-actualizado"]
        verbose_name = "propiedad"
        verbose_name_plural = "propiedades"

    def __str__(self):
        return f"{self.codigo or 'Nueva'} · {self.titulo}"

    def get_absolute_url(self):
        return reverse("propiedades:detalle", args=[self.pk])

    @property
    def publicada(self):
        return self.estado == self.Estado.DISPONIBLE

    @property
    def foto_principal(self):
        fotos = list(self.fotos.all())
        return fotos[0] if fotos else None

    def tiene_fotos_de_solicitud(self):
        from captacion.models import fotos_solicitud_pendientes
        return fotos_solicitud_pendientes(self).exists()

    def errores_para_publicar(self):
        errores = []
        if not self.precio:
            errores.append("Debe registrar un precio antes de publicar.")
        if not self.descripcion.strip():
            errores.append("Debe escribir una descripción comercial antes de publicar.")
        if not self.pk or not (self.fotos.exists() or self.tiene_fotos_de_solicitud()):
            errores.append("Debe subir al menos una fotografía antes de publicar.")
        return errores

    def clean(self):
        if self.operacion == self.Operacion.ARRIENDO and not self.modalidad_arriendo:
            raise ValidationError({"modalidad_arriendo": "Indica si el arriendo es permanente o temporal."})
        if self.operacion == self.Operacion.VENTA:
            self.modalidad_arriendo = ""
        if self.estado == self.Estado.DISPONIBLE:
            errores = self.errores_para_publicar()
            if errores:
                raise ValidationError(errores)

    def save(self, *args, **kwargs):
        if self.estado == self.Estado.DISPONIBLE and self.publicada_desde is None:
            from django.utils import timezone
            self.publicada_desde = timezone.now()
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = list(kwargs["update_fields"]) + ["publicada_desde"]
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f"MM-{self.pk:04d}"
            super().save(update_fields=["codigo"])


def ruta_foto(instancia, nombre):
    return f"propiedades/{instancia.propiedad_id}/{nombre_aleatorio(nombre)}"


class FotoPropiedad(models.Model):
    propiedad = models.ForeignKey(Propiedad, on_delete=models.CASCADE, related_name="fotos")
    imagen = models.ImageField(
        upload_to=ruta_foto,
        validators=[FileExtensionValidator(EXTENSIONES_FOTO), TamanoMaximoValidator(settings.MAX_FOTO_MB)],
    )
    es_principal = models.BooleanField("foto principal", default=False)
    orden = models.PositiveSmallIntegerField(default=0)
    subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-es_principal", "orden", "id"]
        verbose_name = "fotografía"

