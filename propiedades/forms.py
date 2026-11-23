from django import forms
from django.db.models import Q
from django.utils.text import slugify

from contactos.models import Contacto

from .models import ComprobantePago, FotoPropiedad, Propiedad, TipoPropiedad


class PropiedadForm(forms.ModelForm):
    class Meta:
        model = Propiedad
        fields = [
            "titulo", "tipo", "operacion", "modalidad_arriendo", "precio", "moneda",
            "propietario", "arrendatario",
            "zona", "comuna", "sector_publico", "direccion_exacta",
            "dormitorios", "banos", "estacionamientos", "superficie_util", "superficie_total",
            "descripcion", "caracteristicas", "video_url",
        ]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 5}),
            "caracteristicas": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo contactos con el rol correspondiente, más el ya asignado (aunque haya perdido
        # el rol), para que la propiedad siempre se pueda volver a guardar.
        self.fields["propietario"].queryset = Contacto.objects.filter(
            Q(es_propietario=True) | Q(pk=self.instance.propietario_id))
        self.fields["arrendatario"].queryset = Contacto.objects.filter(
            Q(es_arrendatario=True) | Q(pk=self.instance.arrendatario_id))
        # Solo tipos activos, más el que ya tenía la propiedad.
        self.fields["tipo"].queryset = TipoPropiedad.objects.filter(
            Q(activo=True) | Q(pk=self.instance.tipo_id))


class FiltroPropiedadesForm(forms.Form):
    """Filtros de la lista. Se dibujan campo por campo, por eso cada widget trae su clase de Bootstrap."""
    q = forms.CharField(required=False, widget=forms.TextInput(
        attrs={"class": "form-control", "placeholder": "Código, título, comuna o propietario"}))
    estado = forms.ChoiceField(required=False, choices=[("", "Todos los estados")] + Propiedad.Estado.choices,
                               widget=forms.Select(attrs={"class": "form-select"}))
    operacion = forms.ChoiceField(required=False, choices=[("", "Venta y arriendo")] + Propiedad.Operacion.choices,
                                  widget=forms.Select(attrs={"class": "form-select"}))
    tipo = forms.ModelChoiceField(required=False, queryset=TipoPropiedad.objects.all(), empty_label="Todos los tipos",
                                  widget=forms.Select(attrs={"class": "form-select"}))
    zona = forms.ChoiceField(required=False, choices=[("", "Todas las zonas")] + Propiedad.Zona.choices,
                             widget=forms.Select(attrs={"class": "form-select"}))
    moneda = forms.ChoiceField(required=False, choices=Propiedad.Moneda.choices, initial="CLP",
                               widget=forms.Select(attrs={"class": "form-select"}))
    precio_min = forms.DecimalField(required=False, min_value=0, widget=forms.NumberInput(
        attrs={"class": "form-control", "placeholder": "Precio mín."}))
    precio_max = forms.DecimalField(required=False, min_value=0, widget=forms.NumberInput(
        attrs={"class": "form-control", "placeholder": "Precio máx."}))


class CambioEstadoForm(forms.Form):
    estado = forms.ChoiceField(choices=Propiedad.Estado.choices, widget=forms.Select(attrs={"class": "form-select"}))


class FotoForm(forms.ModelForm):
    """Valida UNA foto con las reglas del modelo (JPG/PNG, tamaño máximo, imagen real).
    La vista lo usa una vez por cada archivo cuando se suben varias a la vez."""
    class Meta:
        model = FotoPropiedad
        fields = ["imagen"]


class TipoPropiedadForm(forms.ModelForm):
    class Meta:
        model = TipoPropiedad
        fields = ["nombre", "activo"]

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        if not slugify(nombre):
            raise forms.ValidationError("Escribe un nombre con letras o números.")
        # Sin duplicados aunque cambien las mayúsculas («casa» y «Casa») ni la clave que se genera.
        otros = TipoPropiedad.objects.exclude(pk=self.instance.pk)
        if otros.filter(nombre__iexact=nombre).exists():
            raise forms.ValidationError("Ya existe un tipo con ese nombre.")
        if not self.instance.pk and otros.filter(clave=slugify(nombre)[:30]).exists():
            raise forms.ValidationError("Ya existe un tipo con un nombre equivalente.")
        return nombre


class ComprobantePagoForm(forms.ModelForm):
    """Se dibuja campo por campo en la ficha de la propiedad, por eso cada widget trae su clase.
    La propiedad no se pregunta: la fija la vista."""
    class Meta:
        model = ComprobantePago
        fields = ["nombre", "fecha", "imagen"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre (ej.: Arriendo marzo 2026)"}),
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "imagen": forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png"}),
        }
