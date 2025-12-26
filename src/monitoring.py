import json, os, time, platform
import pandas as pd
from datetime import datetime, timezone

REFRESH_INTERVAL = 5 # secondes
TABLE_WIDTH = 70

try:
    from config import AUDIT_FILE, PARQUET_PATH, AUDIT_BATCH_SIZE
except ImportError:
    print("❌ ERREUR : Impossible de trouver src/config.py")
    print("Assurez-vous de lancer le script depuis la racine du projet !")
    exit(1)

# Vérification WSL 
if platform.system() == "Windows":
    print("⚠️  ERREUR : Ce script est conçu pour WSL/Linux.")
    

def get_producer_count():
    """Lire le fichier témoin généré par le producer"""
    if not os.path.exists(AUDIT_FILE):
        return 0, "Non démarré"
    
    try:
        with open(AUDIT_FILE, 'r') as f:
            data = json.load(f)
            # On récupère le nombre de messages confirmés dans 'metrics'
            return data["metrics"]["confirmed"], data["last_update"]
    except Exception as e:
        return 0, f"Erreur lecture: {e}"

def show_stats():
    # Nettoyage console
    os.system('clear')
    
    # 1. RÉCUPÉRATION DES CHIFFRES
    prod_count, prod_last_seen = get_producer_count()
    
    last_update_str = prod_last_seen
    if "T" in str(prod_last_seen):
        try:
            # On coupe pour garder HH:MM:SS
            last_update_str = prod_last_seen.split('T')[1].split('.')[0]
        except:
            pass # Si format bizarre, on laisse tel quel
    
    spark_count = 0
    df = pd.DataFrame()
    spark_status = "⏳ En attente d'initialisation..."
    
    try:
        # Lecture optimisée avec PyArrow engine
        if os.path.exists(PARQUET_PATH):
            df = pd.read_parquet(PARQUET_PATH, engine='pyarrow')
            spark_count = len(df)
            spark_status = "🟢 Disponible"
        else:
            spark_status = "⚠️ Dossier introuvable"
    except Exception as e:
        spark_status = f"❌ Erreur: {e}"

    # 2. CALCUL DU LAG (Différence)
    diff = prod_count - spark_count
    
    # --- AFFICHAGE DASHBOARD ---
    print(f"📊 MONITORING PIPELINE E2E | {datetime.now(timezone.utc).strftime('%H:%M:%S')} | Rafraîchissement: {REFRESH_INTERVAL}s")
    print("="*TABLE_WIDTH)
    
    print(f"🗣️  PRODUCER (Source)   :   {str(prod_count).ljust(6)} tickets confirmés   [MAJ: {last_update_str}]")    
    print(f"💾  DATALAKE (Cible)    :   {str(spark_count).ljust(6)} tickets stockés")
    print(f"📂  ACCÈS DATALAKE      :   [{spark_status}]")
  
    print("-" * TABLE_WIDTH)
    
    if diff == 0 and prod_count > 0:
        print(f"✅ SYNCHRONISATION PARFAITE (Zero Data Loss)")
    elif diff > 0:
        print(f"⚠️  LAG DÉTECTÉ : {diff} tickets en cours de traitement...")
        print("    (Ils sont dans Redpanda ou dans le buffer Spark)")
    elif diff < 0:        
        gap = abs(diff)        
        # Cas "Normal" : L'écart est petit (inférieur à 2 batchs du producer)
        # Cela veut dire que Spark a bien lu les tickets, mais le Producer n'a pas encore écrit dans le JSON.
        if gap <= AUDIT_BATCH_SIZE * 2:
             print(f"🚀 AVANCE SPARK : {gap} tickets d'avance sur le fichier témoin.")
             print("    (Normal : Le fichier d'audit Producer ne se met à jour que tous les 10 tickets)")
        
        # Cas "Anormal" : L'écart est énorme
        # Là, c'est sûrement qu'on a oublié de vider le dossier avant de commencer
        else:
             print(f"👻 DONNÉES FANTÔMES : {gap} tickets inattendus dans le Data Lake.")
             print("    (Cause probable : Oubli de nettoyage avant le lancement)")
    else:
        print("💤 En attente de données...")

    print("="*TABLE_WIDTH)
    
# Boucle infinie
try:
    while True:
        show_stats()
        time.sleep(REFRESH_INTERVAL)
except KeyboardInterrupt:
    print("\n Arrêt du monitoring.")