"""
Indicadores del panel y exportación CSV.

Período: por fecha de creación (oportunidades, solicitudes), de cierre
(conversión) o de registro de la operación (comisiones y días en mercado).
Los montos se suman por moneda (CLP y UF por separado; no se convierten).
"""
import csv
from datetime import datetime, time
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.utils import timezone

from captacion.models import Encargo, SolicitudCaptacion
from propiedades.models import Propiedad

from .models import Operacion, Oportunidad


def rango(desde, hasta):
    """Fechas -> datetimes con zona horaria [inicio del día desde, fin del día hasta]."""
    tz = timezone.get_current_timezone()
    return (timezone.make_aware(datetime.combine(desde, time.min), tz),
            timezone.make_aware(datetime.combine(hasta, time.max), tz))


def _promedio(valores):
    valores = [v for v in valores if v is not None]
    return round(sum(valores) / len(valores)) if valores else None


def calcular(desde, hasta):
    inicio, fin = rango(desde, hasta)

    # --- Embudo: oportunidades creadas en el período, por etapa actual ---
    ops = Oportunidad.objects.filter(creado__range=(inicio, fin))
    por_etapa = dict(ops.order_by().values_list("etapa").annotate(n=Count("id")))
    total_ops = sum(por_etapa.values())
    # «Alcanzó la etapa»: cuenta las que están en esa etapa o más adelante (las
    # perdidas no se pueden ubicar con certeza, se informan aparte).
    orden = [Oportunidad.Etapa.NUEVA, Oportunidad.Etapa.CONTACTADO, Oportunidad.Etapa.VISITA,
             Oportunidad.Etapa.NEGOCIACION, Oportunidad.Etapa.GANADA]
    embudo = []
    for i, etapa in enumerate(orden):
        alcanzo = sum(por_etapa.get(e, 0) for e in orden[i:])
        if etapa == Oportunidad.Etapa.NUEVA:
            alcanzo += por_etapa.get(Oportunidad.Etapa.PERDIDA, 0)
        embudo.append({"etapa": etapa.label, "clave": etapa.value, "actual": por_etapa.get(etapa, 0),
                       "alcanzo": alcanzo})
    maximo = max([e["alcanzo"] for e in embudo] + [1])
    for e in embudo:
        e["pct"] = round(100 * e["alcanzo"] / maximo)
    por_origen = [{"origen": Oportunidad.Origen(o).label, "total": n}
                  for o, n in ops.order_by().values_list("origen").annotate(n=Count("id")).order_by("-n")]
    perdidas = por_etapa.get(Oportunidad.Etapa.PERDIDA, 0)

    # --- Conversión: oportunidades cerradas en el período ---
    cerradas = Oportunidad.objects.filter(cerrada_en__range=(inicio, fin))
    ganadas = cerradas.filter(etapa=Oportunidad.Etapa.GANADA).count()
    perdidas_cerradas = cerradas.filter(etapa=Oportunidad.Etapa.PERDIDA).count()
    conversion = round(100 * ganadas / (ganadas + perdidas_cerradas)) if (ganadas + perdidas_cerradas) else None
    motivos = list(cerradas.filter(etapa=Oportunidad.Etapa.PERDIDA).order_by("-cerrada_en")
                   .values_list("motivo_perdida", flat=True)[:5])

    # --- Captaciones ---
    sols = SolicitudCaptacion.objects.filter(creado__range=(inicio, fin))
    captaciones = sols.aggregate(
        total=Count("id"),
        aceptadas=Count("id", filter=Q(estado=SolicitudCaptacion.Estado.ACEPTADA)),
        rechazadas=Count("id", filter=Q(estado=SolicitudCaptacion.Estado.RECHAZADA)),
        pendientes=Count("id", filter=Q(estado=SolicitudCaptacion.Estado.PENDIENTE)),
        web=Count("id", filter=Q(origen=SolicitudCaptacion.Origen.WEB)),
    )
    encargos = Encargo.objects.filter(creado__range=(inicio, fin)).aggregate(
        total=Count("id"), exclusivos=Count("id", filter=Q(exclusividad=True)))

    # --- Operaciones y comisiones (operaciones vigentes registradas en el período) ---
    operaciones = (Operacion.objects.filter(estado=Operacion.Estado.VIGENTE, creado__range=(inicio, fin))
                   .select_related("propiedad"))
    comisiones = []
    for moneda in ("CLP", "UF"):
        qs = operaciones.filter(comision_moneda=moneda)
        datos = qs.aggregate(total=Sum("comision_monto"),
                             pagada=Sum("comision_monto", filter=Q(comision_pagada=True)))
        if datos["total"] is not None:
            datos["pendiente"] = datos["total"] - (datos["pagada"] or Decimal("0"))
            datos["moneda"] = moneda
            datos["pagada"] = datos["pagada"] or Decimal("0")
            comisiones.append(datos)
    n_ventas = operaciones.filter(tipo=Propiedad.Operacion.VENTA).count()
    n_arriendos = operaciones.filter(tipo=Propiedad.Operacion.ARRIENDO).count()

    # --- Días en mercado ---
    cerradas_dias = [dias_en_mercado(o.propiedad, o) for o in operaciones]
    hoy = timezone.localdate()
    disponibles = Propiedad.objects.filter(estado=Propiedad.Estado.DISPONIBLE, publicada_desde__isnull=False)
    disponibles_dias = [(hoy - timezone.localtime(p.publicada_desde).date()).days for p in disponibles]

    return {
        "total_ops": total_ops, "embudo": embudo, "por_origen": por_origen, "perdidas": perdidas,
        "ganadas": ganadas, "perdidas_cerradas": perdidas_cerradas, "conversion": conversion, "motivos": motivos,
        "captaciones": captaciones, "encargos": encargos,
        "comisiones": comisiones, "n_ventas": n_ventas, "n_arriendos": n_arriendos,
        "dias_cierre": _promedio(cerradas_dias), "n_dias_cierre": len([d for d in cerradas_dias if d is not None]),
        "dias_disponibles": _promedio(disponibles_dias), "n_disponibles": len(disponibles_dias),
    }


