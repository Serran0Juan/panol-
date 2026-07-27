# Pañol — guía para dejar la app operativa

La app ya está adaptada a la estructura de la planilla del pañol
(pestañas `Inventario`, `Vales APP`, `Registro APP`, `Parametros`, `Plano Pañol`).

Ahora mismo funciona en **modo de prueba**: trabaja sobre una copia local de la
planilla, así podés tocar todo sin miedo a romper los datos reales. Estos pasos
la conectan a la planilla de verdad y la publican en internet.

Los pasos 1, 2, 4 y 5 los tenés que hacer vos porque necesitan tus cuentas de
Google y GitHub. Te acompaño en cada uno.

---

## Antes de empezar: volvé a cerrar la planilla

Para poder leer la estructura, la compartiste como "cualquiera con el enlace".
**Volvé a dejarla en "Restringido"** (Compartir → Acceso general → Restringido).
La app no necesita que sea pública: va a entrar con su propia credencial.

---

## Paso 1 — Crear la cuenta de servicio de Google

Una "cuenta de servicio" es un usuario robot: le das permiso a la planilla y la
app entra con eso, sin usar tu cuenta personal.

1. Entrá a [console.cloud.google.com](https://console.cloud.google.com).
2. Arriba a la izquierda, **Select a project → New Project**. Nombre: `panol`. Create.
3. Con el proyecto seleccionado, buscá **"Google Sheets API"** en la barra de
   búsqueda de arriba y tocá **Enable**.
4. Hacé lo mismo con **"Google Drive API"** → **Enable**.
5. Andá a **APIs & Services → Credentials → + Create Credentials → Service account**.
   - Service account name: `panol-app` → **Create and continue** → **Done**
     (no hace falta asignarle ningún rol).
6. En la lista de Service Accounts, hacé click en la que creaste →
   pestaña **Keys** → **Add key → Create new key → JSON → Create**.
7. Se descarga un archivo `.json`. **Guardalo en un lugar seguro y no lo compartas
   con nadie** — es la llave de entrada a tu planilla.

## Paso 2 — Darle permiso a esa cuenta sobre tu planilla

1. Abrí el `.json` con el Bloc de notas y copiá el valor de `client_email`
   (algo como `panol-app@panol-123456.iam.gserviceaccount.com`).
2. Abrí tu Google Sheet → **Compartir** → pegá ese email → rol **Editor** → Enviar.

## Paso 3 — Probar localmente contra la planilla real

1. Copiá `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml`.
2. Completá los campos con los valores del `.json` descargado. En `sheet_id` va el ID de tu
   planilla (está en su URL, entre `/d/` y `/edit`).
3. Corré la app:

```bash
py -3 -m streamlit run panol_web/app.py
```

Si en la barra lateral **ya no aparece** el cartel amarillo de "Modo de prueba",
está leyendo la planilla real. La primera vez, la app crea sola dos pestañas
nuevas en tu planilla: **Usuarios** y **Reclamos** (no toca ninguna de las que
ya tenías).

Tu email queda cargado como **ADMIN**, y la primera vez que entres vas a elegir
tu contraseña.

## Paso 4 — Subir el proyecto a GitHub

GitHub es donde vive el código para que Streamlit lo pueda publicar.

1. Creá una cuenta en [github.com](https://github.com) si no tenés.
2. Avisame y te ayudo a crear el repositorio y subir el código. Te voy a pedir
   confirmación antes de subir nada.

**Nunca se suben** ni el `.json` de credenciales ni `.streamlit/secrets.toml`
ni la copia local de datos: ya están excluidos en `.gitignore`.

## Paso 5 — Publicar en Streamlit Community Cloud (gratis)

1. Entrá a [share.streamlit.io](https://share.streamlit.io) con tu cuenta de GitHub.
2. **New app** → elegí el repositorio y la rama.
3. Main file path: `panol_web/app.py`.
4. **Advanced settings → Secrets**: pegá exactamente el mismo contenido que
   pusiste en `.streamlit/secrets.toml` en el paso 3.
5. **Deploy**. En un par de minutos te da un link tipo
   `https://panol-xxxx.streamlit.app` que funciona desde cualquier celular o PC.

### Cerrarle la puerta a los de afuera (recomendado)

En Streamlit Cloud, **Settings → Sharing**, poné la app como privada y cargá
los emails de tu equipo. Así hay dos cerraduras: la de Streamlit y la contraseña
de cada usuario dentro de la app.

## Paso 6 — Cargar a los operarios

Desde la app: sección **👥 Usuarios → Nuevo usuario**. Ponés email, nombre, rol
y sector. No hace falta que les asignes contraseña: cada uno elige la suya la
primera vez que entra.

Los roles definen qué ve cada uno:

| Rol | Buscar | Plano | Movimientos | Reclamos | Dashboard | Inventario | Ubicaciones | Usuarios |
|---|---|---|---|---|---|---|---|---|
| OPERARIO | ✅ | ✅ | ✅ | ✅ | — | — | — | — |
| COORDINADOR / JEFE | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| ADMIN | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Lo que ya quedó hecho

- **Buscar productos**: busca por nombre, categoría y estado; muestra la ubicación
  y qué más hay en esa misma estantería.
- **Plano del pañol**: el plano de las 35 estanterías + buscador de contenido
  ("¿dónde están los accesorios de termofusión?") + qué productos hay en cada una.
- **Movimientos**: arma un vale con uno o varios productos (consumo, préstamo,
  devolución, ingreso), descuenta o repone el stock solo, y lleva los préstamos
  abiertos hasta que se devuelven. Escribe en tus pestañas `Vales APP` y `Registro APP`.
- **Pedidos y reclamos**: los operarios avisan qué falta; vos respondés y cerrás.
- **Dashboard**: sin stock, en mínimo, préstamos abiertos, reclamos, valor del
  inventario y productos más movidos.
- **Inventario**: alta y edición de productos (solo escribe las columnas que no
  son fórmulas, así no rompe tu planilla).
- **Asignar ubicaciones**: tu pendiente. Buscás un grupo (ej. "termofusion"),
  los seleccionás todos y los mandás a una estantería de una sola vez.
- **Usuarios**: alta, baja y reinicio de contraseñas.

## Ideas para más adelante

- Código QR pegado en cada estantería que abra el listado de esa ubicación.
- Aviso por email cuando algo se queda sin stock.
- Fotos de los productos.
- Reporte mensual de consumo por sector en PDF.
