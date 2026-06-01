# Code Citations

## License: Creative Commons
https://github.com/fer-moreira/Network-Tools/blob/ef8a46136544213e36c723290062644ea46e38b0/Netool/netool.py

```
Estructura clara: 7 números por sorteo (R1-R6 + R7 adicional) con fecha. Voy a escribir la app Flask completa ahora.No tengo herramienta de edición de archivos disponible. Te presento el código completo para que lo copies directamente en `modelopredictJD.py`:

```python
"""
modelopredictJD.py
App Flask de análisis y predicción de Melate
Basada en Historic.csv (columnas: CONCURSO, R1-R7, FECHA)
"""

import os
import pandas as pd
import numpy as np
from flask import Flask, render_template_string, request, jsonify
from collections import Counter
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

# ── Configuración ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "Historic.csv")
NUMEROS_MAX = 56   # Melate: 1-56
BOLA_ADICIONAL = True  # R7 es número adicional (Bolita)

app = Flask(__name__)

# ── Carga y preprocesamiento de datos ────────────────────────────────────────
def cargar_datos():
    df = pd.read_csv(CSV_PATH, dtype=str)
    df["FECHA"] = pd.to_datetime(df["FECHA"])
    cols_num = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=cols_num)
    df = df.sort_values("FECHA").reset_index(drop=True)
    return df

# ── Análisis de frecuencias ───────────────────────────────────────────────────
def calcular_frecuencias(df, incluir_adicional=False):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    if incluir_adicional:
        cols.append("R7")
    todos = df[cols].values.flatten().astype(int)
    conteo = Counter(todos)
    freq = pd.DataFrame(
        [(n, conteo.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)],
        columns=["numero", "frecuencia"]
    ).sort_values("frecuencia", ascending=False)
    return freq

# ── Frecuencia en ventana temporal (últimos N sorteos) ────────────────────────
def frecuencia_reciente(df, ventana=100, incluir_adicional=False):
    sub = df.tail(ventana)
    return calcular_frecuencias(sub, incluir_adicional)

# ── Análisis de "números fríos" y "calientes" ─────────────────────────────────
def hot_cold(df, ventana=30):
    reciente = calcular_frecuencias(df.tail(ventana))
    historico = calcular_frecuencias(df)
    merged = reciente.merge(historico, on="numero", suffixes=("_rec", "_hist"))
    merged["z_score"] = (
        (merged["frecuencia_rec"] - merged["frecuencia_rec"].mean())
        / (merged["frecuencia_rec"].std() + 1e-9)
    )
    calientes = merged.nlargest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    frios = merged.nsmallest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    return calientes, frios

# ── Modelo predictivo: probabilidad ponderada (bayesian-like) ─────────────────
def predecir_numeros(df, n_pred=6, ventana_reciente=50):
    """
    Combina frecuencia histórica + frecuencia reciente + brecha (números atrasados).
    Devuelve lista ordenada de candidatos con su score.
    """
    freq_hist = calcular_frecuencias(df)
    freq_rec  = frecuencia_reciente(df, ventana=ventana_reciente)
    
    # Calcular brecha: sorteos desde la última aparición de cada número
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    ultimas = {}
    for idx, row in df.iterrows():
        for c in cols:
            n = int(row[c])
            ultimas[n] = idx   # último sorteo donde apareció
    total = len(df)
    brecha = {n: (total - ultimas.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)}
    brecha_s = pd.DataFrame(list(brecha.items()), columns=["numero", "brecha"])

    # Merge de señales
    score = freq_hist.merge(freq_rec, on="numero", suffixes=("_h", "_r"))
    score = score.merge(brecha_s, on="numero")
    
    # Normalizar cada señal a [0,1]
    for col in ["frecuencia_h", "frecuencia_r", "brecha"]:
        rng = score[col].max() - score[col].min()
        score[col + "_n"] = (score[col] - score[col].min()) / (rng + 1e-9)

    # Score compuesto: 40% hist + 40% reciente + 20% brecha
    score["score"] = (
        0.40 * score["frecuencia_h_n"]
        + 0.40 * score["frecuencia_r_n"]
        + 0.20 * score["brecha_n"]
    )
    score = score.sort_values("score", ascending=False).reset_index(drop=True)
    return score[["numero", "score", "frecuencia_h", "frecuencia_r", "brecha"]]

# ── Verificar si una combinación del usuario ha ganado antes ──────────────────
def verificar_combinacion(df, numeros_usuario: list[int]):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    set_usr = set(numeros_usuario)
    resultados = []
    for _, row in df.iterrows():
        set_row = {int(row[c]) for c in cols}
        coincidencias = set_usr & set_row
        if len(coincidencias) >= 3:
            resultados.append({
                "concurso": row["CONCURSO"],
                "fecha": str(row["FECHA"].date()),
                "numeros_sorteo": sorted(set_row),
                "coincidencias": len(coincidencias),
                "numeros_match": sorted(coincidencias),
            })
    return sorted(resultados, key=lambda x: -x["coincidencias"])[:20]

# ── Gráficos Plotly ───────────────────────────────────────────────────────────
def grafico_frecuencias(df):
    freq = calcular_frecuencias(df)
    fig = px.bar(
        freq, x="numero", y="frecuencia",
        title="Frecuencia histórica de números (R1-R6)",
        labels={"numero": "Número", "frecuencia": "Veces sorteado"},
        color="frecuencia",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(xaxis=dict(dtick=1), plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
                      font_color="white", title_font_size=16)
    return fig.to_json()

def grafico_serie_tiempo(df, numero: int):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    df["aparece"] = df[cols].apply(lambda r: int(numero in r.values), axis=1)
    df["acumulado"] = df["aparece"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["FECHA"], y=df["acumulado"],
        mode="lines", name=f"Número {numero} acumulado",
        line=dict(color="#a78bfa", width=2)
    ))
    fig.update_layout(
        title=f"Apariciones acumuladas del número {numero} en el tiempo",
        xaxis_title="Fecha", yaxis_title="Apariciones acumuladas",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white"
    )
    return fig.to_json()

def grafico_heatmap_pares(df):
    """Mapa de calor de co-ocurrencias entre números (R1-R6)."""
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    numeros = range(1, NUMEROS_MAX + 1)
    mat = np.zeros((NUMEROS_MAX, NUMEROS_MAX), dtype=int)
    for _, row in df.iterrows():
        ns = [int(row[c]) for c in cols]
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                a, b = ns[i] - 1, ns[j] - 1
                mat[a][b] += 1
                mat[b][a] += 1
    fig = go.Figure(go.Heatmap(
        z=mat, colorscale="Plasma",
        hovertemplate="(%{x}, %{y}): %{z}<extra></extra>"
    ))
    fig.update_layout(
        title="Co-ocurrencias entre pares de números",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white", height=600,
    )
    return fig.to_json()

