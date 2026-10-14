"""
Module modulaire : Bactériologie & Virologie (ECBU, Prélèvements, Antibiogrammes).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.app.database import get_db
from backend.app.models.core import Demande
from backend.app.models.bacteriology import ExamenBacteriologique, AntibiogrammeLigne
from backend.app.schemas import BacteriologieCreate

router = APIRouter(prefix="/api/bacteriologie", tags=["Bactériologie & Virologie"])


@router.get("")
def get_examens_bacteriologiques(db: Session = Depends(get_db)):
    """Liste tous les examens bactériologiques enregistrés."""
    examens = db.query(ExamenBacteriologique).all()
    results = []
    for e in examens:
        demande = db.query(Demande).filter(Demande.id == e.demande_id).first()
        results.append({
            "id": e.id,
            "demande_id": e.demande_id,
            "code_barres": demande.code_barres if demande else "N/A",
            "patient_nom": f"{demande.patient.nom} {demande.patient.prenom}" if demande and demande.patient else "N/A",
            "type_prelevement": e.type_prelevement,
            "culture_resultat": e.culture_resultat,
            "germe_identifie": e.germe_identifie,
            "numeration_colonies": e.numeration_colonies,
            "conclusion": e.conclusion,
            "date_examen": e.date_examen.strftime("%d/%m/%Y %H:%M") if e.date_examen else None,
            "nb_antibiotiques": len(e.antibiogrammes)
        })
    return results


@router.get("/{demande_id}")
def get_bacteriologie_by_demande(demande_id: int, db: Session = Depends(get_db)):
    """Récupère l'examen bactériologique et l'antibiogramme complet d'une demande."""
    examen = db.query(ExamenBacteriologique).filter(ExamenBacteriologique.demande_id == demande_id).first()
    if not examen:
        return None

    return {
        "id": examen.id,
        "demande_id": examen.demande_id,
        "type_prelevement": examen.type_prelevement,
        "aspect_macroscopique": examen.aspect_macroscopique,
        "cytologie_leucocytes": examen.cytologie_leucocytes,
        "cytologie_hematies": examen.cytologie_hematies,
        "cellules_epitheliales": examen.cellules_epitheliales,
        "coloration_gram": examen.coloration_gram,
        "culture_resultat": examen.culture_resultat,
        "germe_identifie": examen.germe_identifie,
        "numeration_colonies": examen.numeration_colonies,
        "conclusion": examen.conclusion,
        "antibiogrammes": [
            {
                "id": ab.id,
                "antibiotique_nom": ab.antibiotique_nom,
                "famille": ab.famille,
                "diametre_zone": ab.diametre_zone,
                "cmi": ab.cmi,
                "sensibilite": ab.sensibilite
            }
            for ab in examen.antibiogrammes
        ]
    }


@router.post("", status_code=201)
def create_or_update_bacteriologie(payload: BacteriologieCreate, db: Session = Depends(get_db)):
    """Crée ou met à jour l'examen bactériologique et les lignes d'antibiogramme."""
    demande = db.query(Demande).filter(Demande.id == payload.demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    examen = db.query(ExamenBacteriologique).filter(ExamenBacteriologique.demande_id == payload.demande_id).first()
    if not examen:
        examen = ExamenBacteriologique(demande_id=payload.demande_id)
        db.add(examen)
        db.flush()

    examen.type_prelevement = payload.type_prelevement
    examen.aspect_macroscopique = payload.aspect_macroscopique
    examen.cytologie_leucocytes = payload.cytologie_leucocytes
    examen.cytologie_hematies = payload.cytologie_hematies
    examen.cellules_epitheliales = payload.cellules_epitheliales
    examen.coloration_gram = payload.coloration_gram
    examen.culture_resultat = payload.culture_resultat
    examen.germe_identifie = payload.germe_identifie
    examen.numeration_colonies = payload.numeration_colonies
    examen.conclusion = payload.conclusion

    # Mettre à jour l'antibiogramme
    if payload.antibiogrammes:
        # Supprimer les anciens
        db.query(AntibiogrammeLigne).filter(AntibiogrammeLigne.examen_bact_id == examen.id).delete()
        for ab in payload.antibiogrammes:
            ligne = AntibiogrammeLigne(
                examen_bact_id=examen.id,
                antibiotique_nom=ab.antibiotique_nom,
                famille=ab.famille,
                diametre_zone=ab.diametre_zone,
                cmi=ab.cmi,
                sensibilite=ab.sensibilite
            )
            db.add(ligne)

    db.commit()
    return {"status": "success", "message": "Examen bactériologique et antibiogramme enregistrés avec succès."}
