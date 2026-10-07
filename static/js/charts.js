// === Gráficos con Plotly ===

function cargarSerie(){
  const n=document.getElementById('num-serie').value;
  fetch('/api/serie/'+n).then(r=>r.json()).then(d=>Plotly.newPlot('chart-serie',d.data,d.layout,{responsive:true}));
}

function cargarHotCold(){
  const v=document.getElementById('ventana-hc').value;
  fetch('/api/hotcold/'+v).then(r=>r.json()).then(d=>{
    let h='<p style="color:#f87171;font-weight:bold">🔥 Calientes</p>';
    h+='<div class="tags">'+d.calientes.map(n=>`<span class="tag hot">${n}</span>`).join('')+'</div>';
    h+='<p style="color:#60a5fa;font-weight:bold;margin-top:12px">❄️ Fríos</p>';
    h+='<div class="tags">'+d.frios.map(n=>`<span class="tag cold">${n}</span>`).join('')+'</div>';
    document.getElementById('hot-cold-result').innerHTML=h;
  });
}

function esPrimo(numero){
  const n = Number(numero);
  if (!Number.isInteger(n) || n < 2) return false;
  if (n === 2) return true;
  if (n % 2 === 0) return false;
  for (let divisor = 3; divisor <= Math.sqrt(n); divisor += 2){
    if (n % divisor === 0) return false;
  }
  return true;
}

function esCompuesto(numero){
  const n = Number(numero);
  if (!Number.isInteger(n) || n < 4) return false;
  return !esPrimo(n);
}

function actualizarConteoCombinacion(){
  const primos = Number(document.getElementById('cantidad-primos').value);
  const compuestos = Number(document.getElementById('cantidad-compuestos').value);
  const total = primos + compuestos;
  const mensaje = document.getElementById('combinacion-count');
  mensaje.textContent = total === 5
    ? 'Total: 5 números + R7 ✓'
    : 'Total: ' + total + ' números — debe sumar 5';
  mensaje.style.color = total === 5 ? '#86efac' : '#fca5a5';
}

function predecir(){
  const v = document.getElementById('ventana-pred').value;
  const primos = Number(document.getElementById('cantidad-primos').value);
  const compuestos = Number(document.getElementById('cantidad-compuestos').value);
  const container = document.getElementById('resultado-pred');

  if (primos + compuestos !== 5) {
    container.innerHTML = '<div class="alert">La cantidad de primos y compuestos debe sumar 5.</div>';
    return;
  }

  container.innerHTML = '<p style="color:#a78bfa;padding:16px">Calculando predicción y sugerencia combinada...</p>';

  const params = new URLSearchParams({
    primos: String(primos),
    compuestos: String(compuestos)
  });

  return Promise.all([
    fetch('/api/predecir/' + v + '?' + params.toString())
      .then(async response => {
        const content = await response.json();
        if (!response.ok) throw new Error(content.error || 'La predicción no pudo responder.');
        return content;
      }),
    fetch('/api/random?' + params.toString())
      .then(async response => {
        const content = await response.json();
        if (!response.ok) throw new Error(content.error || 'La sugerencia no pudo responder.');
        return content;
      })
  ])
  .then(([d, randomData]) => {
    const ranking = d.slice(0, 5).map(r => Number(r.numero));
    const randomSuggestion = (randomData && randomData.suggestions && randomData.suggestions[0])
      ? randomData.suggestions[0].suggestion.map(Number)
      : [];

    const combined = ranking.slice(0, 5);
    const extra = [...randomSuggestion].reverse().find(n => !combined.includes(n));
    if (combined.length !== 5 || extra === undefined) {
      throw new Error('No se pudo generar una combinación sin números repetidos.');
    }
    const suggestion = combined.concat([extra]);

    let h = '<table><thead><tr><th>Pos.</th><th>Número</th><th>Score</th><th>Frec.hist</th><th>Frec.rec</th><th>Brecha</th></tr></thead><tbody>';
    d.slice(0, 15).forEach((r, i) => {
      h += `<tr><td>${i + 1}</td><td><b>${r.numero}</b></td><td>${r.score.toFixed(4)}</td><td>${r.frecuencia_h}</td><td>${r.frecuencia_r}</td><td>${r.brecha}</td></tr>`;
    });
    h += '</tbody></table>';

    h += '<div class="alert" style="background:#24303c;border-color:#7c3aed; margin-top:16px;">';
    h += '<strong>Combinación de 5 números + R7:</strong> ' + suggestion.join(' ') + '<br>';
    h += '<span style="color:#cbd5e1">' + primos + ' primos + ' + compuestos + ' compuestos + aleatoriedad controlada</span>';
    h += '</div>';
    h += '<div class="alert">⚠️ Modelo estadístico: frecuencia histórica + reciente + brecha + aleatoriedad controlada. No garantiza aciertos.</div>';

    container.innerHTML = h;
  })
  .catch(err => {
    container.innerHTML = '<div class="alert">Error generando predicción: ' + err.message + '</div>';
  });
}

function cargarBolsaNumeros(){
  document.getElementById('chart-bolsa-numeros').innerHTML='<p style="color:#a78bfa;padding:16px">Calculando mapa de calor bolsa vs números...</p>';
  fetch('/api/bolsa_numeros').then(r=>r.json()).then(d=>{
    Plotly.newPlot('chart-bolsa-numeros',d.data,d.layout,{responsive:true});
  });
}

function cargarHeatmap(){
  document.getElementById('chart-heatmap').innerHTML='<p style="color:#a78bfa;padding:20px">Calculando co-ocurrencias para '+56*55/2+' pares posibles...</p>';
  fetch('/api/heatmap').then(r=>r.json()).then(d=>{
    Plotly.newPlot('chart-heatmap',d.data,d.layout,{responsive:true});
    if(d.top_pares && d.top_pares.length){
      let h='<h3 style="color:#c4b5fd;margin-top:20px;margin-bottom:10px">🏆 Top 10 parejas más frecuentes</h3>';
      h+='<table><thead><tr><th>Pos.</th><th>Par</th><th>Veces juntos</th><th>Interpretación</th></tr></thead><tbody>';
      d.top_pares.forEach(([a,b,cnt],i)=>{
        const pct=((cnt/d.top_pares[0][2])*100).toFixed(0);
        h+=`<tr><td>${i+1}</td><td><b>${a} + ${b}</b></td><td>${cnt}</td>
            <td><div style="background:#7c3aed;height:8px;border-radius:4px;width:${pct}%"></div></td></tr>`;
      });
      h+='</tbody></table><div class="alert" style="margin-top:10px">💡 Una pareja frecuente no implica dependencia estadística — el sorteo es independiente cada vez.</div>';
      document.getElementById('top-pares').innerHTML=h;
    }
  });
}
