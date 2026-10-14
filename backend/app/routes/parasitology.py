"""
Module modulaire : Parasitologie & Mycologie (EPS, Frottis, Cultures mycologiques).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.app.database import get_db
from backend.app.models.core import Demande
from backend.app.models.parasitology import ExamenParasitologique
from backend.app.schemas import ParasitologieCreate

router = APIRouter(prefix="/api/parasitologie", tags=["Parasitologie & Mycologie"])


@router.get("")
def get_examens_parasitologiques(db: Session = Depends(get_db)):
    """Liste tous les examens parasitologiques et mycologiques."""
    examens = db.query(ExamenParasitologique).all()
    results = []
    for e in examens:
        demande = db.query(Demande).filter(Demande.id == e.demande_id).first()
        results.append({
            "id": e.id,
            "demande_id": e.demande_id,
            "code_barres": demande.code_barres if demande else "N/A",
            "patient_nom": f"{demande.patient.nom} {demande.patient.prenom}" if demande and demande.patient else "N/A",
            "type_analyse": e.type_analyse,
            "consistance": e.consistance,
            "aspect_couleur": e.aspect_couleur,
            "parasite_identifie": e.parasite_identifie,
            "recherche_mycologique": e.recherche_mycologique,
            "conclusion": e.conclusion,
            "date_examen": e.date_examen.strftime("%d/%m/%Y %H:%M") if e.date_examen else None
        })
    return results


@router.get("/{demande_id}")
def get_parasitologie_by_demande(demande_id: int, db: Session = Depends(get_db)):
    examen = db.query(ExamenParasitologique).filter(ExamenParasitologique.demande_id == demande_id).first()
    if not examen:
        return None

    return {
        "id": examen.id,
        "demande_id": examen.demande_id,
        "type_analyse": examen.type_analyse,
        "consistance": examen.consistance,
        "aspect_couleur": examen.aspect_couleur,
        "examen_direct": examen.examen_direct,
        "technique_concentration": examen.technique_concentration,
        "parasite_identifie": examen.parasite_identifie,
        "frottis_goutte_epaisse": examen.frottis_goutte_epaisse,
        "recherche_mycologique": examen.recherche_mycologique,
        "culture_sabouraud": examen.culture_sabouraud,
        "conclusion": examen.conclusion
    }


@router.post("", status_code=201)
def create_or_update_parasitologie(payload: ParasitologieCreate, db: Session = Depends(get_db)):
    demande = db.query(Demande).filter(Demande.id == payload.demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    examen = db.query(ExamenParasitologique).filter(ExamenParasitologique.demande_id == payload.demande_id).first()
    if not examen:
        examen = ExamenParasitologique(demande_id=payload.demande_id)
        db.add(examen)

    examen.type_analyse = payload.type_analyse
    examen.consistance = payload.consistance
    examen.aspect_couleur = payload.aspect_couleur
    examen.examen_direct = payload.examen_direct
    examen.technique_concentration = payload.technique_concentration
    examen.parasite_identifie = payload.parasite_identifie
    examen.frottis_goutte_epaisse = payload.frottis_goutte_epaisse
    examen.recherche_mycologique = payload.recherche_mycologique
    examen.culture_sabouraud = payload.culture_sabouraud
    examen.conclusion = payload.conclusion

    db.commit()
    return {"status": "success", "message": "Examen parasitologique/mycologique enregistré avec succès."}
