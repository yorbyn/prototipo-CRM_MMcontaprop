"""Validadores y utilidades compartidas."""
import os
import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible

# --------------------------------------------------------------------------
# RUT chileno
# --------------------------------------------------------------------------

def normalizar_rut(valor):
    """Convierte '12.345.678-k' en '12345678-K'. Devuelve '' si está vacío."""
    if not valor:
        return ""
    limpio = re.sub(r"[^0-9kK]", "", str(valor)).upper()
    if len(limpio) < 2:
        return limpio
    # Sin ceros a la izquierda: «01.234.567-4» y «1.234.567-4» son el mismo RUT.
    cuerpo = limpio[:-1].lstrip("0") or "0"
    return f"{cuerpo}-{limpio[-1]}"


def digito_verificador(cuerpo):
    suma, factor = 0, 2
    for d in reversed(cuerpo):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    return {11: "0", 10: "K"}.get(resto, str(resto))


def validar_rut(valor):
    rut = normalizar_rut(valor)
    if not rut:
        return
    cuerpo, _, dv = rut.partition("-")
    if not cuerpo.isdigit() or not (6 <= len(cuerpo) <= 8):
        raise ValidationError("El RUT no tiene un formato válido.")
    if digito_verificador(cuerpo) != dv:
        raise ValidationError("El dígito verificador del RUT no es correcto.")


# --------------------------------------------------------------------------
# Archivos
# --------------------------------------------------------------------------

@deconstructible
class TamanoMaximoValidator:
    """Rechaza archivos que superen `mb` megabytes."""

    def __init__(self, mb):
        self.mb = mb

    def __call__(self, archivo):
        if archivo and archivo.size > self.mb * 1024 * 1024:
            raise ValidationError(f"El archivo supera el máximo de {self.mb} MB.")

    def __eq__(self, otro):
        return isinstance(otro, TamanoMaximoValidator) and self.mb == otro.mb


EXTENSIONES_FOTO = ["jpg", "jpeg", "png"]
EXTENSIONES_DOCUMENTO = ["pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx"]


# YA NO LA USA NINGÚN MODELO. Se mantiene solo porque la nombran las migraciones antiguas
# (captacion/0001 y documentos/0001); se borra al regenerar las migraciones en el cierre.
# Revisaba los primeros bytes («firma») de cada tipo de archivo.
FIRMAS_ARCHIVO = {
    "pdf": (b"%PDF",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "docx": (b"PK\x03\x04",),
    "xlsx": (b"PK\x03\x04",),
    "doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    "xls": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
}


def validar_contenido_archivo(archivo):
    """Comprueba que el contenido real del archivo corresponde a su extensión."""
    if not archivo:
        return
    ext = os.path.splitext(archivo.name)[1].lower().lstrip(".")
    firmas = FIRMAS_ARCHIVO.get(ext)
    if not firmas:
        return  # la extensión la valida FileExtensionValidator
    archivo.seek(0)
    cabecera = archivo.read(8)
    archivo.seek(0)
    if not any(cabecera.startswith(f) for f in firmas):
        raise ValidationError("El contenido del archivo no corresponde a su extensión.")


class AlmacenamientoPrivado(FileSystemStorage):
    """Archivos fuera de MEDIA_ROOT y sin URL pública. La ruta se lee de
    settings.PRIVATE_MEDIA_ROOT en cada uso (permite cambiarla en pruebas)."""

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise ValueError("Los documentos privados no tienen URL pública.")


def almacenamiento_privado():
    return AlmacenamientoPrivado()


def nombre_aleatorio(nombre_original):
    """Nombre de archivo no adivinable, conservando la extensión."""
    ext = os.path.splitext(nombre_original)[1].lower()
    return f"{uuid.uuid4().hex}{ext}"
