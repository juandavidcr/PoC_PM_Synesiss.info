// === Inicialización de la página ===

document.addEventListener('DOMContentLoaded', function(){
  // Cargar gráfico de frecuencias al inicio
  fetch('/api/frecuencias')
    .then(r => r.json())
    .then(d => Plotly.newPlot('chart-freq', d.data, d.layout, {responsive: true}));
  
  // Inicializar selector de números
  initNumeroSelector();
  
  // Cargar números calientes/fríos al inicio
  cargarHotCold();
});
