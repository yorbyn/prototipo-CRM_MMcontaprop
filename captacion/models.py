"""
Captación de propiedades.

- SolicitudCaptacion: un propietario ofrece su inmueble (desde el portal o ingresada a mano).
  La administradora la evalúa; al aceptarla se crea o reutiliza el contacto (por RUT o correo)
  y se crea la propiedad en borrador.
- Encargo: el encargo de corretaje de una propiedad (comisión, exclusividad, inicio y vencimiento).
- FotoSolicitud: fotos que envía el propietario. Son privadas hasta que la propiedad se publica.

Todo lo que llega desde el portal queda «por evaluar»: nada se crea ni se publica sin la administradora.
"""
import os
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Max
from django.urls import reverse
from django.utils import timezone

from actividades.models import Actividad
from contactos.models import Contacto
from core.models import Auditado
from core.validators import (
    EXTENSIONES_FOTO,
    TamanoMaximoValidator,
    almacenamiento_privado,
    nombre_aleatorio,
    normalizar_rut,
    validar_rut,
)
from propiedades.models import FotoPropiedad, Propiedad, TipoPropiedad


class SolicitudCaptacion(Auditado):
    class Origen(models.TextChoices):
        WEB = "web", "Portal web"
        MANUAL = "manual", "Ingreso manual"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Por evaluar"
        ACEPTADA = "aceptada", "Aceptada"
        RECHAZADA = "rechazada", "Rechazada"

    origen = models.CharField(max_length=10, choices=Origen.choices, default=Origen.MANUAL, editable=False)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE, editable=False)

    # --- Datos del propietario (privados) ---
    nombre = models.CharField("nombre completo", max_length=150)
    rut = models.CharField("RUT", max_length=12, blank=True, validators=[validar_rut],
                           help_text="Ej.: 12.345.678-5. Necesario para registrar al propietario.")
    email = models.EmailField("correo electrónico", blank=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)

    # --- Datos del inmueble ---
    tipo = models.ForeignKey(TipoPropiedad, on_delete=models.PROTECT, related_name="solicitudes",
                             verbose_name="tipo de inmueble")
    operacion = models.CharField("operación", max_length=10, choices=Propiedad.Operacion.choices)
    modalidad_arriendo = models.CharField("modalidad de arriendo", max_length=12, blank=True,
                                          choices=Propiedad.ModalidadArriendo.choices)
    zona = models.CharField(max_length=10, choices=Propiedad.Zona.choices)
    comuna = models.CharField(max_length=80)
    direccion = models.CharField("dirección del inmueble", max_length=200,
                                 help_text="Es privada: nunca se publica en el portal.")
    dormitorios = models.PositiveSmallIntegerField(null=True, blank=True,
                                                   validators=[MaxValueValidator(50)])
    banos = models.PositiveSmallIntegerField("baños", null=True, blank=True,
                                             validators=[MaxValueValidator(50)])
    superficie_util = models.DecimalField("superficie útil (m²)", max_digits=10, decimal_places=2,
                                          null=True, blank=True, validators=[MinValueValidator(1)])
    superficie_total = models.DecimalField("superficie total (m²)", max_digits=10, decimal_places=2,
                                           null=True, blank=True, validators=[MinValueValidator(1)])
    precio_esperado = models.DecimalField("precio esperado", max_digits=14, decimal_places=2,
                                          null=True, blank=True, validators=[MinValueValidator(1)])
    moneda = models.CharField(max_length=3, choices=Propiedad.Moneda.choices, default=Propiedad.Moneda.CLP)
    comentarios = models.TextField("comentarios del propietario", blank=True, max_length=2000)

    # --- Evaluación (solo CRM) ---
    observaciones = models.TextField("observaciones internas", blank=True)
    contacto = models.ForeignKey("contactos.Contacto", on_delete=models.SET_NULL, null=True, blank=True,
                                 editable=False, related_name="solicitudes_captacion")
    propiedad = models.OneToOneField(Propiedad, on_delete=models.SET_NULL, null=True, blank=True,
                                     editable=False, related_name="solicitud_captacion")

    class Meta:
        ordering = ["-creado"]
        verbose_name = "solicitud de captación"
        verbose_name_plural = "solicitudes de captación"

    def __str__(self):
        return f"Solicitud #{self.pk} · {self.nombre}"

    def get_absolute_url(self):
        return reverse("captacion:detalle", args=[self.pk])

    @property
    def pendiente(self):
        return self.estado == self.Estado.PENDIENTE

    def clean(self):
        # Se guardan siempre igual: RUT «12345678-K», correo en minúsculas y comuna sin espacios dobles.
        self.rut = normalizar_rut(self.rut)
        self.email = (self.email or "").strip().lower()
        self.comuna = " ".join((self.comuna or "").split())
        if not (self.email or self.telefono):
            raise ValidationError("Indique al menos un correo o un teléfono de contacto.")
        if self.operacion == Propiedad.Operacion.VENTA:
            self.modalidad_arriendo = ""
        if self.superficie_util and self.superficie_total and self.superficie_util > self.superficie_total:
            raise ValidationError({"superficie_util": "La superficie útil no puede superar la total."})

    # ------------------------------------------------------------------
    # Evaluación
    # ------------------------------------------------------------------

    def buscar_contacto(self):
        """Contacto existente para esta solicitud: primero por RUT, luego por correo.

        Devuelve (contacto o None, error o None). Si el correo coincide con una ficha
        que tiene OTRO RUT, no se adivina: se informa el conflicto."""
        if self.rut:
            por_rut = Contacto.objects.filter(rut=self.rut).first()
            if por_rut:
                return por_rut, None
        if self.email:
            por_email = list(Contacto.objects.filter(email__iexact=self.email)[:2])
            if len(por_email) > 1:
                return None, ("Hay más de un contacto con el correo de la solicitud. "
                              "Agregue el RUT a la solicitud para identificar al propietario.")
            if por_email:
                contacto = por_email[0]
                if self.rut and contacto.rut and contacto.rut != self.rut:
                    return None, (f"El correo pertenece a «{contacto}», que tiene otro RUT. "
                                  "Revise los datos de la solicitud antes de aceptarla.")
                return contacto, None
        return None, None

    def aceptar(self):
        """Crea o reutiliza el contacto propietario y crea la propiedad en borrador.
        Devuelve la propiedad creada. Lanza ValidationError si no se puede aceptar."""
        if not self.pendiente:
            raise ValidationError("Esta solicitud ya fue evaluada.")
        contacto, error = self.buscar_contacto()
        if error:
            raise ValidationError(error)

        # transaction.atomic(): o se guarda todo (contacto, propiedad y solicitud) o nada.
        with transaction.atomic():
            if contacto is None:
                if not self.rut:
                    raise ValidationError("Para registrar al propietario se necesita su RUT. "
                                          "Edite la solicitud y agréguelo.")
                contacto = Contacto.objects.create(nombre=self.nombre, rut=self.rut, email=self.email,
                                                   telefono=self.telefono, es_propietario=True)
                reutilizado = False
            else:
                # Se completa la ficha existente sin sobrescribir datos ya registrados.
                if not contacto.rut:
                    if not self.rut:
                        raise ValidationError(f"«{contacto}» ya está registrado pero no tiene RUT. "
                                              "Agregue el RUT a la solicitud para marcarlo como propietario.")
                    if Contacto.objects.filter(rut=self.rut).exclude(pk=contacto.pk).exists():
                        raise ValidationError("El RUT de la solicitud pertenece a otro contacto.")
                    contacto.rut = self.rut
                contacto.es_propietario = True
                if not contacto.telefono and self.telefono:
                    contacto.telefono = self.telefono
                if not contacto.email and self.email:
                    contacto.email = self.email
                contacto.save()
                reutilizado = True

            propiedad = Propiedad.objects.create(
                titulo=f"{self.tipo.nombre} en {self.comuna}"[:120],
                tipo=self.tipo, operacion=self.operacion, modalidad_arriendo=self.modalidad_arriendo,
                precio=self.precio_esperado, moneda=self.moneda,
                dormitorios=self.dormitorios, banos=self.banos,
                superficie_util=self.superficie_util, superficie_total=self.superficie_total,
                zona=self.zona, comuna=self.comuna, direccion_exacta=self.direccion,
                propietario=contacto, estado=Propiedad.Estado.BORRADOR,
                # La descripción comercial la redacta la administradora: los comentarios
                # del propietario pueden traer datos privados.
                descripcion="",
            )

            self.estado = self.Estado.ACEPTADA
            self.contacto = contacto
            self.propiedad = propiedad
            self.save()

            Actividad.registrar_sistema(
                f"Propiedad creada en estado Borrador desde la solicitud de captación #{self.pk}.",
                contacto=contacto, propiedad=propiedad,
            )
            if reutilizado:
                Actividad.registrar_sistema(f"Solicitud de captación #{self.pk} aceptada; se reutilizó esta ficha.",
                                            contacto=contacto)
        return propiedad

    def rechazar(self):
        if not self.pendiente:
            raise ValidationError("Esta solicitud ya fue evaluada.")
        self.estado = self.Estado.RECHAZADA
        self.save()


