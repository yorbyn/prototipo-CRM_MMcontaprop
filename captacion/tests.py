import io
import tempfile
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from contactos.models import Contacto
from propiedades.models import Propiedad, TipoPropiedad

from .models import Encargo, FotoSolicitud, SolicitudCaptacion


def imagen(nombre="foto.jpg"):
    datos = io.BytesIO()
    Image.new("RGB", (40, 30), "purple").save(datos, "JPEG")
    return SimpleUploadedFile(nombre, datos.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), PRIVATE_MEDIA_ROOT=tempfile.mkdtemp())
class CaptacionTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "admin@ejemplo.cl", "clave"))
        self.casa = TipoPropiedad.objects.create(nombre="Casa")
        self.datos = {"nombre": "María", "rut": "11.111.111-1", "email": " MARIA@X.CL ", "tipo": "casa",
                      "operacion": "venta", "zona": "norte", "comuna": "  Arica  ", "direccion": "Calle 1", "moneda": "CLP"}

    def test_crear_normaliza_rut_correo_y_comuna(self):
        self.client.post(reverse("captacion:crear"), self.datos)
        solicitud = SolicitudCaptacion.objects.get()
        self.assertEqual((solicitud.rut, solicitud.email, solicitud.comuna), ("11111111-1", "maria@x.cl", "Arica"))

    def test_exige_correo_o_telefono(self):
        r = self.client.post(reverse("captacion:crear"), dict(self.datos, email=""))
        self.assertContains(r, "al menos un correo o un teléfono")

    def test_aceptar_crea_contacto_y_propiedad(self):
        self.client.post(reverse("captacion:crear"), self.datos)
        solicitud = SolicitudCaptacion.objects.get()
        self.client.post(reverse("captacion:aceptar", args=[solicitud.pk]))
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, SolicitudCaptacion.Estado.ACEPTADA)
        self.assertTrue(solicitud.propiedad.propietario.es_propietario)
        self.client.post(reverse("captacion:aceptar", args=[solicitud.pk]))
        self.assertEqual(Propiedad.objects.count(), 1)  # aceptar dos veces no duplica

    def test_aceptar_reutiliza_el_contacto_por_correo(self):
        juan = Contacto.objects.create(nombre="Juan", email="maria@x.cl", es_interesado=True)
        self.client.post(reverse("captacion:crear"), self.datos)
        self.client.post(reverse("captacion:aceptar", args=[SolicitudCaptacion.objects.get().pk]))
        juan.refresh_from_db()
        self.assertTrue(juan.es_propietario)
        self.assertEqual(Contacto.objects.count(), 1)

    def test_rechazar(self):
        self.client.post(reverse("captacion:crear"), self.datos)
        solicitud = SolicitudCaptacion.objects.get()
        self.client.post(reverse("captacion:rechazar", args=[solicitud.pk]))
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, SolicitudCaptacion.Estado.RECHAZADA)

    def test_encargos_no_se_cruzan(self):
        duena = Contacto.objects.create(nombre="Dueña", rut="22222222-2", es_propietario=True)
        propiedad = Propiedad.objects.create(titulo="Casa", tipo=self.casa, operacion="venta", zona="norte",
                                             comuna="A", direccion_exacta="x", propietario=duena)
        hoy = timezone.localdate()
        url = reverse("captacion:encargo_crear", args=[propiedad.pk])
        self.client.post(url, {"comision_pct": "2", "fecha_inicio": hoy, "fecha_vencimiento": hoy + timedelta(days=90)})
        self.client.post(url, {"comision_pct": "3", "fecha_inicio": hoy + timedelta(days=10),
                               "fecha_vencimiento": hoy + timedelta(days=100)})
        self.assertEqual(Encargo.objects.count(), 1)

    def test_fotos_privadas_pasan_a_la_galeria_al_publicar(self):
        self.client.post(reverse("captacion:crear"), self.datos)
        solicitud = SolicitudCaptacion.objects.get()
        FotoSolicitud.objects.create(solicitud=solicitud, imagen=imagen())
        self.client.post(reverse("captacion:aceptar", args=[solicitud.pk]))
        propiedad = Propiedad.objects.get()
        propiedad.precio, propiedad.descripcion = 100, "Linda"
        propiedad.save()
        self.client.post(reverse("propiedades:cambiar_estado", args=[propiedad.pk]), {"estado": "disponible"})
        self.assertEqual(propiedad.fotos.count(), 1)
        self.assertIsNotNone(FotoSolicitud.objects.get().copiada_a)
