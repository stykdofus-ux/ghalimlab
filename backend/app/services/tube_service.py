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


def generate_next_tube_code(db: Session, date_ref: datetime.date = None, offset: int = 0) -> str:
    """
    Génère un identifiant unique de tube au format : YYMMDDNNN
    Exemple : 261015001
    - YY : 2 derniers chiffres de l'année (ex: 26 pour 2026)
    - MM : Mois sur 2 chiffres (ex: 10 pour octobre)
    - DD : Jour sur 2 chiffres (ex: 15)
    - NNN : Numéro d'ordre journalier du tube sur 3 chiffres au minimum (ex: 001, premier tube du jour).
    """
    if date_ref is None:
        date_ref = datetime.date.today()

    prefix = date_ref.strftime("%y%m%d")

    # Recherche les tubes du même jour pour trouver le numéro de séquence maximal
    existing_tubes = db.query(EchantillonTube.code_tube).filter(
        EchantillonTube.code_tube.like(f"{prefix}%")
    ).all()

    max_seq = 0
    for (code,) in existing_tubes:
        if code and code.startswith(prefix):
            remainder = code[len(prefix):]
            digits = ""
            for ch in remainder:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            if digits:
                try:
                    num = int(digits)
                    if num > max_seq:
                        max_seq = num
                except ValueError:
                    pass

    next_num = max_seq + 1 + offset
    return f"{prefix}{next_num:03d}"


def determine_required_tubes(
    bilan_demande: str,
    code_barres_base: str = "",
    db: Session = None,
    date_ref: datetime.date = None
) -> List[Dict[str, Any]]:
    """
    Analyse le texte du bilan demandé et retourne la liste des tubes nécessaires avec leurs métadonnées.
    Attribue à chaque tube son identifiant unique normalisé YYMMDDNNN (ex: 261015001).
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
    pfx = (date_ref or datetime.date.today()).strftime("%y%m%d")

    for idx, regle in enumerate(selected_rules):
        if db is not None:
            code_tube = generate_next_tube_code(db, date_ref=date_ref, offset=idx)
        else:
            code_tube = f"{pfx}{idx+1:03d}"

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
    Chaque tube reçoit son code officiel journalier YYMMDDNNN (ex: 261015001, 261015002...).
    """
    existing_tubes = db.query(EchantillonTube).filter(EchantillonTube.demande_id == demande.id).all()
    if existing_tubes and not force_recreate:
        return existing_tubes

    if existing_tubes and force_recreate:
        for t in existing_tubes:
            db.delete(t)
        db.flush()

    date_ref = demande.date_reception.date() if demande.date_reception else datetime.date.today()
    specs = determine_required_tubes(
        demande.bilan_demande,
        code_barres_base=demande.code_barres,
        db=db,
        date_ref=date_ref
    )
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
