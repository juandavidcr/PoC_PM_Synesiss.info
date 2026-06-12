"""
modelopredictJD.py
App Flask de análisis y predicción de Melate
Basada en Historic.csv (columnas: CONCURSO, R1-R7, FECHA)
"""

import os
import datetime
import functools
import pandas as pd
import numpy as np
import requests
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, g
from collections import Counter
import plotly.graph_objects as go
import plotly.express as px
import plotly
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import jwt
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
local_csv = os.path.join(BASE_DIR, "Melate.csv")
CSV_PATH = os.environ.get("CSV_PATH", local_csv)
if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(
        f"CSV no encontrado en {CSV_PATH}. Copia Melate.csv en el repositorio o ajusta CSV_PATH."
    )
NUMEROS_MAX = 56

app = Flask(__name__, static_folder='static', static_url_path='/static')

FLASK_ENV = os.environ.get("FLASK_ENV", os.environ.get("ENV", "production"))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
app.config.update({
    "ENV": FLASK_ENV,
    "DEBUG": FLASK_DEBUG,
    "SESSION_COOKIE_SECURE": FLASK_ENV == "production",
    "SESSION_COOKIE_HTTPONLY": True,
})

app.secret_key = os.environ.get("SECRET_KEY")
LOGIN_USER = os.environ.get("LOGIN_USER", "admin")
LOGIN_PASSWORD = os.environ.get("LOGIN_PASSWORD")
JWT_SECRET = os.environ.get("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXP_SECONDS = int(os.environ.get("JWT_EXP_SECONDS", "604800"))
GOOGLE_CALLBACK_URL = os.environ.get("GOOGLE_CALLBACK_URL")

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def authenticate_user(username, password):
    return username == LOGIN_USER and password == LOGIN_PASSWORD


def generate_token(user_id):
    payload = {
        "id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXP_SECONDS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def jwt_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
        if not token:
            return jsonify({"error": "No autorizado - Token no proporcionado"}), 401
        try:
            payload = verify_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401
        g.user = payload.get("id")
        return view(*args, **kwargs)
    return wrapped_view


# ── Datos ─────────────────────────────────────────────────────────────────────
def cargar_datos():
    df = pd.read_csv(CSV_PATH, dtype=str)
    df = df.drop(columns=["NPRODUCTO"], errors="ignore")
    df["FECHA"] = pd.to_datetime(df["FECHA"], dayfirst=True)
    for c in ["R1","R2","R3","R4","R5","R6","R7"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["BOLSA"] = pd.to_numeric(df["BOLSA"], errors="coerce").fillna(0)
    df = df.dropna(subset=["R1","R2","R3","R4","R5","R6","R7"])
    df = df.sort_values("FECHA").reset_index(drop=True)
    return df

# ── Análisis ──────────────────────────────────────────────────────────────────
def calcular_frecuencias(df, incluir_adicional=False):
    cols = ["R1","R2","R3","R4","R5","R6"] + (["R7"] if incluir_adicional else [])
    conteo = Counter(df[cols].values.flatten().astype(int))
    freq = pd.DataFrame(
        [(n, conteo.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)],
        columns=["numero","frecuencia"]
    ).sort_values("frecuencia", ascending=False)
    return freq

def frecuencia_reciente(df, ventana=100):
    return calcular_frecuencias(df.tail(ventana))

def hot_cold(df, ventana=30):
    reciente  = calcular_frecuencias(df.tail(ventana))
    historico = calcular_frecuencias(df)
    m = reciente.merge(historico, on="numero", suffixes=("_rec","_hist"))
    m["z_score"] = (m["frecuencia_rec"] - m["frecuencia_rec"].mean()) / (m["frecuencia_rec"].std() + 1e-9)
    return m.nlargest(10,"z_score")[["numero","frecuencia_rec","z_score"]], \
           m.nsmallest(10,"z_score")[["numero","frecuencia_rec","z_score"]]

def predecir_numeros(df, ventana_reciente=50):
    freq_hist = calcular_frecuencias(df)
    freq_rec  = frecuencia_reciente(df, ventana=ventana_reciente)
    cols = ["R1","R2","R3","R4","R5","R6"]
    ultimas = {}
    for idx, row in df.iterrows():
        for c in cols:
            ultimas[int(row[c])] = idx
    total = len(df)
    brecha_s = pd.DataFrame(
        [(n, total - ultimas.get(n, 0)) for n in range(1, NUMEROS_MAX + 1)],
        columns=["numero","brecha"]
    )
    s = freq_hist.merge(freq_rec, on="numero", suffixes=("_h","_r")).merge(brecha_s, on="numero")
    for col in ["frecuencia_h","frecuencia_r","brecha"]:
        rng = s[col].max() - s[col].min()
        s[col+"_n"] = (s[col] - s[col].min()) / (rng + 1e-9)
    s["score"] = 0.40*s["frecuencia_h_n"] + 0.40*s["frecuencia_r_n"] + 0.20*s["brecha_n"]
    return s.sort_values("score", ascending=False).reset_index(drop=True)[
        ["numero","score","frecuencia_h","frecuencia_r","brecha"]
    ]

def verificar_combinacion(df, numeros_usuario, min_matches=3, exact=False):
    """
    Busca en el historial las filas que coinciden con los números del usuario.
    - `numeros_usuario`: iterable de números seleccionados por el usuario
    - `min_matches`: mínimo de coincidencias requeridas (por defecto 3)
    - `exact`: si True, busca coincidencias exactamente igual a `min_matches`;
       si False (por defecto), busca filas con >= `min_matches` coincidencias.
    Devuelve hasta 20 resultados ordenados por coincidencias descendentes.
    """
    cols = ["R1","R2","R3","R4","R5","R6"]
    set_usr = set(int(n) for n in numeros_usuario)
    resultados = []
    for _, row in df.iterrows():
        set_row = {int(row[c]) for c in cols}
        match = set_usr & set_row
        count = len(match)
        if (exact and count == int(min_matches)) or (not exact and count >= int(min_matches)):
            resultados.append({
                "concurso": row["CONCURSO"],
                "fecha": str(row["FECHA"].date()),
                "numeros_sorteo": sorted(set_row),
                "coincidencias": count,
                "numeros_match": sorted(match),
            })
    return sorted(resultados, key=lambda x: -x["coincidencias"])[:20]

# ── Gráficos ──────────────────────────────────────────────────────────────────
def grafico_frecuencias(df):
    freq = calcular_frecuencias(df)
    fig = px.bar(freq, x="numero", y="frecuencia",
                 title="Frecuencia histórica de números (R1-R6)",
                 labels={"numero":"Número","frecuencia":"Veces sorteado"},
                 color="frecuencia", color_continuous_scale="Viridis")
    fig.update_layout(xaxis=dict(dtick=1), plot_bgcolor="#1e1e2e",
                      paper_bgcolor="#1e1e2e", font_color="white")
    return fig.to_json()

def grafico_serie_tiempo(df, numero):
    cols = ["R1","R2","R3","R4","R5","R6"]
    df = df.copy()
    df["aparece"]   = df[cols].apply(lambda r: int(numero in r.values), axis=1)
    df["acumulado"] = df["aparece"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["FECHA"], y=df["acumulado"], mode="lines",
                             name=f"Número {numero}", line=dict(color="#a78bfa", width=2)))
    fig.update_layout(title=f"Apariciones acumuladas del número {numero}",
                      xaxis_title="Fecha", yaxis_title="Apariciones acumuladas",
                      plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e", font_color="white")
    return fig.to_json()

def grafico_heatmap_pares(df):
    cols = ["R1","R2","R3","R4","R5","R6"]
    etiquetas = list(range(1, NUMEROS_MAX + 1))
    mat = np.zeros((NUMEROS_MAX, NUMEROS_MAX), dtype=int)
    for _, row in df.iterrows():
        ns = [int(row[c]) for c in cols]
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                a, b = ns[i]-1, ns[j]-1
                mat[a][b] += 1
                mat[b][a] += 1
    # Top 10 pares
    pares = []
    for i in range(NUMEROS_MAX):
        for j in range(i+1, NUMEROS_MAX):
            if mat[i][j] > 0:
                pares.append((i+1, j+1, int(mat[i][j])))
    top_pares = sorted(pares, key=lambda x: -x[2])[:10]
    fig = go.Figure(go.Heatmap(
        z=mat,
        x=etiquetas,
        y=etiquetas,
        colorscale="Plasma",
        colorbar=dict(title="Veces juntos"),
        hovertemplate="Número %{x} + Número %{y}: <b>%{z} veces juntos</b><extra></extra>"
    ))
    fig.update_layout(
        title="Co-ocurrencias: cuántas veces dos números salieron en el mismo sorteo",
        xaxis=dict(title="Número", dtick=5, tickmode="linear"),
        yaxis=dict(title="Número", dtick=5, tickmode="linear"),
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white", height=650
    )
    return json.loads(fig.to_json()) | {"top_pares": top_pares}

def grafico_bolsa_vs_numeros(df):
    """Mapa de calor: número (eje Y) vs bolsa acumulada en rangos (eje X).
    Cada celda muestra cuántas veces ese número salió en sorteos con esa bolsa."""
    cols = ["R1","R2","R3","R4","R5","R6"]
    df = df[df["BOLSA"] > 0].copy()

    def fmt_bolsa(val):
        if val >= 1e9:
            return f"${val/1e9:.1f}B"
        return f"${val/1e6:.0f}M"

    # Usar cuantiles para que cada rango tenga ~igual número de sorteos
    df["bolsa_bin"], bins = pd.qcut(df["BOLSA"], q=10, retbins=True, duplicates="drop")
    etiquetas_bin = [f"{fmt_bolsa(bins[i])}–{fmt_bolsa(bins[i+1])}" for i in range(len(bins)-1)]
    numeros = list(range(1, NUMEROS_MAX + 1))
    categorias = df["bolsa_bin"].cat.categories
    mat = np.zeros((NUMEROS_MAX, len(categorias)), dtype=int)
    for bi, intervalo in enumerate(categorias):
        subset = df[df["bolsa_bin"] == intervalo]
        conteo = Counter(subset[cols].values.flatten().astype(int))
        for n in numeros:
            mat[n - 1][bi] = conteo.get(n, 0)
    fig = go.Figure(go.Heatmap(
        z=mat,
        x=etiquetas_bin[:len(categorias)],
        y=numeros,
        colorscale="Turbo",
        colorbar=dict(title="Veces sorteado"),
        hovertemplate="Número %{y} | Bolsa %{x}: <b>%{z} veces</b><extra></extra>"
    ))
    fig.update_layout(
        title="Números más frecuentes según rango de Bolsa Acumulada",
        xaxis=dict(title="Bolsa acumulada (rango)", tickangle=-45),
        yaxis=dict(title="Número", dtick=5, tickmode="linear"),
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white", height=700
    )
    return fig.to_json()


# ── Rutas ─────────────────────────────────────────────────────────────────────
@app.route("/plotly.js")
def serve_plotly():
    plotly_js = os.path.join(os.path.dirname(plotly.__file__), "package_data", "plotly.min.js")
    return send_file(plotly_js, mimetype="application/javascript")

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if authenticate_user(username, password):
            session["user"] = username
            return redirect(url_for("index"))
        error = "Usuario o contraseña incorrectos"
    elif request.method == "GET" and request.args.get("source") == "google":
        error = "Error al intentar iniciar sesión con Google."
    return render_template("login.html", error=error)

@app.route("/auth/google")
def auth_google():
    # Enviar al usuario a la página de login de Google
    if GOOGLE_CALLBACK_URL:
        redirect_uri = GOOGLE_CALLBACK_URL
    else:
        redirect_uri = url_for('auth_google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/auth/google/callback")
def auth_google_callback():
    redirect_uri = GOOGLE_CALLBACK_URL or url_for('auth_google_callback', _external=True)

    if request.args.get("error"):
        app.logger.warning("Google callback returned error: %s", request.args.get("error"))
        return redirect(url_for("login", source="google"))

    try:
        token = google.authorize_access_token(redirect_uri=redirect_uri)
    except requests.exceptions.Timeout as e:
        app.logger.error("Google token exchange timeout: %s", e, exc_info=True)
        return redirect(url_for("login", source="google"))
    except requests.exceptions.RequestException as e:
        app.logger.error("Google token exchange network error: %s", e, exc_info=True)
        return redirect(url_for("login", source="google"))
    except Exception as e:
        app.logger.error("authorize_access_token failed: %s", e, exc_info=True)
        return redirect(url_for("login", source="google"))

    user_info = None

    # Registrar token para debugging
    try:
        app.logger.debug("Google token received: %s", token)
    except Exception:
        pass

    # Extraer datos de usuario: primero intentar usar userinfo incluido en token
    if isinstance(token, dict) and token.get("userinfo"):
        user_info = token.get("userinfo")
        app.logger.debug("Using userinfo from token: %s", user_info)
    else:
        # Intentar parsear id_token
        try:
            user_info = google.parse_id_token(token)
            app.logger.debug("Parsed id_token: %s", user_info)
        except Exception as e:
            app.logger.debug("parse_id_token failed: %s", e)
            try:
                # Usar endpoint userinfo desde metadata
                resp = google.get(google.server_metadata.get("userinfo_endpoint") or "https://openidconnect.googleapis.com/v1/userinfo")
                app.logger.debug("userinfo status: %s, body: %s", getattr(resp, 'status_code', None), getattr(resp, 'text', None))
                user_info = resp.json()
                app.logger.debug("userinfo json: %s", user_info)
            except Exception as e2:
                app.logger.debug("userinfo request failed: %s", e2)
                user_info = None

    if not user_info:
        return redirect(url_for("login", source="google"))
    
    # OPCIONAL: Aquí podrías verificar si el email es uno de los tuyos
    # allowed_emails = ["tu.correo@gmail.com", "otro.admin@gmail.com"]
    # if user_info.get("email") not in allowed_emails:
    #     return "No tienes permiso para acceder", 403

    session["user"] = user_info.get("email")
    return redirect(url_for("index"))

@app.route("/auth/token", methods=["POST"])
def auth_token():
    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not authenticate_user(username, password):
        return jsonify({"error": "Usuario o contraseña incorrectos"}), 401
    token = generate_token(username)
    return jsonify({"token": token, "expires_in": JWT_EXP_SECONDS})

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/tracker")
@login_required
def tracker():
    return render_template("wc2026_tracker.html")

@app.route("/api/send_update", methods=["POST"])
def api_send_update():
    if not session.get("user"):
        return jsonify({"error": "No autorizado"}), 401
    data = request.get_json(silent=True) or {}
    app.logger.debug("API send_update received: %s", data)
    return jsonify({"status": "ok"})

@app.route("/api/frecuencias")
def api_frecuencias():
    return grafico_frecuencias(cargar_datos())

@app.route("/api/serie/<int:numero>")
def api_serie(numero):
    if not 1 <= numero <= NUMEROS_MAX:
        return jsonify({"error": "Número fuera de rango"}), 400
    return grafico_serie_tiempo(cargar_datos(), numero)

@app.route("/api/hotcold/<int:ventana>")
def api_hotcold(ventana):
    ventana = max(10, min(ventana, 500))
    calientes, frios = hot_cold(cargar_datos(), ventana)
    return jsonify({"calientes": calientes["numero"].tolist(),
                    "frios": frios["numero"].tolist()})

@app.route("/api/predecir/<int:ventana>")
def api_predecir(ventana):
    ventana = max(10, min(ventana, 500))
    score = predecir_numeros(cargar_datos(), ventana_reciente=ventana)
    return jsonify(score.head(20).to_dict(orient="records"))

@app.route("/api/verificar", methods=["POST"])
def api_verificar():
    data = request.get_json(force=True)
    numeros = data.get("numeros", [])
    # opcional: min_matches en el payload para exigir más coincidencias (ej: 5)
    min_matches = int(data.get("min_matches", 3))
    if not isinstance(numeros, list) or len(numeros) == 0:
        return jsonify({"error": "Se requieren números en la clave 'numeros'"}), 400
    try:
        numeros = [int(n) for n in numeros]
    except Exception:
        return jsonify({"error": "Los elementos de 'numeros' deben ser enteros."}), 400
    # validar rango
    if any(not (1 <= n <= NUMEROS_MAX) for n in numeros):
        return jsonify({"error": f"Números fuera de rango 1-{NUMEROS_MAX}"}), 400
    return jsonify(verificar_combinacion(cargar_datos(), numeros, min_matches=min_matches))

@app.route("/api/preview")
def api_preview():
    try:
        limit = int(request.args.get("limit", 500))
    except (TypeError, ValueError):
        limit = 500
    limit = max(1, min(limit, 500))
    df = cargar_datos().sort_values("FECHA", ascending=False).head(limit).copy()
    df["FECHA"] = df["FECHA"].dt.strftime("%Y-%m-%d")
    return jsonify(df.to_dict(orient="records"))

@app.route("/api/random")
def api_random():
    df = cargar_datos()
    if df.empty:
        return jsonify({"error": "No hay datos disponibles"}), 400
    
     # Obtener los últimos números ganadores (línea ganadora más reciente)
    last_row = df.iloc[-1]
    recent_numbers = {int(last_row[c]) for c in ["R1","R2","R3","R4","R5","R6","R7"]}
    
    # Obtener top 10 pares del mapa de calor
    cols = ["R1","R2","R3","R4","R5","R6"]
    etiquetas = list(range(1, NUMEROS_MAX + 1))
    mat = np.zeros((NUMEROS_MAX, NUMEROS_MAX), dtype=int)
    for _, row in df.iterrows():
        ns = [int(row[c]) for c in cols]
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                a, b = ns[i]-1, ns[j]-1
                mat[a][b] += 1
                mat[b][a] += 1
    
    # Top 10 pares
    pares = []
    for i in range(NUMEROS_MAX):
        for j in range(i+1, NUMEROS_MAX):
            if mat[i][j] > 0:
                pares.append((i+1, j+1, int(mat[i][j])))
    top_pares = sorted(pares, key=lambda x: -x[2])[:10]
    
    # Números disponibles (excluyendo recientes)
    available = set(range(1, NUMEROS_MAX + 1)) - recent_numbers
    
    suggestions = []
    
    for _ in range(3):
        # Seleccionar al menos 1 número del top 10 pares
        pair_idx = np.random.randint(0, len(top_pares))
        num1, num2, _ = top_pares[pair_idx]
        
        # Elegir uno de los dos números del par
        pair_nums = [num1, num2]
        selected_base = int(np.random.choice(pair_nums))
        
        # Empezar con el número seleccionado
        main = [selected_base]
        available_for_suggestion = available - {selected_base}
        
        # Agregar 5 números más, evitando números muy pegados
        while len(main) < 6:
            # Números muy pegados son ±2 del rango actual
            pegados = set()
            for n in main:
                pegados.update(range(max(1, n-2), min(NUMEROS_MAX+1, n+3)))
            
            candidates = available_for_suggestion - pegados
            if not candidates:
                # Si no hay candidatos, usar los menos pegados
                candidates = available_for_suggestion
            
            if candidates:
                next_num = int(np.random.choice(list(candidates)))
                main.append(next_num)
                available_for_suggestion.discard(next_num)
            else:
                break
        
        # Si no tenemos 6, llenar con números aleatorios disponibles
        while len(main) < 6:
            remaining = available - set(main)
            if remaining:
                next_num = int(np.random.choice(list(remaining)))
                main.append(next_num)
            else:
                break
        
        # Seleccionar adicional
        remaining_for_additional = available - set(main)
        additional = int(np.random.choice(list(remaining_for_additional))) if remaining_for_additional else 1
        
        # Asegurar que tenemos exactamente 6 principales
        main = sorted(main[:6])
        suggestion = main + [int(additional)]
        
        suggestions.append({
            "main": main,
            "additional": int(additional),
            "suggestion": suggestion
        })
    
    return jsonify({"suggestions": suggestions})

@app.route("/api/heatmap")
def api_heatmap():
    return jsonify(grafico_heatmap_pares(cargar_datos()))


@app.route("/api/add_row", methods=["POST"])
def api_add_row():
    """Añade una fila al CSV. Espera JSON con claves:
    - numeros: lista de 6 o 7 números (R1..R6[,R7])
    - concurso (opcional)
    - fecha (opcional, formato DD/MM/YYYY)
    - bolsa (opcional)
    - nproducto (opcional)
    Devuelve el objeto añadido.
    """
    data = request.get_json(force=True) or {}
    numeros = data.get("numeros")
    if not isinstance(numeros, list) or not (6 <= len(numeros) <= 7):
        return jsonify({"error": "Se requieren 6 o 7 números en la clave 'numeros'."}), 400
    try:
        nums = [int(x) for x in numeros]
    except Exception:
        return jsonify({"error": "Los elementos de 'numeros' deben ser enteros."}), 400

    df = cargar_datos() if os.path.exists(CSV_PATH) else pd.DataFrame()
    try:
        max_conc = int(df["CONCURSO"].max()) if not df.empty else 0
    except Exception:
        max_conc = 0
    concurso = int(data.get("concurso", max_conc + 1))
    fecha = data.get("fecha") or pd.Timestamp.now().strftime("%d/%m/%Y")
    bolsa = data.get("bolsa", 0)
    nproducto = data.get("nproducto", 40)

    row = {
        "NPRODUCTO": int(nproducto),
        "CONCURSO": int(concurso),
        "R1": int(nums[0]), "R2": int(nums[1]), "R3": int(nums[2]),
        "R4": int(nums[3]), "R5": int(nums[4]), "R6": int(nums[5]),
        "R7": int(nums[6]) if len(nums) > 6 else "",
        "BOLSA": int(bolsa) if bolsa not in (None, "") else 0,
        "FECHA": fecha
    }

    # Añadir al CSV respetando el header existente (si existe)
    header = not os.path.exists(CSV_PATH)
    try:
        pd.DataFrame([row]).to_csv(CSV_PATH, mode="a", header=header, index=False)
    except Exception as e:
        return jsonify({"error": f"No se pudo escribir en CSV: {e}"}), 500

    return jsonify({"ok": True, "added": row})


@app.route("/api/first_row")
def api_first_row():
    """Devuelve la primera fila del CSV (tras el procesamiento de cargar_datos)."""
    df = cargar_datos()
    if df.empty:
        return jsonify({})
    first = df.iloc[0].to_dict()
    # Asegurar serialización de FECHA
    try:
        first["FECHA"] = first["FECHA"].strftime("%d/%m/%Y")
    except Exception:
        first["FECHA"] = str(first.get("FECHA", ""))
    # Convertir numpy types a nativos
    for k, v in first.items():
        if isinstance(v, (np.integer,)):
            first[k] = int(v)
        elif isinstance(v, (np.floating,)):
            first[k] = float(v)
    return jsonify(first)

@app.route("/api/bolsa_numeros")
def api_bolsa_numeros():
    return grafico_bolsa_vs_numeros(cargar_datos())

# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5050"))
    app.run(host="0.0.0.0", port=port, threaded=True, debug=app.debug)
