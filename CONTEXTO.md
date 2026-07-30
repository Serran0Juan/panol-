# Contexto del proyecto

Documento para ponerse al día con el sistema sin haber participado de su
construcción. Sirve tanto para una persona nueva como para pasárselo a otra IA
y seguir iterando.

---

## 1. Qué es

**Sistema de Gestión Integral de Mantenimiento** del pañol de un hospital.
Arrancó como control de stock del depósito y hoy incluye mantenimiento
correctivo. Está en uso real, con datos reales y varios usuarios.

Dos módulos:

- **Pañol** — inventario, ubicaciones, entregas a operarios, préstamos.
- **Trabajos correctivos** — solicitudes de reparación, órdenes de trabajo,
  agenda y tablero de jefatura.

---

## 2. Arquitectura

```
   PC del autor              GitHub               Streamlit Cloud        Google Sheets
   (desarrollo)         (código oficial)          (ejecuta la app)         (los datos)
        │                      │                        │                       │
        │  git push            │   baja el código       │   lee y escribe       │
        ├─────────────────────►│───────────────────────►│──────────────────────►│
```

- **Streamlit** es a la vez la librería que dibuja la interfaz y el servicio que
  la ejecuta. El código no vive en Streamlit: lo baja de GitHub en cada arranque.
- **Los datos nunca pasan por GitHub.** Van directo de la app a la planilla.
- **Las credenciales tampoco.** Están en `.streamlit/secrets.toml`, que está en
  `.gitignore`, y cargadas aparte en Streamlit Cloud.
- Al hacer push, Streamlit Cloud redespliega solo. **Cuando se agregan archivos
  nuevos suele hacer falta un Reboot manual** desde share.streamlit.io.

---

## 3. Modelo de datos

Todo vive en un Google Sheet. Las pestañas `Inventario`, `Vales APP`,
`Registro APP`, `Parametros`, `Plano Pañol`, `Buscador` y `Dasboard` ya existían
y las armó el usuario; la app se adaptó a ellas. Las demás las crea la app sola.

### Inventario — el catálogo (451 materiales)

| Columna | Nota |
|---|---|
| Nro/SKU | número correlativo, es el id |
| Descripción del Producto | |
| Stock Inicial | se carga a mano |
| **Stock Actual** | **fórmula** `=Stock Inicial − Consumo − Préstamos pendientes` |
| Unidad, Ubicación | ubicación = número de estantería, ej. `18` o `18-2` |
| **Estado/Alerta** | **fórmula** que devuelve 🟢 OK / 🟡 MÍNIMO / 🔴 SIN STOCK |
| Stock Minimo | |
| **Consumo**, **Prestamos Pendiente** | **fórmulas** SUMIFS sobre `Registro APP` |
| Precio Unitario, **Total** | Total es **fórmula** `=Stock Actual × Precio` |
| Categoria/Area, Subcategoria, Fuente del requerimiento | |

> ⚠️ **La regla más importante del proyecto: la app NUNCA escribe el stock.**
> Es una fórmula. Si se escribiera encima, se rompería el cálculo automático de
> ese material para siempre. La app solo registra movimientos y la planilla
> recalcula. Por eso en Inventario se edita el **Stock Inicial**, no el actual.
> Ver `INVENTARIO_ESCRIBIBLES` en `sheets_backend.py`.

### Vales APP + Registro APP — los movimientos

Modelo cabecera/renglones. **Un vale = una visita de un operario al pañol**, y
puede mezclar tipos: se lleva una amoladora prestada y 20 tornillos de consumo.

- `Vales APP`: ID VALE, fecha, tipo (o `MIXTO`), sector, área, receptor,
  estado (`ABIERTO`/`CERRADO`), REGISTRADO_POR.
- `Registro APP`: un renglón por material, con su **propio** TIPO_MOV
  (`CONSUMO` / `PRESTADO` / `INGRESO`), CANT, **CANT_DEVUELTA** y
  **ESTADO_RENGLON** (`PENDIENTE` / `CERRADO`).

El modelo es por **cantidades, no por estados**: cada renglón guarda cuánto se
entregó y cuánto volvió. Eso permite devoluciones parciales y también devolver
el sobrante de un consumo (se entregan 20 tornillos, se usan 15, vuelven 5).

