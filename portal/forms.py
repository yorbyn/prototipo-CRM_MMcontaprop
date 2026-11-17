from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator

from captacion.forms import CAMPOS_SOLICITUD_PUBLICOS, SolicitudBaseForm
from captacion.models import MAX_FOTOS_SOLICITUD, SolicitudCaptacion
from core.forms import BootstrapMixin, CampoTrampaMixin
from core.validators import EXTENSIONES_FOTO, TamanoMaximoValidator, validar_contenido_archivo
from propiedades.models import Propiedad, TipoPropiedad


class BusquedaForm(BootstrapMixin, forms.Form):
    operacion = forms.ChoiceField(required=False, label="Operación",
                                  choices=[("", "Venta o arriendo")] + Propiedad.Operacion.choices)

    # PROPIEDAD
    tipo = forms.ModelChoiceField(required=False, label="Tipo", empty_label="Todos los tipos",
                                  queryset=TipoPropiedad.objects.filter(activo=True))

    zona = forms.ChoiceField(required=False, label="Zona",
                             choices=[("", "Todas las zonas")] + Propiedad.Zona.choices)
    dormitorios = forms.ChoiceField(required=False, label="Dormitorios",
                                    choices=[("", "Cualquiera"), ("1", "1 o más"), ("2", "2 o más"),
                                             ("3", "3 o más"), ("4", "4 o más")])
    moneda = forms.ChoiceField(required=False, label="Moneda", choices=Propiedad.Moneda.choices,
                               widget=forms.Select(attrs={"style": "max-width: 96px"}))
    precio_min = forms.DecimalField(required=False, min_value=0, label="Precio desde",
                                    widget=forms.NumberInput(attrs={"placeholder": "Desde"}))
    precio_max = forms.DecimalField(required=False, min_value=0, label="Precio hasta",
                                    widget=forms.NumberInput(attrs={"placeholder": "Hasta"}))


class ConsultaForm(CampoTrampaMixin, BootstrapMixin, forms.Form):
    """Consulta por una propiedad o mensaje general (página «Contacto»). En el CRM
    crea o reutiliza al contacto por correo y abre una oportunidad nueva."""
    nombre = forms.CharField(max_length=150)
    email = forms.EmailField(label="Correo electrónico")
    telefono = forms.CharField(label="Teléfono", max_length=30, required=False)
    mensaje = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={"rows": 4}))

    def clean_nombre(self):
        return " ".join(self.cleaned_data["nombre"].split())


class VariasImagenesInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class FotosOpcionalesField(forms.ImageField):
    """Varias imágenes opcionales; cada una se valida con Pillow, extensión,
    tamaño y contenido real."""

    def __init__(self, *args, maximo, **kwargs):
        self.maximo = maximo
        kwargs.setdefault("widget", VariasImagenesInput(attrs={"accept": ".jpg,.jpeg,.png"}))
        kwargs["required"] = False
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        archivos = [d for d in (data if isinstance(data, (list, tuple)) else [data]) if d]
        if len(archivos) > self.maximo:
            raise forms.ValidationError(f"Puedes enviar como máximo {self.maximo} fotos.")
        return [super(FotosOpcionalesField, self).clean(a, initial) for a in archivos]


class FotosSolicitudMixin(forms.Form):
    fotos = FotosOpcionalesField(
        label=f"Fotos (opcional, hasta {MAX_FOTOS_SOLICITUD})", maximo=MAX_FOTOS_SOLICITUD,
        validators=[FileExtensionValidator(EXTENSIONES_FOTO), TamanoMaximoValidator(settings.MAX_FOTO_MB),
                    validar_contenido_archivo],
        help_text=f"JPG o PNG, máximo {settings.MAX_FOTO_MB} MB cada una. No se publican hasta que "
                  "evaluemos tu propiedad.",
    )


class OfrecerPropiedadForm(CampoTrampaMixin, FotosSolicitudMixin, SolicitudBaseForm):
    """«Ofrecer mi propiedad». Solo campos que completa el propietario: el estado,
    el origen y las observaciones internas no se pueden enviar desde el portal."""

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

