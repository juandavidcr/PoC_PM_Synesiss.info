// === Agregar registros manuales ===

function addRow(){
  const txt = document.getElementById('input-numeros').value.trim();
  if(!txt){
    alert('Ingresa números separados por comas.');
    return;
  }
  const numeros = txt.split(',').map(s=>s.trim()).filter(s=>s!='').map(Number);
  if(!(numeros.length===6 || numeros.length===7)){
    alert('Ingresa 6 o 7 números.');
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
  fetch('/api/add_row', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  })
    .then(r => r.json())
    .then(d => {
      if(d.error){ 
        document.getElementById('add-result').textContent = 'Error: '+d.error; 
        return; 
      }
      document.getElementById('add-result').textContent = 'Fila añadida: CONCURSO '+d.added.CONCURSO;
      fetchFirstRow();
    })
    .catch(err => { 
      document.getElementById('add-result').textContent = 'Error: '+err.message; 
    });
}

function fetchFirstRow(){
  fetch('/api/first_row')
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
