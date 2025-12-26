import json, time, random, uuid, sys, signal, os
from datetime import datetime
from kafka import KafkaProducer
from faker import Faker

# ==========================================
# --- IMPORT CONFIG ---
# ==========================================

from config import BOOTSTRAP_SERVERS, TOPIC_NAME, TICKET_INTERVAL, AUDIT_FILE, AUDIT_BATCH_SIZE

# ==========================================
# VARIABLES GLOBALES
# ==========================================

metrics = {
    "sent_attempts": 0,
    "confirmed": 0,
    "errors": 0,
    "start_time": None
}
running = True
fake = Faker('fr_FR')

# ==========================================
# TOUTES LES FONCTIONS
# ==========================================

def load_state():
    """Charge l'état précédent depuis le fichier JSON"""
    if os.path.exists(AUDIT_FILE):
        try:
            with open(AUDIT_FILE, 'r') as f:
                data = json.load(f)
                old = data.get("metrics", {})
                print(f"♻️  RESTAURATION : Reprise à {old.get('confirmed', 0)} tickets.")
                return old
        except Exception:
            pass
    # Défaut
    return {
        "sent_attempts": 0, "confirmed": 0, "errors": 0, 
        "start_time": datetime.now().isoformat()
    }

def save_audit():
    """Sauvegarde l'état actuel dans le fichier JSON"""
    audit_data = {
        "last_update": datetime.now().isoformat(),
        "metrics": metrics 
    }
    try:
        with open(AUDIT_FILE, 'w') as f:
            json.dump(audit_data, f, indent=4)
    except Exception as e:
        print(f"⚠️ Erreur écriture audit : {e}")

def on_success(record_metadata):
    """Callback Kafka : Succès"""
    metrics["confirmed"] += 1
    if metrics["confirmed"] % AUDIT_BATCH_SIZE == 0:
        save_audit()

def on_error(excp):
    """Callback Kafka : Erreur"""
    metrics["errors"] += 1
    print(f"❌ ERREUR KAFKA : {excp}")

def stop_script(sig, frame):
    """Gestionnaire de signal (Ctrl+C / Docker Stop)"""
    global running # On précise qu'on veut modifier la variable globale
    print(f"\n🛑 Signal reçu ({sig}). Finalisation en cours...")
    running = False

def generate_ticket():
    """Fabrique un faux ticket"""
    priorities = ['BASSE', 'MOYENNE', 'HAUTE', 'CRITIQUE']
    types = ['Problème Technique', 'Facturation', 'Demande Info', 'Connexion', 'Panne Matérielle']
    
    return {
        "ticket_id": str(uuid.uuid4()),
        "client_id": fake.random_int(min=1000, max=9999), 
        "creation_date": datetime.now().isoformat(),
        "request": fake.sentence(nb_words=10),
        "type": random.choice(types),
        "priority": random.choice(priorities)
    }

def create_kafka_producer():
    """Configure et renvoie le producer Kafka"""
    try:
        return KafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=1000000,
            linger_ms=10,
            compression_type='gzip'
        )
    except Exception as e:
        print(f"❌ Impossible de se connecter à Kafka : {e}")
        sys.exit(1)

# ==========================================
# POINT D'ENTRÉE (MAIN EXECUTION)
# ==========================================
if __name__ == "__main__":
    
    # Gestion des signaux d'arrêt
    signal.signal(signal.SIGINT, stop_script)
    signal.signal(signal.SIGTERM, stop_script)

    # Chargement de l'état (Mise à jour de la variable globale)
    print(f"📂 Fichier d'audit : {AUDIT_FILE}")
    saved_metrics = load_state()
    metrics.update(saved_metrics) # On met à jour le dictionnaire global existant

    # Connexion
    print(f"⏳ Connexion à Redpanda sur {BOOTSTRAP_SERVERS}...")
    producer = create_kafka_producer()
    print("✅ Producer connecté !")

    print(f"📤 Démarrage envoi vers '{TOPIC_NAME}'...")

    # Boucle Principale
    try:
        while running:
            ticket = generate_ticket()
            
            future = producer.send(
                TOPIC_NAME, 
                value=ticket,
                key=str(ticket['client_id']).encode('utf-8')
            )
            future.add_callback(on_success)
            future.add_errback(on_error)
            
            metrics["sent_attempts"] += 1
            
            # Affichage propre (flush=True force l'affichage immédiat dans Docker)
            print(f"✉️  Envoyés : {metrics['sent_attempts']} | ✅ Confirmés : {metrics['confirmed']}", flush=True)
            
            time.sleep(TICKET_INTERVAL)

    except Exception as e:
        print(f"\n❌ Erreur inattendue : {e}")

    finally:
        print("\n⏳ Vidange du Producer (Flush)...")
        producer.flush()
        producer.close()
        
        save_audit() # Sauvegarde finale
        
        print("-" * 30)
        print("📊 RAPPORT FINAL")
        print(f"   Tentatives : {metrics['sent_attempts']}")
        print(f"   Confirmés  : {metrics['confirmed']}")
        print(f"   Erreurs    : {metrics['errors']}")
        print("-" * 30)
        sys.exit(0)