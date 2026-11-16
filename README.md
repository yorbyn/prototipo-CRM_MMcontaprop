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
- Control de acceso mediante inicio de sesión y permisos.

**Portal público**

- Catálogo de propiedades con filtros y ficha de detalle.
- Formularios de contacto y de solicitud para ofrecer una propiedad.

## Tecnologías

| Tecnología | Uso |
|---|---|
| Python | Lenguaje del proyecto |
| Django | Framework web |
| Pillow | Manejo de imágenes (fotografías) |
| Pipenv | Entorno virtual y dependencias |
| HTML, CSS y Bootstrap | Plantillas e interfaz |
| SQLite | Base de datos de desarrollo local |

## Arquitectura

El sistema es un único proyecto Django organizado en nueve aplicaciones. Cada aplicación mantiene sus propias rutas (`urls.py`) y plantillas.

| Aplicación | Responsabilidad |
|---|---|
| `core` | Funcionalidades compartidas, modelo abstracto auditado, permisos del CRM, validaciones y controles de seguridad. |
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
| Miguel | [@King-MZ-90(https://github.com/King-MZ-90)] | `feature/mdiaz` | `captacion`, `correo` | Solicitudes de captación, fotografías, encargos, aceptación/rechazo y correo con plantillas e historial. |

## Estructura del proyecto

Estructura orientativa; puede variar según la implementación final.

```text
prototipo-CRM_MMcontaprop/
├── config/          # Configuración del proyecto Django (settings, urls)
├── core/
├── contactos/
├── propiedades/
├── captacion/
├── comercial/
├── actividades/
├── documentos/
├── correo/
├── portal/
├── manage.py
├── Pipfile
├── Pipfile.lock
└── .env.example
```

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

**Variables de entorno:** el archivo `.env` se crea a partir de `.env.example`. Revisa ese archivo para conocer las variables necesarias y completa sus valores antes de ejecutar el proyecto. El archivo `.env` no debe subirse al repositorio.

**Variante:** también puedes activar el entorno virtual y ejecutar los comandos dentro de él:

```powershell
pipenv shell
py manage.py migrate
py manage.py runserver
```

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