Un vale se cierra solo cuando ningún renglón queda pendiente.

Un préstamo que no vuelve (se perdió o se rompió) se convierte a `CONSUMO`: el
stock ya estaba descontado, así que no se toca ningún número.

### Ordenes + OT_Estados — mantenimiento correctivo

- `Ordenes`: ID_OT, alta, solicitante, área, descripción, prioridad, sector y
  responsable asignados, estado, **FECHA_COMPROMISO**, **FECHA_PROGRAMADA**,
  **HORAS_ESTIMADAS**, cierre técnico (trabajo, causa, horas) y `VALE_REF`
  (reservada para atar los materiales, todavía sin usar).
- `OT_Estados`: bitácora, una fila por cambio de estado con fecha y usuario.

Circuito, con transiciones validadas en `TRANSICIONES_OT`:

```
SOLICITADA → ASIGNADA → EN CURSO ⇄ PAUSADA → RESUELTA
     └──────────────── ANULADA ────────────────┘
```

**El vencimiento se calcula solo** según la prioridad (`SLA_DIAS`): urgente el
mismo día, alta 3, media 7, baja 15. Se puede pisar orden por orden.

### Usuarios

EMAIL, NOMBRE, ROL, SECTOR, ACTIVO, PASSWORD_HASH (pbkdf2, nunca texto plano).
Un usuario sin hash elige su contraseña la primera vez que entra.

---

## 4. Permisos

Definidos en un solo lugar: `PERMISOS` en `auth.py`. Las páginas preguntan con
`puede("accion")` o cortan con `exigir("accion")`.

| Rol | Ve todo | Registra movimientos | Gestiona órdenes | Edita inventario | Administra |
|---|:--:|:--:|:--:|:--:|:--:|
| ADMIN | ✅ | ✅ | ✅ | ✅ | ✅ |
| JEFE | ✅ | ✅ | ✅ | — | — |
| COORDINADOR | ✅ | ✅ | ✅ | — | — |
| LECTOR | ✅ | — | — | — | — |
| OPERARIO | solo lo suyo | — | — | — | — |

Cargar una solicitud de reparación y cerrar las órdenes propias no requiere
permiso: lo puede hacer cualquier usuario.

---

## 5. El código

```
app.py                  entrypoint: login, logo y navegación por rol
auth.py                 permisos y contraseñas
sheets_backend.py       TODO el acceso a datos; las páginas no tocan gspread
estilo.py               CSS y paleta
pages/                  una pantalla por archivo
assets/                 plano del pañol y logo
```

`sheets_backend.py` es la pieza central. Expone funciones de negocio
(`registrar_vale`, `devolver_renglon`, `asignar_orden`...) y esconde si los
datos vienen de Google Sheets o de la copia local.

### Modo local

Si existe `_devdata/MODO_LOCAL` (o `PANOL_MODO_LOCAL=1`), la app trabaja sobre
copias CSV sembradas desde un Excel, sin tocar producción. La app avisa con un
cartel amarillo. **Las pruebas fuerzan ese modo y abortan si detectan que
podrían escribir en la planilla real.**

### Pruebas

Cinco suites, 134 verificaciones, repetibles:

```bash
py -3 _prueba_numeros.py         # conversión de números formateados
py -3 _prueba_movimientos.py     # vales, devoluciones, ingresos
py -3 _prueba_ordenes.py         # circuito de las órdenes
py -3 _prueba_planificacion.py   # vencimientos, agenda, carga
py -3 _prueba_permisos.py        # permisos rol por rol
```

### Scripts de mantenimiento (se corren a mano, una sola vez)

- `crear_hojas_ot.py` — crea y formatea `Ordenes` y `OT_Estados`
- `migracion_formulas.py` — fórmulas de devoluciones parciales, con `restaurar`
- `arreglar_rangos_dashboard.py` — extiende los rangos cortos del Dasboard
- `generar_logo.py` — regenera el logo

---

## 6. Decisiones tomadas, y por qué

