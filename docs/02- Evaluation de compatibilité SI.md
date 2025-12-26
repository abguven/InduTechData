# Évaluation de la compatibilité de l'infrastructure hybride avec le SI existant

**Projet :** Modernisation de l'infrastructure de données InduTechData
**Date :** 17/12/2025
**Auteur :** [Abdulkadir GUVEN]

---

## Introduction
Ce document détaille l'analyse de compatibilité entre l'infrastructure On-Premise actuelle d'InduTechData (SQL Server, AD, SAN) et la nouvelle architecture Cloud Hybride sur AWS. L'objectif est de démontrer comment les choix technologiques garantissent la sécurité, la continuité de gestion des identités et l'interopérabilité des flux de données.

---

## 1. Sécurité et conformité des flux de données sensibles

La sécurité est le pilier central de cette architecture hybride, compte tenu de la criticité des données ERP/CRM et du volume des données IoT. La stratégie de sécurisation repose sur une approche "Défense en profondeur" à trois niveaux :

### A. Sécurisation du Transport (Transit)
Pour garantir qu'aucune donnée sensible ne transite en clair sur l'internet public, nous avons opté pour une **AWS VPN Gateway**.
*   **Tunnel IPsec :** Un tunnel chiffré est établi entre le pare-feu de l'entreprise et le VPC (Virtual Private Cloud) AWS. Cela étend le réseau local vers le cloud de manière transparente.
*   **Protocoles :** Les flux IoT utilisent MQTT via TLS 1.2+, assurant l'authentification des capteurs et le chiffrement des mesures avant même leur arrivée dans Redpanda.

### B. Sécurisation du Stockage (Repos)
La conformité des données (notamment vis-à-vis des potentiels audits industriels ou RGPD pour les données clients) est assurée par le chiffrement systématique :
*   **Amazon S3 (Data Lake) :** Le chiffrement côté serveur (SSE-KMS) est activé par défaut. Les clés de chiffrement sont gérées via **AWS KMS** (Key Management Service), permettant une rotation automatique et une auditabilité des accès aux clés.
*   **Amazon Redshift :** Le cluster est chiffré au repos. De plus, il est déployé dans des sous-réseaux privés (Private Subnets), le rendant inaccessible directement depuis internet.

### C. Isolation et Filtrage
L'architecture utilise des **Security Groups** (pare-feu virtuels) stricts. Seul le trafic provenant du VPN ou des services internes (DMS, Glue) est autorisé à atteindre les bases de données. Cette segmentation garantit que même en cas de compromission d'un service web frontal, les données stockées restent isolées.

---

## 2. Homogénéité de la gestion des identités (AD vs Cloud)

Le défi majeur d'une architecture hybride est d'éviter la multiplication des comptes utilisateurs ("Shadow IT"). Pour InduTechData, qui utilise déjà Active Directory (AD) localement, nous avons choisi une stratégie de **Fédération d'Identité**.

### A. Extension de l'Active Directory
Nous déployons **AWS Directory Service (Managed Microsoft AD)** en mode "Trust Relationship".
*   **Fonctionnement :** Une relation de confiance bidirectionnelle est établie entre l'AD On-Premise et l'AD géré par AWS.
*   **Avantage décisif :** Il n'y a pas de duplication des bases de données utilisateurs. L'AD local reste la "source de vérité" (Master). Si un employé quitte l'entreprise et que son compte est désactivé en local, son accès au Cloud est immédiatement révoqué.

### B. Authentification Unifiée (SSO)
Grâce à l'intégration avec **AWS IAM Identity Center**, nous mettons en place un Single Sign-On (SSO).
*   Les Data Engineers et Data Analysts utilisent leurs identifiants Windows habituels pour se connecter à la console AWS, à Redshift Query Editor ou aux outils BI.
*   Cela réduit considérablement la surface d'attaque liée aux mots de passe faibles ou réutilisés, et simplifie l'onboarding des nouvelles recrues.

---

## 3. Interopérabilité entre Redpanda et SQL Server

L'objectif métier est de croiser les données opérationnelles (SQL Server) avec les données télémétriques (Redpanda). L'architecture proposée résout le problème de "silos de données" grâce à une stratégie de convergence vers le Data Lakehouse.

### A. Flux SQL Server vers Redshift (Données Structurées)
L'interopérabilité est assurée par **AWS DMS (Database Migration Service)** en mode CDC (Change Data Capture).
*   Au lieu de faire des exports nocturnes lourds, DMS capture les transactions en temps réel sur le SQL Server local et les réplique dans Amazon Redshift.
*   Cela garantit que l'entrepôt de données Cloud est toujours synchronisé avec l'ERP local, avec une latence de quelques secondes à peine.

### B. Flux Redpanda vers S3 (Données Non-Structurées)
Redpanda est configuré avec un connecteur **S3 Sink**.
*   Les données IoT ingérées ne restent pas enfermées dans le bus d'événements. Elles sont automatiquement déversées ("offloaded") dans Amazon S3 au format ouvert (Parquet ou JSON).
*   Cela permet de conserver un historique infini des logs capteurs à moindre coût, découplant ainsi le stockage (S3) du calcul (Redpanda).

