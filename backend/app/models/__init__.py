"""
Exportation de tous les modèles SQLAlchemy pour faciliter les migrations et l'initialisation.
"""

from backend.app.models.core import Patient, Demande, AnalyseParameter, Resultat, AutomateLog, DocumentScanne, EchantillonTube
from backend.app.models.bacteriology import ExamenBacteriologique, AntibiogrammeLigne
from backend.app.models.parasitology import ExamenParasitologique

__all__ = [
    "Patient",
    "Demande",
    "AnalyseParameter",
    "Resultat",
    "AutomateLog",
    "DocumentScanne",
    "EchantillonTube",
    "ExamenBacteriologique",
    "AntibiogrammeLigne",
    "ExamenParasitologique",
]
