"""
modelopredictJD.py
App Flask de análisis y predicción de Melate
Basada en Historic.csv (columnas: CONCURSO, R1-R7, FECHA)
"""

import os
import datetime
import functools
import csv
import fcntl
import io
import tempfile
import pandas as pd
import numpy as np
import requests
from flask import Flask, Response, render_template, request, jsonify, send_file, redirect, url_for, session, g
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
HISTORIC_PATH = os.path.join(BASE_DIR, "Historic.csv")
CSV_COLUMNS = ["NPRODUCTO", "CONCURSO", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "BOLSA", "FECHA"]
MAIN_COLUMNS = ["R1", "R2", "R3", "R4", "R5", "R6"]

app = Flask(__name__, static_folder='static', static_url_path='/static')

FLASK_ENV = os.environ.get("FLASK_ENV", os.environ.get("ENV", "production"))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0").lower() in ("1", "true", "yes")
app.config.update({
    "ENV": FLASK_ENV,
    "DEBUG": FLASK_DEBUG,
    "SESSION_COOKIE_SECURE": SESSION_COOKIE_SECURE,
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
def cargar_datos(conservar_producto=False):
    with open(CSV_PATH, "r", encoding="utf-8", newline="") as csv_file:
        fcntl.flock(csv_file, fcntl.LOCK_SH)
        df = pd.read_csv(csv_file, dtype=str)
    if not conservar_producto:
        df = df.drop(columns=["NPRODUCTO"], errors="ignore")
    df["FECHA"] = pd.to_datetime(df["FECHA"], format="mixed", dayfirst=True, errors="coerce")
    if "R7" not in df:
        df["R7"] = np.nan
    if "BOLSA" not in df:
        df["BOLSA"] = 0
    for c in ["R1","R2","R3","R4","R5","R6","R7"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["BOLSA"] = pd.to_numeric(df["BOLSA"], errors="coerce").fillna(0)
    df["CONCURSO"] = pd.to_numeric(df["CONCURSO"], errors="coerce")
    df = df.dropna(subset=MAIN_COLUMNS + ["FECHA", "CONCURSO"])
    validos = df[MAIN_COLUMNS].apply(lambda column: column.between(1, NUMEROS_MAX) & (column % 1 == 0)).all(axis=1)
    validos &= df[MAIN_COLUMNS].apply(lambda row: row.nunique() == 6, axis=1)
    validos &= df["R7"].isna() | (df["R7"].between(1, NUMEROS_MAX) & (df["R7"] % 1 == 0) & ~df[MAIN_COLUMNS].eq(df["R7"], axis=0).any(axis=1))
    df = df[validos]
    df = df.sort_values("FECHA").reset_index(drop=True)
    return df


def validar_numeros(numeros):
    if not isinstance(numeros, list) or len(numeros) not in (6, 7):
        raise ValueError("Se requieren 6 o 7 números.")
    nums = [validar_entero(n, "Los números") for n in numeros]
    if any(not 1 <= n <= NUMEROS_MAX for n in nums):
        raise ValueError(f"Los números deben estar entre 1 y {NUMEROS_MAX}.")
    if len(set(nums)) != len(nums):
        raise ValueError("Los números del sorteo no pueden repetirse.")
    return nums


def validar_entero(valor, nombre):
    if isinstance(valor, bool):
        raise ValueError(f"{nombre} deben ser enteros.")
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{nombre} deben ser enteros.") from None
    return numero


def validar_fecha(valor):
    if not isinstance(valor, str):
        raise ValueError("La fecha debe tener el formato DD/MM/YYYY o YYYY-MM-DD.")
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(valor.strip(), formato).strftime("%d/%m/%Y")
        except ValueError:
            continue
    raise ValueError("La fecha debe ser válida y tener el formato DD/MM/YYYY o YYYY-MM-DD.")


def guardar_sorteos(rows):
    """Asigna concursos y escribe el lote bajo el mismo bloqueo del archivo."""
    with open(CSV_PATH, "a+", encoding="utf-8", newline="") as csv_file:
        fcntl.flock(csv_file, fcntl.LOCK_EX)
        csv_file.seek(0)
        reader = csv.DictReader(csv_file)
        columns = reader.fieldnames or CSV_COLUMNS
        if not set(MAIN_COLUMNS + ["CONCURSO", "FECHA"]).issubset(columns):
            raise ValueError("El CSV de destino no tiene las columnas necesarias.")
        if "R7" not in columns and any(row["R7"] != "" for row in rows):
            raise ValueError("El CSV de destino no tiene una columna R7.")
        concursos = {int(row["CONCURSO"]) for row in reader if row.get("CONCURSO")}
        max_concurso = max(concursos, default=0)
        for row in rows:
            if row["CONCURSO"] is None:
                row["CONCURSO"] = max_concurso + 1
            if row["CONCURSO"] in concursos:
                raise ValueError(f"El concurso {row['CONCURSO']} ya existe.")
            concursos.add(row["CONCURSO"])
            max_concurso = max(max_concurso, row["CONCURSO"])
        csv_file.seek(0, os.SEEK_END)
        size = csv_file.tell()
        if size:
            csv_file.seek(size - 1)
            if csv_file.read(1) not in ("\n", "\r"):
                csv_file.write("\n")
        writer = csv.DictWriter(csv_file, fieldnames=columns, extrasaction="ignore")
        if not size:
            writer.writeheader()
        writer.writerows(rows)


def es_primo(n):
    """Devuelve True si n es primo."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return False
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    limite = int(np.sqrt(n))
    for divisor in range(3, limite + 1, 2):
        if n % divisor == 0:
            return False
    return True


def es_compuesto(n):
    """Devuelve True si n es un número compuesto y no es primo."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return False
    if n < 4:
        return False
    return not es_primo(n)


def filtrar_por_tipo(prediccion, tipo="mixto"):
    """Tipo admitido: mixto, primo, compuesto."""
    tipo = (tipo or "mixto").lower()
    if tipo == "primo":
        return prediccion[prediccion["numero"].apply(es_primo)].reset_index(drop=True)
    if tipo == "compuesto":
        return prediccion[prediccion["numero"].apply(es_compuesto)].reset_index(drop=True)
    return prediccion


def recomendar_sorteo(df, primos=3, compuestos=3, ventana=50,
                      pool_primos=None, pool_compuestos=None, excluir_ultimo=False):
    """Elige seis principales con cupos por tipo y explica el ranking histórico."""
    if df.empty:
        raise ValueError("No hay datos disponibles para el agente.")
    if primos < 0 or compuestos < 0 or primos + compuestos != 6:
        raise ValueError("El agente requiere que primos + compuestos sume 6.")
    pools = {}
    for tipo, valores, cantidad, clasificar in (
        ("primo", pool_primos, primos, es_primo),
        ("compuesto", pool_compuestos, compuestos, es_compuesto),
    ):
        if valores is None:
            valores = [n for n in range(1, NUMEROS_MAX + 1) if clasificar(n)]
        if not isinstance(valores, list):
            raise ValueError(f"El conjunto de {tipo}s debe ser una lista.")
        valores = [validar_entero(n, "Los candidatos") for n in valores]
        if any(not 1 <= n <= NUMEROS_MAX or not clasificar(n) for n in valores):
            raise ValueError(f"El conjunto de {tipo}s contiene números que no corresponden a ese tipo o al rango 1–56.")
        pools[tipo] = set(valores)

    excluidos = set()
    if excluir_ultimo:
        ultimo = df.iloc[-1]
        excluidos = {int(ultimo[c]) for c in MAIN_COLUMNS + ["R7"] if pd.notna(ultimo[c])}
    for tipo, cantidad in (("primo", primos), ("compuesto", compuestos)):
        pools[tipo] -= excluidos
        if len(pools[tipo]) < cantidad:
            raise ValueError(f"No hay suficientes {tipo}s disponibles para el cupo solicitado.")

    ranking = predecir_numeros(df, ventana_reciente=ventana).to_dict(orient="records")
    cupos = {"primo": primos, "compuesto": compuestos}
    elegidos = []
    explicaciones = []
    for _ in range(6):
        candidatos = []
        for row in ranking:
            numero = int(row["numero"])
            tipo = "primo" if es_primo(numero) else "compuesto"
            if cupos[tipo] and numero in pools[tipo] and numero not in elegidos:
                vecinos = sum(abs(numero - otro) <= 2 for otro in elegidos)
                candidatos.append((float(row["score"]) - 0.04 * vecinos, row, tipo))
        _, row, tipo = max(candidatos, key=lambda candidato: (candidato[0], candidato[1]["score"], -candidato[1]["numero"]))
        numero = int(row["numero"])
        elegidos.append(numero)
        cupos[tipo] -= 1
        explicaciones.append({
            "numero": numero,
            "tipo": tipo,
            "score": float(row["score"]),
            "frecuencia_h": int(row["frecuencia_h"]),
            "frecuencia_r": int(row["frecuencia_r"]),
            "brecha": int(row["brecha"]),
        })
    adicional = next(int(row["numero"]) for row in ranking if int(row["numero"]) not in set(elegidos) | excluidos)
    principales = sorted(elegidos)
    return {
        "main": principales,
        "additional": adicional,
        "suggestion": principales + [adicional],
        "primos": sorted(n for n in principales if es_primo(n)),
        "compuestos": sorted(n for n in principales if es_compuesto(n)),
        "explicaciones": sorted(explicaciones, key=lambda row: row["numero"]),
        "ventana": ventana,
        "sorteos_analizados": len(df),
        "criterio": "Frecuencia histórica y reciente, brecha entre apariciones y separación entre números. El score es una puntuación del modelo, no una probabilidad de ganar.",
    }

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
    """Modelo de predicción mejorado para un perfil tipo experto de casino:
    - prioriza números con buena frecuencia histórica,
    - mejora el peso de la frecuencia reciente,
    - favorece números con brecha larga,
    - penaliza clusters de números cercanos para evitar agrupar vecinos.
    """
    freq_hist = calcular_frecuencias(df)
    freq_rec = frecuencia_reciente(df, ventana=ventana_reciente)
    cols = ["R1","R2","R3","R4","R5","R6"]
    ultimas = {}
    for idx, row in df.iterrows():
        for c in cols:
            ultimas[int(row[c])] = idx
    total = len(df)
    brecha_s = pd.DataFrame(
        [(n, total - 1 - ultimas.get(n, -1)) for n in range(1, NUMEROS_MAX + 1)],
        columns=["numero","brecha"]
    )
    s = freq_hist.merge(freq_rec, on="numero", suffixes=("_h","_r")).merge(brecha_s, on="numero")

    for col in ["frecuencia_h","frecuencia_r","brecha"]:
        rng = s[col].max() - s[col].min()
        s[col + "_n"] = (s[col] - s[col].min()) / (rng + 1e-9)

    # Penalización por cercanía: si un número tiene vecinos muy activos, se reduce su score.
    neighbor_score = []
    for n in s["numero"]:
        vecinos = set(range(max(1, n-2), min(NUMEROS_MAX, n+2) + 1)) - {n}
        if not vecinos:
            neighbor_score.append(0.0)
            continue
        vec = s[s["numero"].isin(vecinos)]["frecuencia_r_n"]
        neighbor_score.append(float(vec.mean()) if not vec.empty else 0.0)

    s["neighbor_score"] = neighbor_score
    rng = s["neighbor_score"].max() - s["neighbor_score"].min()
    s["neighbor_penalty_n"] = (s["neighbor_score"] - s["neighbor_score"].min()) / (rng + 1e-9)

    # Pesos del experto: más peso a reciente, luego histórico, luego brecha, y un ajuste de evitar clusters.
    s["score"] = (
        0.32 * s["frecuencia_h_n"] +
        0.38 * s["frecuencia_r_n"] +
        0.17 * s["brecha_n"] +
        0.13 * (1.0 - s["neighbor_penalty_n"])
    )

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
    cols = ["R1","R2","R3","R4","R5","R6","R7"]
    set_usr = set(int(n) for n in numeros_usuario)
    resultados = []
    for _, row in df.iterrows():
        set_row = {int(row[c]) for c in cols if pd.notna(row[c])}
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
    try:
        primos = int(request.args.get("primos", 3))
        compuestos = int(request.args.get("compuestos", 2))
    except (TypeError, ValueError):
        return jsonify({"error": "primos y compuestos deben ser enteros."}), 400

    if not (0 <= primos <= 5 and 0 <= compuestos <= 5) or primos + compuestos != 5:
        return jsonify({"error": "primos + compuestos debe ser 5."}), 400

    df = cargar_datos()
    if df.empty:
        return jsonify({"error": "No hay datos disponibles"}), 400
    score = predecir_numeros(df, ventana_reciente=ventana)
    numeros_primos = score[score["numero"].apply(es_primo)].head(primos)
    numeros_compuestos = score[score["numero"].apply(es_compuesto)].head(compuestos)
    combinacion = pd.concat([numeros_primos, numeros_compuestos], ignore_index=True).sort_values("score", ascending=False)
    return jsonify(combinacion.head(5).to_dict(orient="records"))

@app.route("/api/agente", methods=["POST"])
def api_agente():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Se requiere un objeto JSON."}), 400
    try:
        primos = validar_entero(data.get("primos", 3), "Los cupos")
        compuestos = validar_entero(data.get("compuestos", 3), "Los cupos")
        ventana = max(10, min(validar_entero(data.get("ventana", 50), "Las ventanas"), 500))
        excluir_ultimo = data.get("excluir_ultimo", False)
        if not isinstance(excluir_ultimo, bool):
            raise ValueError("excluir_ultimo debe ser verdadero o falso.")
        recomendacion = recomendar_sorteo(
            cargar_datos(), primos, compuestos, ventana,
            data.get("pool_primos"), data.get("pool_compuestos"), excluir_ultimo,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(recomendacion)


@app.route("/api/verificar", methods=["POST"])
def api_verificar():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Se requiere un objeto JSON."}), 400
    numeros = data.get("numeros", [])
    # opcional: min_matches en el payload para exigir más coincidencias (ej: 5)
    try:
        min_matches = validar_entero(data.get("min_matches", 3), "Las coincidencias")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not 1 <= min_matches <= 7:
        return jsonify({"error": "Las coincidencias deben estar entre 1 y 7."}), 400
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
    return jsonify(df.astype(object).where(pd.notna(df), None).to_dict(orient="records"))


def seleccionar(pool, cantidad, previos=()):
    if len(pool) < cantidad:
        raise ValueError("No hay suficientes números de este tipo para generar la combinación.")
    seleccion = set()
    for _ in range(cantidad):
        disponibles = set(pool) - seleccion
        separados = [n for n in disponibles if all(abs(n - otro) > 2 for otro in set(previos) | seleccion)]
        seleccion.add(int(np.random.choice(separados or sorted(disponibles))))
    return seleccion


@app.route("/api/random")
def api_random():
    df = cargar_datos()
    if df.empty:
        return jsonify({"error": "No hay datos disponibles"}), 400

    # El modo aleatorio usa 6 principales; la predicción solicita 5 explícitamente.
    total = 5 if "primos" in request.args or "compuestos" in request.args else 6
    try:
        primos = int(request.args.get("primos", 3))
        compuestos = int(request.args.get("compuestos", total - 3))
    except (TypeError, ValueError):
        return jsonify({"error": "primos y compuestos deben ser enteros."}), 400

    if not (0 <= primos <= total and 0 <= compuestos <= total) or primos + compuestos != total:
        return jsonify({"error": f"primos + compuestos debe ser {total}."}), 400

    # Obtener los últimos números ganadores (línea ganadora más reciente)
    last_row = df.iloc[-1]
    recent_numbers = {int(last_row[c]) for c in MAIN_COLUMNS + ["R7"] if pd.notna(last_row[c])}

    # Obtener top 10 pares del mapa de calor
    cols = ["R1","R2","R3","R4","R5","R6"]
    mat = np.zeros((NUMEROS_MAX, NUMEROS_MAX), dtype=int)
    for _, row in df.iterrows():
        ns = [int(row[c]) for c in cols]
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                a, b = ns[i]-1, ns[j]-1
                mat[a][b] += 1
                mat[b][a] += 1

    pares = []
    for i in range(NUMEROS_MAX):
        for j in range(i + 1, NUMEROS_MAX):
            if mat[i][j] > 0:
                pares.append((i + 1, j + 1, int(mat[i][j])))
    top_pares = sorted(pares, key=lambda x: -x[2])[:10]

    pools = {
        "primo": [n for n in range(1, NUMEROS_MAX + 1) if n not in recent_numbers and es_primo(n)],
        "compuesto": [n for n in range(1, NUMEROS_MAX + 1) if n not in recent_numbers and es_compuesto(n)],
    }

    suggestions = []
    bases = sorted({n for a, b, _ in top_pares for n in (a, b)
                    if n not in recent_numbers and ((primos and es_primo(n)) or (compuestos and es_compuesto(n)))})
    for _ in range(3):
        main = set()
        if bases:
            main.add(int(np.random.choice(bases)))
        faltan_primos = primos - sum(es_primo(n) for n in main)
        main.update(seleccionar([n for n in pools["primo"] if n not in main], faltan_primos, main))
        faltan_compuestos = compuestos - sum(es_compuesto(n) for n in main)
        main.update(seleccionar([n for n in pools["compuesto"] if n not in main], faltan_compuestos, main))

        main = sorted(main)
        available_for_additional = [n for n in range(1, NUMEROS_MAX + 1) if n not in recent_numbers and n not in main]
        additional = int(np.random.choice(available_for_additional)) if available_for_additional else 1
        suggestion = main + [additional]
        suggestions.append({
            "main": main,
            "additional": additional,
            "suggestion": suggestion,
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
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Se requiere un objeto JSON."}), 400
    numeros = data.get("numeros")
    try:
        nums = validar_numeros(numeros)
        concurso = validar_entero(data["concurso"], "Los concursos") if data.get("concurso") not in (None, "") else None
        fecha = validar_fecha(data.get("fecha") or pd.Timestamp.now().strftime("%d/%m/%Y"))
        bolsa = validar_entero(data.get("bolsa") or 0, "Los importes de bolsa")
        nproducto = validar_entero(data.get("nproducto", 40), "Los productos")
        if (concurso is not None and concurso <= 0) or bolsa < 0 or nproducto <= 0:
            raise ValueError("Concurso y producto deben ser positivos; bolsa no puede ser negativa.")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    row = {
        "NPRODUCTO": int(nproducto),
        "CONCURSO": concurso,
        "R1": int(nums[0]), "R2": int(nums[1]), "R3": int(nums[2]),
        "R4": int(nums[3]), "R5": int(nums[4]), "R6": int(nums[5]),
        "R7": int(nums[6]) if len(nums) > 6 else "",
        "BOLSA": int(bolsa) if bolsa not in (None, "") else 0,
        "FECHA": fecha
    }

    try:
        guardar_sorteos([row])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except OSError as e:
        return jsonify({"error": f"No se pudo escribir en CSV: {e}"}), 500

    return jsonify({"ok": True, "added": row})


@app.route("/api/add_rows", methods=["POST"])
def api_add_rows():
    """Añade hasta 100 sorteos desde líneas separadas por saltos."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Se requiere un objeto JSON."}), 400
    lines = data.get("lines")
    if not isinstance(lines, list) or not lines:
        return jsonify({"error": "Introduce al menos una línea de sorteo."}), 400
    if len(lines) > 100:
        return jsonify({"error": "No se pueden añadir más de 100 sorteos."}), 400

    rows = []
    for line_number, line in enumerate(lines, start=1):
        if not isinstance(line, str) or not line.strip():
            return jsonify({"error": f"La línea {line_number} está vacía."}), 400

        parts = line.split("—", 1)
        if len(parts) != 2:
            return jsonify({"error": f"La línea {line_number} debe contener números y fecha separados por '—'."}), 400

        try:
            nums = validar_numeros(parts[0].split(","))
            fecha = validar_fecha(parts[1].strip())
        except ValueError as exc:
            return jsonify({"error": f"Línea {line_number}: {exc}"}), 400

        rows.append({
            "NPRODUCTO": 40,
            "CONCURSO": None,
            "R1": nums[0], "R2": nums[1], "R3": nums[2],
            "R4": nums[3], "R5": nums[4], "R6": nums[5],
            "R7": nums[6] if len(nums) > 6 else "",
            "BOLSA": 0,
            "FECHA": fecha
        })

    try:
        guardar_sorteos(rows)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except OSError as e:
        return jsonify({"error": f"No se pudo escribir en CSV: {e}"}), 500

    return jsonify({"ok": True, "added": len(rows)})


@app.route("/api/historic_csv")
def api_historic_csv():
    """Exporta los datos actuales para guardarlos en localStorage y espejarlos en Historic.csv."""
    if not os.path.exists(CSV_PATH):
        return jsonify({"error": "CSV de datos no encontrado."}), 404

    df = cargar_datos(conservar_producto=True)
    for column in MAIN_COLUMNS + ["R7", "CONCURSO"]:
        df[column] = df[column].astype("Int64")
    df["FECHA"] = df["FECHA"].dt.strftime("%d/%m/%Y")
    content = df.to_csv(index=False)
    return Response(content, mimetype="text/csv", headers={"Cache-Control": "no-store"})


@app.route("/api/sync_localstorage_csv", methods=["POST"])
def api_sync_localstorage_csv():
    """Escribe el CSV que viene de localStorage sobre Historic.csv como espejo."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Se requiere un objeto JSON."}), 400
    csv_text = data.get("csv")
    if not isinstance(csv_text, str) or not csv_text.strip():
        return jsonify({"error": "Se requiere el contenido CSV en la clave 'csv'."}), 400

    try:
        reader = csv.DictReader(io.StringIO(csv_text))
        columns = reader.fieldnames or []
        if len(columns) != len(set(columns)) or not set(MAIN_COLUMNS + ["CONCURSO", "FECHA"]).issubset(columns):
            raise ValueError("El CSV no tiene las columnas necesarias.")
        rows = list(reader)
        if not rows:
            raise ValueError("El CSV debe contener al menos un sorteo.")
        for index, row in enumerate(rows, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Fila {index}: el número de columnas no coincide.")
            numbers = [row[col] for col in MAIN_COLUMNS]
            if row.get("R7", "").strip():
                numbers.append(row["R7"])
            validar_numeros(numbers)
            validar_fecha(row["FECHA"])
            concurso = validar_entero(row["CONCURSO"], "Los concursos")
            if concurso <= 0:
                raise ValueError(f"Fila {index}: concurso inválido.")
    except (ValueError, csv.Error) as exc:
        return jsonify({"error": str(exc)}), 400

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=os.path.dirname(HISTORIC_PATH), delete=False) as csv_file:
            temp_path = csv_file.name
            csv_file.write(csv_text)
        os.replace(temp_path, HISTORIC_PATH)
    except OSError as exc:
        return jsonify({"error": f"No se pudo escribir Historic.csv: {exc}"}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

    return jsonify({"ok": True, "rows": len(rows), "path": "Historic.csv"})


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
        if pd.isna(v):
            first[k] = None
        elif isinstance(v, (np.integer,)):
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
