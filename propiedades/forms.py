from django import forms

from core.forms import BootstrapMixin

from .models import Propiedad, TipoPropiedad


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