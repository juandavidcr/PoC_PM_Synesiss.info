// Selección explicable a partir del modelo estadístico local.
let recomendacionAgente = null;

function actualizarConteoAgente(){
  const total = Number(document.getElementById('agente-primos').value) + Number(document.getElementById('agente-compuestos').value);
  const mensaje = document.getElementById('agente-count');
  mensaje.textContent = total === 6 ? 'Total: 6 principales + 1 adicional ✓' : `Total: ${total} principales — debe sumar 6`;
  mensaje.style.color = total === 6 ? '#86efac' : '#fca5a5';
}

function leerConjuntoAgente(id){
  const texto = document.getElementById(id).value.trim();
  if(!texto) return null;
  const partes = texto.split(',').map(valor => valor.trim());
  const numeros = partes.map(Number);
  if(partes.some(valor => !valor) || numeros.some(numero => !Number.isInteger(numero) || numero < 1 || numero > 56)){
    throw new Error('Los candidatos deben ser enteros entre 1 y 56, separados por comas.');
  }
  return [...new Set(numeros)];
}

async function generarRecomendacionAgente(){
  const resultado = document.getElementById('agente-result');
  const boton = document.getElementById('agente-generar');
  recomendacionAgente = null;
  try {
    const primos = Number(document.getElementById('agente-primos').value);
    const compuestos = Number(document.getElementById('agente-compuestos').value);
    const ventana = Number(document.getElementById('agente-ventana').value);
    if(!Number.isInteger(primos) || !Number.isInteger(compuestos) || primos < 0 || compuestos < 0 || primos + compuestos !== 6){
      throw new Error('La cantidad de primos y compuestos debe sumar 6.');
    }
    if(!Number.isInteger(ventana) || ventana < 10 || ventana > 500){
      throw new Error('La ventana debe estar entre 10 y 500 sorteos.');
    }
    const payload = {
      primos, compuestos, ventana,
      pool_primos: leerConjuntoAgente('agente-pool-primos'),
      pool_compuestos: leerConjuntoAgente('agente-pool-compuestos'),
      excluir_ultimo: document.getElementById('agente-excluir').checked,
    };
    boton.disabled = true;
    resultado.textContent = 'El agente está analizando el historial y los conjuntos...';
    const response = await fetch('/api/agente', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });
    if(!response.headers.get('content-type')?.includes('application/json')){
      throw new Error('El servidor no tiene disponible el agente. Reinicia Flask para cargar los cambios.');
    }
    const data = await response.json();
    if(!response.ok) throw new Error(data.error || 'No se pudo generar la recomendación.');
    recomendacionAgente = data;
    let html = `<div class="alert"><strong>Principales:</strong> ${data.main.join(', ')}<br><strong>Adicional sugerido:</strong> ${data.additional}<br>Primos: ${data.primos.join(', ') || 'ninguno'} · Compuestos: ${data.compuestos.join(', ') || 'ninguno'}</div>`;
    html += `<p style="color:#94a3b8;font-size:.85rem;margin:12px 0">${data.sorteos_analizados} sorteos analizados; ventana reciente de ${data.ventana} sorteos. El agente ordena por score y reduce agrupaciones de números cercanos.</p>`;
    html += '<table><thead><tr><th>Número</th><th>Conjunto</th><th>Score</th><th>Apariciones históricas</th><th>Apariciones recientes</th><th>Sorteos desde última aparición</th></tr></thead><tbody>';
    data.explicaciones.forEach(row => {
      html += `<tr><td><b>${row.numero}</b></td><td>${row.tipo}</td><td>${row.score.toFixed(4)}</td><td>${row.frecuencia_h}</td><td>${row.frecuencia_r}</td><td>${row.brecha}</td></tr>`;
    });
    html += '</tbody></table><div class="alert">El score resume patrones del historial; no es una probabilidad de ganar ni garantiza aciertos.</div>';
    html += '<button type="button" onclick="usarRecomendacionAgente()" style="margin-top:12px">Usar principales en el verificador</button>';
    resultado.innerHTML = html;
  } catch(error) {
    resultado.textContent = `Error: ${error.message}`;
  } finally {
    boton.disabled = false;
  }
}

function usarRecomendacionAgente(){
  if(!recomendacionAgente) return;
  seleccionados.clear();
  recomendacionAgente.main.forEach(numero => seleccionados.add(numero));
  document.querySelectorAll('#picker .num-btn').forEach(boton => {
    boton.classList.toggle('selected', seleccionados.has(Number(boton.textContent)));
  });
  document.getElementById('seleccion-label').textContent = 'Seleccionados: ' + recomendacionAgente.main.join(', ');
  document.getElementById('resultado-verif').textContent = '';
  document.getElementById('picker').scrollIntoView({behavior: 'smooth', block: 'center'});
}

function inicializarAgente(){
  const numeros = Array.from({length: 56}, (_, index) => index + 1);
  document.getElementById('agente-conjunto-primos').textContent = numeros.filter(esPrimo).join(', ');
  document.getElementById('agente-conjunto-compuestos').textContent = numeros.filter(esCompuesto).join(', ');
  actualizarConteoAgente();
}
