// === Selector de números y verificación ===

const seleccionados = new Set();

function initNumeroSelector(){
  const picker = document.getElementById('picker');
  for(let i=1; i<=56; i++){
    const btn = document.createElement('button');
    btn.className = 'num-btn';
    btn.textContent = i;
    btn.onclick = () => {
      if(seleccionados.has(i)){
        seleccionados.delete(i);
        btn.classList.remove('selected');
      } else if(seleccionados.size < 6){
        seleccionados.add(i);
        btn.classList.add('selected');
      }
      document.getElementById('seleccion-label').textContent =
        'Seleccionados: ' + (seleccionados.size ? [...seleccionados].sort((a,b)=>a-b).join(', ') : 'ninguno');
    };
    picker.appendChild(btn);
  }
}

function verificar(){
  if(seleccionados.size !== 6){
    alert('Selecciona exactamente 6 números.');
    return;
  }
  document.getElementById('loader').style.display = 'block';
  document.getElementById('resultado-verif').innerHTML = '';
  fetch('/api/verificar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({numeros: [...seleccionados]})
  })
  .then(r => r.json())
  .then(d => {
    document.getElementById('loader').style.display = 'none';
    if(!d.length){
      document.getElementById('resultado-verif').innerHTML =
        '<div class="alert">No se encontraron sorteos con 3 o más coincidencias.</div>';
      return;
    }
    let h = `<p style="margin:10px 0;color:#a78bfa">${d.length} sorteos con ≥3 coincidencias:</p>`;
    h += '<table><thead><tr><th>Concurso</th><th>Fecha</th><th>Sorteo</th><th>Match</th><th>Aciertos</th></tr></thead><tbody>';
    d.forEach(r => {
      h += `<tr><td>${r.concurso}</td><td>${r.fecha}</td><td>${r.numeros_sorteo.join(', ')}</td>
          <td style="color:#fbbf24">${r.numeros_match.join(', ')}</td><td><b>${r.coincidencias}</b></td></tr>`;
    });
    h += '</tbody></table>';
    document.getElementById('resultado-verif').innerHTML = h;
  });
}