### C. Le point de convergence : Redshift Spectrum
C'est ici que l'interopérabilité prend tout son sens. **Amazon Redshift** n'est pas seulement un stockage, c'est un moteur de requête fédéré.
*   Grâce à la fonctionnalité **Redshift Spectrum**, il est possible de créer des tables externes pointant vers les fichiers S3 générés par Redpanda.
*   **Scénario d'usage :** Un analyste peut écrire une requête SQL unique (JOIN) liant la table `Clients` (stockée dans Redshift, issue de SQL Server) et les fichiers `Logs_Capteurs` (stockés dans S3, issus de Redpanda).
*   Cette architecture assure une interopérabilité totale sans nécessiter de pipelines ETL complexes pour déplacer physiquement les pétaoctets de données IoT vers l'entrepôt.

---

## 4. Analyse Stratégique : Avantages, Limites et Points d'attention

### 4.1. Synthèse des avantages et de la scalabilité
L'architecture répond aux exigences de croissance via des mécanismes natifs :
*   **Scalabilité Démontrée :**
    *   *Stockage :* Amazon S3 offre une capacité virtuellement illimitée pour les données IoT.
    *   *Calcul :* Amazon Redshift permet d'activer le "Concurrency Scaling" pour absorber les pics de requêtes des analystes sans ralentir le système. (1h gratuit, 45$ par cluster par heure au dela)
    *   *Ingestion :* Le cluster Redpanda peut être étendu horizontalement (ajout de nœuds) pour gérer l'augmentation du flux IoT (50 Go/mois).
*   **Automatisation des Flux :**
    *   L'ensemble du pipeline est automatisé : AWS DMS gère la réplication SQL Server sans intervention humaine, et les connecteurs Redpanda déversent les logs dans S3 automatiquement. Aucun script manuel de transfert de fichier n'est nécessaire.

### 4.2. Limitations et Points d'attention
*   **Latence du lien Hybride :** La performance de la réplication dépendra de la bande passante du VPN. En cas de saturation, un passage vers *AWS Direct Connect* (connection dédiée ou hébergée) devra être envisagé.
*   **Complexité de gestion :** L'équipe devra monter en compétence sur la gestion des Security Groups AWS et le monitoring Redpanda, qui diffèrent des outils Windows Server habituels.
*   **Coûts de sortie (Egress) :** Si de gros volumes de données doivent redescendre du Cloud vers le On-Premise, des frais de bande passante s'appliqueront. L'architecture a été pensée pour éviter cela (le traitement se fait dans le Cloud).

---

## 5. Estimation Financière et Monitoring (FinOps)

### 5.1. Estimation des Coûts (Optimisation FinOps)
*Base de calcul : Région eu-west-3 (Paris) avec Engagement 1 an (Reserved Instances).*

| Service | Configuration | Coût Compute | Coût Stockage | **Coût Mensuel Total** | Type |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Amazon Redshift** | **2 × ra3.xlplus** (Reserved 1yr)<br>Stockage géré : 40 To | $1 292 | $1 024 | **$2 316** | Récurrent |
| **Redshift Spectrum** | Estimation scan : 55 To/mois | - | $275 | **$275** | Récurrent |
| **Amazon S3** | Standard Tier (10 To) | - | $246 | **$246** | Récurrent |
| **Redpanda (EC2)** | **3 × c5.large** (Reserved 1yr)<br>EBS gp3 : 3 × 150 Go | $175 | $42 | **$217** | Récurrent |
| **Load Balancer** | Network Load Balancer (NLB) | $25 | - | **$25** | Récurrent |
| **AWS DMS** | c7i.xlarge (Single-AZ)<br>Réplication continue (CDC) | $270 | $12 | **$282** | Récurrent |
| **Directory Service** | **AWS Managed AD (Standard)**<br>Pour Trust Relationship & SSO | $95 | - | **$95** | Récurrent |
| **VPN / Réseau** | Site-to-site + Data Transfer | $95 | - | **$95** | Récurrent |
| **TOTAL MENSUEL** | **OPEX (Coûts récurrents)** | | | **$3 551** | |

#### Coûts Ponctuels (Migration Initiale)
| Service | Description | Coût Unique |
| :--- | :--- | :--- |
| **Transfert Initial** | Ingestion historique 40 To vers Redshift | **$819** |

*Note : L'application des "Reserved Instances" sur 1 an permet une économie significative par rapport au prix catalogue On-Demand, rendant l'infrastructure viable économiquement pour InduTechData.*

### 5.2. Stratégie de surveillance des coûts
Pour éviter les dérives budgétaires, les mesures suivantes seront appliquées :
1.  **AWS Budgets :** Configuration d'une alerte automatique si la facture dépasse 80% du budget prévisionnel.
2.  **Tagging des ressources :** Application de tags `Projet:InduTech` et `Env:Prod` pour isoler les coûts du projet dans la facture globale.
3.  **Lifecycle Policies S3 :** Automatisation du passage des logs IoT vers *S3 Glacier* après 90 jours pour réduire le coût de stockage par 5.


## Conclusion
L'architecture proposée respecte strictement les contraintes du SI existant. Elle modernise la stack technologique (passage au Streaming et au Cloud) tout en s'appuyant sur les fondations solides de l'entreprise (Active Directory, SQL Server). Elle offre une scalabilité immédiate pour les flux IoT tout en garantissant une gouvernance unifiée de la sécurité.