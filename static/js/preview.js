// === Vista previa del CSV ===

let previewExpanded = false;
let previewLimit = 100;
const STORAGE_KEY = 'melate_table_edits';

function cargarPreview(limit = 500){
  const previewEl = document.getElementById('preview-table');
  const infoEl = document.getElementById('preview-info');
  previewLimit = limit;
  previewExpanded = limit > 100;
  document.getElementById('toggle-preview-btn').textContent = previewExpanded ? 'Ocultar preview' : 'Mostrar preview';
  infoEl.textContent = `Mostrando hasta ${limit} filas.`;
  previewEl.innerHTML = '<p style="color:#a78bfa;padding:16px">Cargando vista previa...</p>';
  fetch(`/api/preview?limit=${limit}`)
    .then(r => r.json())
    .then(rows => {
      if(!rows.length){
        previewEl.innerHTML = '<div class="alert">No hay filas disponibles.</div>';
        return;
      }
      // Cargar ediciones guardadas en localStorage
      const edits = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      
      const cols = Object.keys(rows[0]);
      let html = '<table><thead><tr>' + cols.map(c=>`<th>${c}</th>`).join('') + '</tr></thead><tbody>';
      rows.forEach((row, rowIdx) => {
        html += '<tr>';
        cols.forEach(col => {
          const cellKey = `${rowIdx}-${col}`;
          const editedValue = edits[cellKey];
          const value = editedValue !== undefined ? editedValue : (row[col]===null?"":row[col]);
          html += `<td contenteditable="true" data-row="${rowIdx}" data-col="${col}" class="editable-cell">${value}</td>`;
        });
        html += '</tr>';
      });
      html += '</tbody></table>';
      previewEl.innerHTML = html;
      
      // Agregar event listeners a celdas editables
      attachEditListeners();
    })
    .catch(err => {
      previewEl.innerHTML = `<div class="alert">Error cargando vista previa: ${err.message}</div>`;
    });
}

function attachEditListeners(){
  const cells = document.querySelectorAll('.editable-cell');
  cells.forEach(cell => {
    cell.addEventListener('blur', saveCellEdit);
    cell.addEventListener('keydown', (e) => {
      if(e.key === 'Enter' && !e.shiftKey){
        e.preventDefault();
        cell.blur();
      }
    });
  });
}

function saveCellEdit(event){
  const cell = event.target;
  const rowIdx = cell.dataset.row;
  const col = cell.dataset.col;
  const value = cell.textContent;
  const cellKey = `${rowIdx}-${col}`;
  
  // Guardar en localStorage
  const edits = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  edits[cellKey] = value;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(edits));
}

function togglePreview(){
  previewExpanded = !previewExpanded;
  if(previewExpanded){
    cargarPreview(500);
  } else {
    cargarPreview(100);
  }
}
