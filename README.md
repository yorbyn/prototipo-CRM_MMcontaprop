# MMCONTAPROP

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?logo=django&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-7952B3?logo=bootstrap&logoColor=white)

Sistema web CRM para la gestión de la corredora de propiedades **MMCONTAPROP SPA**, desarrollado con **Django**.

Permite administrar internamente contactos, propiedades, captaciones, oportunidades comerciales, operaciones, actividades, documentos y comunicaciones, e incluye un portal público donde los visitantes pueden consultar propiedades y enviar solicitudes.

> **Estado del proyecto:** en desarrollo. Las funcionalidades descritas corresponden al alcance contemplado del sistema y se incorporan de forma progresiva.

## Contenido

- [Funcionalidades](#funcionalidades)
- [Tecnologías](#tecnologías)
- [Arquitectura](#arquitectura)
- [Integrantes](#integrantes)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación y ejecución](#instalación-y-ejecución)
- [Primer uso](#primer-uso)
- [Pruebas](#pruebas)
- [Flujo de trabajo en GitHub](#flujo-de-trabajo-en-github)

## Funcionalidades

**Gestión interna (CRM)**

- Registro de contactos y sus preferencias de búsqueda.
- Administración de propiedades y sus fotografías.
- Recepción y revisión de solicitudes de captación, con aceptación o rechazo y gestión de encargos.
- Seguimiento comercial: oportunidades, ofertas y operaciones.
- Registro de actividades: notas, llamadas, reuniones, visitas, tareas y correos, además de agenda e indicadores.
- Documentos privados asociados a contactos, propiedades u operaciones.
- Envío de correos con plantillas e historial de mensajes.
- Control de acceso mediante inicio de sesión y roles (Administrador y Trabajador).

**Portal público**

- Catálogo de propiedades con filtros y ficha de detalle.
- Formularios de contacto y de solicitud para ofrecer una propiedad.

## Tecnologías

| Tecnología | Uso |
|---|---|
| Python | Lenguaje del proyecto |
| Django | Framework web |
| Pillow | Manejo de imágenes (fotografías) |
| python-dotenv | Lectura de la configuración desde el archivo `.env` |
| django-crispy-forms + crispy-bootstrap5 | Formularios con estilo Bootstrap 5 |
| Pipenv | Entorno virtual y dependencias |
| HTML, CSS y Bootstrap | Plantillas e interfaz |
| Notyf | Mensajes emergentes (éxito, error) en las pantallas |
| SQLite | Base de datos de desarrollo local |

## Arquitectura

El sistema es un único proyecto Django organizado en diez aplicaciones. Cada aplicación mantiene sus propias rutas (`urls.py`), plantillas y registro en el panel `/admin/`. Las vistas son funciones y los formularios, `ModelForm`.

| Aplicación | Responsabilidad |
|---|---|
| `core` | Plantilla base del CRM, inicio y cierre de sesión, decorador de acceso al CRM, modelo abstracto con fechas de creación y modificación, validación de RUT y filtros de formato (precio, RUT). |
| `usuarios` | Roles (`Rol`) y perfiles (`Perfil`) de quienes entran al CRM, y pantalla de gestión de usuarios para el administrador. |
| `contactos` | Contactos y preferencias de búsqueda. |
| `propiedades` | Propiedades y fotografías. |
| `captacion` | Solicitudes para ofrecer propiedades, fotografías de las solicitudes y encargos. |
| `comercial` | Oportunidades, ofertas y operaciones. |
| `actividades` | Notas, llamadas, reuniones, visitas, tareas, correos y registros de sistema. |
| `documentos` | Documentos privados asociados a contactos, propiedades u operaciones. |
| `correo` | Plantillas y registro de mensajes enviados. |
| `portal` | Catálogo público, filtros, fichas de propiedades y formularios de contacto y captación. |

## Integrantes

| Integrante | GitHub | Rama | Aplicaciones | Responsabilidades |
|---|---|---|---|---|
| Yorbyn | [@yorbyn](https://github.com/yorbyn) | `feature/ymollo` | `config`, `core`, `portal` | Configuración inicial, estructura compartida, permisos, login, portal público, README e integración final. |
| Josué | [@Peschke](https://github.com/Peschke) | `feature/jaraya` | `contactos`, `propiedades`, `documentos` | Contactos, preferencias de búsqueda, propiedades, fotografías y documentos privados. |
| Sebastián | [@Theluxito](https://github.com/Theluxito) | `feature/sferreira` | `comercial`, `actividades` | Oportunidades, ofertas, operaciones, actividades, agenda e indicadores. |
| Miguel | [@King-MZ-90](https://github.com/King-MZ-90) | `feature/mdiaz` | `captacion`, `correo` | Solicitudes de captación, fotografías, encargos, aceptación/rechazo y correo con plantillas e historial. |

## Estructura del proyecto

```text
prototipo-CRM_MMcontaprop/
├── config/          # Configuración del proyecto Django (settings, urls)
├── core/            # Base compartida del CRM
├── usuarios/
├── contactos/
├── propiedades/
├── captacion/
├── comercial/
├── actividades/
├── documentos/
├── correo/
├── portal/
├── templates/       # base.html y plantillas comunes (403, paginación)
├── static/          # CSS, JavaScript, Bootstrap, íconos y fuentes
├── media/           # Fotos públicas de las propiedades (no se sube a git)
├── private_media/   # Documentos y fotos de solicitudes, solo para el CRM (no se sube a git)
├── manage.py
├── Pipfile
├── requirements.txt
└── .env.example
```

Cada aplicación sigue la estructura de Django: `models.py`, `forms.py`, `views.py`, `urls.py`, `admin.py`, `tests.py` y `templates/<app>/`. Las plantillas se nombran `<modelo>_lista.html`, `<modelo>_detalle.html` y `<modelo>_form.html`; las que empiezan con `_` son fragmentos que se incluyen en otras.

## Instalación y ejecución

### Requisitos previos

- Python
- Pipenv
- Git

### Pasos (Windows / PowerShell)

```powershell
git clone https://github.com/yorbyn/prototipo-CRM_MMcontaprop.git
cd prototipo-CRM_MMcontaprop
pipenv install
Copy-Item .env.example .env
pipenv run python manage.py migrate
pipenv run python manage.py runserver
```

Luego abre `http://127.0.0.1:8000/` en el navegador.

**Variables de entorno:** el archivo `.env` se crea a partir de `.env.example` y **debe tener una `SECRET_KEY`**; sin ella, el proyecto no arranca. Para generar una:

```powershell
py -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Pega el resultado en `.env` como `SECRET_KEY='...'`. Deja `DEBUG=True` y `ALLOWED_HOSTS=127.0.0.1,localhost` para trabajar en local. El archivo `.env` no debe subirse al repositorio.

**Variante:** también puedes activar el entorno virtual y ejecutar los comandos dentro de él:

```powershell
pipenv shell
py manage.py migrate
py manage.py runserver
```

**Después de un `git pull`:** si el `Pipfile` cambió, ejecuta `pipenv install`. Si hay migraciones nuevas, ejecuta `pipenv run python manage.py migrate`. Sin esto, el proyecto puede no arrancar o dar errores al guardar.

## Primer uso

La base de datos parte vacía. Antes de usar el CRM:

1. **Crea el administrador** con el administrador de Django:

   ```powershell
   pipenv run python manage.py createsuperuser
   ```

   El superusuario siempre es **Administrador** del CRM. Entra en `http://127.0.0.1:8000/crm/`.

2. **Crea los usuarios del equipo** en **Usuarios** (menú lateral, sección Administración), con el rol **Administrador** (todo el CRM y la gestión de usuarios) o **Trabajador** (todo el CRM, menos la gestión de usuarios). Los roles se crean solos la primera vez que se asignan. También se pueden ver y editar en `/admin/` → Roles y Perfiles.

3. **Crea los tipos de propiedad** en **Tipos de propiedad**, por ejemplo: Casa, Departamento, Terreno, Parcela, Oficina, Local comercial y Bodega. Sin al menos un tipo no se pueden registrar propiedades ni solicitudes.

4. **Opcional: plantillas de correo** en **Correos → Plantillas**. Pueden usar variables como `{nombre}`, `{propiedad}`, `{codigo}`, `{precio}` o `{enlace}`, que se reemplazan al enviar.

5. **Opcional: correo real.** Completa `GMAIL_USUARIO` y `GMAIL_CONTRASENA_APLICACION` en `.env` con una **contraseña de aplicación** de Google (requiere verificación en 2 pasos) y **reinicia el servidor**. Sin ellas, los correos se muestran en la terminal donde corre `runserver`.

## Pruebas

```powershell
pipenv run python manage.py test
```

Las pruebas usan una base de datos temporal y carpetas temporales para los archivos, así que no modifican tus datos.

## Flujo de trabajo en GitHub

### Ramas

| Rama | Propósito |
|---|---|
| `main` | Versión estable y entregas. |
| `develop` | Integración y pruebas. |
| `feature/a` … `feature/d` | Rama de trabajo de cada integrante. |

- Nadie trabaja ni hace commits directamente en `main` o `develop`.
- El trabajo se integra a `develop` mediante **Pull Requests** desde la rama de cada integrante.
- Cada Pull Request debe ser revisado y aprobado por **otro integrante**; no se aprueba el propio.
- Las entregas se integran desde `develop` hacia `main`.

### Comenzar a trabajar

Reemplaza `feature/a` por tu rama correspondiente.

```bash
git checkout develop
git pull origin develop
git checkout -b feature/a
git push -u origin feature/a
```

Para actualizar una rama existente con los últimos cambios de `develop`:

```bash
git checkout feature/a
git pull origin develop
```

### Convención de commits

| Prefijo | Uso | Ejemplo |
|---|---|---|
| `feat` | Nueva funcionalidad | `feat: agrega modelo de propiedades` |
| `fix` | Corrección de errores | `fix: corrige validación de RUT` |
| `style` | Cambios visuales o de formato | `style: ajusta diseño responsivo del portal` |
| `docs` | Documentación | `docs: actualiza documentación del proyecto` |
| `test` | Pruebas | `test: agrega pruebas para captación` |
| `refactor` | Cambio interno del código sin cambiar lo que hace | `refactor(contactos): simplifica vistas y formularios` |
