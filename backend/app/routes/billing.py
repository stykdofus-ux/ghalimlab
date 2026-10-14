"""
Routes API pour la Facturation, Tarification et Nomenclature des Actes de Biologie Médicale.
Gestion des 492 actes officiels, coefficients B, tarifs CNSS/CNOPS (x 1.10) et Normal/Assurances (x 1.36).
"""

import datetime
import os
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.app.config import BASE_DIR
from backend.app.database import get_db
from backend.app.models.billing import ActeBiologique, ParametreTarification, Facture, FactureLigne
from backend.app.models.core import Demande, Patient
from backend.app.schemas import (
    ActeCreate, ActeUpdate, ActeResponse,
    ParametresTarificationResponse, ParametresTarificationUpdate,
    FactureCreate, FactureUpdate, FactureResponse
)
from backend.app.services.billing_service import (
    get_or_create_tarification_params,
    recalculate_all_actes_prices,
    create_or_update_facture,
    match_actes_from_bilan_text
)
from backend.app.services.pdf_service import generate_invoice_pdf

router = APIRouter(prefix="/api/billing", tags=["Facturation & Tarification"])

BRANDING_DIR = BASE_DIR / "uploads" / "branding"
os.makedirs(BRANDING_DIR, exist_ok=True)


# ==============================================================================
# 1. PARAMÈTRES GLOBAUX DU LABORATOIRE & TARIFICATION
# ==============================================================================

@router.get("/parametres", response_model=ParametresTarificationResponse)
def get_parametres_tarification(db: Session = Depends(get_db)):
    """Retourne la configuration globale et l'identité du laboratoire."""
    return get_or_create_tarification_params(db)


@router.patch("/parametres", response_model=ParametresTarificationResponse)
@router.put("/parametres", response_model=ParametresTarificationResponse)
def update_parametres_tarification(payload: ParametresTarificationUpdate, db: Session = Depends(get_db)):
    """
    Met à jour les paramètres généraux (nom, directeur, adresse, ICE, IF, auto-signature, taux CNSS/Normal).
    Si recalculer_prix_actes est True, recalcule les prix par défaut des 492 actes.
    """
    params = get_or_create_tarification_params(db)

    old_cnss = params.taux_cnss_cnops
    old_normal = params.taux_normal_assurance

    for k, v in payload.model_dump(exclude_unset=True).items():
        if k != "recalculer_prix_actes":
            setattr(params, k, v)

    params.date_modification = datetime.datetime.now()
    db.commit()
    db.refresh(params)

    # Recalcul massif des prix si demandé ou si les multiplicateurs ont changé
    if payload.recalculer_prix_actes or (payload.taux_cnss_cnops and payload.taux_cnss_cnops != old_cnss) or (payload.taux_normal_assurance and payload.taux_normal_assurance != old_normal):
        recalculate_all_actes_prices(db, params.taux_cnss_cnops, params.taux_normal_assurance)

    return params


