# Une version STABLE de Debian (Bookworm) pour avoir Java 17
FROM python:3.10-slim-bookworm

# Force les logs à s'afficher en temps réel
ENV PYTHONUNBUFFERED=1

LABEL org.opencontainers.image.created="2025-12-25T00:00:00Z" \
      org.opencontainers.image.authors="Abdulkadir GUVEN" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.title="InduTech Spark ETL" 

# INSTALLATION DE JAVA ET OUTILS
# procps est nécessaire pour que Spark puisse vérifier ses processus
RUN apt-get update && \
    apt-get install -y openjdk-17-jre-headless procps && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Variable d'environnement pour Spark
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# INSTALLATION DES DÉPENDANCES PYTHON
WORKDIR /app

# On copie juste le fichier requirements (optimisation cache Docker)
COPY requirements.txt .

# Installation des bibliothèques
RUN pip install --no-cache-dir -r requirements.txt

ARG SPARK_KAFKA_VERSION=org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3

# Hack prod : démarre Spark pour pré-télécharger les JARs Ivy dans l’image
RUN python -c "from pyspark.sql import SparkSession; \
    SparkSession.builder \
    .config('spark.jars.packages', '$SPARK_KAFKA_VERSION') \
    .getOrCreate()"

# 4. COPIE DU CODE
COPY src/ ./src/

# 5. COMMANDE PAR DÉFAUT
CMD ["python", "src/stream_job.py"]