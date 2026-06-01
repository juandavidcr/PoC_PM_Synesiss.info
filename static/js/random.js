// === Modo aleatorio ===

function cargarAleatorio(){
  const container = document.getElementById('aleatorio-result');
  container.innerHTML = '<p style="color:#a78bfa;padding:16px">Generando sugerencia aleatoria...</p>';
  fetch('/api/random')
    .then(async r => {
      const contentType = r.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        throw new Error(`El servidor respondió con HTML en lugar de JSON (Status: ${r.status}). Verifica el backend.`);
      }
      return r.json();
    })
    .then(data => {
      let html = '';
      data.suggestions.forEach((item, idx) => {
        html += `
          <div class="alert" style="background:#24303c;border-color:#7c3aed;margin-bottom:8px;">
            <strong>Sugerencia ${idx + 1}:</strong> ${item.suggestion.join(' ')}
          </div>
          <p style="margin-top:4px;margin-bottom:16px;color:#94a3b8;">
            Números principales: <strong>${item.main.join(' ')}</strong><br>
            Adicional: <strong>${item.additional}</strong>
          </p>
        `;
      });
      container.innerHTML = html;
    })
    .catch(err => {
      container.innerHTML = `<div class="alert">Error generando sugerencia: ${err.message}</div>`;
    });
}
