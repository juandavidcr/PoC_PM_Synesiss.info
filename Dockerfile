# Usar una imagen oficial de Python ligera
FROM python:3.11-slim

# Variables de entorno para optimizar la ejecución de Python en contenedores
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Puerto por defecto (se puede sobreescribir en tiempo de build/run)
ARG PORT=8000
ENV PORT=${PORT}

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Copiar el archivo de requerimientos e instalar las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar utilidades necesarias (curl para HEALTHCHECK)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para ejecutar la aplicación
RUN useradd -m appuser || true

# Copiar el resto del código del proyecto (incluyendo los archivos .py, .csv, static, templates)
COPY . .
RUN chown -R appuser:appuser /app

# Usar usuario no-root
USER appuser

# Exponer el puerto configurado
EXPOSE ${PORT}

# Healthcheck simple
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
	CMD curl -f http://localhost:${PORT}/api/preview || exit 1

# Ejecutar la aplicación usando Gunicorn con bind dinámico a $PORT
# Usamos la forma shell para permitir expansión de la variable
CMD ["sh", "-c", "gunicorn modelopredictJD:app --bind 0.0.0.0:${PORT} --workers 3 --threads 2"]
