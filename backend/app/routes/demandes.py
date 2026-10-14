"""
Routes API pour la gestion des demandes d'analyses (Ordres de prélèvement & Codes-barres).
"""

import datetime
import random
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from backend.app.database import get_db
from backend.app.models.core import Demande, Patient, AnalyseParameter, Resultat, EchantillonTube
from backend.app.schemas import DemandeCreate

router = APIRouter(prefix="/api/demandes", tags=["Demandes & Prélèvements"])


def generate_unique_barcode(db: Session) -> str:
    """Génère un code-barres unique de prélèvement au format PREL-2026-XXXX."""
    annee = datetime.date.today().year
    for _ in range(100):
        seq = random.randint(100, 9999)
        candidate = f"PREL-{annee}-{seq:04d}"
        if not db.query(Demande).filter(Demande.code_barres == candidate).first():
            return candidate
    return f"PREL-{annee}-{int(datetime.datetime.now().timestamp())}"


@router.get("")
def get_demandes(
    statut: Optional[str] = Query(None, description="Filtrer par statut: 'En attente', 'Résultats reçus', 'Validé'"),
    search: Optional[str] = Query(None, description="Recherche par code-barres, nom patient, CIN ou code tube"),
    db: Session = Depends(get_db)
):
    query = db.query(Demande).join(Demande.patient)

    if statut and statut != "Tous":
        query = query.filter(Demande.statut == statut)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (Demande.code_barres.ilike(s)) |
            (Demande.tubes.any(EchantillonTube.code_tube.ilike(s))) |
            (Patient.nom.ilike(s)) |
            (Patient.prenom.ilike(s)) |
            (Patient.cin.ilike(s))
        )

    demandes = query.order_by(Demande.date_reception.desc()).all()

    # Formater la réponse enrichie
    output = []
    for d in demandes:
        p = d.patient
        # Compter les anomalies
        nb_anomalies = sum(1 for r in d.resultats if r.hors_norme)
        nb_resultats = len(d.resultats)

        output.append({
            "id": d.id,
            "code_barres": d.code_barres,
            "date_reception": d.date_reception.strftime("%d/%m/%Y %H:%M"),
            "statut": d.statut,
            "prescripteur": d.prescripteur,
            "bilan_demande": d.bilan_demande,
            "renseignements_cliniques": d.renseignements_cliniques,
            "date_validation": d.date_validation.strftime("%d/%m/%Y %H:%M") if d.date_validation else None,
            "valide_par": d.valide_par,
            "nb_resultats": nb_resultats,
            "nb_anomalies": nb_anomalies,
            "patient": {
                "id": p.id,
                "cin": p.cin,
                "nom": p.nom,
                "prenom": p.prenom,
                "date_naissance": p.date_naissance,
                "age": p.age,
                "sexe": p.sexe,
                "telephone": p.telephone,
                "numero_securite_sociale": p.numero_securite_sociale
            }
        })

    return output


@router.get("/{demande_id}")
def get_demande_detail(demande_id: int, db: Session = Depends(get_db)):
    d = db.query(Demande).filter(Demande.id == demande_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    p = d.patient
    # Récupérer tous les paramètres disponibles pour saisie manuelle si besoin
    params_catalogue = db.query(AnalyseParameter).order_by(AnalyseParameter.ordre_affichage.asc()).all()

    resultats_list = []
    for r in d.resultats:
        param = r.parametre
        ref_min, ref_max, label_ref = (r.ref_min_applique, r.ref_max_applique, "")
        if ref_min is None and param:
            ref_min, ref_max, label_ref = param.get_reference_range(p.age, p.sexe)

        resultats_list.append({
            "id": r.id,
            "parameter_id": r.parameter_id,
            "code": param.code if param else "N/A",
            "nom": param.nom if param else "Paramètre",
            "categorie": param.categorie if param else "Général",
            "unite": param.unite if param else "",
            "valeur": r.valeur,
            "valeur_num": r.valeur_num,
            "automate_source": r.automate_source,
            "hors_norme": r.hors_norme,
            "drapeau": r.drapeau,  # 'NORMAL', 'ELEVE', 'BAS'
            "ref_min": ref_min,
            "ref_max": ref_max,
            "ref_label": label_ref,
            "date_analyse": r.date_analyse.strftime("%d/%m/%Y %H:%M") if r.date_analyse else None,
            "commentaire": r.commentaire
        })

    return {
        "id": d.id,
        "code_barres": d.code_barres,
        "date_reception": d.date_reception.strftime("%d/%m/%Y %H:%M"),
        "statut": d.statut,
        "prescripteur": d.prescripteur,
        "bilan_demande": d.bilan_demande,
        "renseignements_cliniques": d.renseignements_cliniques,
        "conclusion_biologique": d.conclusion_biologique,
        "date_validation": d.date_validation.strftime("%d/%m/%Y %H:%M") if d.date_validation else None,
        "valide_par": d.valide_par,
        "patient": {
            "id": p.id,
            "cin": p.cin,
            "nom": p.nom,
            "prenom": p.prenom,
            "date_naissance": p.date_naissance,
            "age": p.age,
            "sexe": p.sexe,
            "telephone": p.telephone,
            "adresse": p.adresse,
            "numero_securite_sociale": p.numero_securite_sociale
        },
        "resultats": resultats_list,
        "tubes": [
            {
                "id": t.id,
                "code_tube": t.code_tube,
                "type_tube": t.type_tube,
                "couleur_bouchon": t.couleur_bouchon,
                "analyses_associees": t.analyses_associees,
                "volume_ml": t.volume_ml,
                "statut_tube": t.statut_tube,
                "conformite_preanalytique": t.conformite_preanalytique,
                "emplacement_serotheque": t.emplacement_serotheque
            }
            for t in d.tubes
        ],
        "catalogue_parametres": [
            {
                "id": cp.id,
                "code": cp.code,
                "nom": cp.nom,
                "categorie": cp.categorie,
                "unite": cp.unite
            }
            for cp in params_catalogue
        ]
    }


@router.post("", status_code=201)
def create_demande(payload: DemandeCreate, db: Session = Depends(get_db)):
    from backend.app.services.tube_service import generate_tubes_for_demande

    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient introuvable")

    barcode = payload.code_barres.strip() if payload.code_barres else generate_unique_barcode(db)

    # Vérifier l'unicité
    if db.query(Demande).filter(Demande.code_barres == barcode).first():
        raise HTTPException(status_code=400, detail=f"Le code-barres {barcode} est déjà utilisé.")

    demande = Demande(
        code_barres=barcode,
        patient_id=patient.id,
        date_reception=datetime.datetime.now(),
        statut="En attente",
        prescripteur=payload.prescripteur or "Dr. Externe",
        renseignements_cliniques=payload.renseignements_cliniques,
        bilan_demande=payload.bilan_demande or "NFS, Bilan Métabolique"
    )
    db.add(demande)
    db.commit()
    db.refresh(demande)

    # Génération automatique des tubes pré-analytiques selon le bilan
    tubes = generate_tubes_for_demande(db, demande)

    return {
        "id": demande.id,
        "code_barres": demande.code_barres,
        "statut": demande.statut,
        "nb_tubes": len(tubes),
        "tubes": [
            {
                "id": t.id,
                "code_tube": t.code_tube,
                "type_tube": t.type_tube,
                "couleur_bouchon": t.couleur_bouchon,
                "analyses": t.analyses_associees
            }
            for t in tubes
        ],
        "message": f"Dossier de prélèvement {barcode} créé avec succès ({len(tubes)} tubes générés) !"
    }