@router.post("/parametres/upload/{media_type}", response_model=ParametresTarificationResponse)
async def upload_branding_media(
    media_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Téléverse et configure un élément d'identité visuelle du laboratoire :
    - 'logo' : Logo officiel (SVG, PNG, JPG)
    - 'cachet' : Cachet officiel du laboratoire (PNG transparent recommandé)
    - 'signature' : Signature manuscrite électronique du biologiste (PNG transparent recommandé)
    """
    media_type = media_type.strip().lower()
    if media_type not in ["logo", "cachet", "signature"]:
        raise HTTPException(status_code=400, detail="Type de média invalide. Choisissez parmi: logo, cachet, signature.")

    filename = file.filename or "media"
    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = [".png", ".jpg", ".jpeg", ".webp"]
    if media_type == "logo":
        allowed_exts.append(".svg")

    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Format de fichier non autorisé ({ext}). Formats acceptés : {', '.join(allowed_exts)}"
        )

    # Nom de fichier sécurisé et déterministe
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_filename = f"{media_type}_{timestamp}{ext}"
    dest_path = BRANDING_DIR / dest_filename

    # Sauvegarder le fichier
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    rel_url = f"/uploads/branding/{dest_filename}"
    params = get_or_create_tarification_params(db)

    if media_type == "logo":
        params.logo_path = rel_url
    elif media_type == "cachet":
        params.cachet_path = rel_url
    elif media_type == "signature":
        params.signature_path = rel_url

    params.date_modification = datetime.datetime.now()
    db.commit()
    db.refresh(params)

    return params


# ==============================================================================
# 2. NOMENCLATURE DES ACTES DE BIOLOGIE (492 ACTES)
# ==============================================================================

@router.get("/actes", response_model=List[ActeResponse])
def get_actes_biologiques(
    search: Optional[str] = Query(None, description="Recherche code (ex: B100) ou nom"),
    categorie: Optional[str] = Query(None, description="Filtrer par catégorie"),
    actif_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Retourne la nomenclature officielle des actes de biologie médicale."""
    query = db.query(ActeBiologique)
    if actif_only:
        query = query.filter(ActeBiologique.actif == True)
    if categorie and categorie != "Toutes":
        query = query.filter(ActeBiologique.categorie == categorie)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter((ActeBiologique.code.ilike(s)) | (ActeBiologique.nom.ilike(s)))

    return query.order_by(ActeBiologique.code.asc()).offset(skip).limit(limit).all()


@router.get("/actes/code/{code}", response_model=ActeResponse)
def get_acte_by_code(code: str, db: Session = Depends(get_db)):
    """Recherche un acte biologique par son code nomenclature (ex: B100)."""
    acte = db.query(ActeBiologique).filter(ActeBiologique.code == code.strip().upper()).first()
    if not acte:
        raise HTTPException(status_code=404, detail=f"Acte avec code {code} introuvable")
    return acte


@router.get("/actes/{acte_id}", response_model=ActeResponse)
def get_acte(acte_id: int, db: Session = Depends(get_db)):
    """Détail d'un acte biologique."""
    acte = db.query(ActeBiologique).filter(ActeBiologique.id == acte_id).first()
    if not acte:
        raise HTTPException(status_code=404, detail="Acte introuvable")
    return acte


@router.post("/actes", response_model=ActeResponse, status_code=status.HTTP_201_CREATED)
def create_custom_acte(payload: ActeCreate, db: Session = Depends(get_db)):
    """Crée une nouvelle analyse / acte médical."""
    if db.query(ActeBiologique).filter(ActeBiologique.code == payload.code.strip()).first():
        raise HTTPException(status_code=400, detail=f"L'acte avec le code {payload.code} existe déjà.")

    params = get_or_create_tarification_params(db)
    p_cnss = payload.prix_cnss if payload.prix_cnss is not None else round(payload.coefficient * params.taux_cnss_cnops, 2)
    p_normal = payload.prix_normal if payload.prix_normal is not None else round(payload.coefficient * params.taux_normal_assurance, 2)

    acte = ActeBiologique(
        code=payload.code.strip().upper(),
        nom=payload.nom.strip(),
        coefficient=payload.coefficient,
        categorie=payload.categorie or "Biochimie",
        prix_cnss=p_cnss,
        prix_normal=p_normal,
        actif=payload.actif if payload.actif is not None else True
    )
    db.add(acte)
    db.commit()
    db.refresh(acte)
    return acte


@router.patch("/actes/{acte_id}", response_model=ActeResponse)
def update_acte(acte_id: int, payload: ActeUpdate, db: Session = Depends(get_db)):
    """
    Modifie le coefficient B ou les tarifs (prix CNSS / prix Normal) d'un acte biologique.
    Le biologiste peut ajuster individuellement chaque analyse.
    """
    acte = db.query(ActeBiologique).filter(ActeBiologique.id == acte_id).first()
    if not acte:
        raise HTTPException(status_code=404, detail="Acte introuvable")

    params = get_or_create_tarification_params(db)

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(acte, k, v)

    # Si le coefficient a été modifié sans préciser de prix personnalisés, recalculer automatiquement
    if payload.coefficient is not None:
        if payload.prix_cnss is None:
            acte.prix_cnss = round(acte.coefficient * params.taux_cnss_cnops, 2)
        if payload.prix_normal is None:
            acte.prix_normal = round(acte.coefficient * params.taux_normal_assurance, 2)

    acte.date_modification = datetime.datetime.now()
    db.commit()
    db.refresh(acte)
    return acte


@router.delete("/actes/{acte_id}")
def delete_acte(acte_id: int, db: Session = Depends(get_db)):
    """Désactive ou supprime un acte."""
    acte = db.query(ActeBiologique).filter(ActeBiologique.id == acte_id).first()
    if not acte:
        raise HTTPException(status_code=404, detail="Acte introuvable")

    # Désactiver plutôt que supprimer pour préserver l'historique comptable
    acte.actif = False
    db.commit()
    return {"status": "success", "message": f"Acte {acte.code} désactivé"}


# ==============================================================================
# 3. FACTURATION & ENCAISSEMENTS
# ==============================================================================

@router.get("/factures", response_model=List[FactureResponse])
def get_factures(
    statut_paiement: Optional[str] = Query(None, description="Filtrer par statut de règlement"),
    type_prise_en_charge: Optional[str] = Query(None, description="Filtrer par prise en charge"),
    search: Optional[str] = Query(None, description="Recherche N° facture, patient, CIN, prélèvement"),
    demande_id: Optional[int] = Query(None),
    patient_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Liste de toutes les factures émises."""
    query = db.query(Facture).join(Facture.patient)

    if demande_id:
        query = query.filter(Facture.demande_id == demande_id)
    if patient_id:
        query = query.filter(Facture.patient_id == patient_id)
    if statut_paiement and statut_paiement != "Tous":
        query = query.filter(Facture.statut_paiement == statut_paiement)
    if type_prise_en_charge and type_prise_en_charge != "Tous":
        query = query.filter(Facture.type_prise_en_charge == type_prise_en_charge)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (Facture.numero_facture.ilike(s)) |
            (Patient.nom.ilike(s)) |
            (Patient.prenom.ilike(s)) |
            (Patient.cin.ilike(s))
        )

    return query.order_by(Facture.date_facture.desc()).all()


@router.get("/factures/{facture_id}", response_model=FactureResponse)
def get_facture(facture_id: int, db: Session = Depends(get_db)):
    """Détail complet d'une facture médicale."""
    facture = db.query(Facture).filter(Facture.id == facture_id).first()
    if not facture:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    return facture


@router.post("/factures", response_model=FactureResponse, status_code=status.HTTP_201_CREATED)
def create_facture(payload: FactureCreate, db: Session = Depends(get_db)):
    """Établit une nouvelle facture médicale avec sélection d'actes et calculs automatiques."""
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient introuvable")

    lignes_dict = [l.model_dump() for l in (payload.lignes or [])]

    # Si aucune ligne n'a été manuellement fournie mais qu'une demande est liée, suggérer les actes selon le bilan
    if not lignes_dict and payload.demande_id:
        demande = db.query(Demande).filter(Demande.id == payload.demande_id).first()
        if demande:
            matched_actes = match_actes_from_bilan_text(demande.bilan_demande, db)
            for a in matched_actes:
                lignes_dict.append({
                    "acte_id": a.id,
                    "code_acte": a.code,
                    "nom_acte": a.nom,
                    "coefficient": a.coefficient,
                    "quantite": 1
                })

    facture = create_or_update_facture(
        db=db,
        patient_id=payload.patient_id,
        demande_id=payload.demande_id,
        type_prise_en_charge=payload.type_prise_en_charge,
        organisme_nom=payload.organisme_nom,
        numero_prise_en_charge=payload.numero_prise_en_charge,
        lignes_data=lignes_dict,
        remise_pourcent=payload.remise_pourcent or 0.0,
        montant_paye=payload.montant_paye or 0.0,
        mode_paiement=payload.mode_paiement or "Espèces",
        reference_paiement=payload.reference_paiement,
        notes=payload.notes
    )
    return facture


@router.post("/factures/auto/{demande_id}", response_model=FactureResponse)
def auto_generate_facture_from_demande(
    demande_id: int,
    type_prise_en_charge: Optional[str] = "Normal",
    montant_paye: Optional[float] = 0.0,
    db: Session = Depends(get_db)
):
    """
    Génère automatiquement la facture pour un dossier de prélèvement
    en mappant le bilan demandé vers les actes officiels de la nomenclature.
    """
    demande = db.query(Demande).filter(Demande.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    matched_actes = match_actes_from_bilan_text(demande.bilan_demande, db)
    lignes_data = [
        {
            "acte_id": a.id,
            "code_acte": a.code,
            "nom_acte": a.nom,
            "coefficient": a.coefficient,
            "quantite": 1
        }
        for a in matched_actes
    ]

    facture = create_or_update_facture(
        db=db,
        patient_id=demande.patient_id,
        demande_id=demande.id,
        type_prise_en_charge=type_prise_en_charge,
        lignes_data=lignes_data,
        montant_paye=montant_paye or 0.0
    )
    return facture


@router.patch("/factures/{facture_id}", response_model=FactureResponse)
def update_facture_paiement(facture_id: int, payload: FactureUpdate, db: Session = Depends(get_db)):
    """Enregistre un règlement ou met à jour les modalités d'une facture."""
    facture = db.query(Facture).filter(Facture.id == facture_id).first()
    if not facture:
        raise HTTPException(status_code=404, detail="Facture introuvable")

    if payload.type_prise_en_charge is not None:
        facture.type_prise_en_charge = payload.type_prise_en_charge
        params = get_or_create_tarification_params(db)
        if "cnss" in payload.type_prise_en_charge.lower() or "cnops" in payload.type_prise_en_charge.lower():
            facture.taux_applique = params.taux_cnss_cnops
        else:
            facture.taux_applique = params.taux_normal_assurance

        # Recalculer les prix unitaires des lignes
        tot_brut = 0.0
        for l in facture.lignes:
            l.prix_unitaire = round(l.coefficient * facture.taux_applique, 2)
            l.total_ligne = round(l.prix_unitaire * l.quantite, 2)
            tot_brut += l.total_ligne
        facture.montant_brut = round(tot_brut, 2)
        facture.montant_net = round(facture.montant_brut - (facture.remise_montant or 0.0), 2)

    if payload.organisme_nom is not None:
        facture.organisme_nom = payload.organisme_nom
    if payload.numero_prise_en_charge is not None:
        facture.numero_prise_en_charge = payload.numero_prise_en_charge
    if payload.notes is not None:
        facture.notes = payload.notes
    if payload.mode_paiement is not None:
        facture.mode_paiement = payload.mode_paiement
    if payload.reference_paiement is not None:
        facture.reference_paiement = payload.reference_paiement

    if payload.montant_paye is not None:
        facture.montant_paye = float(payload.montant_paye)
        facture.reste_a_payer = max(0.0, round(facture.montant_net - facture.montant_paye, 2))
        if not facture.date_paiement and facture.montant_paye > 0:
            facture.date_paiement = datetime.datetime.now()

    if payload.statut_paiement is not None:
        facture.statut_paiement = payload.statut_paiement
    else:
        # Auto-déduire le statut
        if facture.reste_a_payer <= 0 and facture.montant_net > 0:
            facture.statut_paiement = "Payé intégralement"
        elif facture.montant_paye > 0:
            facture.statut_paiement = "Avance versée"
        else:
            facture.statut_paiement = "Non payé"

    db.commit()
    db.refresh(facture)
    return facture


# ==============================================================================
# 4. ÉDITION & TÉLÉCHARGEMENT PDF DES FACTURES
# ==============================================================================

@router.get("/factures/{facture_id}/pdf")
def telecharger_facture_pdf(facture_id: int, db: Session = Depends(get_db)):
    """Génère et télécharge la facture officielle / reçu de paiement en PDF."""
    facture = db.query(Facture).filter(Facture.id == facture_id).first()
    if not facture:
        raise HTTPException(status_code=404, detail="Facture introuvable")

    pdf_bytes = generate_invoice_pdf(facture)
    nom_patient = facture.patient.nom if facture.patient else "Patient"
    filename = f"Facture_{facture.numero_facture}_{nom_patient}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}"
        }
    )
