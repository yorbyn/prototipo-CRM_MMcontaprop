"""
Cruce entre preferencias de búsqueda y propiedades.

Una propiedad calza con una preferencia cuando coincide la operación y, si la
preferencia los indica, el tipo, la zona, los dormitorios mínimos y el rango de
precio. Los campos vacíos de la preferencia significan «cualquiera». El precio
solo se compara en la misma moneda (no se convierte UF a pesos); una propiedad
sin precio no calza con una preferencia que tenga rango de precio.
"""
from django.db.models import Q

from contactos.models import PreferenciaBusqueda
from propiedades.models import Propiedad

from .models import Oportunidad

# Propiedades que todavía se pueden ofrecer a un interesado.
ESTADOS_NO_OFRECIBLES = (Propiedad.Estado.ANULADA, Propiedad.Estado.VENDIDA, Propiedad.Estado.ARRENDADA)


def _filtro_propiedades(pref):
    q = Q(operacion=pref.operacion)
    if pref.tipo:
        q &= Q(tipo=pref.tipo)
    if pref.zona:
        q &= Q(zona=pref.zona)
    if pref.dormitorios_min:
        q &= Q(dormitorios__gte=pref.dormitorios_min)
    if pref.tiene_precio:
        q &= Q(moneda=pref.moneda, precio__isnull=False)
        if pref.precio_min is not None:
            q &= Q(precio__gte=pref.precio_min)
        if pref.precio_max is not None:
            q &= Q(precio__lte=pref.precio_max)
    return q


def _abiertas_por(campo, **filtro):
    return {getattr(o, campo): o for o in Oportunidad.objects.filter(etapa__in=Oportunidad.ABIERTAS, **filtro)}


def propiedades_para(contacto, limite=30):
    """Propiedades publicadas que calzan con alguna preferencia del interesado.
    Devuelve [{"propiedad", "oportunidad" (abierta, si existe)}]."""
    preferencias = list(contacto.preferencias.all())
    if not preferencias or not contacto.es_interesado:
        return []
    q = Q()
    for pref in preferencias:
        q |= _filtro_propiedades(pref)
    propiedades = (Propiedad.objects.filter(q, estado=Propiedad.Estado.DISPONIBLE)
                   .exclude(propietario=contacto).order_by("-actualizado")[:limite])
    abiertas = _abiertas_por("propiedad_id", contacto=contacto)
    return [{"propiedad": p, "oportunidad": abiertas.get(p.pk)} for p in propiedades]


def interesados_para(propiedad, limite=50):
    """Interesados con alguna preferencia que calza con la propiedad (útil cuando
    entra una propiedad nueva). Devuelve [{"contacto", "preferencia", "oportunidad"}]."""
    if propiedad.estado in ESTADOS_NO_OFRECIBLES:
        return []
    p = propiedad
    q = Q(operacion=p.operacion) & (Q(tipo__isnull=True) | Q(tipo=p.tipo)) & (Q(zona="") | Q(zona=p.zona))
    q &= Q(dormitorios_min__isnull=True) | Q(dormitorios_min=0) | (
        Q(dormitorios_min__lte=p.dormitorios) if p.dormitorios is not None else Q(pk__in=[]))
    sin_precio = Q(precio_min__isnull=True, precio_max__isnull=True)
    if p.precio is None:
        q &= sin_precio
    else:
        en_rango = (Q(moneda=p.moneda)
                    & (Q(precio_min__isnull=True) | Q(precio_min__lte=p.precio))
                    & (Q(precio_max__isnull=True) | Q(precio_max__gte=p.precio)))
        q &= sin_precio | en_rango
    preferencias = (PreferenciaBusqueda.objects.filter(q, contacto__es_interesado=True)
                    .exclude(contacto_id=p.propietario_id)
                    .select_related("contacto").order_by("contacto__nombre", "id"))
    abiertas = _abiertas_por("contacto_id", propiedad=p)
    resultado, vistos = [], set()
    for pref in preferencias:
        if pref.contacto_id in vistos:
            continue
        vistos.add(pref.contacto_id)
        resultado.append({"contacto": pref.contacto, "preferencia": pref,
                          "oportunidad": abiertas.get(pref.contacto_id)})
        if len(resultado) >= limite:
            break
    return resultado

