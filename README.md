# Sistema de Gestión Integral de Mantenimiento

Aplicación en uso real para el pañol y el mantenimiento correctivo de un
hospital. Arrancó como control de stock del depósito y hoy cubre el circuito
completo: desde que alguien pide una reparación hasta que se cierra la orden y
se descuentan los materiales que se usaron.

Desarrollado por **Juan Serrano** — Pañol / Área de Mantenimiento.

---

## Por qué existe

El punto de partida fue el pañol. El stock, los préstamos, los consumos y la
ubicación de los materiales dependían de registros separados y del conocimiento
de quienes trabajaban ahí. Eso hacía difícil anticipar faltantes, encontrar un
material y relacionar cada entrega con el trabajo realizado.

- **Inventario sin una vista única.** No se podía consultar rápido qué había,
  cuánto quedaba ni dónde estaba.
- **Movimientos sin trazabilidad.** Entregas, consumos, préstamos y devoluciones
  no formaban un historial integrado.
- **Dependencia del conocimiento individual.** Encontrar materiales y detectar
  faltantes dependía demasiado de la experiencia de cada persona.
- **Mantenimiento por canales separados.** Las solicitudes llegaban por teléfono
  o de palabra, sin quedar conectadas con responsables, materiales y cierre.

## Qué abarca hoy

| Módulo | Qué incluye |
|---|---|
| **Pañol e inventario** | Búsqueda de materiales, stock calculado por movimientos, mínimos, ubicaciones y plano físico |
| **Movimientos** | Vales, consumos, préstamos, devoluciones parciales, ingresos, historial, pedidos y reclamos |
| **Mantenimiento correctivo** | Solicitudes, prioridad y plazo, asignación de responsables, agenda, carga de trabajo, estados y cierre técnico |
| **Gestión y control** | Perfiles por rol, seguimiento de órdenes, tablero de jefatura, indicadores y descarga de datos |

Hoy trabaja con datos reales: más de 490 materiales, el plano de 35 estanterías
y todo el circuito de movimientos del pañol.

El **formulario público** es una de las puertas de entrada: cualquier sector del
hospital inicia el circuito escaneando un QR, sin necesidad de usuario.

    mantenimiento2026.streamlit.app/?solicitar=1

---


- **[CONTEXTO.md](CONTEXTO.md)** — cómo funciona por dentro: modelo de datos,
  permisos, decisiones tomadas y trampas conocidas. Es el documento para
  ponerse al día sin haber participado de la construcción.
- **[SETUP.md](SETUP.md)** — paso a paso para dejar la app operativa: cuenta de
  servicio de Google, publicación y alta de usuarios.
