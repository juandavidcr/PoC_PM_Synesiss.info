// === Agregar registros manuales ===

function addRow(){
  const txt = document.getElementById('input-numeros').value.trim();
  if(!txt){
    alert('Ingresa números separados por comas.');
    return;
  }
  const valores = txt.split(',').map(s=>s.trim());
  const numeros = valores.map(Number);
  if(!(numeros.length===6 || numeros.length===7)){
    alert('Ingresa 6 o 7 números.');
    return;
  }
  if(valores.some(s=>s==='') || numeros.some(n=>!Number.isInteger(n) || n<1 || n>56) || new Set(numeros).size !== numeros.length){
    alert('Ingresa números enteros distintos entre 1 y 56.');
    return;
  }
  const concurso = document.getElementById('input-concurso').value.trim();
  const fecha = document.getElementById('input-fecha').value.trim();
  const bolsa = document.getElementById('input-bolsa').value.trim();
  const payload = { numeros };
  if(concurso) payload.concurso = Number(concurso);
  if(fecha) payload.fecha = fecha;
  if(bolsa) payload.bolsa = Number(bolsa);
  document.getElementById('add-result').textContent = 'Enviando...';
  return fetch('/api/add_row', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  })
    .then(async r => {
      const data = await r.json();
      if(!r.ok) throw new Error(data.error || 'No se pudo agregar el sorteo.');
      return data;
    })
    .then(d => {
      if(d.error){ 
        document.getElementById('add-result').textContent = 'Error: '+d.error; 
        return; 
      }
      document.getElementById('add-result').textContent = 'Fila añadida: CONCURSO '+d.added.CONCURSO;
      return refreshAfterAdding();
    })
    .catch(err => { 
      document.getElementById('add-result').textContent = 'Error: '+err.message; 
    });
}

function fetchFirstRow(){
  return fetch('/api/first_row')
    .then(r => r.json())
    .then(d => {
      if(!d || !d.CONCURSO){ 
        document.getElementById('first-row').innerHTML = '<div class="alert">No hay registros disponibles.</div>'; 
        return; 
      }
      const cols = ['CONCURSO','FECHA','R1','R2','R3','R4','R5','R6','R7','BOLSA'];
      let h = '<table><thead><tr>'+cols.map(c=>`<th>${c}</th>`).join('')+'</tr></thead><tbody>';
      h += '<tr>'+cols.map(c=>`<td>${d[c]===null?"":d[c]}</td>`).join('')+'</tr>';
      h += '</tbody></table>';
      document.getElementById('first-row').innerHTML = h;
    })
    .catch(err => { 
      document.getElementById('first-row').textContent = 'Error: '+err.message; 
    });
}

function refreshAfterAdding(){
  if(document.querySelector('#preview-table table')) cargarPreview(previewLimit);
  return Promise.all([fetchFirstRow(), saveHistoricCsvToLocalStorage()]);
}

function clearAddRowForm(){
  document.getElementById('input-numeros').value = '';
  document.getElementById('input-concurso').value = '';
  document.getElementById('input-fecha').value = '';
  document.getElementById('input-bolsa').value = '';
  document.getElementById('add-result').textContent = '';
  document.getElementById('input-bulk').value = '';
  document.getElementById('bulk-count').textContent = '0';
  document.getElementById('bulk-result').textContent = '';
}

function addRowsBulk(){
  const textarea = document.getElementById('input-bulk');
  const result = document.getElementById('bulk-result');
  const lines = textarea.value.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const count = document.getElementById('bulk-count');
  count.textContent = lines.length;

  if(lines.length === 0){
    result.textContent = 'Introduce al menos una línea.';
    return;
  }
  if(lines.length > 100){
    result.textContent = 'No se pueden añadir más de 100 sorteos.';
    return;
  }

  result.textContent = 'Enviando...';
  return fetch('/api/add_rows', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ lines })
  })
    .then(async response => {
      const data = await response.json();
      if(!response.ok) throw new Error(data.error || 'No se pudieron agregar los sorteos.');
      return data;
    })
    .then(data => {
      if(data.error){
        result.textContent = data.error;
        return;
      }
      result.textContent = `${data.added} sorteo${data.added === 1 ? '' : 's'} añadido${data.added === 1 ? '' : 's'} correctamente.`;
      textarea.value = '';
      count.textContent = '0';
      return refreshAfterAdding();
    })
    .catch(error => {
      result.textContent = `Error: ${error.message}`;
    });
}

async function syncLocalStorageToCsv(){
  const status = document.getElementById('sync-storage-status');
  if(status) status.textContent = 'Sincronizando localStorage → CSV...';

  try {
    const key = 'modelo-numeric-historic-csv';
    const csv = localStorage.getItem(key);
    if(!csv || !csv.trim()){
      if(status) status.textContent = 'No hay CSV guardado en localStorage para sincronizar.';
      return { ok: false, error: 'No hay CSV en localStorage.' };
    }
    const response = await fetch('/api/sync_localstorage_csv', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ csv })
    });
    const data = await response.json();

    if(!response.ok || data.error){
      throw new Error(data.error || 'No se pudo sincronizar a Historic.csv.');
    }

    if(status) status.textContent = `Sincronizado: ${data.rows} registros escritos en Historic.csv.`;
    return data;
  } catch(error) {
    if(status) status.textContent = `Error: ${error.message}`;
    return { ok: false, error: error.message };
  }
}

async function saveHistoricCsvToLocalStorage(){
  const result = document.getElementById('historic-storage-result');
  result.textContent = 'Guardando...';

  try {
    const response = await fetch('/api/historic_csv');
    if(!response.ok){
      throw new Error('No se pudieron leer los datos actuales.');
    }

    const csv = await response.text();
    const key = 'modelo-numeric-historic-csv';
    localStorage.setItem(key, csv);

    const lines = csv.split(/\r?\n/).filter(Boolean).length;
    result.textContent = `Guardado correctamente: ${lines - 1} registros en localStorage.`;

    const sync = await syncLocalStorageToCsv();
    if(!sync.ok){
      result.textContent = `Guardado en localStorage, pero no se pudo escribir en CSV: ${sync.error}`;
    }
  } catch(error) {
    result.textContent = `Error: ${error.message}`;
  }
}
