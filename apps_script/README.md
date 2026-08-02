# Google Form → órdenes de trabajo

Camino alternativo al formulario propio de la app (`?solicitar=1`), por si se
prefiere que la gente del hospital cargue los pedidos desde un Google Form.

Los dos pueden convivir: los dos terminan escribiendo en la pestaña `Ordenes`,
y el tablero de mantenimiento no distingue de dónde vino cada pedido.

```
   Google Form          la planilla                  la app
        │                    │                         │
        │  respuesta         │   Apps Script escribe   │  lee las órdenes
        ├───────────────────►│   la fila en Ordenes    │  y las gestiona
        │                    ├────────────────────────►│
```

---

## El formulario

Los títulos de las preguntas tienen que ser **exactos**, porque el script las
busca por su nombre. Si cambiás uno, cambialo también en `PREGUNTAS` dentro de
`formulario_a_ordenes.gs`.

| Pregunta | Tipo | Obligatoria |
|---|---|:--:|
| `Tu nombre y apellido` | Respuesta corta | sí |
| `Tu email` | Respuesta corta (validación: email) | sí |
| `Tu servicio` | Respuesta corta | sí |
| `Interno o teléfono` | Respuesta corta | no |
| `¿Dónde es?` | Respuesta corta | sí |
| `¿Qué pasa?` | Párrafo | sí |
| `¿Qué tan urgente es?` | Opción múltiple | sí |

**El email conviene pedirlo obligatorio**: es lo que da trazabilidad y lo que
permite después consultar el estado desde *Seguir un pedido* en la app.

Las opciones de urgencia van explicadas, para que no marquen todo urgente. El
script rescata la palabra en mayúsculas de cada una:

```
Urgente — hay riesgo para alguien o el servicio está parado. Se atiende hoy.
Alta — molesta para trabajar pero se puede seguir. Dentro de 3 días.
Media — hay que arreglarlo, no corre apuro. Dentro de la semana.
Baja — puede esperar. Dentro de los 15 días.
```

### Un formulario por sector

Se puede duplicar el formulario y dejar `¿Dónde es?` precargado con el sector,
así en Quirófano 2 nadie escribe nada. Google permite prellenar campos: en el
formulario, menú ⋮ → **Obtener enlace prellenado**.

---

## La instalación

Está paso a paso en el comentario de arriba de `formulario_a_ordenes.gs`.
Resumido:

1. Vinculá las respuestas del formulario a **la misma planilla del pañol**.
2. Extensiones → Apps Script → pegá el archivo.
3. Activadores → `alFormulario`, al enviar el formulario.
4. Probá con la función `probar()` antes de largarlo, y borrá la orden de prueba.

---

## Lo que hay que tener presente

**Lo único duplicado es la numeración.** El script arma el `OT-0001` con el
mismo criterio que la app. El plazo de vencimiento **no** está duplicado: la app
lo calcula sola al asignar la orden, según la prioridad.

**Las columnas se buscan por nombre, no por posición.** Si mañana se agrega una
columna a `Ordenes`, el script sigue andando. Si se *renombra* una, no: por eso
existe `_prueba_apps_script.py`, que compara los nombres que usa el script
contra los que usa la app y avisa si se desfasaron.

**Dos personas pueden mandar el formulario en el mismo segundo.** El script usa
`LockService` para que no salgan dos órdenes con el mismo número.

**La zona horaria va escrita en el script.** No se toma de la planilla, porque
la planilla puede estar configurada en otra y nadie se entera.

**Si el script falla, no se pierde nada.** La respuesta queda igual en la
pestaña del formulario y se puede pasar a mano. En Apps Script → Ejecuciones
está el detalle de cada disparo.

---

## Comparado con el formulario de la app

| | Google Form | Formulario de la app |
|---|---|---|
| Armarlo | Sin código, en 10 minutos | Ya está hecho |
| Fotos del problema | Sí, subida de archivos | No |
| Funciona si la app está caída | Sí | No |
| Ver cómo viene el pedido | No, hay que entrar a la app | Sí, en la misma pantalla |
| Piezas que mantener | Formulario + script + app | Solo la app |
| Si se renombra una columna | Se rompe en silencio | No aplica |

La ventaja fuerte del Google Form son las **fotos**: que el enfermero saque una
foto del enchufe quemado y venga adjunta al pedido. Eso el formulario propio hoy
no lo hace.