| Decisión | Razón |
|---|---|
| Streamlit y no una web tradicional | Sin equipo de desarrollo; prioridad era que funcione, no que sea perfecta |
| Google Sheets como base y no SQL | El usuario ya tenía la planilla armada y sabe usarla; puede corregir a mano |
| El stock lo calcula la planilla | Ya estaba resuelto ahí; duplicarlo en la app generaba dos fuentes de verdad |
| Devoluciones por cantidad y no por estado | Permite parciales y sobrantes, que pasan en la realidad |
| Vencimiento automático por prioridad | Si hay que cargar una fecha en cada orden, en la práctica quedan vacías |
| Un vale por visita, con tipo por renglón | Un operario se lleva préstamos y consumos en el mismo momento |
| Permisos en un único diccionario | Antes estaban repartidos en cada página y se desincronizaban |
| Repo público | Streamlit Cloud gratuito no lee repos privados. Se sacaron del código el ID de la planilla, el email del admin y el nombre de la institución |

---

## 7. Trampas conocidas

Cosas que ya costaron un rato. Vale la pena leerlas antes de tocar.

1. **Google Sheets devuelve los números formateados.** `get_all_values()` da
   `"$ 10.000"`, no `10000`. Interpretar mal ese punto hacía que el inventario
   valiera cien veces menos. Usar siempre `a_numero()`, nunca `float()` directo.
   Inventario además se lee con `sin_formato=True` porque los precios se
   muestran redondeados.
2. **`st.navigation()` va antes que cualquier otra cosa.** Si se escribe en la
   barra lateral antes de llamarla, la barra lateral no se dibuja.
3. **pandas convierte `None` en `NaN`.** Al armar columnas de fechas conviene
   construir listas y no usar `.apply()`, y comparar con `pd.isna()` y no con
   `is None`. `int(NaN)` explota.
4. **Streamlit no admite dos controles con la misma clave.** Una orden vencida y
   sin programar sale en dos listas: la clave tiene que incluir el contexto.
5. **Los rangos de las fórmulas de la planilla se quedan cortos.** El Dasboard
   miraba hasta la fila 449 con 451 materiales cargados.
6. **Los nombres tienen que coincidir exactos.** "Mi historial" y "Mis órdenes"
   filtran por el nombre del usuario. Hay dos parecidos: "Serrano Juan" (admin)
   y "Juan Serrano" (operario).
7. **Streamlit Cloud cachea.** Con archivos nuevos, hace falta Reboot.

---

## 8. Estado actual

**Funcionando:** inventario y búsqueda, plano de las 35 estanterías, vales con
préstamos y devoluciones parciales, ingresos, pedidos y reclamos, panel de
control, historial, solicitudes de reparación, órdenes con asignación y
seguimiento, cierre técnico, agenda, carga de trabajo, tablero de jefatura con
descarga a CSV, usuarios y permisos.

**Pendiente:**

- **Ubicaciones**: los 451 materiales están sin ubicación cargada. Es el
  pendiente que más impacto tiene para los operarios: hoy la app dice si hay
  stock pero no dónde está. Se carga desde *Asignar ubicaciones*, en lote.
- **Integración órdenes ↔ pañol**: al cerrar una orden, cargar los materiales
  usados y que genere el vale solo. La columna `VALE_REF` ya está reservada.
- **Rediseño de ingresos**: hoy suma al Stock Inicial y deja el renglón como
  historial. Funciona, pero merece su propio circuito con proveedor y remito.
- **Reportes automáticos por mail**: Streamlit no puede mandarlos solo (la app
  solo corre cuando alguien la abre). Se resuelve con un Google Apps Script
  dentro de la planilla.
- **Mantenimiento preventivo**: el grupo del menú ya se llama "Trabajos
  correctivos" justamente para dejarle lugar.
- **Diferenciar JEFE de COORDINADOR**: hoy tienen los mismos permisos.

---

## 9. Cómo trabajar

```bash
# probar sin tocar los datos reales
py -3 -c "open('panol_web/_devdata/MODO_LOCAL','w').close()"
py -3 -m streamlit run panol_web/app.py

# correr las pruebas
cd panol_web && py -3 _prueba_movimientos.py

# publicar
git add -A && git commit -m "..." && git push    # Streamlit redespliega solo
```

Para conectar la planilla real desde cero, ver `SETUP.md`.
