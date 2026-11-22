import io
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from captacion.models import SolicitudCaptacion
from comercial.models import Oportunidad
from contactos.models import Contacto
from propiedades.models import Propiedad, TipoPropiedad


def imagen(nombre="foto.jpg"):
    datos = io.BytesIO()
    Image.new("RGB", (40, 30), "purple").save(datos, "JPEG")
    return SimpleUploadedFile(nombre, datos.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), PRIVATE_MEDIA_ROOT=tempfile.mkdtemp())
class PortalTests(TestCase):
    """El portal es público: estas pruebas no inician sesión."""

    def setUp(self):
        self.casa = TipoPropiedad.objects.create(nombre="Casa")
        duena = Contacto.objects.create(nombre="María Secreta", rut="11111111-1", es_propietario=True)
        datos = dict(tipo=self.casa, operacion="venta", zona="norte", comuna="Arica", precio=100,
                     direccion_exacta="Calle Escondida 123", propietario=duena, descripcion="Linda")
        self.publicada = Propiedad.objects.create(titulo="Casa publicada", estado="disponible", **datos)
        self.borrador = Propiedad.objects.create(titulo="Casa en borrador", estado="borrador", **datos)

    def test_catalogo_solo_muestra_publicadas(self):
        r = self.client.get("/")
        self.assertContains(r, "Casa publicada")
        self.assertNotContains(r, "Casa en borrador")

    def test_ficha_sin_datos_privados(self):
        r = self.client.get(f"/propiedad/{self.publicada.codigo}/")
        for privado in ("Calle Escondida", "María Secreta", "11.111.111-1"):
            self.assertNotContains(r, privado)
        self.assertEqual(self.client.get(f"/propiedad/{self.borrador.codigo}/").status_code, 404)

    def test_consulta_crea_una_oportunidad(self):
        self.client.post(f"/propiedad/{self.publicada.codigo}/", {"nombre": "Juan", "email": "juan@x.cl", "mensaje": "Hola"})
        oportunidad = Oportunidad.objects.get()
        self.assertEqual((oportunidad.origen, oportunidad.propiedad), (Oportunidad.Origen.PORTAL, self.publicada))

    def test_contacto_crea_una_oportunidad_sin_propiedad(self):
        self.client.post("/contacto/", {"nombre": "Ana", "email": "ana@x.cl", "mensaje": "Hola"})
        self.assertTrue(Oportunidad.objects.filter(origen=Oportunidad.Origen.CONTACTO, propiedad=None).exists())

    def test_ofrecer_con_fotos(self):
        datos = {"nombre": "Dueño", "email": "d@x.cl", "tipo": "casa", "operacion": "venta", "zona": "norte",
                 "comuna": "Arica", "direccion": "Calle 2", "moneda": "CLP"}
        self.client.post("/ofrecer-mi-propiedad/", dict(datos, fotos=[imagen(f"{i}.jpg") for i in range(7)]))
        self.assertFalse(SolicitudCaptacion.objects.exists())  # más de 6 fotos
        self.client.post("/ofrecer-mi-propiedad/", dict(datos, fotos=[imagen("a.jpg"), imagen("b.jpg")]))
        solicitud = SolicitudCaptacion.objects.get()
        self.assertEqual((solicitud.origen, solicitud.fotos.count()), (SolicitudCaptacion.Origen.WEB, 2))
