"""
Service de gestion des tubes et échantillons pré-analytiques :
- Détermination automatique des types de tubes requis selon le bilan prescrit
- Génération des codes-barres uniques des tubes
- Suivi de la chaîne de traçabilité (Prélèvement -> Réception -> Centrifugation -> Automate -> Sérothèque)
"""

import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.core import Demande, EchantillonTube


# Règles de correspondance entre analyses demandées et types de tubes de prélèvement
REGLES_TUBES = [
    {
        "keywords": ["nfs", "hémogramme", "plaquettes", "frottis", "réticulocytes", "vitesse de sédimentation", "vs"],
        "suffix": "EDTA",
        "type_tube": "EDTA K3 / K2",
        "couleur_bouchon": "violet",
        "analyses_associees": "Hémogramme complet (NFS), Plaquettes",
        "volume_ml": 3.0
    },
    {
        "keywords": ["glycémie", "urée", "créatinine", "créat", "bilan rénal", "bilan lipidique", "cholestérol", 
                     "triglycérides", "hdl", "ldl", "crp", "protéine c", "transaminases", "alat", "asat", 
                     "bilirubine", "acide urique", "ionogramme", "calcium", "fer", "ferritine", "métabolique", "biochimie", "sérologie"],
        "suffix": "SEC",
        "type_tube": "Sec avec gel séparateur",
        "couleur_bouchon": "jaune",
        "analyses_associees": "Biochimie clinique, Ionogramme & Sérologie",
        "volume_ml": 5.0
    },
    {
        "keywords": ["hémostase", "tp", "inr", "tca", "fibrinogène", "d-dimères", "facteur"],
        "suffix": "CIT",
        "type_tube": "Citrate de sodium 3.2%",
        "couleur_bouchon": "bleu",
        "analyses_associees": "Bilan d'hémostase et de coagulation",
        "volume_ml": 2.7
    },
    {
        "keywords": ["ecbu", "urine", "bactériologie", "cytologie urinaire"],
        "suffix": "ECBU",
        "type_tube": "Flacon stérile urinaire",
        "couleur_bouchon": "rouge",
        "analyses_associees": "Examen Cytobactériologique des Urines",
        "volume_ml": 30.0
    },
    {
        "keywords": ["eps", "selles", "parasitologie", "coproculture", "helminth"],
        "suffix": "EPS",
        "type_tube": "Pot stérile à selles",
        "couleur_bouchon": "blanc",
        "analyses_associees": "Examen Parasitologique des Selles",
        "volume_ml": 20.0
    }
]


def determine_required_tubes(bilan_demande: str, code_barres_base: str) -> List[Dict[str, Any]]:
    """
    Analyse le texte du bilan demandé et retourne la liste des tubes nécessaires avec leurs métadonnées.
    """
    bilan_lower = (bilan_demande or "").lower()
    selected_rules = []

    for regle in REGLES_TUBES:
        if any(kw in bilan_lower for kw in regle["keywords"]):
            selected_rules.append(regle)

    # Si aucune correspondance spécifique n'est trouvée, attribuer au moins un tube Sec et un tube EDTA par défaut
    if not selected_rules:
        selected_rules = [REGLES_TUBES[0], REGLES_TUBES[1]]

    tubes_data = []
    for regle in selected_rules:
        code_tube = f"{code_barres_base}-{regle['suffix']}"
        tubes_data.append({
            "code_tube": code_tube,
            "type_tube": regle["type_tube"],
            "couleur_bouchon": regle["couleur_bouchon"],
            "analyses_associees": regle["analyses_associees"],
            "volume_ml": regle["volume_ml"],
            "statut_tube": "Non prélevé",
            "conformite_preanalytique": "Conforme"
        })

    return tubes_data


def generate_tubes_for_demande(db: Session, demande: Demande, force_recreate: bool = False) -> List[EchantillonTube]:
    """
    Crée en base de données les tubes requis pour une demande s'ils n'existent pas déjà.
    """
    existing_tubes = db.query(EchantillonTube).filter(EchantillonTube.demande_id == demande.id).all()
    if existing_tubes and not force_recreate:
        return existing_tubes

    if existing_tubes and force_recreate:
        for t in existing_tubes:
            db.delete(t)
        db.flush()

    specs = determine_required_tubes(demande.bilan_demande, demande.code_barres)
    created_tubes = []

    for spec in specs:
        tube = EchantillonTube(
            demande_id=demande.id,
            code_tube=spec["code_tube"],
            type_tube=spec["type_tube"],
            couleur_bouchon=spec["couleur_bouchon"],
            analyses_associees=spec["analyses_associees"],
            volume_ml=spec["volume_ml"],
            statut_tube=spec["statut_tube"],
            conformite_preanalytique=spec["conformite_preanalytique"],
            date_creation=datetime.datetime.now()
        )
        db.add(tube)
        created_tubes.append(tube)

    db.commit()
    for t in created_tubes:
        db.refresh(t)

    return created_tubes
