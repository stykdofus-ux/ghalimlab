# GhalimLab LIMS - Application de Gestion de Laboratoire d'Analyses Médicales

Application full-stack de biologie médicale de niveau production, conçue selon les normes des systèmes d'information de laboratoire (LIMS). Elle intègre un **moteur de communication bidirectionnelle ASTM E1381 / E1394** (`senaite.astm` / socket TCP asynchrone) permettant la réception, le décodage et l'ingestion automatique en base de données des résultats d'analyses issus d'automates d'hématologie (ex: **Sysmex XN/XS**) et de biochimie clinique (ex: **Roche Cobas 6000/8000**).

---

## 1. Architecture Technique

* **Backend & API** : Python (FastAPI, SQLAlchemy 2.0, Pydantic v2)
* **Base de Données** : SQLite (par défaut) ou PostgreSQL
* **Frontend** : Interface réactive moderne en HTML5 / CSS3 (palette clinique soignée, micro-animations, drapeaux d'alerte biologique) avec moteur de templating **Jinja2**
* **Moteur d'Intégration Automates** : Démon asynchrone TCP/IP ASTM E1381/E1394 avec gestion du handshake (`ENQ`, `ACK`, `NAK`, `STX`, `ETX`, `EOT`), calcul de checksum modulo 256 et parsing des enregistrements (`H`, `P`, `O`, `R`, `C`, `L`)
* **Moteur d'Édition PDF** : Génération de comptes-rendus d'analyses biomédicales officiels haute définition via **ReportLab**
* **Langue** : 100% en Français (interfaces, logs, schémas de base de données, comptes-rendus)

---

## 2. Structure du Projet

```text
ghalimlab/
├── backend/
│   ├── app/
│   │   ├── config.py              # Configuration (Ports, chemins, coordonnées labo)
│   │   ├── database.py            # Moteur SQLAlchemy et sessions
│   │   ├── main.py                # Application FastAPI et routes web HTML
│   │   ├── models/                # Modèles ORM
│   │   │   ├── core.py            # Patient, Demande, AnalyseParameter, Resultat, AutomateLog
│   │   │   ├── billing.py         # ActeBiologique, ParametreTarification, Facture, FactureLigne
│   │   │   ├── bacteriology.py    # ExamenBacteriologique, AntibiogrammeLigne
│   │   │   └── parasitology.py    # ExamenParasitologique
│   │   ├── schemas/               # Schémas de validation Pydantic
│   │   ├── services/
│   │   │   ├── billing_service.py # Ingestion nomenclature V4, tarification CNSS/Normal & facturation
│   │   │   ├── result_service.py  # Ingestion automatique & calcul des bornes de référence
│   │   │   ├── pdf_service.py     # Édition des comptes-rendus et factures médicales PDF
│   │   │   └── seed_data.py       # 492 actes nomenclature, catalogue & dossiers de test
│   │   └── routes/                # API REST
│   │       ├── billing.py         # Facturation, nomenclature 492 actes, règlements & PDF
│   │       ├── patients.py        # Gestion des patients
│   │       ├── demandes.py        # Gestion des prélèvements & codes-barres
│   │       ├── validation.py      # Validation biologique & saisie manuelle
│   │       ├── automates.py       # Télémétrie ASTM & déclenchement de simulation
│   │       ├── documents.py       # Gestion des documents & bulletins scannés
│   │       ├── tubes.py           # Traçabilité des tubes & étiquettes thermiques
│   │       ├── bacteriology.py    # Endpoints ECBU & Antibiogrammes
│   │       ├── parasitology.py    # Endpoints Parasitologie & Mycologie
│   │       └── pdf_export.py      # Téléchargement du compte-rendu PDF
│   └── astm/
│       ├── protocol.py            # Parser ASTM E1381/E1394, trames et checksum modulo 256
│       ├── server.py              # Démon socket TCP asynchrone (Port 5000)
│       └── simulator.py           # Simulateur d'automates Sysmex et Cobas
├── frontend/
│   ├── static/
│   │   ├── css/style.css          # Design médical moderne, badges et mise en page
│   │   └── js/app.js              # Interactions dynamiques, requêtes asynchrones, alertes
│   └── templates/
│       ├── base.html              # Gabarit principal avec barre latérale et indicateur ASTM
│       ├── dashboard.html         # Tableau de bord principal avec KPIs & Chiffre d'Affaires
│       ├── billing_dashboard.html # Gestion de la facturation, encaissements et reçus
│       ├── billing_settings.html  # Paramètres des taux (CNSS / Normal) & 492 actes de nomenclature
│       ├── worklist.html          # Liste de travail (Worklist) avec filtres par statut
│       ├── new_demande.html       # Enregistrement patient, prise en charge & facturation auto
│       ├── patient_detail.html    # Dossier complet patient & visionneuse de scans
│       ├── validation_dossier.html# Dashboard de validation biologique (Élevé/Bas/Normal)
│       ├── automates_monitor.html # Console de télémétrie ASTM en direct
│       ├── bacteriology.html      # Module spécialisé Bactériologie & Antibiogrammes
│       ├── parasitology.html      # Module spécialisé Parasitologie & Mycologie
│       └── patients_list.html     # Annuaire des patients
├── uploads/
│   └── documents/                 # Répertoire sécurisé de stockage des scans numérisés
├── tests/
│   ├── test_astm_protocol.py      # Tests unitaires du protocole ASTM & checksum
│   ├── test_reference_ranges.py   # Tests du calcul des bornes normales selon l'âge et le sexe
│   └── test_api.py                # Tests API, validation, traçabilité tubes, factures & PDF
├── liste_actes_biologie_V4.pdf    # Nomenclature officielle marocaine des actes de biologie
├── run_server.py                  # Lanceur unifié (FastAPI + Démon ASTM)
├── requirements.txt
└── README.md
```

---

## 3. Installation et Démarrage Rapide

### Prérequis
* Python 3.10+ (ou version récente)
* Navigateur Web moderne

### Installation des Dépendances
```powershell
py -m pip install -r requirements.txt
```

### Démarrage Conjoint de l'Application Web et du Démon ASTM
Une commande unique permet de lancer le serveur Web FastAPI et le serveur socket ASTM :
```powershell
py run_server.py
```

* **Interface Web LIMS** : [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Démon d'écoute ASTM** : `0.0.0.0:5000` (Socket TCP prêt à recevoir les trames)
* **Documentation OpenAPI / Swagger** : [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 4. Intégration des Automates ASTM (`senaite.astm`)

### Cycle d'Échange ASTM E1381
1. **Établissement de Liaison** : L'automate émet le caractère `<ENQ>` (`0x05`). Le serveur répond immédiatement par `<ACK>` (`0x06`).
2. **Transmission des Trames** : Chaque enregistrement est transmis sous la forme :
   `<STX><Numéro_Trame><Enregistrement_ASTM><ETX><Checksum><CR><LF>`
   Le checksum est la somme modulo 256 des octets compris entre `<STX>` (exclu) et `<ETX>` (inclus), formatée en 2 caractères hexadécimaux majuscules.
3. **Acquittement** : Le serveur vérifie le checksum. S'il est valide, il renvoie `<ACK>`. En cas de corruption, il renvoie `<NAK>` (`0x15`).
4. **Fin de Transmission** : L'automate émet `<EOT>` (`0x04`). Le serveur parse l'ensemble du message et ingère automatiquement les résultats dans le dossier du prélèvement correspondant.

### Simulation et Test des Automates
Vous pouvez envoyer des trames ASTM réelles vers le serveur :

#### Option A : En un clic depuis l'interface Web
Rendez-vous sur [http://127.0.0.1:8000/automates](http://127.0.0.1:8000/automates) ou sur l'écran d'un dossier en attente et cliquez sur :
* `Transmettre Sysmex (NFS)`
* `Transmettre Cobas (Biochimie)`

#### Option B : En ligne de commande via le script simulateur
```powershell
# Simulation d'un hémogramme complet Sysmex XN pour le prélèvement PREL-2026-002
py -m backend.astm.simulator --automate sysmex --barcode PREL-2026-002

# Simulation d'un bilan biochimique complet Cobas 6000
py -m backend.astm.simulator --automate cobas --barcode PREL-2026-002
```

---

## 5. Fonctionnalités Principales

### A. Gestion des Patients & Prélèvements (Demandes)
* Enregistrement complet : CIN/Identifiant, Nom, Prénom, Date de Naissance, Sexe, N° Sécurité Sociale / CNSS, Téléphone, Adresse.
* Génération automatique ou personnalisée de code-barres unique (`PREL-2026-XXXX`).
* Sélection modulaire des bilans demandés (NFS, Glycémie, Bilan Rénal, Bilan Lipidique, CRP, ECBU).

### B. Validation Biologique & Bornes de Référence Conditionnées
* Chaque paramètre possède des intervalles de référence physiologiques différenciés par **Âge** (Enfants < 15 ans) et **Sexe Biologique** (Hommes, Femmes).
* Mise en évidence automatique par badges colorés :
  * **▲ ÉLEVÉ** : Rouge vif (`#EF4444`)
  * **▼ BAS** : Bleu indigo (`#3B82F6`)
  * **✓ NORMAL** : Vert émeraude (`#10B981`)
* Possibilité d'ajouter des analyses manuelles, de modifier les valeurs et de renseigner l'interprétation biologique.
* Validation en un clic verrouillant le dossier avec horodatage et identifiant du biologiste validateur.

### C. Édition & Impression de Comptes-Rendus Médicaux (PDF)
* Génération instantanée conforme aux exigences cliniques : en-tête officielle du laboratoire, informations administratives du patient, tableau structuré des résultats par spécialité avec valeurs de référence et alertes, bloc d'antibiogramme si applicable, conclusions et signature électronique du biologiste médical.
* Téléchargement via `/api/rapports/{id}/pdf`.

### D. Gestion des Bulletins & Documents Scannés (Ordonnances, Scanners, Antériorités)
* **Pour la Secrétaire Médicale** :
  * Possibilité de numériser et téléverser des ordonnances papier dès l'accueil (`/demande/nouvelle`) ou depuis la fiche patient (`/patient/{id}`).
  * Typage des documents : *Ordonnance Médicale*, *Résultat d'Imagerie / Scanner*, *Bilan Antérieur Externe*, *Prise en charge Assurance/CNSS*.
  * Prise en charge des formats PDF, JPEG, PNG, WEBP avec horodatage, auteur du dépôt et notes cliniques.
* **Pour le Biologiste Médical** :
  * Indicateur d'alerte visuel dans la Worklist (`📑 X document(s) scanné(s)`) et sur le bandeau patient.
  * Section dédiée sur le dashboard de validation (`/validation/{id}`) permettant de consulter les scans en haute définition (visionneuse en ligne) pour corréler les résultats de l'automate avec l'ordonnance ou le scanner du patient.
  * Possibilité d'ajouter des documents complémentaires directement lors de la phase de validation technique.

### E. Modules Spécialisés Extensibles
1. **Bactériologie & Virologie** (`/bacteriologie`) :
   * Prélèvements ECBU, vaginaux, urétraux, écouvillons de gorge.
   * Cytologie (Leucocytes, Hématies, Cellules épithéliales), Coloration de Gram, Numération de colonies (UFC/mL).
   * Antibiogramme complet avec antibiotique, famille, diamètre d'inhibition, CMI et statut normalisé (`S` = Sensible, `I` = Intermédiaire, `R` = Résistant).
2. **Parasitologie & Mycologie** (`/parasitologie`) :
   * Examen Parasitologique des Selles (EPS) à l'état direct et après concentration (Ritchie).
   * Recherche d'hématozoaires sur frottis sanguin et goutte épaisse (Paludisme).
   * Examen mycologique et cultures sur milieu de Sabouraud (Candida, Dermatophytes).

### F. Traçabilité Pré-analytique, Étiquetage Thermique des Tubes & Sérothèque (`/echantillons-serotheque`)
* **Détermination Automatique des Tubes** : Selon le bilan prescrit (EDTA Bouchon Violet pour NFS, Sec/Gel Bouchon Jaune pour Biochimie/CRP, Citrate Bouchon Bleu pour Hémostase, Flacon Stérile pour ECBU, Pot Stérile pour Parasito).
* **Génération d'Étiquettes Thermiques Code128 (PDF)** :
  * Format standard pour imprimantes d'étiquettes de laboratoire (50mm x 25mm / Zebra, Brother, Dymo).
  * Impression en lot pour un prélèvement (`/api/rapports/demande/{id}/etiquettes/pdf`) ou individuelle par tube (`/api/rapports/tube/{id}/etiquette/pdf`).
* **Suivi de la Chaîne de Vie des Échantillons** :
  * Statuts en 1 clic : *Non prélevé* ➔ *Prélevé* ➔ *Reçu au Laboratoire* ➔ *Centrifugé* ➔ *En cours sur automate* ➔ *Analysé* ➔ *Archivé en sérothèque*.
  * Déclaration des non-conformités pré-analytiques (*Hémolyse*, *Tube coagulé*, *Volume insuffisant*).
* **Gestion et Localisation en Sérothèque** :
  * Attribution d'emplacements précis de conservation sous température contrôlée (ex: *Frigo Sérothèque 1 - Rack A1 - Pos 04*, *Congélateur -20°C - Rack C1*).
  * Horodatage d'archivage et traçabilité des opérateurs préleveurs et réceptionnaires.

### G. Facturation Médicale & Nomenclature Officielle des Actes (492 Actes V4)
* **Catalogue Intégral de la Nomenclature Marocaine** (`/parametres-tarifs`) :
  * Intégration exhaustive de la totalité des **492 actes de biologie** issus du document officiel `liste_actes_biologie_V4.pdf` (codes B100 à B591, catégories Biochimie, Hématologie, Immunologie, Bactériologie, Hormonologie, etc.).
  * Règle de tarification stricte selon la prise en charge :
    * **CNSS / CNOPS** : `Prix = Coefficient B × 1.10 DH`
    * **Normal / Assurances Privées** : `Prix = Coefficient B × 1.36 DH`
* **Pilotage Paramétrique par le Biologiste** :
  * Possibilité pour le biologiste médical de modifier globalement les multiplicateurs (taux CNSS et Normal) avec recalcul automatique instantané de l'ensemble des 492 actes.
  * Possibilité d'ajuster individuellement le coefficient B, le prix conventionné CNSS ou le prix Normal de n'importe quel acte avec mémorisation instantanée.
  * Ajout d'actes personnalisés hors nomenclature avec cotation propre.
* **Module de Facturation & Règlements** (`/facturation`) :
  * Facturation automatique lors de l'enregistrement d'une demande avec sélection du mode de couverture (*Normal / Privé*, *CNSS*, *CNOPS*, *Assurance*).
  * Suivi des règlements : Espèces, Carte Bancaire, Virement, Prise en charge tierce avec statut de solde (*Payé intégralement*, *Avance versée*, *Non payé*).
  * Tableau de bord financier : Chiffre d'Affaires total, montants encaissés, reste à recouvrer.
  * **Édition de Factures & Reçus de Paiement Officiels (PDF)** : Génération haute définition avec ReportLab conforme aux mentions fiscales (ICE, Identifiant Fiscal, Patente, N° CNSS). Téléchargement direct via `/api/billing/factures/{id}/pdf`.

---

## 6. Exécution des Tests Automatisés

Le projet comprend une suite complète de 17 tests unitaires et d'intégration validant le protocole ASTM, le calcul des bornes normales, la gestion des documents scannés, la traçabilité des tubes, la nomenclature des 492 actes, le calcul des tarifs CNSS/Normal et la génération des factures PDF :

```powershell
py -m pytest tests/
```

*Résultat attendu : 17 passed.*

