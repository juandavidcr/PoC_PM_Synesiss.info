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

function predecir(){
  const v=document.getElementById('ventana-pred').value;
  fetch('/api/predecir/'+v).then(r=>r.json()).then(d=>{
    let h='<table><thead><tr><th>Pos.</th><th>Número</th><th>Score</th><th>Frec.hist</th><th>Frec.rec</th><th>Brecha</th></tr></thead><tbody>';
    d.slice(0,15).forEach((r,i)=>{
      h+=`<tr><td>${i+1}</td><td><b>${r.numero}</b></td><td>${r.score.toFixed(4)}</td><td>${r.frecuencia_h}</td><td>${r.frecuencia_r}</td><td>${r.brecha}</td></tr>`;
    });
    h+='</tbody></table><div class="alert">⚠️ Modelo estadístico: frecuencia histórica + reciente + brecha. No garantiza aciertos.</div>';
    document.getElementById('resultado-pred').innerHTML=h;
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
