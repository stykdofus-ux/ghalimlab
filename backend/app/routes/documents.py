"""
Routes API pour la gestion des documents scannés :
- Ordonnances médicales scannées par la secrétaire
- Résultats d'imagerie / scanners
- Bilans antérieurs externes
- Prises en charge assurance / CNSS
"""

import os
import uuid
import datetime
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.config import UPLOAD_DIR
from backend.app.database import get_db
from backend.app.models.core import DocumentScanne, Patient, Demande

router = APIRouter(prefix="/api/documents", tags=["Documents & Bulletins Scannés"])


@router.post("/upload", status_code=201)
async def upload_document_scanne(
    file: UploadFile = File(...),
    patient_id: int = Form(...),
    demande_id: Optional[int] = Form(None),
    titre: Optional[str] = Form(None),
    type_document: str = Form("Ordonnance"),
    notes: Optional[str] = Form(None),
    ajoute_par: str = Form("Secrétariat Médical"),
    db: Session = Depends(get_db)
):
    """
    Téléversement et enregistrement d'un document ou bulletin scanné par la secrétaire médicale.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient introuvable")

    if demande_id:
        demande = db.query(Demande).filter(Demande.id == demande_id).first()
        if not demande:
            raise HTTPException(status_code=404, detail="Demande introuvable")

    original_filename = file.filename or "document_scanne.pdf"
    file_ext = Path(original_filename).suffix.lower()
    
    # Extension autorisées
    allowed_exts = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    if file_ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté ({file_ext}). Formats autorisés : PDF, JPEG, PNG, WEBP, TIFF."
        )

    # Nom unique pour le stockage physique
    unique_suffix = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    stored_filename = f"DOC_{patient_id}_{unique_suffix}{file_ext}"
    target_path = UPLOAD_DIR / stored_filename

    # Sauvegarde sur le disque
    content = await file.read()
    file_size = len(content)

    with open(target_path, "wb") as f:
        f.write(content)

    # Titre par défaut si non spécifié
    titre_doc = titre.strip() if titre else f"{type_document} du {datetime.date.today().strftime('%d/%m/%Y')}"

    # Déterminer le mime-type
    content_type = file.content_type or "application/pdf"
    if file_ext in (".jpg", ".jpeg"):
        content_type = "image/jpeg"
    elif file_ext == ".png":
        content_type = "image/png"
    elif file_ext == ".pdf":
        content_type = "application/pdf"

    doc_record = DocumentScanne(
        patient_id=patient.id,
        demande_id=demande_id if demande_id else None,
        titre=titre_doc,
        type_document=type_document,
        nom_fichier_original=original_filename,
        nom_fichier_stocke=stored_filename,
        chemin_fichier=str(target_path),
        taille_octets=file_size,
        mime_type=content_type,
        date_televersement=datetime.datetime.now(),
        ajoute_par=ajoute_par,
        notes=notes
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    return {
        "status": "success",
        "message": f"Document '{titre_doc}' scanné et associé au patient avec succès.",
        "document": {
            "id": doc_record.id,
            "titre": doc_record.titre,
            "type_document": doc_record.type_document,
            "nom_fichier_original": doc_record.nom_fichier_original,
            "taille_ko": round(file_size / 1024, 1),
            "date_televersement": doc_record.date_televersement.strftime("%d/%m/%Y %H:%M"),
            "ajoute_par": doc_record.ajoute_par,
            "demande_id": doc_record.demande_id
        }
    }


@router.get("/patient/{patient_id}")
def get_documents_by_patient(patient_id: int, db: Session = Depends(get_db)):
    """Liste tous les documents scannés d'un patient."""
    docs = db.query(DocumentScanne).filter(DocumentScanne.patient_id == patient_id).order_by(DocumentScanne.date_televersement.desc()).all()
    return [
        {
            "id": d.id,
            "titre": d.titre,
            "type_document": d.type_document,
            "nom_fichier_original": d.nom_fichier_original,
            "taille_ko": round(d.taille_octets / 1024, 1),
            "mime_type": d.mime_type,
            "date_televersement": d.date_televersement.strftime("%d/%m/%Y %H:%M"),
            "ajoute_par": d.ajoute_par,
            "notes": d.notes,
            "demande_id": d.demande_id,
            "code_barres": d.demande.code_barres if d.demande else None,
            "url_view": f"/api/documents/{d.id}/view"
        }
        for d in docs
    ]


@router.get("/demande/{demande_id}")
def get_documents_by_demande(demande_id: int, db: Session = Depends(get_db)):
    """Récupère les documents scannés pour une demande et son patient."""
    demande = db.query(Demande).filter(Demande.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    # Documents spécifiques à la demande OU attachés globalement au patient
    docs = db.query(DocumentScanne).filter(
        (DocumentScanne.demande_id == demande_id) | (DocumentScanne.patient_id == demande.patient_id)
    ).order_by(DocumentScanne.date_televersement.desc()).all()

    return [
        {
            "id": d.id,
            "titre": d.titre,
            "type_document": d.type_document,
            "nom_fichier_original": d.nom_fichier_original,
            "taille_ko": round(d.taille_octets / 1024, 1),
            "mime_type": d.mime_type,
            "date_televersement": d.date_televersement.strftime("%d/%m/%Y %H:%M"),
            "ajoute_par": d.ajoute_par,
            "notes": d.notes,
            "est_specifique_demande": d.demande_id == demande_id,
            "url_view": f"/api/documents/{d.id}/view"
        }
        for d in docs
    ]


@router.get("/{doc_id}/view")
def visualiser_document(doc_id: int, db: Session = Depends(get_db)):
    """Visualisation en ligne du document scanné (PDF ou image) pour le biologiste ou la secrétaire."""
    doc = db.query(DocumentScanne).filter(DocumentScanne.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")

    if not os.path.exists(doc.chemin_fichier):
        raise HTTPException(status_code=404, detail="Fichier physique introuvable sur le disque.")

    return FileResponse(
        path=doc.chemin_fichier,
        media_type=doc.mime_type,
        filename=doc.nom_fichier_original,
        content_disposition_type="inline"
    )


@router.get("/{doc_id}/download")
def telecharger_document(doc_id: int, db: Session = Depends(get_db)):
    """Téléchargement du document scanné."""
    doc = db.query(DocumentScanne).filter(DocumentScanne.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")

    if not os.path.exists(doc.chemin_fichier):
        raise HTTPException(status_code=404, detail="Fichier physique introuvable sur le disque.")

    return FileResponse(
        path=doc.chemin_fichier,
        media_type=doc.mime_type,
        filename=doc.nom_fichier_original,
        content_disposition_type="attachment"
    )


@router.delete("/{doc_id}")
def supprimer_document(doc_id: int, db: Session = Depends(get_db)):
    """Suppression d'un document scanné."""
    doc = db.query(DocumentScanne).filter(DocumentScanne.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")

    # Supprimer du disque si existant
    if os.path.exists(doc.chemin_fichier):
        try:
            os.remove(doc.chemin_fichier)
        except Exception:
            pass

    db.delete(doc)
    db.commit()

    return {"status": "success", "message": "Document supprimé avec succès."}
