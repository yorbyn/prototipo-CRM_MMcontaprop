from django import forms
from django.db.models import Q

from core.forms import BootstrapMixin

from contactos.models import Contacto
from .models import Propiedad, TipoPropiedad
from core.forms import BootstrapMixin

class PropiedadForm(BootstrapMixin, forms.ModelForm):
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
        # Solo contactos con el rol correspondiente, más el ya asignado (aunque haya
        # perdido el rol), para que la propiedad siempre se pueda volver a guardar.
        actual_prop = self.instance.propietario_id if self.instance.pk else None
        actual_arr = self.instance.arrendatario_id if self.instance.pk else None
        self.fields["propietario"].queryset = Contacto.objects.filter(
            Q(es_propietario=True) | Q(pk=actual_prop))
        self.fields["arrendatario"].queryset = Contacto.objects.filter(
            Q(es_arrendatario=True) | Q(pk=actual_arr))
        # Solo tipos activos, más el que ya tenía la propiedad.
        self.fields["tipo"].queryset = TipoPropiedad.objects.filter(
            Q(activo=True) | Q(pk=self.instance.tipo_id))


class FiltroPropiedadesForm(BootstrapMixin, forms.Form):
    q = forms.CharField(required=False, label="Buscar",
                        widget=forms.TextInput(attrs={"placeholder": "Código, título, comuna o propietario"}))
    estado = forms.ChoiceField(required=False, choices=[("", "Todos los estados")] + Propiedad.Estado.choices)
    operacion = forms.ChoiceField(required=False, choices=[("", "Venta y arriendo")] + Propiedad.Operacion.choices)
    tipo = forms.ModelChoiceField(required=False, queryset=TipoPropiedad.objects.all(), empty_label="Todos los tipos")
    zona = forms.ChoiceField(required=False, choices=[("", "Todas las zonas")] + Propiedad.Zona.choices)
    moneda = forms.ChoiceField(required=False, choices=Propiedad.Moneda.choices, initial="CLP")
    precio_min = forms.DecimalField(required=False, min_value=0, label="Precio mín.",
                                    widget=forms.NumberInput(attrs={"placeholder": "Precio mín."}))
    precio_max = forms.DecimalField(required=False, min_value=0, label="Precio máx.",
                                    widget=forms.NumberInput(attrs={"placeholder": "Precio máx."}))