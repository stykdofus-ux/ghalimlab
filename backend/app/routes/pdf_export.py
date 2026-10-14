"""
Route API pour le téléchargement du compte-rendu médical au format PDF.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.core import Demande
from backend.app.services.pdf_service import generate_medical_report_pdf

router = APIRouter(prefix="/api/rapports", tags=["Comptes-Rendus PDF"])


@router.get("/{demande_id}/pdf")
def telecharger_rapport_pdf(demande_id: int, db: Session = Depends(get_db)):
    """Génère et télécharge le compte-rendu d'analyses officiel en PDF."""
    demande = db.query(Demande).filter(Demande.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    pdf_bytes = generate_medical_report_pdf(demande)

    filename = f"Rapport_Analyses_{demande.code_barres}_{demande.patient.nom}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}"
        }
    )


@router.get("/demande/{demande_id}/etiquettes/pdf")
def telecharger_etiquettes_demande_pdf(demande_id: int, db: Session = Depends(get_db)):
    """Génère et télécharge le fichier PDF des étiquettes code-barres pour tous les tubes du prélèvement."""
    from backend.app.models.core import EchantillonTube
    from backend.app.services.tube_service import generate_tubes_for_demande
    from backend.app.services.pdf_service import generate_tube_labels_pdf

    demande = db.query(Demande).filter(Demande.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    tubes = db.query(EchantillonTube).filter(EchantillonTube.demande_id == demande_id).all()
    if not tubes:
        tubes = generate_tubes_for_demande(db, demande)

    pdf_bytes = generate_tube_labels_pdf(tubes, patient=demande.patient)
    filename = f"Etiquettes_{demande.code_barres}_{demande.patient.nom}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}"
        }
    )


@router.get("/tube/{tube_id}/etiquette/pdf")
def telecharger_etiquette_tube_unique_pdf(tube_id: int, db: Session = Depends(get_db)):
    """Génère l'étiquette code-barres individuelle pour un tube spécifique."""
    from backend.app.models.core import EchantillonTube
    from backend.app.services.pdf_service import generate_tube_labels_pdf

    tube = db.query(EchantillonTube).filter(EchantillonTube.id == tube_id).first()
    if not tube:
        raise HTTPException(status_code=404, detail="Tube introuvable")

    pdf_bytes = generate_tube_labels_pdf([tube], patient=tube.demande.patient)
    filename = f"Etiquette_{tube.code_tube}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}"
        }
    )

