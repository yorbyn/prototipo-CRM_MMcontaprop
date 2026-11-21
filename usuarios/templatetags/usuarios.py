from django import template

from usuarios.roles import es_admin_crm

register = template.Library()


@register.filter
def es_admin(usuario):
    """Uso en plantillas: {% if request.user|es_admin %} ... {% endif %}"""
    return es_admin_crm(usuario)
