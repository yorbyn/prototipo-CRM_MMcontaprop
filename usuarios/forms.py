from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from core.forms import BootstrapMixin

from .roles import ROLES


class UsuarioCrearForm(BootstrapMixin, UserCreationForm):
    """Crea un usuario con contraseña (se pide dos veces y Django revisa que sea segura)."""
    first_name = forms.CharField(label="Nombre", max_length=150)
    last_name = forms.CharField(label="Apellido", max_length=150, required=False)
    email = forms.EmailField(label="Correo", required=False)
    rol = forms.ChoiceField(label="Rol", choices=ROLES)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe un usuario con ese correo.")
        return email


class UsuarioEditarForm(BootstrapMixin, forms.ModelForm):
    """Edita los datos y el rol. La contraseña no se cambia aquí."""
    rol = forms.ChoiceField(label="Rol", choices=ROLES)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {"first_name": "Nombre", "last_name": "Apellido", "email": "Correo"}

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un usuario con ese correo.")
        return email
