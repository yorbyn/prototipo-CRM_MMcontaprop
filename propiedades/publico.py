from django.db.models import Prefetch

from .models import FotoPropiedad, Propiedad

CAMPOS_PUBLICOS = (
    "id", "codigo", "titulo", "tipo", "operacion", "modalidad_arriendo",
    "precio", "moneda", "descripcion", "dormitorios", "banos", "estacionamientos",
    "superficie_util", "superficie_total", "caracteristicas", "video_url",
    "zona", "comuna", "sector_publico", "estado", "actualizado",
)


def propiedades_publicas():
    return (
        Propiedad.objects.filter(estado=Propiedad.Estado.DISPONIBLE)
        .only(*CAMPOS_PUBLICOS)
        .prefetch_related(Prefetch("fotos", queryset=FotoPropiedad.objects.only("id", "imagen", "propiedad_id", "es_principal", "orden")))
    )


def ficha_publica(p):
    fotos = [f.imagen.url for f in p.fotos.all()]
    return {
        "codigo": p.codigo,
        "titulo": p.titulo,
        "tipo": p.get_tipo_display(),
        "operacion": p.get_operacion_display(),
        "es_arriendo": p.operacion == Propiedad.Operacion.ARRIENDO,
        "modalidad_arriendo": p.get_modalidad_arriendo_display() if p.modalidad_arriendo else "",
        "precio": p.precio,
        "moneda": p.moneda,
        "descripcion": p.descripcion,
        "dormitorios": p.dormitorios,
        "banos": p.banos,
        "estacionamientos": p.estacionamientos,
        "superficie_util": p.superficie_util,
        "superficie_total": p.superficie_total,
        "caracteristicas": p.caracteristicas,
        "video_url": p.video_url,
        "zona": p.get_zona_display(),
        "comuna": p.comuna,
        "sector_publico": p.sector_publico,
        "fotos": fotos,
        "foto_principal": fotos[0] if fotos else None,
    }
