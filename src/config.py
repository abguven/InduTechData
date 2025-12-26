# --- src/config.py ---
import os

# Kafka Config
# Par défaut localhost pour test Windows, sinon la valeur de Docker
BOOTSTRAP_SERVERS = os.getenv('KAFKA_BROKER', 'localhost:9094')
TOPIC_NAME = os.getenv('TOPIC_NAME', 'client_tickets')

# Producer Config
AUDIT_BATCH_SIZE = 10
TICKET_INTERVAL = 0.5

# Gestion des Chemins
# Si on est dans Docker, on utilise la variable d'env. Sinon, un dossier local par défaut.
DATA_DIR = os.getenv('CONTAINER_DATA_DIR', 'data_output')

# Le fichier d'audit sera stocké dans ce dossier
AUDIT_FILE = os.path.join(DATA_DIR, 'audit_producer.json')
PARQUET_PATH = os.path.join(DATA_DIR, 'tickets_parquet')

# Vérification : Créer le dossier s'il n'existe pas (utile pour tests locaux)
if not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR)
    except OSError:
        pass # Ignorer si erreur de permission dans Docker