class Encargo(Auditado):
    """Encargo de corretaje pactado con el propietario."""
    propiedad = models.ForeignKey(Propiedad, on_delete=models.PROTECT, related_name="encargos")
    comision_pct = models.DecimalField(
        "comisión (%)", max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("100"))],
        help_text="Porcentaje pactado. Ej.: 2 o 2,5",
    )
    exclusividad = models.BooleanField("con exclusividad", default=False)
    fecha_inicio = models.DateField("inicio")
    fecha_vencimiento = models.DateField("vencimiento")

    class Meta:
        ordering = ["-fecha_inicio", "-id"]
        verbose_name = "encargo de corretaje"
        verbose_name_plural = "encargos de corretaje"

    def __str__(self):
        return f"Encargo {self.comision_pct}% · {self.propiedad.codigo}"

    def clean(self):
        if self.fecha_inicio and self.fecha_vencimiento:
            if self.fecha_vencimiento <= self.fecha_inicio:
                raise ValidationError({"fecha_vencimiento": "El vencimiento debe ser posterior al inicio."})
            # Dos encargos de la misma propiedad no pueden tener fechas que se crucen.
            cruzados = Encargo.objects.filter(
                propiedad_id=self.propiedad_id,
                fecha_inicio__lte=self.fecha_vencimiento,
                fecha_vencimiento__gte=self.fecha_inicio,
            ).exclude(pk=self.pk)
            if cruzados.exists():
                raise ValidationError("Las fechas se cruzan con otro encargo de esta propiedad. "
                                      "Para renovar, el nuevo encargo debe comenzar después del vencimiento anterior.")

    @property
    def estado_vigencia(self):
        """«futuro», «vigente» o «vencido» (coincide con las clases CSS estado-...)."""
        hoy = timezone.localdate()
        if hoy < self.fecha_inicio:
            return "futuro"
        if hoy > self.fecha_vencimiento:
            return "vencido"
        return "vigente"

    @property
    def comision_texto(self):
        """2.50 -> '2,5'; 3.00 -> '3' (formato chileno)."""
        texto = f"{self.comision_pct:f}"
        if "." in texto:
            texto = texto.rstrip("0").rstrip(".")
        return texto.replace(".", ",")

    def resumen(self):
        exclusividad = "con exclusividad" if self.exclusividad else "sin exclusividad"
        return (f"comisión {self.comision_texto} %, {exclusividad}, del "
                f"{self.fecha_inicio:%d-%m-%Y} al {self.fecha_vencimiento:%d-%m-%Y}")


