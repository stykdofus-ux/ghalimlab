"""
Routes API pour la Validation Biologique et la saisie/modification des résultats.
"""

import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.database import get_db
from backend.app.models.core import Demande, AnalyseParameter, Resultat
from backend.app.schemas import ValidationRequest, ResultatItem

router = APIRouter(prefix="/api/validation", tags=["Validation Biologique"])


@router.post("/{demande_id}/valider")
def valider_dossier(
    demande_id: int,
    payload: ValidationRequest,
    db: Session = Depends(get_db)
):
    """
    Validation biologique officielle d'un dossier de prélèvement.
    Verrouille le statut à 'Validé' et enregistre la conclusion du biologiste.
    """
    demande = db.query(Demande).filter(Demande.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    patient = demande.patient

    # Appliquer d'éventuelles modifications manuelles sur les résultats
    if payload.resultats_modifies:
        for item in payload.resultats_modifies:
            param = db.query(AnalyseParameter).filter(AnalyseParameter.id == item.parameter_id).first()
            if not param:
                continue

            try:
                val_num = float(item.valeur.replace(',', '.'))
            except (ValueError, TypeError):
                val_num = None

            ref_min, ref_max, _ = param.get_reference_range(patient.age, patient.sexe)
            hors_norme = False
            drapeau = "NORMAL"
            if val_num is not None:
                if ref_min is not None and val_num < ref_min:
                    hors_norme = True
                    drapeau = "BAS"
                elif ref_max is not None and val_num > ref_max:
                    hors_norme = True
                    drapeau = "ELEVE"

            res = db.query(Resultat).filter(
                Resultat.demande_id == demande.id,
                Resultat.parameter_id == param.id
            ).first()

            if res:
                res.valeur = item.valeur
                res.valeur_num = val_num
                res.hors_norme = hors_norme
                res.drapeau = drapeau
                res.ref_min_applique = ref_min
                res.ref_max_applique = ref_max
                if item.automate_source:
                    res.automate_source = item.automate_source
                if item.commentaire:
                    res.commentaire = item.commentaire
            else:
                new_res = Resultat(
                    demande_id=demande.id,
                    parameter_id=param.id,
                    valeur=item.valeur,
                    valeur_num=val_num,
                    automate_source=item.automate_source or "Manuel",
                    hors_norme=hors_norme,
                    drapeau=drapeau,
                    ref_min_applique=ref_min,
                    ref_max_applique=ref_max,
                    commentaire=item.commentaire
                )
                db.add(new_res)

    from backend.app.services.billing_service import get_or_create_tarification_params
    params = get_or_create_tarification_params(db)

    demande.statut = "Validé"
    demande.date_validation = datetime.datetime.now()
    demande.valide_par = payload.valide_par or params.directeur or "Dr. M. GHALIM (Biologiste Médical)"
    if payload.conclusion_biologique:
        demande.conclusion_biologique = payload.conclusion_biologique

    db.commit()

    sig_mention = " et signé électroniquement" if params.auto_signer_validation else ""
    return {
        "status": "success",
        "message": f"Dossier {demande.code_barres} validé{sig_mention} avec succès !",
        "date_validation": demande.date_validation.strftime("%d/%m/%Y %H:%M"),
        "valide_par": demande.valide_par,
        "auto_signed": params.auto_signer_validation
    }


@router.post("/{demande_id}/devalider")
def devalider_dossier(demande_id: int, db: Session = Depends(get_db)):
    """Déverrouille un dossier pour correction."""
    demande = db.query(Demande).filter(Demande.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    demande.statut = "Résultats reçus" if demande.resultats else "En attente"
    demande.date_validation = None
    db.commit()

    return {"status": "success", "message": f"Dossier {demande.code_barres} déverrouillé."}


@router.post("/{demande_id}/ajouter-resultat")
def ajouter_resultat_manuel(
    demande_id: int,
    item: ResultatItem,
    db: Session = Depends(get_db)
):
    """Ajoute ou modifie un résultat manuellement pour une demande."""
    demande = db.query(Demande).filter(Demande.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    param = db.query(AnalyseParameter).filter(AnalyseParameter.id == item.parameter_id).first()
    if not param:
        raise HTTPException(status_code=404, detail="Paramètre d'analyse introuvable")

    patient = demande.patient
    try:
        val_num = float(item.valeur.replace(',', '.'))
    except (ValueError, TypeError):
        val_num = None

    ref_min, ref_max, _ = param.get_reference_range(patient.age, patient.sexe)
    hors_norme = False
    drapeau = "NORMAL"
    if val_num is not None:
        if ref_min is not None and val_num < ref_min:
            hors_norme = True
            drapeau = "BAS"
        elif ref_max is not None and val_num > ref_max:
            hors_norme = True
            drapeau = "ELEVE"

    res = db.query(Resultat).filter(
        Resultat.demande_id == demande.id,
        Resultat.parameter_id == param.id
    ).first()

    if res:
        res.valeur = item.valeur
        res.valeur_num = val_num
        res.automate_source = item.automate_source or "Manuel"
        res.hors_norme = hors_norme
        res.drapeau = drapeau
        res.ref_min_applique = ref_min
        res.ref_max_applique = ref_max
        res.commentaire = item.commentaire
    else:
        res = Resultat(
            demande_id=demande.id,
            parameter_id=param.id,
            valeur=item.valeur,
            valeur_num=val_num,
            automate_source=item.automate_source or "Manuel",
            hors_norme=hors_norme,
            drapeau=drapeau,
            ref_min_applique=ref_min,
            ref_max_applique=ref_max,
            commentaire=item.commentaire
        )
        db.add(res)

    if demande.statut == "En attente":
        demande.statut = "Résultats reçus"

    db.commit()

    return {"status": "success", "message": f"Résultat pour {param.nom} enregistré."}