# ── HTML Template ─────────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Predictor Melate — JD</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #13131f; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; padding: 20px; }
  h1 { color: #a78bfa; text-align: center; margin-bottom: 8px; font-size: 2rem; }
  .subtitle { text-align: center; color: #94a3b8; margin-bottom: 30px; font-size: .9rem; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media(max-width:768px){ .grid { grid-template-columns: 1fr; } }
  .card { background: #1e1e2e; border-radius: 12px; padding: 20px; border: 1px solid #2e2e4e; }
  .card h2 { color: #c4b5fd; margin-bottom: 14px; font-size: 1.1rem; }
  input[type=text], input[type=number], select {
    background: #2a2a3e; border: 1px solid #4c4c75; color: #e2e8f0;
    border-radius: 6px; padding: 8px 12px; width: 100%; margin-bottom: 10px; font-size: .95rem;
  }
  button {
    background: #7c3aed; color: white; border: none; border-radius: 8px;
    padding: 10px 20px; cursor: pointer; font-size: .95rem; width: 100%;
    transition: background .2s;
  }
  button:hover { background: #6d28d9; }
  .numeros-selector { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
  .num-btn {
    width: 42px; height: 42px; border-radius: 50%; background: #2a2a3e;
    border: 2px solid #4c4c75; color: #e2e8f0; cursor: pointer;
    font-weight: bold; transition: all .15s;
  }
  .num-btn.selected { background: #7c3aed; border-color: #a78bfa; color: white; }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; }
  .tag { background: #7c3aed; border-radius: 20px; padding: 4px 12px; font-size: .85rem; }
  .tag.cold { background: #1d4ed8; }
  .tag.hot { background: #dc2626; }
  #resultado-pred { margin-top: 14px; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th { background: #2a2a3e; padding: 8px; text-align: left; color: #a78bfa; }
  td { padding: 7px 8px; border-bottom: 1px solid #2a2a3e; }
  tr:hover td { background: #252535; }
  .alert { background: #1e3a5f; border-left: 3px solid #3b82f6; padding: 10px; border-radius: 6px; margin-top: 10px; font-size: .85rem;}
  .full { grid-column: 1 / -1; }
  #loader { display:none; text-align:center; color: #a78bfa; margin-top: 10px; }
</style>
</head>
<body>
<h1>🎱 Predictor Melate</h1>
<p class="subtitle">Análisis estadístico del sorteo histórico — no garantiza resultados</p>

<div class="grid">
  <!-- Frecuencias Históricas -->
  <div class="card full">
    <h2>📊 Frecuencia histórica de números</h2>
    <div id="chart-freq"></div>
  </div>

  <!-- Serie de tiempo por número -->
  <div class="card">
    <h2>📈 Serie de tiempo por número</h2>
    <label>Número a analizar (1-56):</label>
    <input type="number" id="num-serie" min="1" max="56" value="7">
    <button onclick="cargarSerie()">Ver serie de tiempo</button>
    <div id="chart-serie"></div>
  </div>

  <!-- Hot & Cold -->
  <div class="card">
    <h2>🔥❄️ Números calientes y fríos</h2>
    <label>Ventana de sorteos recientes:</label>
    <input type="number" id="ventana-hc" value="30" min="10" max="500">
    <button onclick="cargarHotCold()">Analizar</button>
    <div id="hot-cold-result" style="margin-top:12px;"></div>
  </div>

  <!-- Predicción -->
  <div class="card">
    <h2>🔮 Predicción de próximos números</h2>
    <label>Ventana reciente para el modelo:</label>
    <input type="number" id="ventana-pred" value="50" min="10" max="500">
    <button onclick="predecir()">Generar predicción</button>
    <div id="resultado-pred"></div>
  </div>

  <!-- Verificador de combinación -->
  <div class="card full">
    <h2>🎯 Verifica tu combinación contra el historial</h2>
    <p style="color:#94a3b8; font-size:.85rem; margin-bottom:12px;">
      Selecciona exactamente 6 números y verifica cuántas coincidencias tuvieron en sorteos pasados.
    </p>
    <div class="numeros-selector" id="picker"></div>
    <p id="seleccion-label" style="color:#a78bfa; margin-bottom:10px;">Seleccionados: ninguno</p>
    <button onclick="verificar()">Verificar en historial</button>
    <div id="loader">Buscando coincidencias...</div>
    <div id="resultado-verif"></div>
  </div>

  <!-- Heatmap de co-ocurrencias -->
  <div class="card full">
    <h2>🧩 Co-ocurrencias entre pares de números</h2>
    <button onclick="cargarHeatmap()">Cargar mapa de calor (puede tardar)</button>
    <div id="chart-heatmap"></div>
  </div>
</div>

<script>
// ── Cargar gráfico de frecuencias al inicio ───────────────────────────────
fetch('/api/frecuencias')
  .then(r => r.json())
  .then(data => Plotly.newPlot('chart-freq', data.data, data.layout, {responsive:true}));

// ── Serie de tiempo ───────────────────────────────────────────────────────
function cargarSerie() {
  const n = document.getElementById('num-serie').value;
  fetch('/api/serie/' + n)
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-serie', data.data, data.layout, {responsive:true}));
}

// ── Hot & Cold ────────────────────────────────────────────────────────────
function cargarHotCold() {
  const v = document.getElementById('ventana-hc').value;
  fetch('/api/hotcold/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<p style="color:#f87171;font-size:.9rem;font-weight:bold;">🔥 Calientes</p>';
      html += '<div class="tags">' + data.calientes.map(n => `<span class="tag hot">${n}</span>`).join('') + '</div>';
      html += '<p style="color:#60a5fa;font-size:.9rem;font-weight:bold;margin-top:12px;">❄️ Fríos</p>';
      html += '<div class="tags">' + data.frios.map(n => `<span class="tag cold">${n}</span>`).join('') + '</div>';
      document.getElementById('hot-cold-result').innerHTML = html;
    });
}

// ── Predicción ────────────────────────────────────────────────────────────
function predecir() {
  const v = document.getElementById('ventana-pred').value;
  fetch('/api/predecir/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<table><thead><tr><th>Pos.</th><th>Número</th><th>Score</th><th>Frec. hist.</th><th>Frec. rec.</th><th>Brecha</th></tr></thead><tbody>';
      data.slice(0, 15).forEach((row, i) => {
        html += `<tr><td>${i+1}</td><td><b>${row.numero}</b></td><td>${row.score.toFixed(4)}</td><td>${row.frecuencia_h}</td><td>${row.frecuencia_r}</td><td>${row.brecha}</td></tr>`;
      });
      html += '</tbody></table>';
      html += '<div class="alert" style="margin-top:10px;">⚠️ El modelo combina frecuencia histórica, frecuencia reciente y brecha de aparición. No es garantía de acierto.</div>';
      document.getElementById('resultado-pred').innerHTML = html;
    });
}

// ── Picker de números ─────────────────────────────────────────────────────
const seleccionados = new Set();
const picker = document.getElementById('picker');
for (let i = 1; i <= 56; i++) {
  const btn = document.createElement('button');
  btn.className = 'num-btn';
  btn.textContent = i;
  btn.onclick = () => {
    if (seleccionados.has(i)) {
      seleccionados.delete(i);
      btn.classList.remove('selected');
    } else if (seleccionados.size < 6) {
      seleccionados.add(i);
      btn.classList.add('selected');
    }
    document.getElementById('seleccion-label').textContent =
      'Seleccionados: ' + (seleccionados.size ? [...seleccionados].sort((a,b)=>a-b).join(', ') : 'ninguno');
  };
  picker.appendChild(btn);
}

function verificar() {
  if (seleccionados.size !== 6) { alert('Selecciona exactamente 6 números.'); return; }
  document.getElementById('loader').style.display = 'block';
  document.getElementById('resultado-verif').innerHTML = '';
  fetch('/api/verificar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({numeros: [...seleccionados]})
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('loader').style.display = 'none';
    if (!data.length) {
      document.getElementById('resultado-verif').innerHTML =
        '<div class="alert">No se encontraron sorteos con 3 o más coincidencias.</div>';
      return;
    }
    let html = `<p style="margin:10px 0;color:#a78bfa;">${data.length} sorteos con ≥3 coincidencias:</p>`;
    html += '<table><thead><tr><th>Concurso</th><th>Fecha</th><th>Sorteo</th><th>Match</th><th>Aciertos</th></tr></thead><tbody>';
    data.forEach(r => {
      html += `<tr><td>${r.concurso}</td><td>${r.fecha}</td><td>${r.numeros_sorteo.join(', ')}</td>
               <td style="color:#fbbf24;">${r.numeros_match.join(', ')}</td>
               <td><b>${r.coincidencias}</b></td></tr>`;
    });
    html += '</tbody></table>';
    document.getElementById('resultado-verif').innerHTML = html;
  });
}

// ── Heatmap ───────────────────────────────────────────────────────────────
function cargarHeatmap() {
  document.getElementById('chart-heatmap').innerHTML = '<p style="color:#a78bfa;padding:20px;">Calculando... puede tomar unos segundos.</p>';
  fetch('/api/heatmap')
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-heatmap', data.data, data.layout, {responsive:true}));
}

// Cargar hot/cold automáticamente
cargarHotCold();
</script>
</body>
</html>
"""

# ── Rutas Flask ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/frecuencias")
def api_frecuencias():
    df = cargar_datos()
    return grafico_frecuencias(df)

@app.route("/api/serie/<int:numero>")
def api_serie(numero):
    if not 1 <= numero <= NUMEROS_MAX:
        return jsonify({"error": "Número fuera de rango"}), 400
    df = cargar_datos()
    return grafico_serie_tiempo(df, numero)

@app.route("/api/hotcold/<int:ventana>")
def api_hotcold(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    calientes, frios = hot_cold(df, ventana)
    return jsonify({
        "calientes": calientes["numero"].tolist(),
        "frios": frios["numero"].tolist(),
    })

@app.route("/api/predecir/<int:ventana>")
def api_predecir(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    score = predecir_numeros(df, ventana_reciente=ventana)
    return jsonify(score.head(20).to_dict(orient="records"))

@app.route("/api/verificar", methods=["POST"])
def api_verificar():
    data = request.get_json(force=True)
    numeros = data.get("numeros", [])
    if len(numeros) != 6:
        return jsonify({"error": "Se requieren exactamente 6 números"}), 400
    numeros = [int(n) for n in numeros if 1 <= int(n) <= NUMEROS_MAX]
    if len(numeros) != 6:
        return jsonify({"error": "Números fuera de rango"}), 400
    df = cargar_datos()
    resultados = verificar_combinacion(df, numeros)
    return jsonify(resultados)

@app.route("/api/heatmap")
def api_heatmap():
    df = cargar_datos()
    return grafico_heatmap_pares(df)

# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0
```


## License: GPL-3.0
https://github.com/Tranovice-SCEAV/TallyWeb/blob/ade0d93b1e3760403ee2ef172e7d22bd92a229f4/TallyWeb.py

```
Estructura clara: 7 números por sorteo (R1-R6 + R7 adicional) con fecha. Voy a escribir la app Flask completa ahora.No tengo herramienta de edición de archivos disponible. Te presento el código completo para que lo copies directamente en `modelopredictJD.py`:

```python
"""
modelopredictJD.py
App Flask de análisis y predicción de Melate
Basada en Historic.csv (columnas: CONCURSO, R1-R7, FECHA)
"""

import os
import pandas as pd
import numpy as np
from flask import Flask, render_template_string, request, jsonify
from collections import Counter
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

# ── Configuración ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "Historic.csv")
NUMEROS_MAX = 56   # Melate: 1-56
BOLA_ADICIONAL = True  # R7 es número adicional (Bolita)

app = Flask(__name__)

# ── Carga y preprocesamiento de datos ────────────────────────────────────────
def cargar_datos():
    df = pd.read_csv(CSV_PATH, dtype=str)
    df["FECHA"] = pd.to_datetime(df["FECHA"])
    cols_num = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=cols_num)
    df = df.sort_values("FECHA").reset_index(drop=True)
    return df

# ── Análisis de frecuencias ───────────────────────────────────────────────────
def calcular_frecuencias(df, incluir_adicional=False):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    if incluir_adicional:
        cols.append("R7")
    todos = df[cols].values.flatten().astype(int)
    conteo = Counter(todos)
    freq = pd.DataFrame(
        [(n, conteo.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)],
        columns=["numero", "frecuencia"]
    ).sort_values("frecuencia", ascending=False)
    return freq

# ── Frecuencia en ventana temporal (últimos N sorteos) ────────────────────────
def frecuencia_reciente(df, ventana=100, incluir_adicional=False):
    sub = df.tail(ventana)
    return calcular_frecuencias(sub, incluir_adicional)

# ── Análisis de "números fríos" y "calientes" ─────────────────────────────────
def hot_cold(df, ventana=30):
    reciente = calcular_frecuencias(df.tail(ventana))
    historico = calcular_frecuencias(df)
    merged = reciente.merge(historico, on="numero", suffixes=("_rec", "_hist"))
    merged["z_score"] = (
        (merged["frecuencia_rec"] - merged["frecuencia_rec"].mean())
        / (merged["frecuencia_rec"].std() + 1e-9)
    )
    calientes = merged.nlargest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    frios = merged.nsmallest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    return calientes, frios

# ── Modelo predictivo: probabilidad ponderada (bayesian-like) ─────────────────
def predecir_numeros(df, n_pred=6, ventana_reciente=50):
    """
    Combina frecuencia histórica + frecuencia reciente + brecha (números atrasados).
    Devuelve lista ordenada de candidatos con su score.
    """
    freq_hist = calcular_frecuencias(df)
    freq_rec  = frecuencia_reciente(df, ventana=ventana_reciente)
    
    # Calcular brecha: sorteos desde la última aparición de cada número
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    ultimas = {}
    for idx, row in df.iterrows():
        for c in cols:
            n = int(row[c])
            ultimas[n] = idx   # último sorteo donde apareció
    total = len(df)
    brecha = {n: (total - ultimas.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)}
    brecha_s = pd.DataFrame(list(brecha.items()), columns=["numero", "brecha"])

    # Merge de señales
    score = freq_hist.merge(freq_rec, on="numero", suffixes=("_h", "_r"))
    score = score.merge(brecha_s, on="numero")
    
    # Normalizar cada señal a [0,1]
    for col in ["frecuencia_h", "frecuencia_r", "brecha"]:
        rng = score[col].max() - score[col].min()
        score[col + "_n"] = (score[col] - score[col].min()) / (rng + 1e-9)

    # Score compuesto: 40% hist + 40% reciente + 20% brecha
    score["score"] = (
        0.40 * score["frecuencia_h_n"]
        + 0.40 * score["frecuencia_r_n"]
        + 0.20 * score["brecha_n"]
    )
    score = score.sort_values("score", ascending=False).reset_index(drop=True)
    return score[["numero", "score", "frecuencia_h", "frecuencia_r", "brecha"]]

# ── Verificar si una combinación del usuario ha ganado antes ──────────────────
def verificar_combinacion(df, numeros_usuario: list[int]):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    set_usr = set(numeros_usuario)
    resultados = []
    for _, row in df.iterrows():
        set_row = {int(row[c]) for c in cols}
        coincidencias = set_usr & set_row
        if len(coincidencias) >= 3:
            resultados.append({
                "concurso": row["CONCURSO"],
                "fecha": str(row["FECHA"].date()),
                "numeros_sorteo": sorted(set_row),
                "coincidencias": len(coincidencias),
                "numeros_match": sorted(coincidencias),
            })
    return sorted(resultados, key=lambda x: -x["coincidencias"])[:20]

# ── Gráficos Plotly ───────────────────────────────────────────────────────────
def grafico_frecuencias(df):
    freq = calcular_frecuencias(df)
    fig = px.bar(
        freq, x="numero", y="frecuencia",
        title="Frecuencia histórica de números (R1-R6)",
        labels={"numero": "Número", "frecuencia": "Veces sorteado"},
        color="frecuencia",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(xaxis=dict(dtick=1), plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
                      font_color="white", title_font_size=16)
    return fig.to_json()

def grafico_serie_tiempo(df, numero: int):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    df["aparece"] = df[cols].apply(lambda r: int(numero in r.values), axis=1)
    df["acumulado"] = df["aparece"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["FECHA"], y=df["acumulado"],
        mode="lines", name=f"Número {numero} acumulado",
        line=dict(color="#a78bfa", width=2)
    ))
    fig.update_layout(
        title=f"Apariciones acumuladas del número {numero} en el tiempo",
        xaxis_title="Fecha", yaxis_title="Apariciones acumuladas",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white"
    )
    return fig.to_json()

def grafico_heatmap_pares(df):
    """Mapa de calor de co-ocurrencias entre números (R1-R6)."""
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    numeros = range(1, NUMEROS_MAX + 1)
    mat = np.zeros((NUMEROS_MAX, NUMEROS_MAX), dtype=int)
    for _, row in df.iterrows():
        ns = [int(row[c]) for c in cols]
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                a, b = ns[i] - 1, ns[j] - 1
                mat[a][b] += 1
                mat[b][a] += 1
    fig = go.Figure(go.Heatmap(
        z=mat, colorscale="Plasma",
        hovertemplate="(%{x}, %{y}): %{z}<extra></extra>"
    ))
    fig.update_layout(
        title="Co-ocurrencias entre pares de números",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white", height=600,
    )
    return fig.to_json()

# ── HTML Template ─────────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Predictor Melate — JD</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #13131f; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; padding: 20px; }
  h1 { color: #a78bfa; text-align: center; margin-bottom: 8px; font-size: 2rem; }
  .subtitle { text-align: center; color: #94a3b8; margin-bottom: 30px; font-size: .9rem; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media(max-width:768px){ .grid { grid-template-columns: 1fr; } }
  .card { background: #1e1e2e; border-radius: 12px; padding: 20px; border: 1px solid #2e2e4e; }
  .card h2 { color: #c4b5fd; margin-bottom: 14px; font-size: 1.1rem; }
  input[type=text], input[type=number], select {
    background: #2a2a3e; border: 1px solid #4c4c75; color: #e2e8f0;
    border-radius: 6px; padding: 8px 12px; width: 100%; margin-bottom: 10px; font-size: .95rem;
  }
  button {
    background: #7c3aed; color: white; border: none; border-radius: 8px;
    padding: 10px 20px; cursor: pointer; font-size: .95rem; width: 100%;
    transition: background .2s;
  }
  button:hover { background: #6d28d9; }
  .numeros-selector { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
  .num-btn {
    width: 42px; height: 42px; border-radius: 50%; background: #2a2a3e;
    border: 2px solid #4c4c75; color: #e2e8f0; cursor: pointer;
    font-weight: bold; transition: all .15s;
  }
  .num-btn.selected { background: #7c3aed; border-color: #a78bfa; color: white; }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; }
  .tag { background: #7c3aed; border-radius: 20px; padding: 4px 12px; font-size: .85rem; }
  .tag.cold { background: #1d4ed8; }
  .tag.hot { background: #dc2626; }
  #resultado-pred { margin-top: 14px; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th { background: #2a2a3e; padding: 8px; text-align: left; color: #a78bfa; }
  td { padding: 7px 8px; border-bottom: 1px solid #2a2a3e; }
  tr:hover td { background: #252535; }
  .alert { background: #1e3a5f; border-left: 3px solid #3b82f6; padding: 10px; border-radius: 6px; margin-top: 10px; font-size: .85rem;}
  .full { grid-column: 1 / -1; }
  #loader { display:none; text-align:center; color: #a78bfa; margin-top: 10px; }
</style>
</head>
<body>
<h1>🎱 Predictor Melate</h1>
<p class="subtitle">Análisis estadístico del sorteo histórico — no garantiza resultados</p>

<div class="grid">
  <!-- Frecuencias Históricas -->
  <div class="card full">
    <h2>📊 Frecuencia histórica de números</h2>
    <div id="chart-freq"></div>
  </div>

  <!-- Serie de tiempo por número -->
  <div class="card">
    <h2>📈 Serie de tiempo por número</h2>
    <label>Número a analizar (1-56):</label>
    <input type="number" id="num-serie" min="1" max="56" value="7">
    <button onclick="cargarSerie()">Ver serie de tiempo</button>
    <div id="chart-serie"></div>
  </div>

  <!-- Hot & Cold -->
  <div class="card">
    <h2>🔥❄️ Números calientes y fríos</h2>
    <label>Ventana de sorteos recientes:</label>
    <input type="number" id="ventana-hc" value="30" min="10" max="500">
    <button onclick="cargarHotCold()">Analizar</button>
    <div id="hot-cold-result" style="margin-top:12px;"></div>
  </div>

  <!-- Predicción -->
  <div class="card">
    <h2>🔮 Predicción de próximos números</h2>
    <label>Ventana reciente para el modelo:</label>
    <input type="number" id="ventana-pred" value="50" min="10" max="500">
    <button onclick="predecir()">Generar predicción</button>
    <div id="resultado-pred"></div>
  </div>

  <!-- Verificador de combinación -->
  <div class="card full">
    <h2>🎯 Verifica tu combinación contra el historial</h2>
    <p style="color:#94a3b8; font-size:.85rem; margin-bottom:12px;">
      Selecciona exactamente 6 números y verifica cuántas coincidencias tuvieron en sorteos pasados.
    </p>
    <div class="numeros-selector" id="picker"></div>
    <p id="seleccion-label" style="color:#a78bfa; margin-bottom:10px;">Seleccionados: ninguno</p>
    <button onclick="verificar()">Verificar en historial</button>
    <div id="loader">Buscando coincidencias...</div>
    <div id="resultado-verif"></div>
  </div>

  <!-- Heatmap de co-ocurrencias -->
  <div class="card full">
    <h2>🧩 Co-ocurrencias entre pares de números</h2>
    <button onclick="cargarHeatmap()">Cargar mapa de calor (puede tardar)</button>
    <div id="chart-heatmap"></div>
  </div>
</div>

<script>
// ── Cargar gráfico de frecuencias al inicio ───────────────────────────────
fetch('/api/frecuencias')
  .then(r => r.json())
  .then(data => Plotly.newPlot('chart-freq', data.data, data.layout, {responsive:true}));

// ── Serie de tiempo ───────────────────────────────────────────────────────
function cargarSerie() {
  const n = document.getElementById('num-serie').value;
  fetch('/api/serie/' + n)
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-serie', data.data, data.layout, {responsive:true}));
}

// ── Hot & Cold ────────────────────────────────────────────────────────────
function cargarHotCold() {
  const v = document.getElementById('ventana-hc').value;
  fetch('/api/hotcold/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<p style="color:#f87171;font-size:.9rem;font-weight:bold;">🔥 Calientes</p>';
      html += '<div class="tags">' + data.calientes.map(n => `<span class="tag hot">${n}</span>`).join('') + '</div>';
      html += '<p style="color:#60a5fa;font-size:.9rem;font-weight:bold;margin-top:12px;">❄️ Fríos</p>';
      html += '<div class="tags">' + data.frios.map(n => `<span class="tag cold">${n}</span>`).join('') + '</div>';
      document.getElementById('hot-cold-result').innerHTML = html;
    });
}

// ── Predicción ────────────────────────────────────────────────────────────
function predecir() {
  const v = document.getElementById('ventana-pred').value;
  fetch('/api/predecir/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<table><thead><tr><th>Pos.</th><th>Número</th><th>Score</th><th>Frec. hist.</th><th>Frec. rec.</th><th>Brecha</th></tr></thead><tbody>';
      data.slice(0, 15).forEach((row, i) => {
        html += `<tr><td>${i+1}</td><td><b>${row.numero}</b></td><td>${row.score.toFixed(4)}</td><td>${row.frecuencia_h}</td><td>${row.frecuencia_r}</td><td>${row.brecha}</td></tr>`;
      });
      html += '</tbody></table>';
      html += '<div class="alert" style="margin-top:10px;">⚠️ El modelo combina frecuencia histórica, frecuencia reciente y brecha de aparición. No es garantía de acierto.</div>';
      document.getElementById('resultado-pred').innerHTML = html;
    });
}

// ── Picker de números ─────────────────────────────────────────────────────
const seleccionados = new Set();
const picker = document.getElementById('picker');
for (let i = 1; i <= 56; i++) {
  const btn = document.createElement('button');
  btn.className = 'num-btn';
  btn.textContent = i;
  btn.onclick = () => {
    if (seleccionados.has(i)) {
      seleccionados.delete(i);
      btn.classList.remove('selected');
    } else if (seleccionados.size < 6) {
      seleccionados.add(i);
      btn.classList.add('selected');
    }
    document.getElementById('seleccion-label').textContent =
      'Seleccionados: ' + (seleccionados.size ? [...seleccionados].sort((a,b)=>a-b).join(', ') : 'ninguno');
  };
  picker.appendChild(btn);
}

function verificar() {
  if (seleccionados.size !== 6) { alert('Selecciona exactamente 6 números.'); return; }
  document.getElementById('loader').style.display = 'block';
  document.getElementById('resultado-verif').innerHTML = '';
  fetch('/api/verificar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({numeros: [...seleccionados]})
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('loader').style.display = 'none';
    if (!data.length) {
      document.getElementById('resultado-verif').innerHTML =
        '<div class="alert">No se encontraron sorteos con 3 o más coincidencias.</div>';
      return;
    }
    let html = `<p style="margin:10px 0;color:#a78bfa;">${data.length} sorteos con ≥3 coincidencias:</p>`;
    html += '<table><thead><tr><th>Concurso</th><th>Fecha</th><th>Sorteo</th><th>Match</th><th>Aciertos</th></tr></thead><tbody>';
    data.forEach(r => {
      html += `<tr><td>${r.concurso}</td><td>${r.fecha}</td><td>${r.numeros_sorteo.join(', ')}</td>
               <td style="color:#fbbf24;">${r.numeros_match.join(', ')}</td>
               <td><b>${r.coincidencias}</b></td></tr>`;
    });
    html += '</tbody></table>';
    document.getElementById('resultado-verif').innerHTML = html;
  });
}

// ── Heatmap ───────────────────────────────────────────────────────────────
function cargarHeatmap() {
  document.getElementById('chart-heatmap').innerHTML = '<p style="color:#a78bfa;padding:20px;">Calculando... puede tomar unos segundos.</p>';
  fetch('/api/heatmap')
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-heatmap', data.data, data.layout, {responsive:true}));
}

// Cargar hot/cold automáticamente
cargarHotCold();
</script>
</body>
</html>
"""

# ── Rutas Flask ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/frecuencias")
def api_frecuencias():
    df = cargar_datos()
    return grafico_frecuencias(df)

@app.route("/api/serie/<int:numero>")
def api_serie(numero):
    if not 1 <= numero <= NUMEROS_MAX:
        return jsonify({"error": "Número fuera de rango"}), 400
    df = cargar_datos()
    return grafico_serie_tiempo(df, numero)

@app.route("/api/hotcold/<int:ventana>")
def api_hotcold(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    calientes, frios = hot_cold(df, ventana)
    return jsonify({
        "calientes": calientes["numero"].tolist(),
        "frios": frios["numero"].tolist(),
    })

@app.route("/api/predecir/<int:ventana>")
def api_predecir(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    score = predecir_numeros(df, ventana_reciente=ventana)
    return jsonify(score.head(20).to_dict(orient="records"))

@app.route("/api/verificar", methods=["POST"])
def api_verificar():
    data = request.get_json(force=True)
    numeros = data.get("numeros", [])
    if len(numeros) != 6:
        return jsonify({"error": "Se requieren exactamente 6 números"}), 400
    numeros = [int(n) for n in numeros if 1 <= int(n) <= NUMEROS_MAX]
    if len(numeros) != 6:
        return jsonify({"error": "Números fuera de rango"}), 400
    df = cargar_datos()
    resultados = verificar_combinacion(df, numeros)
    return jsonify(resultados)

@app.route("/api/heatmap")
def api_heatmap():
    df = cargar_datos()
    return grafico_heatmap_pares(df)

# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0
```


## License: desconocido
https://github.com/fer-moreira/Network-Tools/blob/ef8a46136544213e36c723290062644ea46e38b0/Netool/netool.py

```
Estructura clara: 7 números por sorteo (R1-R6 + R7 adicional) con fecha. Voy a escribir la app Flask completa ahora.No tengo herramienta de edición de archivos disponible. Te presento el código completo para que lo copies directamente en `modelopredictJD.py`:

```python
"""
modelopredictJD.py
App Flask de análisis y predicción de Melate
Basada en Historic.csv (columnas: CONCURSO, R1-R7, FECHA)
"""

import os
import pandas as pd
import numpy as np
from flask import Flask, render_template_string, request, jsonify
from collections import Counter
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

# ── Configuración ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "Historic.csv")
NUMEROS_MAX = 56   # Melate: 1-56
BOLA_ADICIONAL = True  # R7 es número adicional (Bolita)

app = Flask(__name__)

# ── Carga y preprocesamiento de datos ────────────────────────────────────────
def cargar_datos():
    df = pd.read_csv(CSV_PATH, dtype=str)
    df["FECHA"] = pd.to_datetime(df["FECHA"])
    cols_num = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=cols_num)
    df = df.sort_values("FECHA").reset_index(drop=True)
    return df

# ── Análisis de frecuencias ───────────────────────────────────────────────────
def calcular_frecuencias(df, incluir_adicional=False):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    if incluir_adicional:
        cols.append("R7")
    todos = df[cols].values.flatten().astype(int)
    conteo = Counter(todos)
    freq = pd.DataFrame(
        [(n, conteo.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)],
        columns=["numero", "frecuencia"]
    ).sort_values("frecuencia", ascending=False)
    return freq

# ── Frecuencia en ventana temporal (últimos N sorteos) ────────────────────────
def frecuencia_reciente(df, ventana=100, incluir_adicional=False):
    sub = df.tail(ventana)
    return calcular_frecuencias(sub, incluir_adicional)

# ── Análisis de "números fríos" y "calientes" ─────────────────────────────────
def hot_cold(df, ventana=30):
    reciente = calcular_frecuencias(df.tail(ventana))
    historico = calcular_frecuencias(df)
    merged = reciente.merge(historico, on="numero", suffixes=("_rec", "_hist"))
    merged["z_score"] = (
        (merged["frecuencia_rec"] - merged["frecuencia_rec"].mean())
        / (merged["frecuencia_rec"].std() + 1e-9)
    )
    calientes = merged.nlargest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    frios = merged.nsmallest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    return calientes, frios

# ── Modelo predictivo: probabilidad ponderada (bayesian-like) ─────────────────
def predecir_numeros(df, n_pred=6, ventana_reciente=50):
    """
    Combina frecuencia histórica + frecuencia reciente + brecha (números atrasados).
    Devuelve lista ordenada de candidatos con su score.
    """
    freq_hist = calcular_frecuencias(df)
    freq_rec  = frecuencia_reciente(df, ventana=ventana_reciente)
    
    # Calcular brecha: sorteos desde la última aparición de cada número
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    ultimas = {}
    for idx, row in df.iterrows():
        for c in cols:
            n = int(row[c])
            ultimas[n] = idx   # último sorteo donde apareció
    total = len(df)
    brecha = {n: (total - ultimas.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)}
    brecha_s = pd.DataFrame(list(brecha.items()), columns=["numero", "brecha"])

    # Merge de señales
    score = freq_hist.merge(freq_rec, on="numero", suffixes=("_h", "_r"))
    score = score.merge(brecha_s, on="numero")
    
    # Normalizar cada señal a [0,1]
    for col in ["frecuencia_h", "frecuencia_r", "brecha"]:
        rng = score[col].max() - score[col].min()
        score[col + "_n"] = (score[col] - score[col].min()) / (rng + 1e-9)

    # Score compuesto: 40% hist + 40% reciente + 20% brecha
    score["score"] = (
        0.40 * score["frecuencia_h_n"]
        + 0.40 * score["frecuencia_r_n"]
        + 0.20 * score["brecha_n"]
    )
    score = score.sort_values("score", ascending=False).reset_index(drop=True)
    return score[["numero", "score", "frecuencia_h", "frecuencia_r", "brecha"]]

# ── Verificar si una combinación del usuario ha ganado antes ──────────────────
def verificar_combinacion(df, numeros_usuario: list[int]):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    set_usr = set(numeros_usuario)
    resultados = []
    for _, row in df.iterrows():
        set_row = {int(row[c]) for c in cols}
        coincidencias = set_usr & set_row
        if len(coincidencias) >= 3:
            resultados.append({
                "concurso": row["CONCURSO"],
                "fecha": str(row["FECHA"].date()),
                "numeros_sorteo": sorted(set_row),
                "coincidencias": len(coincidencias),
                "numeros_match": sorted(coincidencias),
            })
    return sorted(resultados, key=lambda x: -x["coincidencias"])[:20]

# ── Gráficos Plotly ───────────────────────────────────────────────────────────
def grafico_frecuencias(df):
    freq = calcular_frecuencias(df)
    fig = px.bar(
        freq, x="numero", y="frecuencia",
        title="Frecuencia histórica de números (R1-R6)",
        labels={"numero": "Número", "frecuencia": "Veces sorteado"},
        color="frecuencia",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(xaxis=dict(dtick=1), plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
                      font_color="white", title_font_size=16)
    return fig.to_json()

def grafico_serie_tiempo(df, numero: int):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    df["aparece"] = df[cols].apply(lambda r: int(numero in r.values), axis=1)
    df["acumulado"] = df["aparece"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["FECHA"], y=df["acumulado"],
        mode="lines", name=f"Número {numero} acumulado",
        line=dict(color="#a78bfa", width=2)
    ))
    fig.update_layout(
        title=f"Apariciones acumuladas del número {numero} en el tiempo",
        xaxis_title="Fecha", yaxis_title="Apariciones acumuladas",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white"
    )
    return fig.to_json()

def grafico_heatmap_pares(df):
    """Mapa de calor de co-ocurrencias entre números (R1-R6)."""
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    numeros = range(1, NUMEROS_MAX + 1)
    mat = np.zeros((NUMEROS_MAX, NUMEROS_MAX), dtype=int)
    for _, row in df.iterrows():
        ns = [int(row[c]) for c in cols]
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                a, b = ns[i] - 1, ns[j] - 1
                mat[a][b] += 1
                mat[b][a] += 1
    fig = go.Figure(go.Heatmap(
        z=mat, colorscale="Plasma",
        hovertemplate="(%{x}, %{y}): %{z}<extra></extra>"
    ))
    fig.update_layout(
        title="Co-ocurrencias entre pares de números",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white", height=600,
    )
    return fig.to_json()

# ── HTML Template ─────────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Predictor Melate — JD</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #13131f; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; padding: 20px; }
  h1 { color: #a78bfa; text-align: center; margin-bottom: 8px; font-size: 2rem; }
  .subtitle { text-align: center; color: #94a3b8; margin-bottom: 30px; font-size: .9rem; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media(max-width:768px){ .grid { grid-template-columns: 1fr; } }
  .card { background: #1e1e2e; border-radius: 12px; padding: 20px; border: 1px solid #2e2e4e; }
  .card h2 { color: #c4b5fd; margin-bottom: 14px; font-size: 1.1rem; }
  input[type=text], input[type=number], select {
    background: #2a2a3e; border: 1px solid #4c4c75; color: #e2e8f0;
    border-radius: 6px; padding: 8px 12px; width: 100%; margin-bottom: 10px; font-size: .95rem;
  }
  button {
    background: #7c3aed; color: white; border: none; border-radius: 8px;
    padding: 10px 20px; cursor: pointer; font-size: .95rem; width: 100%;
    transition: background .2s;
  }
  button:hover { background: #6d28d9; }
  .numeros-selector { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
  .num-btn {
    width: 42px; height: 42px; border-radius: 50%; background: #2a2a3e;
    border: 2px solid #4c4c75; color: #e2e8f0; cursor: pointer;
    font-weight: bold; transition: all .15s;
  }
  .num-btn.selected { background: #7c3aed; border-color: #a78bfa; color: white; }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; }
  .tag { background: #7c3aed; border-radius: 20px; padding: 4px 12px; font-size: .85rem; }
  .tag.cold { background: #1d4ed8; }
  .tag.hot { background: #dc2626; }
  #resultado-pred { margin-top: 14px; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th { background: #2a2a3e; padding: 8px; text-align: left; color: #a78bfa; }
  td { padding: 7px 8px; border-bottom: 1px solid #2a2a3e; }
  tr:hover td { background: #252535; }
  .alert { background: #1e3a5f; border-left: 3px solid #3b82f6; padding: 10px; border-radius: 6px; margin-top: 10px; font-size: .85rem;}
  .full { grid-column: 1 / -1; }
  #loader { display:none; text-align:center; color: #a78bfa; margin-top: 10px; }
</style>
</head>
<body>
<h1>🎱 Predictor Melate</h1>
<p class="subtitle">Análisis estadístico del sorteo histórico — no garantiza resultados</p>

<div class="grid">
  <!-- Frecuencias Históricas -->
  <div class="card full">
    <h2>📊 Frecuencia histórica de números</h2>
    <div id="chart-freq"></div>
  </div>

  <!-- Serie de tiempo por número -->
  <div class="card">
    <h2>📈 Serie de tiempo por número</h2>
    <label>Número a analizar (1-56):</label>
    <input type="number" id="num-serie" min="1" max="56" value="7">
    <button onclick="cargarSerie()">Ver serie de tiempo</button>
    <div id="chart-serie"></div>
  </div>

  <!-- Hot & Cold -->
  <div class="card">
    <h2>🔥❄️ Números calientes y fríos</h2>
    <label>Ventana de sorteos recientes:</label>
    <input type="number" id="ventana-hc" value="30" min="10" max="500">
    <button onclick="cargarHotCold()">Analizar</button>
    <div id="hot-cold-result" style="margin-top:12px;"></div>
  </div>

  <!-- Predicción -->
  <div class="card">
    <h2>🔮 Predicción de próximos números</h2>
    <label>Ventana reciente para el modelo:</label>
    <input type="number" id="ventana-pred" value="50" min="10" max="500">
    <button onclick="predecir()">Generar predicción</button>
    <div id="resultado-pred"></div>
  </div>

  <!-- Verificador de combinación -->
  <div class="card full">
    <h2>🎯 Verifica tu combinación contra el historial</h2>
    <p style="color:#94a3b8; font-size:.85rem; margin-bottom:12px;">
      Selecciona exactamente 6 números y verifica cuántas coincidencias tuvieron en sorteos pasados.
    </p>
    <div class="numeros-selector" id="picker"></div>
    <p id="seleccion-label" style="color:#a78bfa; margin-bottom:10px;">Seleccionados: ninguno</p>
    <button onclick="verificar()">Verificar en historial</button>
    <div id="loader">Buscando coincidencias...</div>
    <div id="resultado-verif"></div>
  </div>

  <!-- Heatmap de co-ocurrencias -->
  <div class="card full">
    <h2>🧩 Co-ocurrencias entre pares de números</h2>
    <button onclick="cargarHeatmap()">Cargar mapa de calor (puede tardar)</button>
    <div id="chart-heatmap"></div>
  </div>
</div>

<script>
// ── Cargar gráfico de frecuencias al inicio ───────────────────────────────
fetch('/api/frecuencias')
  .then(r => r.json())
  .then(data => Plotly.newPlot('chart-freq', data.data, data.layout, {responsive:true}));

// ── Serie de tiempo ───────────────────────────────────────────────────────
function cargarSerie() {
  const n = document.getElementById('num-serie').value;
  fetch('/api/serie/' + n)
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-serie', data.data, data.layout, {responsive:true}));
}

// ── Hot & Cold ────────────────────────────────────────────────────────────
function cargarHotCold() {
  const v = document.getElementById('ventana-hc').value;
  fetch('/api/hotcold/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<p style="color:#f87171;font-size:.9rem;font-weight:bold;">🔥 Calientes</p>';
      html += '<div class="tags">' + data.calientes.map(n => `<span class="tag hot">${n}</span>`).join('') + '</div>';
      html += '<p style="color:#60a5fa;font-size:.9rem;font-weight:bold;margin-top:12px;">❄️ Fríos</p>';
      html += '<div class="tags">' + data.frios.map(n => `<span class="tag cold">${n}</span>`).join('') + '</div>';
      document.getElementById('hot-cold-result').innerHTML = html;
    });
}

// ── Predicción ────────────────────────────────────────────────────────────
function predecir() {
  const v = document.getElementById('ventana-pred').value;
  fetch('/api/predecir/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<table><thead><tr><th>Pos.</th><th>Número</th><th>Score</th><th>Frec. hist.</th><th>Frec. rec.</th><th>Brecha</th></tr></thead><tbody>';
      data.slice(0, 15).forEach((row, i) => {
        html += `<tr><td>${i+1}</td><td><b>${row.numero}</b></td><td>${row.score.toFixed(4)}</td><td>${row.frecuencia_h}</td><td>${row.frecuencia_r}</td><td>${row.brecha}</td></tr>`;
      });
      html += '</tbody></table>';
      html += '<div class="alert" style="margin-top:10px;">⚠️ El modelo combina frecuencia histórica, frecuencia reciente y brecha de aparición. No es garantía de acierto.</div>';
      document.getElementById('resultado-pred').innerHTML = html;
    });
}

// ── Picker de números ─────────────────────────────────────────────────────
const seleccionados = new Set();
const picker = document.getElementById('picker');
for (let i = 1; i <= 56; i++) {
  const btn = document.createElement('button');
  btn.className = 'num-btn';
  btn.textContent = i;
  btn.onclick = () => {
    if (seleccionados.has(i)) {
      seleccionados.delete(i);
      btn.classList.remove('selected');
    } else if (seleccionados.size < 6) {
      seleccionados.add(i);
      btn.classList.add('selected');
    }
    document.getElementById('seleccion-label').textContent =
      'Seleccionados: ' + (seleccionados.size ? [...seleccionados].sort((a,b)=>a-b).join(', ') : 'ninguno');
  };
  picker.appendChild(btn);
}

function verificar() {
  if (seleccionados.size !== 6) { alert('Selecciona exactamente 6 números.'); return; }
  document.getElementById('loader').style.display = 'block';
  document.getElementById('resultado-verif').innerHTML = '';
  fetch('/api/verificar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({numeros: [...seleccionados]})
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('loader').style.display = 'none';
    if (!data.length) {
      document.getElementById('resultado-verif').innerHTML =
        '<div class="alert">No se encontraron sorteos con 3 o más coincidencias.</div>';
      return;
    }
    let html = `<p style="margin:10px 0;color:#a78bfa;">${data.length} sorteos con ≥3 coincidencias:</p>`;
    html += '<table><thead><tr><th>Concurso</th><th>Fecha</th><th>Sorteo</th><th>Match</th><th>Aciertos</th></tr></thead><tbody>';
    data.forEach(r => {
      html += `<tr><td>${r.concurso}</td><td>${r.fecha}</td><td>${r.numeros_sorteo.join(', ')}</td>
               <td style="color:#fbbf24;">${r.numeros_match.join(', ')}</td>
               <td><b>${r.coincidencias}</b></td></tr>`;
    });
    html += '</tbody></table>';
    document.getElementById('resultado-verif').innerHTML = html;
  });
}

// ── Heatmap ───────────────────────────────────────────────────────────────
function cargarHeatmap() {
  document.getElementById('chart-heatmap').innerHTML = '<p style="color:#a78bfa;padding:20px;">Calculando... puede tomar unos segundos.</p>';
  fetch('/api/heatmap')
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-heatmap', data.data, data.layout, {responsive:true}));
}

// Cargar hot/cold automáticamente
cargarHotCold();
</script>
</body>
</html>
"""

# ── Rutas Flask ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/frecuencias")
def api_frecuencias():
    df = cargar_datos()
    return grafico_frecuencias(df)

@app.route("/api/serie/<int:numero>")
def api_serie(numero):
    if not 1 <= numero <= NUMEROS_MAX:
        return jsonify({"error": "Número fuera de rango"}), 400
    df = cargar_datos()
    return grafico_serie_tiempo(df, numero)

@app.route("/api/hotcold/<int:ventana>")
def api_hotcold(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    calientes, frios = hot_cold(df, ventana)
    return jsonify({
        "calientes": calientes["numero"].tolist(),
        "frios": frios["numero"].tolist(),
    })

@app.route("/api/predecir/<int:ventana>")
def api_predecir(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    score = predecir_numeros(df, ventana_reciente=ventana)
    return jsonify(score.head(20).to_dict(orient="records"))

@app.route("/api/verificar", methods=["POST"])
def api_verificar():
    data = request.get_json(force=True)
    numeros = data.get("numeros", [])
    if len(numeros) != 6:
        return jsonify({"error": "Se requieren exactamente 6 números"}), 400
    numeros = [int(n) for n in numeros if 1 <= int(n) <= NUMEROS_MAX]
    if len(numeros) != 6:
        return jsonify({"error": "Números fuera de rango"}), 400
    df = cargar_datos()
    resultados = verificar_combinacion(df, numeros)
    return jsonify(resultados)

@app.route("/api/heatmap")
def api_heatmap():
    df = cargar_datos()
    return grafico_heatmap_pares(df)

# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0
```


## License: GPL-3.0
https://github.com/Tranovice-SCEAV/TallyWeb/blob/ade0d93b1e3760403ee2ef172e7d22bd92a229f4/TallyWeb.py

```
Estructura clara: 7 números por sorteo (R1-R6 + R7 adicional) con fecha. Voy a escribir la app Flask completa ahora.No tengo herramienta de edición de archivos disponible. Te presento el código completo para que lo copies directamente en `modelopredictJD.py`:

```python
"""
modelopredictJD.py
App Flask de análisis y predicción de Melate
Basada en Historic.csv (columnas: CONCURSO, R1-R7, FECHA)
"""

import os
import pandas as pd
import numpy as np
from flask import Flask, render_template_string, request, jsonify
from collections import Counter
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

# ── Configuración ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "Historic.csv")
NUMEROS_MAX = 56   # Melate: 1-56
BOLA_ADICIONAL = True  # R7 es número adicional (Bolita)

app = Flask(__name__)

# ── Carga y preprocesamiento de datos ────────────────────────────────────────
def cargar_datos():
    df = pd.read_csv(CSV_PATH, dtype=str)
    df["FECHA"] = pd.to_datetime(df["FECHA"])
    cols_num = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=cols_num)
    df = df.sort_values("FECHA").reset_index(drop=True)
    return df

# ── Análisis de frecuencias ───────────────────────────────────────────────────
def calcular_frecuencias(df, incluir_adicional=False):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    if incluir_adicional:
        cols.append("R7")
    todos = df[cols].values.flatten().astype(int)
    conteo = Counter(todos)
    freq = pd.DataFrame(
        [(n, conteo.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)],
        columns=["numero", "frecuencia"]
    ).sort_values("frecuencia", ascending=False)
    return freq

# ── Frecuencia en ventana temporal (últimos N sorteos) ────────────────────────
def frecuencia_reciente(df, ventana=100, incluir_adicional=False):
    sub = df.tail(ventana)
    return calcular_frecuencias(sub, incluir_adicional)

# ── Análisis de "números fríos" y "calientes" ─────────────────────────────────
def hot_cold(df, ventana=30):
    reciente = calcular_frecuencias(df.tail(ventana))
    historico = calcular_frecuencias(df)
    merged = reciente.merge(historico, on="numero", suffixes=("_rec", "_hist"))
    merged["z_score"] = (
        (merged["frecuencia_rec"] - merged["frecuencia_rec"].mean())
        / (merged["frecuencia_rec"].std() + 1e-9)
    )
    calientes = merged.nlargest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    frios = merged.nsmallest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    return calientes, frios

# ── Modelo predictivo: probabilidad ponderada (bayesian-like) ─────────────────
def predecir_numeros(df, n_pred=6, ventana_reciente=50):
    """
    Combina frecuencia histórica + frecuencia reciente + brecha (números atrasados).
    Devuelve lista ordenada de candidatos con su score.
    """
    freq_hist = calcular_frecuencias(df)
    freq_rec  = frecuencia_reciente(df, ventana=ventana_reciente)
    
    # Calcular brecha: sorteos desde la última aparición de cada número
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    ultimas = {}
    for idx, row in df.iterrows():
        for c in cols:
            n = int(row[c])
            ultimas[n] = idx   # último sorteo donde apareció
    total = len(df)
    brecha = {n: (total - ultimas.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)}
    brecha_s = pd.DataFrame(list(brecha.items()), columns=["numero", "brecha"])

    # Merge de señales
    score = freq_hist.merge(freq_rec, on="numero", suffixes=("_h", "_r"))
    score = score.merge(brecha_s, on="numero")
    
    # Normalizar cada señal a [0,1]
    for col in ["frecuencia_h", "frecuencia_r", "brecha"]:
        rng = score[col].max() - score[col].min()
        score[col + "_n"] = (score[col] - score[col].min()) / (rng + 1e-9)

    # Score compuesto: 40% hist + 40% reciente + 20% brecha
    score["score"] = (
        0.40 * score["frecuencia_h_n"]
        + 0.40 * score["frecuencia_r_n"]
        + 0.20 * score["brecha_n"]
    )
    score = score.sort_values("score", ascending=False).reset_index(drop=True)
    return score[["numero", "score", "frecuencia_h", "frecuencia_r", "brecha"]]

# ── Verificar si una combinación del usuario ha ganado antes ──────────────────
def verificar_combinacion(df, numeros_usuario: list[int]):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    set_usr = set(numeros_usuario)
    resultados = []
    for _, row in df.iterrows():
        set_row = {int(row[c]) for c in cols}
        coincidencias = set_usr & set_row
        if len(coincidencias) >= 3:
            resultados.append({
                "concurso": row["CONCURSO"],
                "fecha": str(row["FECHA"].date()),
                "numeros_sorteo": sorted(set_row),
                "coincidencias": len(coincidencias),
                "numeros_match": sorted(coincidencias),
            })
    return sorted(resultados, key=lambda x: -x["coincidencias"])[:20]

# ── Gráficos Plotly ───────────────────────────────────────────────────────────
def grafico_frecuencias(df):
    freq = calcular_frecuencias(df)
    fig = px.bar(
        freq, x="numero", y="frecuencia",
        title="Frecuencia histórica de números (R1-R6)",
        labels={"numero": "Número", "frecuencia": "Veces sorteado"},
        color="frecuencia",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(xaxis=dict(dtick=1), plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
                      font_color="white", title_font_size=16)
    return fig.to_json()

def grafico_serie_tiempo(df, numero: int):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    df["aparece"] = df[cols].apply(lambda r: int(numero in r.values), axis=1)
    df["acumulado"] = df["aparece"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["FECHA"], y=df["acumulado"],
        mode="lines", name=f"Número {numero} acumulado",
        line=dict(color="#a78bfa", width=2)
    ))
    fig.update_layout(
        title=f"Apariciones acumuladas del número {numero} en el tiempo",
        xaxis_title="Fecha", yaxis_title="Apariciones acumuladas",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white"
    )
    return fig.to_json()

def grafico_heatmap_pares(df):
    """Mapa de calor de co-ocurrencias entre números (R1-R6)."""
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    numeros = range(1, NUMEROS_MAX + 1)
    mat = np.zeros((NUMEROS_MAX, NUMEROS_MAX), dtype=int)
    for _, row in df.iterrows():
        ns = [int(row[c]) for c in cols]
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                a, b = ns[i] - 1, ns[j] - 1
                mat[a][b] += 1
                mat[b][a] += 1
    fig = go.Figure(go.Heatmap(
        z=mat, colorscale="Plasma",
        hovertemplate="(%{x}, %{y}): %{z}<extra></extra>"
    ))
    fig.update_layout(
        title="Co-ocurrencias entre pares de números",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white", height=600,
    )
    return fig.to_json()

# ── HTML Template ─────────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Predictor Melate — JD</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #13131f; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; padding: 20px; }
  h1 { color: #a78bfa; text-align: center; margin-bottom: 8px; font-size: 2rem; }
  .subtitle { text-align: center; color: #94a3b8; margin-bottom: 30px; font-size: .9rem; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media(max-width:768px){ .grid { grid-template-columns: 1fr; } }
  .card { background: #1e1e2e; border-radius: 12px; padding: 20px; border: 1px solid #2e2e4e; }
  .card h2 { color: #c4b5fd; margin-bottom: 14px; font-size: 1.1rem; }
  input[type=text], input[type=number], select {
    background: #2a2a3e; border: 1px solid #4c4c75; color: #e2e8f0;
    border-radius: 6px; padding: 8px 12px; width: 100%; margin-bottom: 10px; font-size: .95rem;
  }
  button {
    background: #7c3aed; color: white; border: none; border-radius: 8px;
    padding: 10px 20px; cursor: pointer; font-size: .95rem; width: 100%;
    transition: background .2s;
  }
  button:hover { background: #6d28d9; }
  .numeros-selector { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
  .num-btn {
    width: 42px; height: 42px; border-radius: 50%; background: #2a2a3e;
    border: 2px solid #4c4c75; color: #e2e8f0; cursor: pointer;
    font-weight: bold; transition: all .15s;
  }
  .num-btn.selected { background: #7c3aed; border-color: #a78bfa; color: white; }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; }
  .tag { background: #7c3aed; border-radius: 20px; padding: 4px 12px; font-size: .85rem; }
  .tag.cold { background: #1d4ed8; }
  .tag.hot { background: #dc2626; }
  #resultado-pred { margin-top: 14px; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th { background: #2a2a3e; padding: 8px; text-align: left; color: #a78bfa; }
  td { padding: 7px 8px; border-bottom: 1px solid #2a2a3e; }
  tr:hover td { background: #252535; }
  .alert { background: #1e3a5f; border-left: 3px solid #3b82f6; padding: 10px; border-radius: 6px; margin-top: 10px; font-size: .85rem;}
  .full { grid-column: 1 / -1; }
  #loader { display:none; text-align:center; color: #a78bfa; margin-top: 10px; }
</style>
</head>
<body>
<h1>🎱 Predictor Melate</h1>
<p class="subtitle">Análisis estadístico del sorteo histórico — no garantiza resultados</p>

<div class="grid">
  <!-- Frecuencias Históricas -->
  <div class="card full">
    <h2>📊 Frecuencia histórica de números</h2>
    <div id="chart-freq"></div>
  </div>

  <!-- Serie de tiempo por número -->
  <div class="card">
    <h2>📈 Serie de tiempo por número</h2>
    <label>Número a analizar (1-56):</label>
    <input type="number" id="num-serie" min="1" max="56" value="7">
    <button onclick="cargarSerie()">Ver serie de tiempo</button>
    <div id="chart-serie"></div>
  </div>

  <!-- Hot & Cold -->
  <div class="card">
    <h2>🔥❄️ Números calientes y fríos</h2>
    <label>Ventana de sorteos recientes:</label>
    <input type="number" id="ventana-hc" value="30" min="10" max="500">
    <button onclick="cargarHotCold()">Analizar</button>
    <div id="hot-cold-result" style="margin-top:12px;"></div>
  </div>

  <!-- Predicción -->
  <div class="card">
    <h2>🔮 Predicción de próximos números</h2>
    <label>Ventana reciente para el modelo:</label>
    <input type="number" id="ventana-pred" value="50" min="10" max="500">
    <button onclick="predecir()">Generar predicción</button>
    <div id="resultado-pred"></div>
  </div>

  <!-- Verificador de combinación -->
  <div class="card full">
    <h2>🎯 Verifica tu combinación contra el historial</h2>
    <p style="color:#94a3b8; font-size:.85rem; margin-bottom:12px;">
      Selecciona exactamente 6 números y verifica cuántas coincidencias tuvieron en sorteos pasados.
    </p>
    <div class="numeros-selector" id="picker"></div>
    <p id="seleccion-label" style="color:#a78bfa; margin-bottom:10px;">Seleccionados: ninguno</p>
    <button onclick="verificar()">Verificar en historial</button>
    <div id="loader">Buscando coincidencias...</div>
    <div id="resultado-verif"></div>
  </div>

  <!-- Heatmap de co-ocurrencias -->
  <div class="card full">
    <h2>🧩 Co-ocurrencias entre pares de números</h2>
    <button onclick="cargarHeatmap()">Cargar mapa de calor (puede tardar)</button>
    <div id="chart-heatmap"></div>
  </div>
</div>

<script>
// ── Cargar gráfico de frecuencias al inicio ───────────────────────────────
fetch('/api/frecuencias')
  .then(r => r.json())
  .then(data => Plotly.newPlot('chart-freq', data.data, data.layout, {responsive:true}));

// ── Serie de tiempo ───────────────────────────────────────────────────────
function cargarSerie() {
  const n = document.getElementById('num-serie').value;
  fetch('/api/serie/' + n)
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-serie', data.data, data.layout, {responsive:true}));
}

// ── Hot & Cold ────────────────────────────────────────────────────────────
function cargarHotCold() {
  const v = document.getElementById('ventana-hc').value;
  fetch('/api/hotcold/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<p style="color:#f87171;font-size:.9rem;font-weight:bold;">🔥 Calientes</p>';
      html += '<div class="tags">' + data.calientes.map(n => `<span class="tag hot">${n}</span>`).join('') + '</div>';
      html += '<p style="color:#60a5fa;font-size:.9rem;font-weight:bold;margin-top:12px;">❄️ Fríos</p>';
      html += '<div class="tags">' + data.frios.map(n => `<span class="tag cold">${n}</span>`).join('') + '</div>';
      document.getElementById('hot-cold-result').innerHTML = html;
    });
}

// ── Predicción ────────────────────────────────────────────────────────────
function predecir() {
  const v = document.getElementById('ventana-pred').value;
  fetch('/api/predecir/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<table><thead><tr><th>Pos.</th><th>Número</th><th>Score</th><th>Frec. hist.</th><th>Frec. rec.</th><th>Brecha</th></tr></thead><tbody>';
      data.slice(0, 15).forEach((row, i) => {
        html += `<tr><td>${i+1}</td><td><b>${row.numero}</b></td><td>${row.score.toFixed(4)}</td><td>${row.frecuencia_h}</td><td>${row.frecuencia_r}</td><td>${row.brecha}</td></tr>`;
      });
      html += '</tbody></table>';
      html += '<div class="alert" style="margin-top:10px;">⚠️ El modelo combina frecuencia histórica, frecuencia reciente y brecha de aparición. No es garantía de acierto.</div>';
      document.getElementById('resultado-pred').innerHTML = html;
    });
}

// ── Picker de números ─────────────────────────────────────────────────────
const seleccionados = new Set();
const picker = document.getElementById('picker');
for (let i = 1; i <= 56; i++) {
  const btn = document.createElement('button');
  btn.className = 'num-btn';
  btn.textContent = i;
  btn.onclick = () => {
    if (seleccionados.has(i)) {
      seleccionados.delete(i);
      btn.classList.remove('selected');
    } else if (seleccionados.size < 6) {
      seleccionados.add(i);
      btn.classList.add('selected');
    }
    document.getElementById('seleccion-label').textContent =
      'Seleccionados: ' + (seleccionados.size ? [...seleccionados].sort((a,b)=>a-b).join(', ') : 'ninguno');
  };
  picker.appendChild(btn);
}

function verificar() {
  if (seleccionados.size !== 6) { alert('Selecciona exactamente 6 números.'); return; }
  document.getElementById('loader').style.display = 'block';
  document.getElementById('resultado-verif').innerHTML = '';
  fetch('/api/verificar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({numeros: [...seleccionados]})
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('loader').style.display = 'none';
    if (!data.length) {
      document.getElementById('resultado-verif').innerHTML =
        '<div class="alert">No se encontraron sorteos con 3 o más coincidencias.</div>';
      return;
    }
    let html = `<p style="margin:10px 0;color:#a78bfa;">${data.length} sorteos con ≥3 coincidencias:</p>`;
    html += '<table><thead><tr><th>Concurso</th><th>Fecha</th><th>Sorteo</th><th>Match</th><th>Aciertos</th></tr></thead><tbody>';
    data.forEach(r => {
      html += `<tr><td>${r.concurso}</td><td>${r.fecha}</td><td>${r.numeros_sorteo.join(', ')}</td>
               <td style="color:#fbbf24;">${r.numeros_match.join(', ')}</td>
               <td><b>${r.coincidencias}</b></td></tr>`;
    });
    html += '</tbody></table>';
    document.getElementById('resultado-verif').innerHTML = html;
  });
}

// ── Heatmap ───────────────────────────────────────────────────────────────
function cargarHeatmap() {
  document.getElementById('chart-heatmap').innerHTML = '<p style="color:#a78bfa;padding:20px;">Calculando... puede tomar unos segundos.</p>';
  fetch('/api/heatmap')
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-heatmap', data.data, data.layout, {responsive:true}));
}

// Cargar hot/cold automáticamente
cargarHotCold();
</script>
</body>
</html>
"""

# ── Rutas Flask ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/frecuencias")
def api_frecuencias():
    df = cargar_datos()
    return grafico_frecuencias(df)

@app.route("/api/serie/<int:numero>")
def api_serie(numero):
    if not 1 <= numero <= NUMEROS_MAX:
        return jsonify({"error": "Número fuera de rango"}), 400
    df = cargar_datos()
    return grafico_serie_tiempo(df, numero)

@app.route("/api/hotcold/<int:ventana>")
def api_hotcold(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    calientes, frios = hot_cold(df, ventana)
    return jsonify({
        "calientes": calientes["numero"].tolist(),
        "frios": frios["numero"].tolist(),
    })

@app.route("/api/predecir/<int:ventana>")
def api_predecir(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    score = predecir_numeros(df, ventana_reciente=ventana)
    return jsonify(score.head(20).to_dict(orient="records"))

@app.route("/api/verificar", methods=["POST"])
def api_verificar():
    data = request.get_json(force=True)
    numeros = data.get("numeros", [])
    if len(numeros) != 6:
        return jsonify({"error": "Se requieren exactamente 6 números"}), 400
    numeros = [int(n) for n in numeros if 1 <= int(n) <= NUMEROS_MAX]
    if len(numeros) != 6:
        return jsonify({"error": "Números fuera de rango"}), 400
    df = cargar_datos()
    resultados = verificar_combinacion(df, numeros)
    return jsonify(resultados)

@app.route("/api/heatmap")
def api_heatmap():
    df = cargar_datos()
    return grafico_heatmap_pares(df)

# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0
```


## License: desconocido
https://github.com/fer-moreira/Network-Tools/blob/ef8a46136544213e36c723290062644ea46e38b0/Netool/netool.py

```
Estructura clara: 7 números por sorteo (R1-R6 + R7 adicional) con fecha. Voy a escribir la app Flask completa ahora.No tengo herramienta de edición de archivos disponible. Te presento el código completo para que lo copies directamente en `modelopredictJD.py`:

```python
"""
modelopredictJD.py
App Flask de análisis y predicción de Melate
Basada en Historic.csv (columnas: CONCURSO, R1-R7, FECHA)
"""

import os
import pandas as pd
import numpy as np
from flask import Flask, render_template_string, request, jsonify
from collections import Counter
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

# ── Configuración ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "Historic.csv")
NUMEROS_MAX = 56   # Melate: 1-56
BOLA_ADICIONAL = True  # R7 es número adicional (Bolita)

app = Flask(__name__)

# ── Carga y preprocesamiento de datos ────────────────────────────────────────
def cargar_datos():
    df = pd.read_csv(CSV_PATH, dtype=str)
    df["FECHA"] = pd.to_datetime(df["FECHA"])
    cols_num = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=cols_num)
    df = df.sort_values("FECHA").reset_index(drop=True)
    return df

# ── Análisis de frecuencias ───────────────────────────────────────────────────
def calcular_frecuencias(df, incluir_adicional=False):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    if incluir_adicional:
        cols.append("R7")
    todos = df[cols].values.flatten().astype(int)
    conteo = Counter(todos)
    freq = pd.DataFrame(
        [(n, conteo.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)],
        columns=["numero", "frecuencia"]
    ).sort_values("frecuencia", ascending=False)
    return freq

# ── Frecuencia en ventana temporal (últimos N sorteos) ────────────────────────
def frecuencia_reciente(df, ventana=100, incluir_adicional=False):
    sub = df.tail(ventana)
    return calcular_frecuencias(sub, incluir_adicional)

# ── Análisis de "números fríos" y "calientes" ─────────────────────────────────
def hot_cold(df, ventana=30):
    reciente = calcular_frecuencias(df.tail(ventana))
    historico = calcular_frecuencias(df)
    merged = reciente.merge(historico, on="numero", suffixes=("_rec", "_hist"))
    merged["z_score"] = (
        (merged["frecuencia_rec"] - merged["frecuencia_rec"].mean())
        / (merged["frecuencia_rec"].std() + 1e-9)
    )
    calientes = merged.nlargest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    frios = merged.nsmallest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    return calientes, frios

# ── Modelo predictivo: probabilidad ponderada (bayesian-like) ─────────────────
def predecir_numeros(df, n_pred=6, ventana_reciente=50):
    """
    Combina frecuencia histórica + frecuencia reciente + brecha (números atrasados).
    Devuelve lista ordenada de candidatos con su score.
    """
    freq_hist = calcular_frecuencias(df)
    freq_rec  = frecuencia_reciente(df, ventana=ventana_reciente)
    
    # Calcular brecha: sorteos desde la última aparición de cada número
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    ultimas = {}
    for idx, row in df.iterrows():
        for c in cols:
            n = int(row[c])
            ultimas[n] = idx   # último sorteo donde apareció
    total = len(df)
    brecha = {n: (total - ultimas.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)}
    brecha_s = pd.DataFrame(list(brecha.items()), columns=["numero", "brecha"])

    # Merge de señales
    score = freq_hist.merge(freq_rec, on="numero", suffixes=("_h", "_r"))
    score = score.merge(brecha_s, on="numero")
    
    # Normalizar cada señal a [0,1]
    for col in ["frecuencia_h", "frecuencia_r", "brecha"]:
        rng = score[col].max() - score[col].min()
        score[col + "_n"] = (score[col] - score[col].min()) / (rng + 1e-9)

    # Score compuesto: 40% hist + 40% reciente + 20% brecha
    score["score"] = (
        0.40 * score["frecuencia_h_n"]
        + 0.40 * score["frecuencia_r_n"]
        + 0.20 * score["brecha_n"]
    )
    score = score.sort_values("score", ascending=False).reset_index(drop=True)
    return score[["numero", "score", "frecuencia_h", "frecuencia_r", "brecha"]]

# ── Verificar si una combinación del usuario ha ganado antes ──────────────────
def verificar_combinacion(df, numeros_usuario: list[int]):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    set_usr = set(numeros_usuario)
    resultados = []
    for _, row in df.iterrows():
        set_row = {int(row[c]) for c in cols}
        coincidencias = set_usr & set_row
        if len(coincidencias) >= 3:
            resultados.append({
                "concurso": row["CONCURSO"],
                "fecha": str(row["FECHA"].date()),
                "numeros_sorteo": sorted(set_row),
                "coincidencias": len(coincidencias),
                "numeros_match": sorted(coincidencias),
            })
    return sorted(resultados, key=lambda x: -x["coincidencias"])[:20]

# ── Gráficos Plotly ───────────────────────────────────────────────────────────
def grafico_frecuencias(df):
    freq = calcular_frecuencias(df)
    fig = px.bar(
        freq, x="numero", y="frecuencia",
        title="Frecuencia histórica de números (R1-R6)",
        labels={"numero": "Número", "frecuencia": "Veces sorteado"},
        color="frecuencia",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(xaxis=dict(dtick=1), plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
                      font_color="white", title_font_size=16)
    return fig.to_json()

def grafico_serie_tiempo(df, numero: int):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    df["aparece"] = df[cols].apply(lambda r: int(numero in r.values), axis=1)
    df["acumulado"] = df["aparece"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["FECHA"], y=df["acumulado"],
        mode="lines", name=f"Número {numero} acumulado",
        line=dict(color="#a78bfa", width=2)
    ))
    fig.update_layout(
        title=f"Apariciones acumuladas del número {numero} en el tiempo",
        xaxis_title="Fecha", yaxis_title="Apariciones acumuladas",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white"
    )
    return fig.to_json()

def grafico_heatmap_pares(df):
    """Mapa de calor de co-ocurrencias entre números (R1-R6)."""
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    numeros = range(1, NUMEROS_MAX + 1)
    mat = np.zeros((NUMEROS_MAX, NUMEROS_MAX), dtype=int)
    for _, row in df.iterrows():
        ns = [int(row[c]) for c in cols]
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                a, b = ns[i] - 1, ns[j] - 1
                mat[a][b] += 1
                mat[b][a] += 1
    fig = go.Figure(go.Heatmap(
        z=mat, colorscale="Plasma",
        hovertemplate="(%{x}, %{y}): %{z}<extra></extra>"
    ))
    fig.update_layout(
        title="Co-ocurrencias entre pares de números",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white", height=600,
    )
    return fig.to_json()

# ── HTML Template ─────────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Predictor Melate — JD</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #13131f; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; padding: 20px; }
  h1 { color: #a78bfa; text-align: center; margin-bottom: 8px; font-size: 2rem; }
  .subtitle { text-align: center; color: #94a3b8; margin-bottom: 30px; font-size: .9rem; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media(max-width:768px){ .grid { grid-template-columns: 1fr; } }
  .card { background: #1e1e2e; border-radius: 12px; padding: 20px; border: 1px solid #2e2e4e; }
  .card h2 { color: #c4b5fd; margin-bottom: 14px; font-size: 1.1rem; }
  input[type=text], input[type=number], select {
    background: #2a2a3e; border: 1px solid #4c4c75; color: #e2e8f0;
    border-radius: 6px; padding: 8px 12px; width: 100%; margin-bottom: 10px; font-size: .95rem;
  }
  button {
    background: #7c3aed; color: white; border: none; border-radius: 8px;
    padding: 10px 20px; cursor: pointer; font-size: .95rem; width: 100%;
    transition: background .2s;
  }
  button:hover { background: #6d28d9; }
  .numeros-selector { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
  .num-btn {
    width: 42px; height: 42px; border-radius: 50%; background: #2a2a3e;
    border: 2px solid #4c4c75; color: #e2e8f0; cursor: pointer;
    font-weight: bold; transition: all .15s;
  }
  .num-btn.selected { background: #7c3aed; border-color: #a78bfa; color: white; }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; }
  .tag { background: #7c3aed; border-radius: 20px; padding: 4px 12px; font-size: .85rem; }
  .tag.cold { background: #1d4ed8; }
  .tag.hot { background: #dc2626; }
  #resultado-pred { margin-top: 14px; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th { background: #2a2a3e; padding: 8px; text-align: left; color: #a78bfa; }
  td { padding: 7px 8px; border-bottom: 1px solid #2a2a3e; }
  tr:hover td { background: #252535; }
  .alert { background: #1e3a5f; border-left: 3px solid #3b82f6; padding: 10px; border-radius: 6px; margin-top: 10px; font-size: .85rem;}
  .full { grid-column: 1 / -1; }
  #loader { display:none; text-align:center; color: #a78bfa; margin-top: 10px; }
</style>
</head>
<body>
<h1>🎱 Predictor Melate</h1>
<p class="subtitle">Análisis estadístico del sorteo histórico — no garantiza resultados</p>

<div class="grid">
  <!-- Frecuencias Históricas -->
  <div class="card full">
    <h2>📊 Frecuencia histórica de números</h2>
    <div id="chart-freq"></div>
  </div>

  <!-- Serie de tiempo por número -->
  <div class="card">
    <h2>📈 Serie de tiempo por número</h2>
    <label>Número a analizar (1-56):</label>
    <input type="number" id="num-serie" min="1" max="56" value="7">
    <button onclick="cargarSerie()">Ver serie de tiempo</button>
    <div id="chart-serie"></div>
  </div>

  <!-- Hot & Cold -->
  <div class="card">
    <h2>🔥❄️ Números calientes y fríos</h2>
    <label>Ventana de sorteos recientes:</label>
    <input type="number" id="ventana-hc" value="30" min="10" max="500">
    <button onclick="cargarHotCold()">Analizar</button>
    <div id="hot-cold-result" style="margin-top:12px;"></div>
  </div>

  <!-- Predicción -->
  <div class="card">
    <h2>🔮 Predicción de próximos números</h2>
    <label>Ventana reciente para el modelo:</label>
    <input type="number" id="ventana-pred" value="50" min="10" max="500">
    <button onclick="predecir()">Generar predicción</button>
    <div id="resultado-pred"></div>
  </div>

  <!-- Verificador de combinación -->
  <div class="card full">
    <h2>🎯 Verifica tu combinación contra el historial</h2>
    <p style="color:#94a3b8; font-size:.85rem; margin-bottom:12px;">
      Selecciona exactamente 6 números y verifica cuántas coincidencias tuvieron en sorteos pasados.
    </p>
    <div class="numeros-selector" id="picker"></div>
    <p id="seleccion-label" style="color:#a78bfa; margin-bottom:10px;">Seleccionados: ninguno</p>
    <button onclick="verificar()">Verificar en historial</button>
    <div id="loader">Buscando coincidencias...</div>
    <div id="resultado-verif"></div>
  </div>

  <!-- Heatmap de co-ocurrencias -->
  <div class="card full">
    <h2>🧩 Co-ocurrencias entre pares de números</h2>
    <button onclick="cargarHeatmap()">Cargar mapa de calor (puede tardar)</button>
    <div id="chart-heatmap"></div>
  </div>
</div>

<script>
// ── Cargar gráfico de frecuencias al inicio ───────────────────────────────
fetch('/api/frecuencias')
  .then(r => r.json())
  .then(data => Plotly.newPlot('chart-freq', data.data, data.layout, {responsive:true}));

// ── Serie de tiempo ───────────────────────────────────────────────────────
function cargarSerie() {
  const n = document.getElementById('num-serie').value;
  fetch('/api/serie/' + n)
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-serie', data.data, data.layout, {responsive:true}));
}

// ── Hot & Cold ────────────────────────────────────────────────────────────
function cargarHotCold() {
  const v = document.getElementById('ventana-hc').value;
  fetch('/api/hotcold/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<p style="color:#f87171;font-size:.9rem;font-weight:bold;">🔥 Calientes</p>';
      html += '<div class="tags">' + data.calientes.map(n => `<span class="tag hot">${n}</span>`).join('') + '</div>';
      html += '<p style="color:#60a5fa;font-size:.9rem;font-weight:bold;margin-top:12px;">❄️ Fríos</p>';
      html += '<div class="tags">' + data.frios.map(n => `<span class="tag cold">${n}</span>`).join('') + '</div>';
      document.getElementById('hot-cold-result').innerHTML = html;
    });
}

// ── Predicción ────────────────────────────────────────────────────────────
function predecir() {
  const v = document.getElementById('ventana-pred').value;
  fetch('/api/predecir/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<table><thead><tr><th>Pos.</th><th>Número</th><th>Score</th><th>Frec. hist.</th><th>Frec. rec.</th><th>Brecha</th></tr></thead><tbody>';
      data.slice(0, 15).forEach((row, i) => {
        html += `<tr><td>${i+1}</td><td><b>${row.numero}</b></td><td>${row.score.toFixed(4)}</td><td>${row.frecuencia_h}</td><td>${row.frecuencia_r}</td><td>${row.brecha}</td></tr>`;
      });
      html += '</tbody></table>';
      html += '<div class="alert" style="margin-top:10px;">⚠️ El modelo combina frecuencia histórica, frecuencia reciente y brecha de aparición. No es garantía de acierto.</div>';
      document.getElementById('resultado-pred').innerHTML = html;
    });
}

// ── Picker de números ─────────────────────────────────────────────────────
const seleccionados = new Set();
const picker = document.getElementById('picker');
for (let i = 1; i <= 56; i++) {
  const btn = document.createElement('button');
  btn.className = 'num-btn';
  btn.textContent = i;
  btn.onclick = () => {
    if (seleccionados.has(i)) {
      seleccionados.delete(i);
      btn.classList.remove('selected');
    } else if (seleccionados.size < 6) {
      seleccionados.add(i);
      btn.classList.add('selected');
    }
    document.getElementById('seleccion-label').textContent =
      'Seleccionados: ' + (seleccionados.size ? [...seleccionados].sort((a,b)=>a-b).join(', ') : 'ninguno');
  };
  picker.appendChild(btn);
}

function verificar() {
  if (seleccionados.size !== 6) { alert('Selecciona exactamente 6 números.'); return; }
  document.getElementById('loader').style.display = 'block';
  document.getElementById('resultado-verif').innerHTML = '';
  fetch('/api/verificar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({numeros: [...seleccionados]})
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('loader').style.display = 'none';
    if (!data.length) {
      document.getElementById('resultado-verif').innerHTML =
        '<div class="alert">No se encontraron sorteos con 3 o más coincidencias.</div>';
      return;
    }
    let html = `<p style="margin:10px 0;color:#a78bfa;">${data.length} sorteos con ≥3 coincidencias:</p>`;
    html += '<table><thead><tr><th>Concurso</th><th>Fecha</th><th>Sorteo</th><th>Match</th><th>Aciertos</th></tr></thead><tbody>';
    data.forEach(r => {
      html += `<tr><td>${r.concurso}</td><td>${r.fecha}</td><td>${r.numeros_sorteo.join(', ')}</td>
               <td style="color:#fbbf24;">${r.numeros_match.join(', ')}</td>
               <td><b>${r.coincidencias}</b></td></tr>`;
    });
    html += '</tbody></table>';
    document.getElementById('resultado-verif').innerHTML = html;
  });
}

// ── Heatmap ───────────────────────────────────────────────────────────────
function cargarHeatmap() {
  document.getElementById('chart-heatmap').innerHTML = '<p style="color:#a78bfa;padding:20px;">Calculando... puede tomar unos segundos.</p>';
  fetch('/api/heatmap')
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-heatmap', data.data, data.layout, {responsive:true}));
}

// Cargar hot/cold automáticamente
cargarHotCold();
</script>
</body>
</html>
"""

# ── Rutas Flask ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/frecuencias")
def api_frecuencias():
    df = cargar_datos()
    return grafico_frecuencias(df)

@app.route("/api/serie/<int:numero>")
def api_serie(numero):
    if not 1 <= numero <= NUMEROS_MAX:
        return jsonify({"error": "Número fuera de rango"}), 400
    df = cargar_datos()
    return grafico_serie_tiempo(df, numero)

@app.route("/api/hotcold/<int:ventana>")
def api_hotcold(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    calientes, frios = hot_cold(df, ventana)
    return jsonify({
        "calientes": calientes["numero"].tolist(),
        "frios": frios["numero"].tolist(),
    })

@app.route("/api/predecir/<int:ventana>")
def api_predecir(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    score = predecir_numeros(df, ventana_reciente=ventana)
    return jsonify(score.head(20).to_dict(orient="records"))

@app.route("/api/verificar", methods=["POST"])
def api_verificar():
    data = request.get_json(force=True)
    numeros = data.get("numeros", [])
    if len(numeros) != 6:
        return jsonify({"error": "Se requieren exactamente 6 números"}), 400
    numeros = [int(n) for n in numeros if 1 <= int(n) <= NUMEROS_MAX]
    if len(numeros) != 6:
        return jsonify({"error": "Números fuera de rango"}), 400
    df = cargar_datos()
    resultados = verificar_combinacion(df, numeros)
    return jsonify(resultados)

@app.route("/api/heatmap")
def api_heatmap():
    df = cargar_datos()
    return grafico_heatmap_pares(df)

# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0
```


## License: GPL-3.0
https://github.com/Tranovice-SCEAV/TallyWeb/blob/ade0d93b1e3760403ee2ef172e7d22bd92a229f4/TallyWeb.py

```
Estructura clara: 7 números por sorteo (R1-R6 + R7 adicional) con fecha. Voy a escribir la app Flask completa ahora.No tengo herramienta de edición de archivos disponible. Te presento el código completo para que lo copies directamente en `modelopredictJD.py`:

```python
"""
modelopredictJD.py
App Flask de análisis y predicción de Melate
Basada en Historic.csv (columnas: CONCURSO, R1-R7, FECHA)
"""

import os
import pandas as pd
import numpy as np
from flask import Flask, render_template_string, request, jsonify
from collections import Counter
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

# ── Configuración ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "Historic.csv")
NUMEROS_MAX = 56   # Melate: 1-56
BOLA_ADICIONAL = True  # R7 es número adicional (Bolita)

app = Flask(__name__)

# ── Carga y preprocesamiento de datos ────────────────────────────────────────
def cargar_datos():
    df = pd.read_csv(CSV_PATH, dtype=str)
    df["FECHA"] = pd.to_datetime(df["FECHA"])
    cols_num = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=cols_num)
    df = df.sort_values("FECHA").reset_index(drop=True)
    return df

# ── Análisis de frecuencias ───────────────────────────────────────────────────
def calcular_frecuencias(df, incluir_adicional=False):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    if incluir_adicional:
        cols.append("R7")
    todos = df[cols].values.flatten().astype(int)
    conteo = Counter(todos)
    freq = pd.DataFrame(
        [(n, conteo.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)],
        columns=["numero", "frecuencia"]
    ).sort_values("frecuencia", ascending=False)
    return freq

# ── Frecuencia en ventana temporal (últimos N sorteos) ────────────────────────
def frecuencia_reciente(df, ventana=100, incluir_adicional=False):
    sub = df.tail(ventana)
    return calcular_frecuencias(sub, incluir_adicional)

# ── Análisis de "números fríos" y "calientes" ─────────────────────────────────
def hot_cold(df, ventana=30):
    reciente = calcular_frecuencias(df.tail(ventana))
    historico = calcular_frecuencias(df)
    merged = reciente.merge(historico, on="numero", suffixes=("_rec", "_hist"))
    merged["z_score"] = (
        (merged["frecuencia_rec"] - merged["frecuencia_rec"].mean())
        / (merged["frecuencia_rec"].std() + 1e-9)
    )
    calientes = merged.nlargest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    frios = merged.nsmallest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    return calientes, frios

# ── Modelo predictivo: probabilidad ponderada (bayesian-like) ─────────────────
def predecir_numeros(df, n_pred=6, ventana_reciente=50):
    """
    Combina frecuencia histórica + frecuencia reciente + brecha (números atrasados).
    Devuelve lista ordenada de candidatos con su score.
    """
    freq_hist = calcular_frecuencias(df)
    freq_rec  = frecuencia_reciente(df, ventana=ventana_reciente)
    
    # Calcular brecha: sorteos desde la última aparición de cada número
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    ultimas = {}
    for idx, row in df.iterrows():
        for c in cols:
            n = int(row[c])
            ultimas[n] = idx   # último sorteo donde apareció
    total = len(df)
    brecha = {n: (total - ultimas.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)}
    brecha_s = pd.DataFrame(list(brecha.items()), columns=["numero", "brecha"])

    # Merge de señales
    score = freq_hist.merge(freq_rec, on="numero", suffixes=("_h", "_r"))
    score = score.merge(brecha_s, on="numero")
    
    # Normalizar cada señal a [0,1]
    for col in ["frecuencia_h", "frecuencia_r", "brecha"]:
        rng = score[col].max() - score[col].min()
        score[col + "_n"] = (score[col] - score[col].min()) / (rng + 1e-9)

    # Score compuesto: 40% hist + 40% reciente + 20% brecha
    score["score"] = (
        0.40 * score["frecuencia_h_n"]
        + 0.40 * score["frecuencia_r_n"]
        + 0.20 * score["brecha_n"]
    )
    score = score.sort_values("score", ascending=False).reset_index(drop=True)
    return score[["numero", "score", "frecuencia_h", "frecuencia_r", "brecha"]]

# ── Verificar si una combinación del usuario ha ganado antes ──────────────────
def verificar_combinacion(df, numeros_usuario: list[int]):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    set_usr = set(numeros_usuario)
    resultados = []
    for _, row in df.iterrows():
        set_row = {int(row[c]) for c in cols}
        coincidencias = set_usr & set_row
        if len(coincidencias) >= 3:
            resultados.append({
                "concurso": row["CONCURSO"],
                "fecha": str(row["FECHA"].date()),
                "numeros_sorteo": sorted(set_row),
                "coincidencias": len(coincidencias),
                "numeros_match": sorted(coincidencias),
            })
    return sorted(resultados, key=lambda x: -x["coincidencias"])[:20]

# ── Gráficos Plotly ───────────────────────────────────────────────────────────
def grafico_frecuencias(df):
    freq = calcular_frecuencias(df)
    fig = px.bar(
        freq, x="numero", y="frecuencia",
        title="Frecuencia histórica de números (R1-R6)",
        labels={"numero": "Número", "frecuencia": "Veces sorteado"},
        color="frecuencia",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(xaxis=dict(dtick=1), plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
                      font_color="white", title_font_size=16)
    return fig.to_json()

def grafico_serie_tiempo(df, numero: int):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    df["aparece"] = df[cols].apply(lambda r: int(numero in r.values), axis=1)
    df["acumulado"] = df["aparece"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["FECHA"], y=df["acumulado"],
        mode="lines", name=f"Número {numero} acumulado",
        line=dict(color="#a78bfa", width=2)
    ))
    fig.update_layout(
        title=f"Apariciones acumuladas del número {numero} en el tiempo",
        xaxis_title="Fecha", yaxis_title="Apariciones acumuladas",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white"
    )
    return fig.to_json()

def grafico_heatmap_pares(df):
    """Mapa de calor de co-ocurrencias entre números (R1-R6)."""
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    numeros = range(1, NUMEROS_MAX + 1)
    mat = np.zeros((NUMEROS_MAX, NUMEROS_MAX), dtype=int)
    for _, row in df.iterrows():
        ns = [int(row[c]) for c in cols]
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                a, b = ns[i] - 1, ns[j] - 1
                mat[a][b] += 1
                mat[b][a] += 1
    fig = go.Figure(go.Heatmap(
        z=mat, colorscale="Plasma",
        hovertemplate="(%{x}, %{y}): %{z}<extra></extra>"
    ))
    fig.update_layout(
        title="Co-ocurrencias entre pares de números",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white", height=600,
    )
    return fig.to_json()

# ── HTML Template ─────────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Predictor Melate — JD</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #13131f; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; padding: 20px; }
  h1 { color: #a78bfa; text-align: center; margin-bottom: 8px; font-size: 2rem; }
  .subtitle { text-align: center; color: #94a3b8; margin-bottom: 30px; font-size: .9rem; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media(max-width:768px){ .grid { grid-template-columns: 1fr; } }
  .card { background: #1e1e2e; border-radius: 12px; padding: 20px; border: 1px solid #2e2e4e; }
  .card h2 { color: #c4b5fd; margin-bottom: 14px; font-size: 1.1rem; }
  input[type=text], input[type=number], select {
    background: #2a2a3e; border: 1px solid #4c4c75; color: #e2e8f0;
    border-radius: 6px; padding: 8px 12px; width: 100%; margin-bottom: 10px; font-size: .95rem;
  }
  button {
    background: #7c3aed; color: white; border: none; border-radius: 8px;
    padding: 10px 20px; cursor: pointer; font-size: .95rem; width: 100%;
    transition: background .2s;
  }
  button:hover { background: #6d28d9; }
  .numeros-selector { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
  .num-btn {
    width: 42px; height: 42px; border-radius: 50%; background: #2a2a3e;
    border: 2px solid #4c4c75; color: #e2e8f0; cursor: pointer;
    font-weight: bold; transition: all .15s;
  }
  .num-btn.selected { background: #7c3aed; border-color: #a78bfa; color: white; }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; }
  .tag { background: #7c3aed; border-radius: 20px; padding: 4px 12px; font-size: .85rem; }
  .tag.cold { background: #1d4ed8; }
  .tag.hot { background: #dc2626; }
  #resultado-pred { margin-top: 14px; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th { background: #2a2a3e; padding: 8px; text-align: left; color: #a78bfa; }
  td { padding: 7px 8px; border-bottom: 1px solid #2a2a3e; }
  tr:hover td { background: #252535; }
  .alert { background: #1e3a5f; border-left: 3px solid #3b82f6; padding: 10px; border-radius: 6px; margin-top: 10px; font-size: .85rem;}
  .full { grid-column: 1 / -1; }
  #loader { display:none; text-align:center; color: #a78bfa; margin-top: 10px; }
</style>
</head>
<body>
<h1>🎱 Predictor Melate</h1>
<p class="subtitle">Análisis estadístico del sorteo histórico — no garantiza resultados</p>

<div class="grid">
  <!-- Frecuencias Históricas -->
  <div class="card full">
    <h2>📊 Frecuencia histórica de números</h2>
    <div id="chart-freq"></div>
  </div>

  <!-- Serie de tiempo por número -->
  <div class="card">
    <h2>📈 Serie de tiempo por número</h2>
    <label>Número a analizar (1-56):</label>
    <input type="number" id="num-serie" min="1" max="56" value="7">
    <button onclick="cargarSerie()">Ver serie de tiempo</button>
    <div id="chart-serie"></div>
  </div>

  <!-- Hot & Cold -->
  <div class="card">
    <h2>🔥❄️ Números calientes y fríos</h2>
    <label>Ventana de sorteos recientes:</label>
    <input type="number" id="ventana-hc" value="30" min="10" max="500">
    <button onclick="cargarHotCold()">Analizar</button>
    <div id="hot-cold-result" style="margin-top:12px;"></div>
  </div>

  <!-- Predicción -->
  <div class="card">
    <h2>🔮 Predicción de próximos números</h2>
    <label>Ventana reciente para el modelo:</label>
    <input type="number" id="ventana-pred" value="50" min="10" max="500">
    <button onclick="predecir()">Generar predicción</button>
    <div id="resultado-pred"></div>
  </div>

  <!-- Verificador de combinación -->
  <div class="card full">
    <h2>🎯 Verifica tu combinación contra el historial</h2>
    <p style="color:#94a3b8; font-size:.85rem; margin-bottom:12px;">
      Selecciona exactamente 6 números y verifica cuántas coincidencias tuvieron en sorteos pasados.
    </p>
    <div class="numeros-selector" id="picker"></div>
    <p id="seleccion-label" style="color:#a78bfa; margin-bottom:10px;">Seleccionados: ninguno</p>
    <button onclick="verificar()">Verificar en historial</button>
    <div id="loader">Buscando coincidencias...</div>
    <div id="resultado-verif"></div>
  </div>

  <!-- Heatmap de co-ocurrencias -->
  <div class="card full">
    <h2>🧩 Co-ocurrencias entre pares de números</h2>
    <button onclick="cargarHeatmap()">Cargar mapa de calor (puede tardar)</button>
    <div id="chart-heatmap"></div>
  </div>
</div>

<script>
// ── Cargar gráfico de frecuencias al inicio ───────────────────────────────
fetch('/api/frecuencias')
  .then(r => r.json())
  .then(data => Plotly.newPlot('chart-freq', data.data, data.layout, {responsive:true}));

// ── Serie de tiempo ───────────────────────────────────────────────────────
function cargarSerie() {
  const n = document.getElementById('num-serie').value;
  fetch('/api/serie/' + n)
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-serie', data.data, data.layout, {responsive:true}));
}

// ── Hot & Cold ────────────────────────────────────────────────────────────
function cargarHotCold() {
  const v = document.getElementById('ventana-hc').value;
  fetch('/api/hotcold/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<p style="color:#f87171;font-size:.9rem;font-weight:bold;">🔥 Calientes</p>';
      html += '<div class="tags">' + data.calientes.map(n => `<span class="tag hot">${n}</span>`).join('') + '</div>';
      html += '<p style="color:#60a5fa;font-size:.9rem;font-weight:bold;margin-top:12px;">❄️ Fríos</p>';
      html += '<div class="tags">' + data.frios.map(n => `<span class="tag cold">${n}</span>`).join('') + '</div>';
      document.getElementById('hot-cold-result').innerHTML = html;
    });
}

// ── Predicción ────────────────────────────────────────────────────────────
function predecir() {
  const v = document.getElementById('ventana-pred').value;
  fetch('/api/predecir/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<table><thead><tr><th>Pos.</th><th>Número</th><th>Score</th><th>Frec. hist.</th><th>Frec. rec.</th><th>Brecha</th></tr></thead><tbody>';
      data.slice(0, 15).forEach((row, i) => {
        html += `<tr><td>${i+1}</td><td><b>${row.numero}</b></td><td>${row.score.toFixed(4)}</td><td>${row.frecuencia_h}</td><td>${row.frecuencia_r}</td><td>${row.brecha}</td></tr>`;
      });
      html += '</tbody></table>';
      html += '<div class="alert" style="margin-top:10px;">⚠️ El modelo combina frecuencia histórica, frecuencia reciente y brecha de aparición. No es garantía de acierto.</div>';
      document.getElementById('resultado-pred').innerHTML = html;
    });
}

// ── Picker de números ─────────────────────────────────────────────────────
const seleccionados = new Set();
const picker = document.getElementById('picker');
for (let i = 1; i <= 56; i++) {
  const btn = document.createElement('button');
  btn.className = 'num-btn';
  btn.textContent = i;
  btn.onclick = () => {
    if (seleccionados.has(i)) {
      seleccionados.delete(i);
      btn.classList.remove('selected');
    } else if (seleccionados.size < 6) {
      seleccionados.add(i);
      btn.classList.add('selected');
    }
    document.getElementById('seleccion-label').textContent =
      'Seleccionados: ' + (seleccionados.size ? [...seleccionados].sort((a,b)=>a-b).join(', ') : 'ninguno');
  };
  picker.appendChild(btn);
}

function verificar() {
  if (seleccionados.size !== 6) { alert('Selecciona exactamente 6 números.'); return; }
  document.getElementById('loader').style.display = 'block';
  document.getElementById('resultado-verif').innerHTML = '';
  fetch('/api/verificar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({numeros: [...seleccionados]})
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('loader').style.display = 'none';
    if (!data.length) {
      document.getElementById('resultado-verif').innerHTML =
        '<div class="alert">No se encontraron sorteos con 3 o más coincidencias.</div>';
      return;
    }
    let html = `<p style="margin:10px 0;color:#a78bfa;">${data.length} sorteos con ≥3 coincidencias:</p>`;
    html += '<table><thead><tr><th>Concurso</th><th>Fecha</th><th>Sorteo</th><th>Match</th><th>Aciertos</th></tr></thead><tbody>';
    data.forEach(r => {
      html += `<tr><td>${r.concurso}</td><td>${r.fecha}</td><td>${r.numeros_sorteo.join(', ')}</td>
               <td style="color:#fbbf24;">${r.numeros_match.join(', ')}</td>
               <td><b>${r.coincidencias}</b></td></tr>`;
    });
    html += '</tbody></table>';
    document.getElementById('resultado-verif').innerHTML = html;
  });
}

// ── Heatmap ───────────────────────────────────────────────────────────────
function cargarHeatmap() {
  document.getElementById('chart-heatmap').innerHTML = '<p style="color:#a78bfa;padding:20px;">Calculando... puede tomar unos segundos.</p>';
  fetch('/api/heatmap')
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-heatmap', data.data, data.layout, {responsive:true}));
}

// Cargar hot/cold automáticamente
cargarHotCold();
</script>
</body>
</html>
"""

# ── Rutas Flask ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/frecuencias")
def api_frecuencias():
    df = cargar_datos()
    return grafico_frecuencias(df)

@app.route("/api/serie/<int:numero>")
def api_serie(numero):
    if not 1 <= numero <= NUMEROS_MAX:
        return jsonify({"error": "Número fuera de rango"}), 400
    df = cargar_datos()
    return grafico_serie_tiempo(df, numero)

@app.route("/api/hotcold/<int:ventana>")
def api_hotcold(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    calientes, frios = hot_cold(df, ventana)
    return jsonify({
        "calientes": calientes["numero"].tolist(),
        "frios": frios["numero"].tolist(),
    })

@app.route("/api/predecir/<int:ventana>")
def api_predecir(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    score = predecir_numeros(df, ventana_reciente=ventana)
    return jsonify(score.head(20).to_dict(orient="records"))

@app.route("/api/verificar", methods=["POST"])
def api_verificar():
    data = request.get_json(force=True)
    numeros = data.get("numeros", [])
    if len(numeros) != 6:
        return jsonify({"error": "Se requieren exactamente 6 números"}), 400
    numeros = [int(n) for n in numeros if 1 <= int(n) <= NUMEROS_MAX]
    if len(numeros) != 6:
        return jsonify({"error": "Números fuera de rango"}), 400
    df = cargar_datos()
    resultados = verificar_combinacion(df, numeros)
    return jsonify(resultados)

@app.route("/api/heatmap")
def api_heatmap():
    df = cargar_datos()
    return grafico_heatmap_pares(df)

# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0
```


## License: desconocido
https://github.com/fer-moreira/Network-Tools/blob/ef8a46136544213e36c723290062644ea46e38b0/Netool/netool.py

```
Estructura clara: 7 números por sorteo (R1-R6 + R7 adicional) con fecha. Voy a escribir la app Flask completa ahora.No tengo herramienta de edición de archivos disponible. Te presento el código completo para que lo copies directamente en `modelopredictJD.py`:

```python
"""
modelopredictJD.py
App Flask de análisis y predicción de Melate
Basada en Historic.csv (columnas: CONCURSO, R1-R7, FECHA)
"""

import os
import pandas as pd
import numpy as np
from flask import Flask, render_template_string, request, jsonify
from collections import Counter
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

# ── Configuración ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "Historic.csv")
NUMEROS_MAX = 56   # Melate: 1-56
BOLA_ADICIONAL = True  # R7 es número adicional (Bolita)

app = Flask(__name__)

# ── Carga y preprocesamiento de datos ────────────────────────────────────────
def cargar_datos():
    df = pd.read_csv(CSV_PATH, dtype=str)
    df["FECHA"] = pd.to_datetime(df["FECHA"])
    cols_num = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=cols_num)
    df = df.sort_values("FECHA").reset_index(drop=True)
    return df

# ── Análisis de frecuencias ───────────────────────────────────────────────────
def calcular_frecuencias(df, incluir_adicional=False):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    if incluir_adicional:
        cols.append("R7")
    todos = df[cols].values.flatten().astype(int)
    conteo = Counter(todos)
    freq = pd.DataFrame(
        [(n, conteo.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)],
        columns=["numero", "frecuencia"]
    ).sort_values("frecuencia", ascending=False)
    return freq

# ── Frecuencia en ventana temporal (últimos N sorteos) ────────────────────────
def frecuencia_reciente(df, ventana=100, incluir_adicional=False):
    sub = df.tail(ventana)
    return calcular_frecuencias(sub, incluir_adicional)

# ── Análisis de "números fríos" y "calientes" ─────────────────────────────────
def hot_cold(df, ventana=30):
    reciente = calcular_frecuencias(df.tail(ventana))
    historico = calcular_frecuencias(df)
    merged = reciente.merge(historico, on="numero", suffixes=("_rec", "_hist"))
    merged["z_score"] = (
        (merged["frecuencia_rec"] - merged["frecuencia_rec"].mean())
        / (merged["frecuencia_rec"].std() + 1e-9)
    )
    calientes = merged.nlargest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    frios = merged.nsmallest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    return calientes, frios

# ── Modelo predictivo: probabilidad ponderada (bayesian-like) ─────────────────
def predecir_numeros(df, n_pred=6, ventana_reciente=50):
    """
    Combina frecuencia histórica + frecuencia reciente + brecha (números atrasados).
    Devuelve lista ordenada de candidatos con su score.
    """
    freq_hist = calcular_frecuencias(df)
    freq_rec  = frecuencia_reciente(df, ventana=ventana_reciente)
    
    # Calcular brecha: sorteos desde la última aparición de cada número
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    ultimas = {}
    for idx, row in df.iterrows():
        for c in cols:
            n = int(row[c])
            ultimas[n] = idx   # último sorteo donde apareció
    total = len(df)
    brecha = {n: (total - ultimas.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)}
    brecha_s = pd.DataFrame(list(brecha.items()), columns=["numero", "brecha"])

    # Merge de señales
    score = freq_hist.merge(freq_rec, on="numero", suffixes=("_h", "_r"))
    score = score.merge(brecha_s, on="numero")
    
    # Normalizar cada señal a [0,1]
    for col in ["frecuencia_h", "frecuencia_r", "brecha"]:
        rng = score[col].max() - score[col].min()
        score[col + "_n"] = (score[col] - score[col].min()) / (rng + 1e-9)

    # Score compuesto: 40% hist + 40% reciente + 20% brecha
    score["score"] = (
        0.40 * score["frecuencia_h_n"]
        + 0.40 * score["frecuencia_r_n"]
        + 0.20 * score["brecha_n"]
    )
    score = score.sort_values("score", ascending=False).reset_index(drop=True)
    return score[["numero", "score", "frecuencia_h", "frecuencia_r", "brecha"]]

# ── Verificar si una combinación del usuario ha ganado antes ──────────────────
def verificar_combinacion(df, numeros_usuario: list[int]):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    set_usr = set(numeros_usuario)
    resultados = []
    for _, row in df.iterrows():
        set_row = {int(row[c]) for c in cols}
        coincidencias = set_usr & set_row
        if len(coincidencias) >= 3:
            resultados.append({
                "concurso": row["CONCURSO"],
                "fecha": str(row["FECHA"].date()),
                "numeros_sorteo": sorted(set_row),
                "coincidencias": len(coincidencias),
                "numeros_match": sorted(coincidencias),
            })
    return sorted(resultados, key=lambda x: -x["coincidencias"])[:20]

# ── Gráficos Plotly ───────────────────────────────────────────────────────────
def grafico_frecuencias(df):
    freq = calcular_frecuencias(df)
    fig = px.bar(
        freq, x="numero", y="frecuencia",
        title="Frecuencia histórica de números (R1-R6)",
        labels={"numero": "Número", "frecuencia": "Veces sorteado"},
        color="frecuencia",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(xaxis=dict(dtick=1), plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
                      font_color="white", title_font_size=16)
    return fig.to_json()

def grafico_serie_tiempo(df, numero: int):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    df["aparece"] = df[cols].apply(lambda r: int(numero in r.values), axis=1)
    df["acumulado"] = df["aparece"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["FECHA"], y=df["acumulado"],
        mode="lines", name=f"Número {numero} acumulado",
        line=dict(color="#a78bfa", width=2)
    ))
    fig.update_layout(
        title=f"Apariciones acumuladas del número {numero} en el tiempo",
        xaxis_title="Fecha", yaxis_title="Apariciones acumuladas",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white"
    )
    return fig.to_json()

def grafico_heatmap_pares(df):
    """Mapa de calor de co-ocurrencias entre números (R1-R6)."""
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    numeros = range(1, NUMEROS_MAX + 1)
    mat = np.zeros((NUMEROS_MAX, NUMEROS_MAX), dtype=int)
    for _, row in df.iterrows():
        ns = [int(row[c]) for c in cols]
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                a, b = ns[i] - 1, ns[j] - 1
                mat[a][b] += 1
                mat[b][a] += 1
    fig = go.Figure(go.Heatmap(
        z=mat, colorscale="Plasma",
        hovertemplate="(%{x}, %{y}): %{z}<extra></extra>"
    ))
    fig.update_layout(
        title="Co-ocurrencias entre pares de números",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white", height=600,
    )
    return fig.to_json()

# ── HTML Template ─────────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Predictor Melate — JD</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #13131f; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; padding: 20px; }
  h1 { color: #a78bfa; text-align: center; margin-bottom: 8px; font-size: 2rem; }
  .subtitle { text-align: center; color: #94a3b8; margin-bottom: 30px; font-size: .9rem; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media(max-width:768px){ .grid { grid-template-columns: 1fr; } }
  .card { background: #1e1e2e; border-radius: 12px; padding: 20px; border: 1px solid #2e2e4e; }
  .card h2 { color: #c4b5fd; margin-bottom: 14px; font-size: 1.1rem; }
  input[type=text], input[type=number], select {
    background: #2a2a3e; border: 1px solid #4c4c75; color: #e2e8f0;
    border-radius: 6px; padding: 8px 12px; width: 100%; margin-bottom: 10px; font-size: .95rem;
  }
  button {
    background: #7c3aed; color: white; border: none; border-radius: 8px;
    padding: 10px 20px; cursor: pointer; font-size: .95rem; width: 100%;
    transition: background .2s;
  }
  button:hover { background: #6d28d9; }
  .numeros-selector { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
  .num-btn {
    width: 42px; height: 42px; border-radius: 50%; background: #2a2a3e;
    border: 2px solid #4c4c75; color: #e2e8f0; cursor: pointer;
    font-weight: bold; transition: all .15s;
  }
  .num-btn.selected { background: #7c3aed; border-color: #a78bfa; color: white; }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; }
  .tag { background: #7c3aed; border-radius: 20px; padding: 4px 12px; font-size: .85rem; }
  .tag.cold { background: #1d4ed8; }
  .tag.hot { background: #dc2626; }
  #resultado-pred { margin-top: 14px; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th { background: #2a2a3e; padding: 8px; text-align: left; color: #a78bfa; }
  td { padding: 7px 8px; border-bottom: 1px solid #2a2a3e; }
  tr:hover td { background: #252535; }
  .alert { background: #1e3a5f; border-left: 3px solid #3b82f6; padding: 10px; border-radius: 6px; margin-top: 10px; font-size: .85rem;}
  .full { grid-column: 1 / -1; }
  #loader { display:none; text-align:center; color: #a78bfa; margin-top: 10px; }
</style>
</head>
<body>
<h1>🎱 Predictor Melate</h1>
<p class="subtitle">Análisis estadístico del sorteo histórico — no garantiza resultados</p>

<div class="grid">
  <!-- Frecuencias Históricas -->
  <div class="card full">
    <h2>📊 Frecuencia histórica de números</h2>
    <div id="chart-freq"></div>
  </div>

  <!-- Serie de tiempo por número -->
  <div class="card">
    <h2>📈 Serie de tiempo por número</h2>
    <label>Número a analizar (1-56):</label>
    <input type="number" id="num-serie" min="1" max="56" value="7">
    <button onclick="cargarSerie()">Ver serie de tiempo</button>
    <div id="chart-serie"></div>
  </div>

  <!-- Hot & Cold -->
  <div class="card">
    <h2>🔥❄️ Números calientes y fríos</h2>
    <label>Ventana de sorteos recientes:</label>
    <input type="number" id="ventana-hc" value="30" min="10" max="500">
    <button onclick="cargarHotCold()">Analizar</button>
    <div id="hot-cold-result" style="margin-top:12px;"></div>
  </div>

  <!-- Predicción -->
  <div class="card">
    <h2>🔮 Predicción de próximos números</h2>
    <label>Ventana reciente para el modelo:</label>
    <input type="number" id="ventana-pred" value="50" min="10" max="500">
    <button onclick="predecir()">Generar predicción</button>
    <div id="resultado-pred"></div>
  </div>

  <!-- Verificador de combinación -->
  <div class="card full">
    <h2>🎯 Verifica tu combinación contra el historial</h2>
    <p style="color:#94a3b8; font-size:.85rem; margin-bottom:12px;">
      Selecciona exactamente 6 números y verifica cuántas coincidencias tuvieron en sorteos pasados.
    </p>
    <div class="numeros-selector" id="picker"></div>
    <p id="seleccion-label" style="color:#a78bfa; margin-bottom:10px;">Seleccionados: ninguno</p>
    <button onclick="verificar()">Verificar en historial</button>
    <div id="loader">Buscando coincidencias...</div>
    <div id="resultado-verif"></div>
  </div>

  <!-- Heatmap de co-ocurrencias -->
  <div class="card full">
    <h2>🧩 Co-ocurrencias entre pares de números</h2>
    <button onclick="cargarHeatmap()">Cargar mapa de calor (puede tardar)</button>
    <div id="chart-heatmap"></div>
  </div>
</div>

<script>
// ── Cargar gráfico de frecuencias al inicio ───────────────────────────────
fetch('/api/frecuencias')
  .then(r => r.json())
  .then(data => Plotly.newPlot('chart-freq', data.data, data.layout, {responsive:true}));

// ── Serie de tiempo ───────────────────────────────────────────────────────
function cargarSerie() {
  const n = document.getElementById('num-serie').value;
  fetch('/api/serie/' + n)
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-serie', data.data, data.layout, {responsive:true}));
}

// ── Hot & Cold ────────────────────────────────────────────────────────────
function cargarHotCold() {
  const v = document.getElementById('ventana-hc').value;
  fetch('/api/hotcold/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<p style="color:#f87171;font-size:.9rem;font-weight:bold;">🔥 Calientes</p>';
      html += '<div class="tags">' + data.calientes.map(n => `<span class="tag hot">${n}</span>`).join('') + '</div>';
      html += '<p style="color:#60a5fa;font-size:.9rem;font-weight:bold;margin-top:12px;">❄️ Fríos</p>';
      html += '<div class="tags">' + data.frios.map(n => `<span class="tag cold">${n}</span>`).join('') + '</div>';
      document.getElementById('hot-cold-result').innerHTML = html;
    });
}

// ── Predicción ────────────────────────────────────────────────────────────
function predecir() {
  const v = document.getElementById('ventana-pred').value;
  fetch('/api/predecir/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<table><thead><tr><th>Pos.</th><th>Número</th><th>Score</th><th>Frec. hist.</th><th>Frec. rec.</th><th>Brecha</th></tr></thead><tbody>';
      data.slice(0, 15).forEach((row, i) => {
        html += `<tr><td>${i+1}</td><td><b>${row.numero}</b></td><td>${row.score.toFixed(4)}</td><td>${row.frecuencia_h}</td><td>${row.frecuencia_r}</td><td>${row.brecha}</td></tr>`;
      });
      html += '</tbody></table>';
      html += '<div class="alert" style="margin-top:10px;">⚠️ El modelo combina frecuencia histórica, frecuencia reciente y brecha de aparición. No es garantía de acierto.</div>';
      document.getElementById('resultado-pred').innerHTML = html;
    });
}

// ── Picker de números ─────────────────────────────────────────────────────
const seleccionados = new Set();
const picker = document.getElementById('picker');
for (let i = 1; i <= 56; i++) {
  const btn = document.createElement('button');
  btn.className = 'num-btn';
  btn.textContent = i;
  btn.onclick = () => {
    if (seleccionados.has(i)) {
      seleccionados.delete(i);
      btn.classList.remove('selected');
    } else if (seleccionados.size < 6) {
      seleccionados.add(i);
      btn.classList.add('selected');
    }
    document.getElementById('seleccion-label').textContent =
      'Seleccionados: ' + (seleccionados.size ? [...seleccionados].sort((a,b)=>a-b).join(', ') : 'ninguno');
  };
  picker.appendChild(btn);
}

function verificar() {
  if (seleccionados.size !== 6) { alert('Selecciona exactamente 6 números.'); return; }
  document.getElementById('loader').style.display = 'block';
  document.getElementById('resultado-verif').innerHTML = '';
  fetch('/api/verificar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({numeros: [...seleccionados]})
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('loader').style.display = 'none';
    if (!data.length) {
      document.getElementById('resultado-verif').innerHTML =
        '<div class="alert">No se encontraron sorteos con 3 o más coincidencias.</div>';
      return;
    }
    let html = `<p style="margin:10px 0;color:#a78bfa;">${data.length} sorteos con ≥3 coincidencias:</p>`;
    html += '<table><thead><tr><th>Concurso</th><th>Fecha</th><th>Sorteo</th><th>Match</th><th>Aciertos</th></tr></thead><tbody>';
    data.forEach(r => {
      html += `<tr><td>${r.concurso}</td><td>${r.fecha}</td><td>${r.numeros_sorteo.join(', ')}</td>
               <td style="color:#fbbf24;">${r.numeros_match.join(', ')}</td>
               <td><b>${r.coincidencias}</b></td></tr>`;
    });
    html += '</tbody></table>';
    document.getElementById('resultado-verif').innerHTML = html;
  });
}

// ── Heatmap ───────────────────────────────────────────────────────────────
function cargarHeatmap() {
  document.getElementById('chart-heatmap').innerHTML = '<p style="color:#a78bfa;padding:20px;">Calculando... puede tomar unos segundos.</p>';
  fetch('/api/heatmap')
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-heatmap', data.data, data.layout, {responsive:true}));
}

// Cargar hot/cold automáticamente
cargarHotCold();
</script>
</body>
</html>
"""

# ── Rutas Flask ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/frecuencias")
def api_frecuencias():
    df = cargar_datos()
    return grafico_frecuencias(df)

@app.route("/api/serie/<int:numero>")
def api_serie(numero):
    if not 1 <= numero <= NUMEROS_MAX:
        return jsonify({"error": "Número fuera de rango"}), 400
    df = cargar_datos()
    return grafico_serie_tiempo(df, numero)

@app.route("/api/hotcold/<int:ventana>")
def api_hotcold(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    calientes, frios = hot_cold(df, ventana)
    return jsonify({
        "calientes": calientes["numero"].tolist(),
        "frios": frios["numero"].tolist(),
    })

@app.route("/api/predecir/<int:ventana>")
def api_predecir(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    score = predecir_numeros(df, ventana_reciente=ventana)
    return jsonify(score.head(20).to_dict(orient="records"))

@app.route("/api/verificar", methods=["POST"])
def api_verificar():
    data = request.get_json(force=True)
    numeros = data.get("numeros", [])
    if len(numeros) != 6:
        return jsonify({"error": "Se requieren exactamente 6 números"}), 400
    numeros = [int(n) for n in numeros if 1 <= int(n) <= NUMEROS_MAX]
    if len(numeros) != 6:
        return jsonify({"error": "Números fuera de rango"}), 400
    df = cargar_datos()
    resultados = verificar_combinacion(df, numeros)
    return jsonify(resultados)

@app.route("/api/heatmap")
def api_heatmap():
    df = cargar_datos()
    return grafico_heatmap_pares(df)

# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0
```


## License: GPL-3.0
https://github.com/Tranovice-SCEAV/TallyWeb/blob/ade0d93b1e3760403ee2ef172e7d22bd92a229f4/TallyWeb.py

```
Estructura clara: 7 números por sorteo (R1-R6 + R7 adicional) con fecha. Voy a escribir la app Flask completa ahora.No tengo herramienta de edición de archivos disponible. Te presento el código completo para que lo copies directamente en `modelopredictJD.py`:

```python
"""
modelopredictJD.py
App Flask de análisis y predicción de Melate
Basada en Historic.csv (columnas: CONCURSO, R1-R7, FECHA)
"""

import os
import pandas as pd
import numpy as np
from flask import Flask, render_template_string, request, jsonify
from collections import Counter
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

# ── Configuración ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "Historic.csv")
NUMEROS_MAX = 56   # Melate: 1-56
BOLA_ADICIONAL = True  # R7 es número adicional (Bolita)

app = Flask(__name__)

# ── Carga y preprocesamiento de datos ────────────────────────────────────────
def cargar_datos():
    df = pd.read_csv(CSV_PATH, dtype=str)
    df["FECHA"] = pd.to_datetime(df["FECHA"])
    cols_num = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=cols_num)
    df = df.sort_values("FECHA").reset_index(drop=True)
    return df

# ── Análisis de frecuencias ───────────────────────────────────────────────────
def calcular_frecuencias(df, incluir_adicional=False):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    if incluir_adicional:
        cols.append("R7")
    todos = df[cols].values.flatten().astype(int)
    conteo = Counter(todos)
    freq = pd.DataFrame(
        [(n, conteo.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)],
        columns=["numero", "frecuencia"]
    ).sort_values("frecuencia", ascending=False)
    return freq

# ── Frecuencia en ventana temporal (últimos N sorteos) ────────────────────────
def frecuencia_reciente(df, ventana=100, incluir_adicional=False):
    sub = df.tail(ventana)
    return calcular_frecuencias(sub, incluir_adicional)

# ── Análisis de "números fríos" y "calientes" ─────────────────────────────────
def hot_cold(df, ventana=30):
    reciente = calcular_frecuencias(df.tail(ventana))
    historico = calcular_frecuencias(df)
    merged = reciente.merge(historico, on="numero", suffixes=("_rec", "_hist"))
    merged["z_score"] = (
        (merged["frecuencia_rec"] - merged["frecuencia_rec"].mean())
        / (merged["frecuencia_rec"].std() + 1e-9)
    )
    calientes = merged.nlargest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    frios = merged.nsmallest(10, "z_score")[["numero", "frecuencia_rec", "z_score"]]
    return calientes, frios

# ── Modelo predictivo: probabilidad ponderada (bayesian-like) ─────────────────
def predecir_numeros(df, n_pred=6, ventana_reciente=50):
    """
    Combina frecuencia histórica + frecuencia reciente + brecha (números atrasados).
    Devuelve lista ordenada de candidatos con su score.
    """
    freq_hist = calcular_frecuencias(df)
    freq_rec  = frecuencia_reciente(df, ventana=ventana_reciente)
    
    # Calcular brecha: sorteos desde la última aparición de cada número
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    ultimas = {}
    for idx, row in df.iterrows():
        for c in cols:
            n = int(row[c])
            ultimas[n] = idx   # último sorteo donde apareció
    total = len(df)
    brecha = {n: (total - ultimas.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)}
    brecha_s = pd.DataFrame(list(brecha.items()), columns=["numero", "brecha"])

    # Merge de señales
    score = freq_hist.merge(freq_rec, on="numero", suffixes=("_h", "_r"))
    score = score.merge(brecha_s, on="numero")
    
    # Normalizar cada señal a [0,1]
    for col in ["frecuencia_h", "frecuencia_r", "brecha"]:
        rng = score[col].max() - score[col].min()
        score[col + "_n"] = (score[col] - score[col].min()) / (rng + 1e-9)

    # Score compuesto: 40% hist + 40% reciente + 20% brecha
    score["score"] = (
        0.40 * score["frecuencia_h_n"]
        + 0.40 * score["frecuencia_r_n"]
        + 0.20 * score["brecha_n"]
    )
    score = score.sort_values("score", ascending=False).reset_index(drop=True)
    return score[["numero", "score", "frecuencia_h", "frecuencia_r", "brecha"]]

# ── Verificar si una combinación del usuario ha ganado antes ──────────────────
def verificar_combinacion(df, numeros_usuario: list[int]):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    set_usr = set(numeros_usuario)
    resultados = []
    for _, row in df.iterrows():
        set_row = {int(row[c]) for c in cols}
        coincidencias = set_usr & set_row
        if len(coincidencias) >= 3:
            resultados.append({
                "concurso": row["CONCURSO"],
                "fecha": str(row["FECHA"].date()),
                "numeros_sorteo": sorted(set_row),
                "coincidencias": len(coincidencias),
                "numeros_match": sorted(coincidencias),
            })
    return sorted(resultados, key=lambda x: -x["coincidencias"])[:20]

# ── Gráficos Plotly ───────────────────────────────────────────────────────────
def grafico_frecuencias(df):
    freq = calcular_frecuencias(df)
    fig = px.bar(
        freq, x="numero", y="frecuencia",
        title="Frecuencia histórica de números (R1-R6)",
        labels={"numero": "Número", "frecuencia": "Veces sorteado"},
        color="frecuencia",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(xaxis=dict(dtick=1), plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
                      font_color="white", title_font_size=16)
    return fig.to_json()

def grafico_serie_tiempo(df, numero: int):
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    df["aparece"] = df[cols].apply(lambda r: int(numero in r.values), axis=1)
    df["acumulado"] = df["aparece"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["FECHA"], y=df["acumulado"],
        mode="lines", name=f"Número {numero} acumulado",
        line=dict(color="#a78bfa", width=2)
    ))
    fig.update_layout(
        title=f"Apariciones acumuladas del número {numero} en el tiempo",
        xaxis_title="Fecha", yaxis_title="Apariciones acumuladas",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white"
    )
    return fig.to_json()

def grafico_heatmap_pares(df):
    """Mapa de calor de co-ocurrencias entre números (R1-R6)."""
    cols = ["R1", "R2", "R3", "R4", "R5", "R6"]
    numeros = range(1, NUMEROS_MAX + 1)
    mat = np.zeros((NUMEROS_MAX, NUMEROS_MAX), dtype=int)
    for _, row in df.iterrows():
        ns = [int(row[c]) for c in cols]
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                a, b = ns[i] - 1, ns[j] - 1
                mat[a][b] += 1
                mat[b][a] += 1
    fig = go.Figure(go.Heatmap(
        z=mat, colorscale="Plasma",
        hovertemplate="(%{x}, %{y}): %{z}<extra></extra>"
    ))
    fig.update_layout(
        title="Co-ocurrencias entre pares de números",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white", height=600,
    )
    return fig.to_json()

# ── HTML Template ─────────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Predictor Melate — JD</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #13131f; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; padding: 20px; }
  h1 { color: #a78bfa; text-align: center; margin-bottom: 8px; font-size: 2rem; }
  .subtitle { text-align: center; color: #94a3b8; margin-bottom: 30px; font-size: .9rem; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media(max-width:768px){ .grid { grid-template-columns: 1fr; } }
  .card { background: #1e1e2e; border-radius: 12px; padding: 20px; border: 1px solid #2e2e4e; }
  .card h2 { color: #c4b5fd; margin-bottom: 14px; font-size: 1.1rem; }
  input[type=text], input[type=number], select {
    background: #2a2a3e; border: 1px solid #4c4c75; color: #e2e8f0;
    border-radius: 6px; padding: 8px 12px; width: 100%; margin-bottom: 10px; font-size: .95rem;
  }
  button {
    background: #7c3aed; color: white; border: none; border-radius: 8px;
    padding: 10px 20px; cursor: pointer; font-size: .95rem; width: 100%;
    transition: background .2s;
  }
  button:hover { background: #6d28d9; }
  .numeros-selector { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
  .num-btn {
    width: 42px; height: 42px; border-radius: 50%; background: #2a2a3e;
    border: 2px solid #4c4c75; color: #e2e8f0; cursor: pointer;
    font-weight: bold; transition: all .15s;
  }
  .num-btn.selected { background: #7c3aed; border-color: #a78bfa; color: white; }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; }
  .tag { background: #7c3aed; border-radius: 20px; padding: 4px 12px; font-size: .85rem; }
  .tag.cold { background: #1d4ed8; }
  .tag.hot { background: #dc2626; }
  #resultado-pred { margin-top: 14px; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th { background: #2a2a3e; padding: 8px; text-align: left; color: #a78bfa; }
  td { padding: 7px 8px; border-bottom: 1px solid #2a2a3e; }
  tr:hover td { background: #252535; }
  .alert { background: #1e3a5f; border-left: 3px solid #3b82f6; padding: 10px; border-radius: 6px; margin-top: 10px; font-size: .85rem;}
  .full { grid-column: 1 / -1; }
  #loader { display:none; text-align:center; color: #a78bfa; margin-top: 10px; }
</style>
</head>
<body>
<h1>🎱 Predictor Melate</h1>
<p class="subtitle">Análisis estadístico del sorteo histórico — no garantiza resultados</p>

<div class="grid">
  <!-- Frecuencias Históricas -->
  <div class="card full">
    <h2>📊 Frecuencia histórica de números</h2>
    <div id="chart-freq"></div>
  </div>

  <!-- Serie de tiempo por número -->
  <div class="card">
    <h2>📈 Serie de tiempo por número</h2>
    <label>Número a analizar (1-56):</label>
    <input type="number" id="num-serie" min="1" max="56" value="7">
    <button onclick="cargarSerie()">Ver serie de tiempo</button>
    <div id="chart-serie"></div>
  </div>

  <!-- Hot & Cold -->
  <div class="card">
    <h2>🔥❄️ Números calientes y fríos</h2>
    <label>Ventana de sorteos recientes:</label>
    <input type="number" id="ventana-hc" value="30" min="10" max="500">
    <button onclick="cargarHotCold()">Analizar</button>
    <div id="hot-cold-result" style="margin-top:12px;"></div>
  </div>

  <!-- Predicción -->
  <div class="card">
    <h2>🔮 Predicción de próximos números</h2>
    <label>Ventana reciente para el modelo:</label>
    <input type="number" id="ventana-pred" value="50" min="10" max="500">
    <button onclick="predecir()">Generar predicción</button>
    <div id="resultado-pred"></div>
  </div>

  <!-- Verificador de combinación -->
  <div class="card full">
    <h2>🎯 Verifica tu combinación contra el historial</h2>
    <p style="color:#94a3b8; font-size:.85rem; margin-bottom:12px;">
      Selecciona exactamente 6 números y verifica cuántas coincidencias tuvieron en sorteos pasados.
    </p>
    <div class="numeros-selector" id="picker"></div>
    <p id="seleccion-label" style="color:#a78bfa; margin-bottom:10px;">Seleccionados: ninguno</p>
    <button onclick="verificar()">Verificar en historial</button>
    <div id="loader">Buscando coincidencias...</div>
    <div id="resultado-verif"></div>
  </div>

  <!-- Heatmap de co-ocurrencias -->
  <div class="card full">
    <h2>🧩 Co-ocurrencias entre pares de números</h2>
    <button onclick="cargarHeatmap()">Cargar mapa de calor (puede tardar)</button>
    <div id="chart-heatmap"></div>
  </div>
</div>

<script>
// ── Cargar gráfico de frecuencias al inicio ───────────────────────────────
fetch('/api/frecuencias')
  .then(r => r.json())
  .then(data => Plotly.newPlot('chart-freq', data.data, data.layout, {responsive:true}));

// ── Serie de tiempo ───────────────────────────────────────────────────────
function cargarSerie() {
  const n = document.getElementById('num-serie').value;
  fetch('/api/serie/' + n)
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-serie', data.data, data.layout, {responsive:true}));
}

// ── Hot & Cold ────────────────────────────────────────────────────────────
function cargarHotCold() {
  const v = document.getElementById('ventana-hc').value;
  fetch('/api/hotcold/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<p style="color:#f87171;font-size:.9rem;font-weight:bold;">🔥 Calientes</p>';
      html += '<div class="tags">' + data.calientes.map(n => `<span class="tag hot">${n}</span>`).join('') + '</div>';
      html += '<p style="color:#60a5fa;font-size:.9rem;font-weight:bold;margin-top:12px;">❄️ Fríos</p>';
      html += '<div class="tags">' + data.frios.map(n => `<span class="tag cold">${n}</span>`).join('') + '</div>';
      document.getElementById('hot-cold-result').innerHTML = html;
    });
}

// ── Predicción ────────────────────────────────────────────────────────────
function predecir() {
  const v = document.getElementById('ventana-pred').value;
  fetch('/api/predecir/' + v)
    .then(r => r.json())
    .then(data => {
      let html = '<table><thead><tr><th>Pos.</th><th>Número</th><th>Score</th><th>Frec. hist.</th><th>Frec. rec.</th><th>Brecha</th></tr></thead><tbody>';
      data.slice(0, 15).forEach((row, i) => {
        html += `<tr><td>${i+1}</td><td><b>${row.numero}</b></td><td>${row.score.toFixed(4)}</td><td>${row.frecuencia_h}</td><td>${row.frecuencia_r}</td><td>${row.brecha}</td></tr>`;
      });
      html += '</tbody></table>';
      html += '<div class="alert" style="margin-top:10px;">⚠️ El modelo combina frecuencia histórica, frecuencia reciente y brecha de aparición. No es garantía de acierto.</div>';
      document.getElementById('resultado-pred').innerHTML = html;
    });
}

// ── Picker de números ─────────────────────────────────────────────────────
const seleccionados = new Set();
const picker = document.getElementById('picker');
for (let i = 1; i <= 56; i++) {
  const btn = document.createElement('button');
  btn.className = 'num-btn';
  btn.textContent = i;
  btn.onclick = () => {
    if (seleccionados.has(i)) {
      seleccionados.delete(i);
      btn.classList.remove('selected');
    } else if (seleccionados.size < 6) {
      seleccionados.add(i);
      btn.classList.add('selected');
    }
    document.getElementById('seleccion-label').textContent =
      'Seleccionados: ' + (seleccionados.size ? [...seleccionados].sort((a,b)=>a-b).join(', ') : 'ninguno');
  };
  picker.appendChild(btn);
}

function verificar() {
  if (seleccionados.size !== 6) { alert('Selecciona exactamente 6 números.'); return; }
  document.getElementById('loader').style.display = 'block';
  document.getElementById('resultado-verif').innerHTML = '';
  fetch('/api/verificar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({numeros: [...seleccionados]})
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('loader').style.display = 'none';
    if (!data.length) {
      document.getElementById('resultado-verif').innerHTML =
        '<div class="alert">No se encontraron sorteos con 3 o más coincidencias.</div>';
      return;
    }
    let html = `<p style="margin:10px 0;color:#a78bfa;">${data.length} sorteos con ≥3 coincidencias:</p>`;
    html += '<table><thead><tr><th>Concurso</th><th>Fecha</th><th>Sorteo</th><th>Match</th><th>Aciertos</th></tr></thead><tbody>';
    data.forEach(r => {
      html += `<tr><td>${r.concurso}</td><td>${r.fecha}</td><td>${r.numeros_sorteo.join(', ')}</td>
               <td style="color:#fbbf24;">${r.numeros_match.join(', ')}</td>
               <td><b>${r.coincidencias}</b></td></tr>`;
    });
    html += '</tbody></table>';
    document.getElementById('resultado-verif').innerHTML = html;
  });
}

// ── Heatmap ───────────────────────────────────────────────────────────────
function cargarHeatmap() {
  document.getElementById('chart-heatmap').innerHTML = '<p style="color:#a78bfa;padding:20px;">Calculando... puede tomar unos segundos.</p>';
  fetch('/api/heatmap')
    .then(r => r.json())
    .then(data => Plotly.newPlot('chart-heatmap', data.data, data.layout, {responsive:true}));
}

// Cargar hot/cold automáticamente
cargarHotCold();
</script>
</body>
</html>
"""

# ── Rutas Flask ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/frecuencias")
def api_frecuencias():
    df = cargar_datos()
    return grafico_frecuencias(df)

@app.route("/api/serie/<int:numero>")
def api_serie(numero):
    if not 1 <= numero <= NUMEROS_MAX:
        return jsonify({"error": "Número fuera de rango"}), 400
    df = cargar_datos()
    return grafico_serie_tiempo(df, numero)

@app.route("/api/hotcold/<int:ventana>")
def api_hotcold(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    calientes, frios = hot_cold(df, ventana)
    return jsonify({
        "calientes": calientes["numero"].tolist(),
        "frios": frios["numero"].tolist(),
    })

@app.route("/api/predecir/<int:ventana>")
def api_predecir(ventana):
    ventana = max(10, min(ventana, 500))
    df = cargar_datos()
    score = predecir_numeros(df, ventana_reciente=ventana)
    return jsonify(score.head(20).to_dict(orient="records"))

@app.route("/api/verificar", methods=["POST"])
def api_verificar():
    data = request.get_json(force=True)
    numeros = data.get("numeros", [])
    if len(numeros) != 6:
        return jsonify({"error": "Se requieren exactamente 6 números"}), 400
    numeros = [int(n) for n in numeros if 1 <= int(n) <= NUMEROS_MAX]
    if len(numeros) != 6:
        return jsonify({"error": "Números fuera de rango"}), 400
    df = cargar_datos()
    resultados = verificar_combinacion(df, numeros)
    return jsonify(resultados)

@app.route("/api/heatmap")
def api_heatmap():
    df = cargar_datos()
    return grafico_heatmap_pares(df)

# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0
```