# ---------------------------------------------------------------------------
# Fotos enviadas con la solicitud: PRIVADAS hasta que la propiedad se publica
# ---------------------------------------------------------------------------

MAX_FOTOS_SOLICITUD = 6


def ruta_foto_solicitud(instancia, nombre):
    return f"captacion/{instancia.solicitud_id}/{nombre_aleatorio(nombre)}"


class FotoSolicitud(models.Model):
    """Foto que envía el propietario. Se guarda fuera de media/ (sin URL pública) y solo se ve
    en el CRM. Al publicar la propiedad se copia a la galería pública."""
    solicitud = models.ForeignKey(SolicitudCaptacion, on_delete=models.CASCADE, related_name="fotos")
    imagen = models.ImageField(
        upload_to=ruta_foto_solicitud, storage=almacenamiento_privado,
        validators=[FileExtensionValidator(EXTENSIONES_FOTO), TamanoMaximoValidator(settings.MAX_FOTO_MB)],
    )
    copiada_a = models.OneToOneField("propiedades.FotoPropiedad", on_delete=models.SET_NULL, null=True, blank=True,
                                     editable=False, related_name="origen_solicitud")
    subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "foto de la solicitud"
        verbose_name_plural = "fotos de la solicitud"


def fotos_solicitud_pendientes(propiedad):
    """Fotos privadas de la solicitud de origen que aún no pasan a la galería pública."""
    return FotoSolicitud.objects.filter(solicitud__propiedad=propiedad, copiada_a__isnull=True)


def publicar_fotos_solicitud(propiedad):
    """Copia a la galería pública (media/) las fotos privadas de la solicitud.
    Se llama al publicar la propiedad. Devuelve cuántas se copiaron."""
    pendientes = list(fotos_solicitud_pendientes(propiedad))
    orden = (propiedad.fotos.aggregate(m=Max("orden"))["m"] or 0) + 1
    sin_principal = not propiedad.fotos.filter(es_principal=True).exists()
    for i, foto in enumerate(pendientes):
        publica = FotoPropiedad(propiedad=propiedad, orden=orden + i, es_principal=sin_principal and i == 0)
        with foto.imagen.open("rb") as archivo:
            publica.imagen.save(os.path.basename(foto.imagen.name), File(archivo), save=False)
        publica.save()
        foto.copiada_a = publica
        foto.save()
    return len(pendientes)
