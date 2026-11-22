from django import forms
from django.utils import timezone

from contactos.models import Contacto
from propiedades.models import Propiedad

from .models import Actividad


class ActividadForm(forms.ModelForm):
    """Registro rápido en el historial de una ficha. Se dibuja campo por campo,
    por eso cada widget trae su clase de Bootstrap."""

    class Meta:
        model = Actividad
        fields = ["tipo", "descripcion"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "¿Qué ocurrió?"}),
        }
        labels = {"descripcion": ""}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Los registros automáticos solo los crea el sistema.
        self.fields["tipo"].choices = [c for c in Actividad.Tipo.choices if c[0] != Actividad.Tipo.SISTEMA]


class ProgramarForm(forms.ModelForm):
    """Programa una visita o una tarea con fecha; queda pendiente hasta marcarla como realizada.
    `fijo` («contacto», «propiedad» u «oportunidad») es la ficha desde la que se programa:
    esa relación la pone la vista y no se pregunta en el formulario."""

    class Meta:
        model = Actividad
        fields = ["tipo", "fecha", "descripcion", "contacto", "propiedad"]
        widgets = {
            "fecha": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "descripcion": forms.Textarea(attrs={"rows": 2, "placeholder": "Ej.: Visita con interesado / Llamar para renovar encargo"}),
        }
        labels = {"fecha": "Fecha y hora programada", "descripcion": "Detalle", "contacto": "Contacto",
                  "propiedad": "Propiedad"}
        help_texts = {"fecha": ""}

    def __init__(self, *args, fijo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].choices = [(t.value, t.label) for t in Actividad.TIPOS_AGENDA]
        self.fields["propiedad"].queryset = Propiedad.objects.exclude(estado=Propiedad.Estado.ANULADA)
        self.fields["contacto"].queryset = Contacto.objects.order_by("nombre")
        if fijo in ("contacto", "propiedad"):
            del self.fields[fijo]
        elif fijo == "oportunidad":
            # El contacto y la propiedad son los de la oportunidad.
            del self.fields["contacto"]
            del self.fields["propiedad"]
        if not self.instance.pk:
            # Sin fecha precargada: la hora actual ya estaría en el pasado al enviar.
            self.initial["fecha"] = None

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha < timezone.now():
            raise forms.ValidationError("La fecha programada no puede estar en el pasado.")
        return fecha

    def clean(self):
        datos = super().clean()
        # Si el campo no está en el formulario, se usa el que ya trae la actividad (la ficha fija).
        contacto = datos.get("contacto") if "contacto" in self.fields else self.instance.contacto
        propiedad = datos.get("propiedad") if "propiedad" in self.fields else self.instance.propiedad
        if datos.get("tipo") == Actividad.Tipo.VISITA and not (contacto and propiedad):
            raise forms.ValidationError("Una visita debe indicar la propiedad y el contacto que asiste.")
        if not (contacto or propiedad):
            raise forms.ValidationError("Asocie la tarea a un contacto o a una propiedad.")
        return datos

    def save(self, commit=True):
        self.instance.estado = Actividad.Estado.PENDIENTE
        return super().save(commit)
