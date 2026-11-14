from django.conf import settings


def empresa(request):
    return {"EMPRESA": settings.EMPRESA}
