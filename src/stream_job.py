import os, signal, sys, time
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, current_timestamp, when
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

# --- IMPORT CONFIG CENTRALISÉE ---
from config import BOOTSTRAP_SERVERS, TOPIC_NAME, PARQUET_PATH, DATA_DIR

# Version Linux (WSL)
os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3 pyspark-shell'

query = None
stop_requested = False

def signal_handler(sig, frame):
    global stop_requested
    print(f"\n🛑 Signal reçu ({sig}) ! Demande d'arrêt enregistrée.")
    stop_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

try:
    print("⏳ Démarrage de la session Spark...")
    spark = (SparkSession.builder 
                .appName("InduTech_Ticket_Export") 
                .master("local[*]") 
                .config("spark.task.maxFailures", "20") 
                .config("spark.network.timeout", "600s") 
                .getOrCreate()
            )

    # --- SCHÉMA ---
    ticket_schema = StructType([
        StructField("ticket_id", StringType(), True),
        StructField("client_id", IntegerType(), True),
        StructField("creation_date", StringType(), True),
        StructField("request", StringType(), True),
        StructField("type", StringType(), True),
        StructField("priority", StringType(), True)
    ])

    # --- LECTURE (INPUT) ---
    print(f"🎧 Écoute du topic '{TOPIC_NAME}' sur {BOOTSTRAP_SERVERS}...")
    
    raw_stream = (spark.readStream 
                    .format("kafka") 
                    .option("kafka.bootstrap.servers", BOOTSTRAP_SERVERS)
                    .option("subscribe", TOPIC_NAME) 
                    .option("startingOffsets", "earliest") 
                    .option("kafka.reconnect.backoff.ms", "1000")       
                    .option("kafka.reconnect.backoff.max.ms", "10000")                       
                    .load()
    )

    # TRANSFORMATION
    clean_df = raw_stream.select(
        from_json(col("value").cast("string"), ticket_schema).alias("data")
    ).select("data.*") 
    
    enriched_df = (
            clean_df
            .withColumn("support_team", 
                when((col("type") == "Panne Matérielle") | (col("type") == "Problème Technique"), "Support Technique")
                .when(col("type") == "Connexion", "Support Réseau")
                .when(col("type") == "Facturation", "Support Compta")
                .otherwise("Support Clientèle"))
            .withColumn("last_processed_at", current_timestamp())
    ) 

    # --- SAUVEGARDE SOUS FORMAT PARQUET ---
    output_path = PARQUET_PATH
    
    # On crée le dossier checkpoints DANS le dossier data centralisé
    checkpoint_path = os.path.join(DATA_DIR, "checkpoints")

    print(f"📂 Destination des données : {output_path}")
    print(f"📍 Destination checkpoints : {checkpoint_path}")

    query = (enriched_df.writeStream 
                .outputMode("append")
                .format("parquet") 
                .option("path", output_path) 
                .option("checkpointLocation", checkpoint_path) 
                # .trigger(processingTime="10 seconds")
                .start()
    )
    
    print("🚀 Stream démarré. La sentinelle surveille...")

    # --- BOUCLE DE SURVIE ---
    while not stop_requested and query.isActive:
        time.sleep(1)
    
    if stop_requested:
        print("💾 Arrêt propre demandé...")
        query.stop()
        query.awaitTermination(timeout=60)
        print("✅ Spark éteint proprement.")
        sys.exit(0)
    
    else:
        print("❌ LE STREAM S'EST ARRÊTÉ ANORMALEMENT !")
        if query.exception():
            print(f"Cause : {query.exception()}")
        sys.exit(1)

except Exception as e:
    print(f"❌ Erreur critique du script : {e}")
    sys.exit(1)

finally:
    spark.stop()