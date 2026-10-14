"""
Configuration de l'application GhalimLab LIMS
Paramètres généraux, ports réseaux des automates et métadonnées du laboratoire.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Base de données SQLite par défaut (ou PostgreSQL via variable d'environnement)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'ghalimlab.db'}")

# Répertoire de stockage des documents scannés (ordonnances, scanners, comptes-rendus)
UPLOAD_DIR = BASE_DIR / "uploads" / "documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Port d'écoute pour l'intégration des automates de laboratoire (ASTM E1381/E1394)
ASTM_HOST = os.getenv("ASTM_HOST", "0.0.0.0")
ASTM_PORT = int(os.getenv("ASTM_PORT", "5000"))

# Paramètres de l'application Web FastAPI (Support variable PORT pour déploiement Cloud)
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))

# Métadonnées du Laboratoire d'Analyses Médicales
LABO_NOM = "Laboratoire d'analyses médicales GhalimLab"
LABO_SOUS_TITRE = "Biologie Médicale - Hématologie, Biochimie, Bactériologie, Parasitologie"
LABO_ADRESSE = "124 Avenue Hassan II, Casablanca, Maroc"
LABO_TEL = "+212 5 22 45 67 89"
LABO_EMAIL = "contact@ghalimlab.ma"
LABO_SITE = "www.ghalimlab.ma"
LABO_DIRECTEUR = "Dr. Kawtar GHALIM"
LABO_AGREMENT = "Agrément Ministère de la Santé N° 8492/BM"
