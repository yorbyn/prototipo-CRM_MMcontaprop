"""Limpieza de imágenes antes de publicarlas."""
from io import BytesIO

from django.core.files.base import ContentFile


def limpiar_imagen(archivo):
    """Devuelve una copia de la imagen SIN metadatos (EXIF, GPS, XMP, perfil ICC,
    comentarios JPEG, textos PNG, etc.), respetando su orientación. Las fotos de
    teléfono pueden traer la ubicación exacta del inmueble, que nunca debe publicarse.

    La copia se arma solo con los píxeles: no hereda ningún dato adicional del
    archivo original. Acepta un archivo subido o un archivo ya guardado."""
    from PIL import Image, ImageOps

    if hasattr(archivo, "open"):
        archivo.open("rb")
    archivo.seek(0)
    with Image.open(archivo) as original:
        formato = "PNG" if (original.format or "").upper() == "PNG" else "JPEG"
        img = ImageOps.exif_transpose(original)
        modo = ("RGBA" if "A" in img.getbands() else "RGB") if formato == "PNG" else "RGB"
        if img.mode == "L" and formato == "JPEG":
            modo = "L"
        if img.mode != modo:
            img = img.convert(modo)
        # Imagen nueva a partir de los píxeles: sin info, comentarios ni perfiles.
        limpia = Image.frombytes(modo, img.size, img.tobytes())
        salida = BytesIO()
        limpia.save(salida, format=formato, **({"quality": 90, "optimize": True} if formato == "JPEG" else {}))
    archivo.seek(0)
    return ContentFile(salida.getvalue(), name="foto.png" if formato == "PNG" else "foto.jpg")
