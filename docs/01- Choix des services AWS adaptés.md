---
tags:
  - s3
  - redpanda
  - pandas
  - RedShift
---

# 01- Choix des services AWS adaptés

##  Identification et sélectionne des composants

### 1. Stockage de données non structurées 
*logs, données brutes IoT, fichiers utilisateurs *
  
>**Service proposé :** `Amazon S3`

#### Pourquoi Amazon S3 ?

- Capacité illimitée et scalable
- Support universel, parfait pour un datalake
- Chiffrement intégré
- Durable et disponible (replication multi-zones)

---

### 2. Entrepôt de données (Data Warehouse)
*Objectif : Centraliser les données analytiques et supporter des requêtes SQL complexes.*

> ✅ **Service proposé :** `Amazon Redshift`

#### Pourquoi Amazon Redshift ?

- **Performance et scalabilité**
  Architecture MPP (Massively Parallel Processing) et stockage en colonnes. Concurrency Scaling pour gérer les pics de charge.

- **Support SQL avancé**
  Compatible avec les outils standards et les requêtes complexes.

- **Intégration BI**
  Connectivité native avec QuickSight, Tableau, PowerBI.

---

### 3. Traitement des données en temps réel (streaming)
*Flux IoT, Logs applicatifs, événements temps réel.*

> ✅ **Service proposé :** `Redpanda`
> *Plateforme compatible Kafka, mais sans la complexité de ZooKeeper.*

#### Pourquoi Redpanda ?

- Simplicité d'installation (Zero-Ops)
	**Comparaison avec Amazon MSK :**
	
	```text
	Amazon MSK : Kafka + ZooKeeper + Configuration complexe
	Redpanda : Un seul service + Configuration automatique
	```

- Faible consommation de ressources (C++)
- Latence ultra-faible
- Réduction des coûts d'infrastructure

#### Comparatif : Redpanda vs Solutions AWS

| Critère | Redpanda | Amazon MSK (Managed Kafka) | Amazon Kinesis |
| :--- | :--- | :--- | :--- |
| **Complexité** | ⭐⭐⭐⭐⭐ (Simple, 1 binaire) | ⭐⭐⭐ (Lourd, Zookeeper masqué) | ⭐⭐⭐⭐ (Serverless) |
| **Performance** | ⭐⭐⭐⭐⭐ (C++, <1ms) | ⭐⭐⭐ (Java, latence standard) | ⭐⭐⭐ (<100ms) |
| **Coût** | ⭐⭐⭐⭐⭐ (Faible, instances optimisées) | ⭐⭐⭐ (Coûteux pour petits clusters) | ⭐⭐⭐⭐ (Pay-per-shard) |
| **Compatibilité** | 100% Kafka API | 100% Kafka API | Propriétaire AWS |

---

### 4. Sécurisation et gestion des accès

> ✅ **Service proposé :** `AWS Directory Service` combiné avec `AWS IAM Identity Center`

#### Solution recommandée : AWS Managed Microsoft AD (Hybrid Edition)

#### Pourquoi cette solution ?

- **Authentification Unique (SSO) :**
  Les employés utilisent leurs identifiants Active Directory actuels pour se connecter à la console AWS et aux services de données. Pas de nouveaux mots de passe à gérer.

- **Sécurité du tunnel :**
  L'ajout d'une **VPN Gateway** assure que les données d'authentification et les flux d'administration ne transitent jamais en clair sur l'internet public.

- **Centralisation :**
  Si un employé quitte l'entreprise, son compte est désactivé dans l'AD local et l'accès au Cloud est coupé instantanément.


