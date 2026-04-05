# Etapa 1: construir FARSITE
FROM gcc:12 AS builder

WORKDIR /farsite
COPY src/ src/
COPY Makefile .

RUN mkdir -p bin obj && make

# Etapa final: contenedor con Python y numpy
FROM python:3.11-slim

# Dependencias de sistema necesarias para FARSITE
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Copiar binario FARSITE desde builder
COPY --from=builder /farsite/bin/TestFARSITE /usr/local/bin/TestFARSITE

# Instalar numpy
RUN pip install --no-cache-dir numpy

# Crear directorios de datos
RUN mkdir -p /data/input /data/output

WORKDIR /data

# Entry point: tu script de FARSITE
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
