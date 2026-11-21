from django.conf import settings
from django.db import migrations


def crear_grupos(apps, schema_editor):
    """Crea los dos grupos que representan los roles del CRM."""
    Group = apps.get_model("auth", "Group")
    for nombre in (settings.GRUPO_CRM, settings.GRUPO_TRABAJADORES):
        Group.objects.get_or_create(name=nombre)


class Migration(migrations.Migration):
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [migrations.RunPython(crear_grupos, migrations.RunPython.noop)]
