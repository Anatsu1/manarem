FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends dumb-init \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# psycopg viene en rueda precompilada tambien para arm64, asi que no hace falta
# ningun toolchain de compilacion en la imagen.
COPY requirements.txt requirements-postgres.txt ./
RUN pip install --no-cache-dir -r requirements-postgres.txt

COPY app.py db.py wsgi.py ./

# Solo hace falta si se corre sobre SQLite; con Postgres queda vacio.
RUN mkdir -p /data && chown -R nobody:nogroup /data /app

USER nobody
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/salud', timeout=4).status == 200 else 1)"

ENTRYPOINT ["dumb-init", "--"]
CMD ["gunicorn", "--workers", "2", "--threads", "4", "--bind", "0.0.0.0:5000", \
     "--access-logfile", "-", "--error-logfile", "-", "--forwarded-allow-ips", "*", \
     "wsgi:app"]
