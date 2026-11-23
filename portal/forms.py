from django import forms

from captacion.forms import CAMPOS_SOLICITUD_PUBLICOS, SolicitudBaseForm
from captacion.models import FotoSolicitud, SolicitudCaptacion
from propiedades.models import Propiedad, TipoPropiedad


class BusquedaForm(forms.Form):
    """Buscador del catálogo. Se dibuja campo por campo, por eso cada widget trae su clase de Bootstrap."""
    operacion = forms.ChoiceField(required=False, choices=[("", "Venta o arriendo")] + Propiedad.Operacion.choices,
                                  widget=forms.Select(attrs={"class": "form-select"}))
    tipo = forms.ModelChoiceField(required=False, empty_label="Todos los tipos",
                                  queryset=TipoPropiedad.objects.filter(activo=True),
                                  widget=forms.Select(attrs={"class": "form-select"}))
    zona = forms.ChoiceField(required=False, choices=[("", "Todas las zonas")] + Propiedad.Zona.choices,
                             widget=forms.Select(attrs={"class": "form-select"}))
    dormitorios = forms.ChoiceField(required=False, widget=forms.Select(attrs={"class": "form-select"}),
                                    choices=[("", "Cualquiera"), ("1", "1 o más"), ("2", "2 o más"),
                                             ("3", "3 o más"), ("4", "4 o más")])
    moneda = forms.ChoiceField(required=False, choices=Propiedad.Moneda.choices,
                               widget=forms.Select(attrs={"class": "form-select", "style": "max-width: 96px"}))
    precio_min = forms.DecimalField(required=False, min_value=0, widget=forms.NumberInput(
        attrs={"class": "form-control", "placeholder": "Desde"}))
    precio_max = forms.DecimalField(required=False, min_value=0, widget=forms.NumberInput(
        attrs={"class": "form-control", "placeholder": "Hasta"}))


class ConsultaForm(forms.Form):
    """Consulta por una propiedad o mensaje general (página «Contacto»). En el CRM crea o
    reutiliza al contacto por correo y abre una oportunidad nueva."""
    nombre = forms.CharField(max_length=150)
    email = forms.EmailField(label="Correo electrónico")
    telefono = forms.CharField(label="Teléfono", max_length=30, required=False)
    mensaje = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={"rows": 4}))

    def clean_nombre(self):
        return " ".join(self.cleaned_data["nombre"].split())


class OfrecerPropiedadForm(SolicitudBaseForm):
    """«Ofrecer mi propiedad». Solo los campos que completa el propietario: el estado, el origen
    y las observaciones internas no se pueden enviar desde el portal. Las fotos van aparte."""

    class Meta:
        model = SolicitudCaptacion
        fields = CAMPOS_SOLICITUD_PUBLICOS
        widgets = {
            "comentarios": forms.Textarea(attrs={"rows": 4, "placeholder": "Estado del inmueble, horarios para visitar, "
                                                                            "si está habitada, etc."}),
            "direccion": forms.TextInput(attrs={"placeholder": "Calle, número y depto. si corresponde"}),
        }
        labels = {"nombre": "Tu nombre completo", "rut": "RUT (opcional)", "precio_esperado": "Precio esperado (opcional)"}
        help_texts = {
            "rut": "Ej.: 12.345.678-5. Agiliza el registro si aceptamos tu propiedad.",
            "direccion": "Solo la usamos para evaluar y visitar. Nunca se publica.",
        }


class FotoSolicitudForm(forms.ModelForm):
    """Valida UNA foto con las reglas del modelo (JPG/PNG, tamaño máximo, imagen real).
    La vista lo usa una vez por cada archivo cuando se envían varias."""
    class Meta:
        model = FotoSolicitud
        fields = ["imagen"]
