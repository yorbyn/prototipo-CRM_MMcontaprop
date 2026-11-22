import io
import os
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from contactos.models import Contacto

from .models import FotoPropiedad, Propiedad, TipoPropiedad


def imagen(nombre="foto.jpg"):
    """Una imagen JPG pequeña de prueba."""
    datos = io.BytesIO()
    Image.new("RGB", (40, 30), "purple").save(datos, "JPEG")
    return SimpleUploadedFile(nombre, datos.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())  # las fotos de prueba no van a media/
class PropiedadTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "admin@ejemplo.cl", "clave"))
        TipoPropiedad.objects.create(nombre="Casa")
        self.duena = Contacto.objects.create(nombre="Dueña", rut="11111111-1", es_propietario=True)
        self.datos = {"titulo": "Casa linda", "tipo": "casa", "operacion": "venta", "moneda": "CLP",
                      "propietario": self.duena.pk, "zona": "norte", "comuna": "Arica", "direccion_exacta": "Calle 1"}

    def crear(self):
        self.client.post(reverse("propiedades:propiedad_crear"), self.datos)
        return Propiedad.objects.get()

    def test_crear_queda_en_borrador_con_codigo(self):
        propiedad = self.crear()
        self.assertEqual((propiedad.codigo, propiedad.estado), ("MM-0001", Propiedad.Estado.BORRADOR))

    def test_arriendo_exige_modalidad(self):
        r = self.client.post(reverse("propiedades:propiedad_crear"), dict(self.datos, operacion="arriendo"))
        self.assertContains(r, "permanente o temporal")

    def test_no_se_publica_incompleta(self):
        propiedad = self.crear()
        self.client.post(reverse("propiedades:cambiar_estado", args=[propiedad.pk]), {"estado": "disponible"})
        propiedad.refresh_from_db()
        self.assertEqual(propiedad.estado, Propiedad.Estado.BORRADOR)

    def test_subir_varias_fotos_y_publicar(self):
        propiedad = self.crear()
        self.client.post(reverse("propiedades:subir_fotos", args=[propiedad.pk]), {"imagenes": [imagen("a.jpg"), imagen("b.jpg")]})
        self.assertEqual(propiedad.fotos.count(), 2)
        self.assertTrue(propiedad.fotos.first().es_principal)
        propiedad.precio, propiedad.descripcion = 100, "Linda"
        propiedad.save()
        self.client.post(reverse("propiedades:cambiar_estado", args=[propiedad.pk]), {"estado": "disponible"})
        propiedad.refresh_from_db()
        self.assertEqual(propiedad.estado, Propiedad.Estado.DISPONIBLE)
        self.assertIsNotNone(propiedad.publicada_desde)

    def test_foto_falsa_no_se_guarda(self):
        propiedad = self.crear()
        self.client.post(reverse("propiedades:subir_fotos", args=[propiedad.pk]),
                         {"imagenes": [imagen(), SimpleUploadedFile("falsa.jpg", b"no soy imagen")]})
        self.assertFalse(FotoPropiedad.objects.exists())

    def test_eliminar_foto_borra_el_archivo(self):
        propiedad = self.crear()
        foto = FotoPropiedad.objects.create(propiedad=propiedad, imagen=imagen())
        ruta = foto.imagen.path
        self.client.post(reverse("propiedades:eliminar_foto", args=[foto.pk]))
        self.assertFalse(FotoPropiedad.objects.exists())
        self.assertFalse(os.path.exists(ruta))

    def test_tipos(self):
        self.client.post(reverse("propiedades:tipo_crear"), {"nombre": " casa ", "activo": "on"})
        self.assertEqual(TipoPropiedad.objects.count(), 1)  # repetido con otras mayúsculas
        self.client.post(reverse("propiedades:tipo_crear"), {"nombre": "Local comercial", "activo": "on"})
        self.assertTrue(TipoPropiedad.objects.filter(clave="local-comercial").exists())
        self.crear()
        self.client.post(reverse("propiedades:tipo_eliminar", args=["casa"]))
        self.assertTrue(TipoPropiedad.objects.filter(clave="casa").exists())  # en uso: no se elimina