def dias_en_mercado(propiedad, operacion=None):
    """Días desde la primera publicación hasta el cierre (o hasta hoy si sigue disponible)."""
    if propiedad.publicada_desde is None:
        return None
    inicio = timezone.localtime(propiedad.publicada_desde).date()
    fin = operacion.fecha_cierre if operacion is not None else timezone.localdate()
    return max((fin - inicio).days, 0)


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def _celda(valor):
    """Convierte un valor al formato chileno para la planilla: Sí/No, coma decimal y fechas dd-mm-aaaa."""
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, Decimal):
        return f"{valor:f}".replace(".", ",")
    if hasattr(valor, "strftime"):
        if isinstance(valor, datetime):
            valor = timezone.localtime(valor)
            return valor.strftime("%d-%m-%Y %H:%M")
        return valor.strftime("%d-%m-%Y")
    return str(valor).replace("\r", " ").replace("\n", " ")  # cada registro en una sola línea


def respuesta_csv(nombre, encabezados, filas):
    """CSV en UTF-8 con BOM y punto y coma: abre bien en Excel con configuración chilena."""
    respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'  # se descarga como archivo
    respuesta.write("\ufeff")  # BOM: le indica a Excel que el archivo está en UTF-8 (tildes y ñ)
    escritor = csv.writer(respuesta, delimiter=";")
    escritor.writerow(encabezados)
    for fila in filas:
        escritor.writerow([_celda(v) for v in fila])
    return respuesta


def csv_oportunidades(desde, hasta):
    inicio, fin = rango(desde, hasta)
    qs = (Oportunidad.objects.filter(creado__range=(inicio, fin))
          .select_related("contacto", "propiedad").order_by("creado"))
    return ["N°", "Creada", "Interesado", "Correo", "Teléfono", "Propiedad", "Título", "Origen", "Etapa",
            "Cerrada", "Motivo de pérdida"], (
        [o.pk, o.creado, o.contacto.nombre, o.contacto.email, o.contacto.telefono,
         o.propiedad.codigo if o.propiedad_id else "", o.propiedad.titulo if o.propiedad_id else "",
         o.get_origen_display(), o.get_etapa_display(), o.cerrada_en, o.motivo_perdida] for o in qs)


def csv_operaciones(desde, hasta):
    inicio, fin = rango(desde, hasta)
    qs = (Operacion.objects.filter(creado__range=(inicio, fin))
          .select_related("propiedad", "oportunidad__contacto").order_by("creado"))
    return ["N°", "Registrada", "Estado", "Tipo", "Propiedad", "Cliente", "Precio final", "Moneda", "Comisión",
            "Moneda comisión", "Comisión pagada", "Fecha pago", "Promesa", "Escritura", "Firma contrato",
            "Días en mercado"], (
        [o.pk, o.creado, o.get_estado_display(), o.get_tipo_display(), o.propiedad.codigo,
         o.oportunidad.contacto.nombre, o.precio_final, o.moneda, o.comision_monto, o.comision_moneda,
         o.comision_pagada, o.fecha_pago_comision, o.fecha_promesa, o.fecha_escritura, o.fecha_firma_contrato,
         dias_en_mercado(o.propiedad, o)] for o in qs)


def csv_propiedades():
    qs = Propiedad.objects.select_related("propietario", "tipo").order_by("codigo")
    return ["Código", "Título", "Tipo", "Operación", "Estado", "Precio", "Moneda", "Comuna", "Zona",
            "Propietario", "Publicada desde", "Días en mercado (disponibles)"], (
        [p.codigo, p.titulo, p.tipo.nombre, p.get_operacion_display(), p.get_estado_display(), p.precio,
         p.moneda, p.comuna, p.get_zona_display(), p.propietario.nombre, p.publicada_desde,
         dias_en_mercado(p) if p.estado == Propiedad.Estado.DISPONIBLE else None] for p in qs)
