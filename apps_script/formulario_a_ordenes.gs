/**
 * Convierte cada respuesta de un Google Form en una orden de trabajo.
 *
 * Es el camino alternativo al formulario propio de la app (?solicitar=1). Sirve
 * si se prefiere que la gente del hospital cargue los pedidos desde un Google
 * Form: el script agarra la respuesta y escribe la fila en `Ordenes` con el
 * mismo formato que escribiría la app, así el pedido aparece en el tablero sin
 * que nadie transcriba nada.
 *
 * Los dos caminos pueden convivir: los dos terminan escribiendo en `Ordenes`.
 *
 * ── Qué replica de la app ──────────────────────────────────────────────────
 * Solo la numeración (OT-0001, OT-0002...) y el sello de tiempo. El plazo de
 * vencimiento NO se calcula acá: la app lo calcula sola al asignar la orden,
 * según la prioridad. Ver SLA_DIAS en sheets_backend.py.
 *
 * ── Instalación ────────────────────────────────────────────────────────────
 * 1. Armá el Google Form con las preguntas de PREGUNTAS (abajo), con esos
 *    títulos exactos. Marcá como obligatorias las que acá figuran así.
 * 2. En el formulario: Respuestas → Vincular a Hojas de cálculo → elegí LA
 *    MISMA planilla del pañol. Se crea una pestaña nueva de respuestas; no la
 *    toques, es el respaldo.
 * 3. En la planilla: Extensiones → Apps Script. Pegá este archivo entero.
 * 4. Arriba, en el reloj (Activadores) → Añadir activador:
 *       Función:            alFormulario
 *       Origen del evento:  Desde la hoja de cálculo
 *       Tipo de evento:     Al enviar el formulario
 * 5. Google va a pedir permisos la primera vez. Son para escribir en tu propia
 *    planilla.
 * 6. Probá mandando una respuesta y fijate que aparezca en `Ordenes`.
 *
 * ── Si algo falla ──────────────────────────────────────────────────────────
 * Apps Script → Ejecuciones muestra el detalle de cada disparo. Los pedidos que
 * no se hayan podido convertir quedan igual en la pestaña de respuestas: no se
 * pierde nada, se pueden pasar a mano.
 */

// Zona horaria del hospital. Va fija y no se toma de la planilla, porque la
// planilla puede quedar configurada en otra y nadie se entera.
var ZONA = 'America/Argentina/Buenos_Aires';

var HOJA_ORDENES = 'Ordenes';
var HOJA_ESTADOS = 'OT_Estados';

// Título exacto de cada pregunta del formulario -> qué campo alimenta.
// Si cambiás un título en el formulario, cambialo también acá.
var PREGUNTAS = {
  nombre:      'Tu nombre y apellido',
  email:       'Tu email',
  servicio:    'Tu servicio',
  contacto:    'Interno o teléfono',
  area:        '¿Dónde es?',
  descripcion: '¿Qué pasa?',
  prioridad:   '¿Qué tan urgente es?'
};

var PRIORIDADES = ['URGENTE', 'ALTA', 'MEDIA', 'BAJA'];
var PRIORIDAD_POR_DEFECTO = 'MEDIA';


/** Punto de entrada: lo llama el activador con cada respuesta. */
function alFormulario(e) {
  // Dos personas pueden mandar el formulario en el mismo segundo. Sin esto,
  // las dos leerían el mismo último número y quedarían dos OT-0007.
  var candado = LockService.getScriptLock();
  candado.waitLock(30000);
  try {
    crearOrdenDesdeRespuesta(e.namedValues || {});
  } finally {
    candado.releaseLock();
  }
}


function crearOrdenDesdeRespuesta(respuestas) {
  var area = leer(respuestas, PREGUNTAS.area);
  var descripcion = leer(respuestas, PREGUNTAS.descripcion);

  // Sin lugar o sin problema no hay orden que valga. La respuesta igual queda
  // guardada en la pestaña del formulario.
  if (!area || !descripcion) {
    Logger.log('Respuesta incompleta, no se creó la orden: ' + JSON.stringify(respuestas));
    return;
  }

  var planilla = SpreadsheetApp.getActiveSpreadsheet();
  var hoja = planilla.getSheetByName(HOJA_ORDENES);
  if (!hoja) {
    throw new Error('No existe la pestaña "' + HOJA_ORDENES + '" en esta planilla.');
  }

  var idOt = siguienteIdOt(hoja);
  var momento = ahora();
  var nombre = leer(respuestas, PREGUNTAS.nombre);
  var servicio = leer(respuestas, PREGUNTAS.servicio);
  var contacto = leer(respuestas, PREGUNTAS.contacto);

  // El servicio y el interno van juntos en OBSERVACIONES, igual que hace la app
  var observaciones = [servicio, contacto].filter(function (x) { return x; }).join(' · ');

  escribirFila(hoja, {
    'ID_OT': idOt,
    'FECHA_ALTA': momento,
    'SOLICITANTE': nombre,
    'SOLICITANTE_EMAIL': leer(respuestas, PREGUNTAS.email).toLowerCase(),
    'AREA': area,
    'DESCRIPCION': descripcion,
    'PRIORIDAD': prioridadDe(leer(respuestas, PREGUNTAS.prioridad)),
    'ESTADO': 'SOLICITADA',
    'OBSERVACIONES': observaciones
  });

  anotarEstado(planilla, idOt, nombre, descripcion.substring(0, 120), momento);
  Logger.log('Creada ' + idOt + ' desde el formulario.');
}


