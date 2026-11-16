from decimal import Decimal, InvalidOperation

from django import template

from core.validators import normalizar_rut

register = template.Library()


def _miles(entero):
    return f"{entero:,}".replace(",", ".")


@register.filter
def precio(valor, moneda="CLP"):
    """Formatea un precio: '$ 120.000.000' o 'UF 4.500,50'."""
    if valor in (None, ""):
        return "Precio a consultar"
    try:
        valor = Decimal(valor)
    except (InvalidOperation, TypeError):
        return valor
    if moneda == "UF":
        valor = valor.quantize(Decimal("0.01"))
        entero = int(valor)
        decimales = int((valor - entero) * 100)
        texto = _miles(entero)
        if decimales:
            texto += f",{decimales:02d}"
        return f"UF {texto}"
    return f"$ {_miles(int(round(valor)))}"


@register.filter
def rut(valor):
    """Formatea un RUT almacenado como '12345678-9' -> '12.345.678-9'."""
    r = normalizar_rut(valor)
    if not r or "-" not in r:
        return valor or ""
    cuerpo, dv = r.split("-")
    return f"{_miles(int(cuerpo))}-{dv}"


@register.filter
def lineas(valor):
    """Divide un texto en líneas no vacías."""
    return [l.strip() for l in (valor or "").splitlines() if l.strip()]


@register.simple_tag(takes_context=True)
def url_con(context, **kwargs):
    """Conserva los parámetros GET actuales y reemplaza los indicados (paginación)."""
    params = context["request"].GET.copy()
    for k, v in kwargs.items():
        params[k] = v
    return "?" + params.urlencode()
