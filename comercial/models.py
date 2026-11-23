"""
Gestión comercial.

La OPORTUNIDAD es el eje del seguimiento: un negocio en curso entre un interesado y una
propiedad, que avanza por etapas (nueva, contactado, visita, negociación) hasta ganarse
(se registra la OPERACIÓN) o perderse con motivo. Las OFERTAS se registran dentro de ella.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone

from actividades.models import Actividad
from contactos.models import Contacto
from core.models import Auditado
from core.templatetags.formato import precio
from propiedades.models import Propiedad

# Propiedades que ya no se pueden ofrecer a un interesado.
ESTADOS_NO_OFRECIBLES = (Propiedad.Estado.ANULADA, Propiedad.Estado.VENDIDA, Propiedad.Estado.ARRENDADA)


class Oportunidad(Auditado):
    class Etapa(models.TextChoices):
        NUEVA = "nueva", "Nueva"
        CONTACTADO = "contactado", "Contactado"
        VISITA = "visita", "Visita"
        NEGOCIACION = "negociacion", "Negociación"
        GANADA = "ganada", "Ganada"
        PERDIDA = "perdida", "Perdida"

    class Origen(models.TextChoices):
        PORTAL = "portal", "Consulta en el portal"
        CONTACTO = "contacto", "Página de contacto"
        CRUCE = "cruce", "Cruce de propiedades"
        MANUAL = "manual", "Ingreso manual"

    ABIERTAS = (Etapa.NUEVA, Etapa.CONTACTADO, Etapa.VISITA, Etapa.NEGOCIACION)
    # Etapas que exigen tener una propiedad asignada.
    CON_PROPIEDAD = (Etapa.VISITA, Etapa.NEGOCIACION, Etapa.GANADA)

    contacto = models.ForeignKey("contactos.Contacto", on_delete=models.PROTECT, related_name="oportunidades",
                                 verbose_name="interesado")
    propiedad = models.ForeignKey("propiedades.Propiedad", on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="oportunidades",
                                  help_text="Puede quedar vacía si el interesado aún no elige propiedad.")
    etapa = models.CharField(max_length=12, choices=Etapa.choices, default=Etapa.NUEVA, editable=False)
    origen = models.CharField(max_length=10, choices=Origen.choices, default=Origen.MANUAL, editable=False)
    mensaje = models.TextField("mensaje inicial", blank=True, max_length=2000)
    motivo_perdida = models.TextField("motivo de pérdida", blank=True, editable=False)
    cerrada_en = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-creado", "-id"]
        verbose_name = "oportunidad"
        verbose_name_plural = "oportunidades"

    def __str__(self):
        destino = self.propiedad.codigo if self.propiedad_id else "sin propiedad"
        return f"{self.contacto} · {destino}"

    def get_absolute_url(self):
        return reverse("comercial:detalle", args=[self.pk])

    @property
    def abierta(self):
        return self.etapa in self.ABIERTAS

    @property
    def operacion(self):
        """La operación vigente; si no hay, la última anulada (o None)."""
        return (self.operaciones.filter(estado=Operacion.Estado.VIGENTE).first()
                or self.operaciones.order_by("-pk").first())

    def clean(self):
        if self.propiedad_id and self.propiedad.estado == Propiedad.Estado.ANULADA:
            raise ValidationError({"propiedad": "No se pueden crear oportunidades sobre una propiedad anulada."})

    def _registrar(self, texto):
        """Deja el hecho en el historial de la oportunidad (y de su contacto y propiedad)."""
        Actividad.registrar_sistema(texto, oportunidad=self)

    # ------------------------------------------------------------------
    # Cambios de etapa (siempre quedan en el historial)
    # ------------------------------------------------------------------

    def cambiar_etapa(self, nueva):
        """Devuelve True si la etapa cambió. Lanza ValidationError si no se puede."""
        if not self.abierta:
            raise ValidationError("La oportunidad está cerrada.")
        if nueva not in self.ABIERTAS:
            raise ValidationError("Para ganar use «Registrar cierre»; para perder, indique el motivo.")
        if nueva in self.CON_PROPIEDAD and not self.propiedad_id:
            raise ValidationError("Asigne una propiedad antes de pasar a esa etapa.")
        if nueva == self.etapa:
            return False
        anterior = self.get_etapa_display()
        self.etapa = nueva
        self.save()
        self._registrar(f"Etapa cambiada de «{anterior}» a «{self.get_etapa_display()}».")
        return True

    def perder(self, motivo):
        motivo = (motivo or "").strip()
        if not self.abierta:
            raise ValidationError("La oportunidad ya está cerrada.")
        if not motivo:
            raise ValidationError("Indique el motivo por el que se perdió la oportunidad.")
        self.etapa = self.Etapa.PERDIDA
        self.motivo_perdida = motivo
        self.cerrada_en = timezone.now()
        self.save()
        self._registrar(f"Oportunidad perdida. Motivo: {motivo}")

    def asignar_propiedad(self, propiedad):
        if not self.abierta:
            raise ValidationError("La oportunidad está cerrada.")
        if propiedad.estado in ESTADOS_NO_OFRECIBLES:
            raise ValidationError("La propiedad no está disponible para nuevas oportunidades.")
        anterior = self.propiedad
        self.propiedad = propiedad
        self.save()
        if anterior is None:
            self._registrar(f"Propiedad asignada: {propiedad}.")
        else:
            self._registrar(f"Propiedad cambiada de {anterior.codigo} a {propiedad.codigo}.")

    # ------------------------------------------------------------------
    # Entrada desde el portal (consulta en una ficha o página «Contacto»)
    # ------------------------------------------------------------------

    @classmethod
    def desde_portal(cls, *, nombre, email, telefono="", mensaje, propiedad=None, origen=Origen.PORTAL):
        """Crea o reutiliza al contacto (por correo) como interesado y crea la oportunidad.
        Si ya tiene una abierta por la misma propiedad, el mensaje se agrega a esa y no se duplica.
        Devuelve (oportunidad, True si ya existía)."""
        email = (email or "").strip().lower()
        with transaction.atomic():
            contacto = Contacto.objects.filter(email__iexact=email).order_by("id").first()
            if contacto is None:
                contacto = Contacto.objects.create(nombre=nombre, email=email, telefono=telefono, es_interesado=True)
            else:
                # Se completa la ficha sin sobrescribir lo que ya tenía.
                contacto.es_interesado = True
                if not contacto.telefono and telefono:
                    contacto.telefono = telefono
                contacto.save()

            existente = None
            if propiedad is not None:
                existente = cls.objects.filter(contacto=contacto, propiedad=propiedad, etapa__in=cls.ABIERTAS).first()
            oportunidad = existente or cls.objects.create(contacto=contacto, propiedad=propiedad, origen=origen,
                                                          mensaje=mensaje)
            datos = " · ".join(x for x in (nombre, email, telefono) if x)
            oportunidad._registrar(f"{cls.Origen(origen).label}. Datos enviados: {datos}. Mensaje: {mensaje}")
        return oportunidad, existente is not None


class Oferta(Auditado):
    """Oferta del interesado o contraoferta del propietario dentro de una oportunidad."""

    class Tipo(models.TextChoices):
        OFERTA = "oferta", "Oferta del interesado"
        CONTRAOFERTA = "contraoferta", "Contraoferta del propietario"

    class Respuesta(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ACEPTADA = "aceptada", "Aceptada"
        RECHAZADA = "rechazada", "Rechazada"
        CONTRAOFERTADA = "contraofertada", "Contraofertada"

    oportunidad = models.ForeignKey(Oportunidad, on_delete=models.CASCADE, related_name="ofertas")
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.OFERTA)
    monto = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("1"))])
    moneda = models.CharField(max_length=3, choices=Propiedad.Moneda.choices, default="CLP")
    fecha = models.DateField(default=timezone.localdate)
    respuesta = models.CharField(max_length=14, choices=Respuesta.choices, default=Respuesta.PENDIENTE,
                                 editable=False)

    class Meta:
        ordering = ["fecha", "id"]
        verbose_name = "oferta"
        verbose_name_plural = "ofertas"

    def __str__(self):
        return f"{self.get_tipo_display()} {self.monto} {self.moneda}"

    def clean(self):
        if self.fecha and self.fecha > timezone.localdate():
            raise ValidationError({"fecha": "La fecha no puede ser futura."})

    def registrar(self):
        """Guarda la oferta, marca como contraofertada la pendiente de la otra parte,
        pasa la oportunidad a negociación si aún no lo estaba y deja constancia."""
        op = self.oportunidad
        if not op.abierta:
            raise ValidationError("La oportunidad está cerrada.")
        if not op.propiedad_id:
            raise ValidationError("Asigne una propiedad antes de registrar ofertas.")
        with transaction.atomic():
            otra_parte = self.Tipo.CONTRAOFERTA if self.tipo == self.Tipo.OFERTA else self.Tipo.OFERTA
            op.ofertas.filter(tipo=otra_parte, respuesta=self.Respuesta.PENDIENTE).update(
                respuesta=self.Respuesta.CONTRAOFERTADA)
            self.save()
            op._registrar(f"{self.get_tipo_display()} registrada: {precio(self.monto, self.moneda)} "
                          f"({self.fecha:%d-%m-%Y}).")
            if op.etapa in (Oportunidad.Etapa.NUEVA, Oportunidad.Etapa.CONTACTADO, Oportunidad.Etapa.VISITA):
                op.cambiar_etapa(Oportunidad.Etapa.NEGOCIACION)

    def responder(self, respuesta):
        if respuesta not in (self.Respuesta.ACEPTADA, self.Respuesta.RECHAZADA):
            raise ValidationError("Respuesta no válida.")
        if self.respuesta != self.Respuesta.PENDIENTE:
            raise ValidationError("Esta oferta ya tiene respuesta.")
        if not self.oportunidad.abierta:
            raise ValidationError("La oportunidad está cerrada.")
        self.respuesta = respuesta
        self.save()
        self.oportunidad._registrar(f"{self.get_tipo_display()} de {precio(self.monto, self.moneda)} "
                                    f"{self.get_respuesta_display().lower()}.")


class Operacion(Auditado):
    """Cierre de una oportunidad ganada: precio final, comisión, fechas clave y pago de la
    comisión. Como máximo una operación vigente por propiedad. Se anula; no se borra."""

    class Estado(models.TextChoices):
        VIGENTE = "vigente", "Vigente"
        ANULADA = "anulada", "Anulada"

    oportunidad = models.ForeignKey(Oportunidad, on_delete=models.PROTECT, related_name="operaciones", editable=False)
    propiedad = models.ForeignKey(Propiedad, on_delete=models.PROTECT, related_name="operaciones", editable=False)
    tipo = models.CharField(max_length=10, choices=Propiedad.Operacion.choices, editable=False)
    precio_final = models.DecimalField("precio final", max_digits=14, decimal_places=2,
                                       validators=[MinValueValidator(Decimal("1"))])
    moneda = models.CharField(max_length=3, choices=Propiedad.Moneda.choices, default="CLP")
    comision_monto = models.DecimalField("comisión", max_digits=14, decimal_places=2,
                                         validators=[MinValueValidator(Decimal("0"))])
    comision_moneda = models.CharField("moneda de la comisión", max_length=3, choices=Propiedad.Moneda.choices,
                                       default="CLP")
    fecha_promesa = models.DateField("fecha de promesa", null=True, blank=True)
    fecha_escritura = models.DateField("fecha de escritura", null=True, blank=True)
    fecha_firma_contrato = models.DateField("fecha de firma del contrato", null=True, blank=True)
    comision_pagada = models.BooleanField("comisión pagada", default=False)
    fecha_pago_comision = models.DateField("fecha de pago de la comisión", null=True, blank=True)
    estado = models.CharField(max_length=8, choices=Estado.choices, default=Estado.VIGENTE, editable=False)
    motivo_anulacion = models.TextField(blank=True, editable=False)

    class Meta:
        ordering = ["-creado", "-id"]
        verbose_name = "operación"
        verbose_name_plural = "operaciones"
        # La base de datos impide dos operaciones vigentes para la misma propiedad u oportunidad.
        # Si se anula, la oportunidad puede volver a cerrarse con una operación nueva.
        constraints = [
            models.UniqueConstraint(fields=["propiedad"], condition=models.Q(estado="vigente"),
                                    name="una_operacion_vigente_por_propiedad"),
            models.UniqueConstraint(fields=["oportunidad"], condition=models.Q(estado="vigente"),
                                    name="una_operacion_vigente_por_oportunidad"),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.propiedad.codigo}"

    def get_absolute_url(self):
        return self.oportunidad.get_absolute_url()

    @property
    def es_venta(self):
        return self.tipo == Propiedad.Operacion.VENTA

    @property
    def fecha_cierre(self):
        """Fecha del cierre: escritura o firma del contrato; si aún no la hay, la promesa o el registro."""
        return (self.fecha_escritura or self.fecha_firma_contrato or self.fecha_promesa
                or timezone.localtime(self.creado).date())

    def clean(self):
        if self.es_venta:
            self.fecha_firma_contrato = None
            if not (self.fecha_promesa or self.fecha_escritura):
                raise ValidationError("Indique la fecha de promesa o la de escritura.")
            if self.fecha_promesa and self.fecha_escritura and self.fecha_escritura < self.fecha_promesa:
                raise ValidationError({"fecha_escritura": "La escritura no puede ser anterior a la promesa."})
        else:
            self.fecha_promesa = self.fecha_escritura = None
            if not self.fecha_firma_contrato:
                raise ValidationError({"fecha_firma_contrato": "Indique la fecha de firma del contrato de arriendo."})
        if self.comision_pagada and not self.fecha_pago_comision:
            raise ValidationError({"fecha_pago_comision": "Indique la fecha en que se pagó la comisión."})
        if not self.comision_pagada:
            self.fecha_pago_comision = None
        if self.fecha_pago_comision and self.fecha_pago_comision > timezone.localdate():
            raise ValidationError({"fecha_pago_comision": "La fecha de pago no puede ser futura."})

    def resumen(self):
        return (f"precio final {precio(self.precio_final, self.moneda)}, "
                f"comisión {precio(self.comision_monto, self.comision_moneda)}"
                f"{' (pagada)' if self.comision_pagada else ''}")

    # ------------------------------------------------------------------

    @staticmethod
    def comision_sugerida(propiedad, precio_final):
        """Comisión según el encargo de corretaje vigente hoy. Devuelve (monto, encargo) o (None, None)."""
        if precio_final is None:
            return None, None
        hoy = timezone.localdate()
        encargo = propiedad.encargos.filter(fecha_inicio__lte=hoy, fecha_vencimiento__gte=hoy).first()
        if encargo is None:
            return None, None
        return (Decimal(precio_final) * encargo.comision_pct / 100).quantize(Decimal("0.01")), encargo

    def cerrar(self):
        """Registra el cierre: la oportunidad queda ganada y la propiedad, vendida o arrendada."""
        op = self.oportunidad
        propiedad = op.propiedad
        if not op.abierta:
            raise ValidationError("La oportunidad ya está cerrada.")
        if propiedad is None:
            raise ValidationError("La oportunidad no tiene propiedad.")
        if propiedad.estado in ESTADOS_NO_OFRECIBLES:
            raise ValidationError(f"La propiedad está {propiedad.get_estado_display().lower()}.")
        if propiedad.operaciones.filter(estado=self.Estado.VIGENTE).exists():
            raise ValidationError("La propiedad ya tiene una operación vigente.")

        # transaction.atomic(): o se guarda todo (operación, oportunidad y propiedad) o nada.
        with transaction.atomic():
            self.propiedad, self.tipo = propiedad, propiedad.operacion
            self.full_clean(exclude=["oportunidad", "propiedad"])
            self.save()

            op.etapa = Oportunidad.Etapa.GANADA
            op.cerrada_en = timezone.now()
            op.save()

            anterior = propiedad.get_estado_display()
            if self.es_venta:
                propiedad.estado = Propiedad.Estado.VENDIDA
            else:
                propiedad.estado = Propiedad.Estado.ARRENDADA
                propiedad.arrendatario = op.contacto
                op.contacto.es_arrendatario = True
                op.contacto.save()
            propiedad.save()

            op._registrar(f"Oportunidad ganada. Operación de {self.get_tipo_display().lower()} "
                          f"registrada: {self.resumen()}.")
            Actividad.registrar_sistema(f"Estado cambiado de «{anterior}» a «{propiedad.get_estado_display()}» "
                                        f"por el cierre de la oportunidad #{op.pk}.", propiedad=propiedad)
        return self

    def cerrar_otras_como_perdidas(self):
        """Marca como perdidas las demás oportunidades abiertas de la propiedad. Solo se hace
        cuando la administradora lo pide; nunca es automático. Devuelve cuántas cerró."""
        if self.estado != self.Estado.VIGENTE:
            raise ValidationError("La operación está anulada.")
        motivo = "Propiedad vendida." if self.es_venta else "Propiedad arrendada."
        otras = (Oportunidad.objects.filter(propiedad=self.propiedad, etapa__in=Oportunidad.ABIERTAS)
                 .exclude(pk=self.oportunidad_id))
        with transaction.atomic():
            for op in otras:
                op.perder(motivo)
        return len(otras)

    def anular(self, motivo):
        """Anula la operación: la oportunidad vuelve a negociación y la propiedad, a borrador.
        La administradora la vuelve a publicar a mano si corresponde."""
        motivo = (motivo or "").strip()
        if not motivo:
            raise ValidationError("Indique el motivo de la anulación.")
        if self.estado != self.Estado.VIGENTE:
            raise ValidationError("La operación ya está anulada.")
        with transaction.atomic():
            self.estado = self.Estado.ANULADA
            self.motivo_anulacion = motivo
            self.save()

            op = self.oportunidad
            op.etapa = Oportunidad.Etapa.NEGOCIACION
            op.cerrada_en = None
            op.save()

            propiedad = self.propiedad
            anterior = propiedad.get_estado_display()
            propiedad.estado = Propiedad.Estado.BORRADOR
            if not self.es_venta and propiedad.arrendatario_id == op.contacto_id:
                propiedad.arrendatario = None
            propiedad.save()

            op._registrar(f"Operación anulada. Motivo: {motivo}. La oportunidad vuelve a negociación.")
            Actividad.registrar_sistema(f"Estado cambiado de «{anterior}» a «{propiedad.get_estado_display()}» "
                                        f"por la anulación de la operación.", propiedad=propiedad)