/** La fecha y hora del hospital, con el formato que usa la app. */
function ahora() {
  return Utilities.formatDate(new Date(), ZONA, 'yyyy-MM-dd HH:mm:ss');
}


/** Una respuesta del formulario, o cadena vacía si no vino. */
function leer(respuestas, titulo) {
  var valor = respuestas[titulo];
  if (!valor) return '';
  return String(Array.isArray(valor) ? valor[0] : valor).trim();
}


/**
 * La prioridad, sacada del texto que eligió la persona.
 *
 * En el formulario las opciones se escriben explicadas ("Urgente — hay riesgo
 * para alguien...") para que no marquen todo urgente. Acá se rescata la palabra.
 */
function prioridadDe(texto) {
  var arriba = String(texto || '').toUpperCase();
  for (var i = 0; i < PRIORIDADES.length; i++) {
    if (arriba.indexOf(PRIORIDADES[i]) !== -1) return PRIORIDADES[i];
  }
  return PRIORIDAD_POR_DEFECTO;
}


/**
 * El próximo número de orden, con el mismo criterio que la app: el mayor que
 * haya más uno, con cuatro dígitos.
 */
function siguienteIdOt(hoja) {
  var columna = indiceDeColumna(hoja, 'ID_OT');
  var ultimaFila = hoja.getLastRow();
  var maximo = 0;

  if (ultimaFila > 1) {
    var valores = hoja.getRange(2, columna, ultimaFila - 1, 1).getValues();
    for (var i = 0; i < valores.length; i++) {
      var encontrado = String(valores[i][0]).match(/(\d+)/);
      if (encontrado) {
        var numero = parseInt(encontrado[1], 10);
        if (numero > maximo) maximo = numero;
      }
    }
  }
  return 'OT-' + ('0000' + (maximo + 1)).slice(-4);
}


/** Deja una fila en la bitácora, igual que _anotar_estado() en la app. */
function anotarEstado(planilla, idOt, usuario, nota, momento) {
  var hoja = planilla.getSheetByName(HOJA_ESTADOS);
  if (!hoja) return;  // si la app todavía no creó la hoja, no es motivo de error

  var columna = indiceDeColumna(hoja, 'ID');
  var ultimaFila = hoja.getLastRow();
  var maximo = 0;
  if (ultimaFila > 1) {
    var valores = hoja.getRange(2, columna, ultimaFila - 1, 1).getValues();
    for (var i = 0; i < valores.length; i++) {
      var numero = parseInt(valores[i][0], 10);
      if (!isNaN(numero) && numero > maximo) maximo = numero;
    }
  }

  escribirFila(hoja, {
    'ID': maximo + 1,
    'ID_OT': idOt,
    'FECHA_HORA': momento,
    'ESTADO': 'SOLICITADA',
    'USUARIO': usuario,
    'NOTA': nota
  });
}


/**
 * Agrega una fila ubicando cada valor por el nombre de su encabezado.
 *
 * Por nombre y no por posición a propósito: si mañana se agrega o se mueve una
 * columna en `Ordenes`, esto sigue funcionando. Las columnas que no se
 * mencionan quedan vacías, que es lo que corresponde en una orden recién
 * pedida (todavía no tiene responsable ni fecha de cierre).
 */
function escribirFila(hoja, datos) {
  var encabezados = hoja.getRange(1, 1, 1, hoja.getLastColumn()).getValues()[0];
  var fila = [];

  for (var i = 0; i < encabezados.length; i++) {
    var nombre = String(encabezados[i]).trim();
    fila.push(datos.hasOwnProperty(nombre) ? datos[nombre] : '');
  }
  hoja.appendRow(fila);
}


/** En qué columna está un encabezado. Explota si no está, que es lo que se quiere. */
function indiceDeColumna(hoja, nombre) {
  var encabezados = hoja.getRange(1, 1, 1, hoja.getLastColumn()).getValues()[0];
  for (var i = 0; i < encabezados.length; i++) {
    if (String(encabezados[i]).trim() === nombre) return i + 1;
  }
  throw new Error('La pestaña "' + hoja.getName() + '" no tiene la columna "' + nombre + '".');
}


/**
 * Prueba a mano, sin tener que mandar el formulario.
 *
 * Se corre desde Apps Script: elegí `probar` en el desplegable y dale Ejecutar.
 * Crea una orden de mentira en la planilla REAL, así que borrala después.
 */
function probar() {
  var respuestas = {};
  respuestas[PREGUNTAS.nombre] = ['Prueba Apps Script'];
  respuestas[PREGUNTAS.email] = ['prueba@ejemplo.com'];
  respuestas[PREGUNTAS.servicio] = ['Enfermería'];
  respuestas[PREGUNTAS.contacto] = ['interno 999'];
  respuestas[PREGUNTAS.area] = ['Sala de prueba'];
  respuestas[PREGUNTAS.descripcion] = ['Esto es una prueba del script, se puede borrar'];
  respuestas[PREGUNTAS.prioridad] = ['Baja — puede esperar'];
  crearOrdenDesdeRespuesta(respuestas);
}
