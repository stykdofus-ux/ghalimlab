"""
Routes API pour la traçabilité des tubes d'échantillons, la gestion pré-analytique
et l'archivage en sérothèque.
"""

import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.core import EchantillonTube, Demande, Patient
from backend.app.schemas import TubeCreate, TubeUpdate, TubeResponse
from backend.app.services.tube_service import generate_tubes_for_demande, generate_next_tube_code

router = APIRouter(prefix="/api/tubes", tags=["Traçabilité Tubes & Sérothèque"])


@router.get("", response_model=List[TubeResponse])
def get_all_tubes(
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    conformite: Optional[str] = Query(None, description="Filtrer par conformité"),
    demande_id: Optional[int] = Query(None, description="Filtrer par demande ID"),
    search: Optional[str] = Query(None, description="Recherche code tube, code prélèvement, patient"),
    db: Session = Depends(get_db)
):
    """Retourne la liste des tubes d'échantillons avec filtres."""
    query = db.query(EchantillonTube).join(EchantillonTube.demande).join(Demande.patient)

    if demande_id:
        query = query.filter(EchantillonTube.demande_id == demande_id)

    if statut and statut != "Tous":
        query = query.filter(EchantillonTube.statut_tube == statut)

    if conformite and conformite != "Tous":
        query = query.filter(EchantillonTube.conformite_preanalytique == conformite)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (EchantillonTube.code_tube.ilike(s)) |
            (Demande.code_barres.ilike(s)) |
            (Patient.nom.ilike(s)) |
            (Patient.prenom.ilike(s)) |
            (Patient.cin.ilike(s))
        )

    return query.order_by(EchantillonTube.date_creation.desc()).all()


@router.get("/{tube_id}", response_model=TubeResponse)
def get_tube(tube_id: int, db: Session = Depends(get_db)):
    """Détail d'un tube d'échantillon."""
    tube = db.query(EchantillonTube).filter(EchantillonTube.id == tube_id).first()
    if not tube:
        raise HTTPException(status_code=404, detail="Tube introuvable")
    return tube


@router.post("/demande/{demande_id}/generer", response_model=List[TubeResponse])
def generer_tubes_demande(demande_id: int, db: Session = Depends(get_db)):
    """Génère automatiquement les tubes requis pour une demande selon le bilan prescrit."""
    demande = db.query(Demande).filter(Demande.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    tubes = generate_tubes_for_demande(db, demande)
    return tubes


@router.post("", response_model=TubeResponse, status_code=status.HTTP_201_CREATED)
def create_custom_tube(payload: TubeCreate, db: Session = Depends(get_db)):
    """Ajoute manuellement un tube pour un prélèvement."""
    demande = db.query(Demande).filter(Demande.id == payload.demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    code_tube = payload.code_tube
    if not code_tube:
        code_tube = generate_next_tube_code(db)

    # Vérifier l'unicité
    if db.query(EchantillonTube).filter(EchantillonTube.code_tube == code_tube).first():
        raise HTTPException(status_code=400, detail="Ce code-barres de tube existe déjà.")

    tube = EchantillonTube(
        demande_id=demande.id,
        code_tube=code_tube,
        type_tube=payload.type_tube,
        couleur_bouchon=payload.couleur_bouchon,
        analyses_associees=payload.analyses_associees,
        volume_ml=payload.volume_ml,
        statut_tube="Non prélevé",
        conformite_preanalytique="Conforme",
        date_creation=datetime.datetime.now()
    )
    db.add(tube)
    db.commit()
    db.refresh(tube)
    return tube


@router.patch("/{tube_id}", response_model=TubeResponse)
def update_tube(tube_id: int, payload: TubeUpdate, db: Session = Depends(get_db)):
    """Met à jour les données de traçabilité d'un tube."""
    tube = db.query(EchantillonTube).filter(EchantillonTube.id == tube_id).first()
    if not tube:
        raise HTTPException(status_code=404, detail="Tube introuvable")

    now = datetime.datetime.now()

    if payload.statut_tube is not None:
        tube.statut_tube = payload.statut_tube
        if payload.statut_tube == "Prélevé" and not tube.date_prelevement:
            tube.date_prelevement = now
        elif payload.statut_tube == "Reçu au Laboratoire" and not tube.date_reception_labo:
            tube.date_reception_labo = now
        elif payload.statut_tube == "Archivé en sérothèque" and not tube.date_archivage:
            tube.date_archivage = now

    if payload.preleve_par is not None:
        tube.preleve_par = payload.preleve_par
    if payload.receptionne_par is not None:
        tube.receptionne_par = payload.receptionne_par
    if payload.conformite_preanalytique is not None:
        tube.conformite_preanalytique = payload.conformite_preanalytique
    if payload.emplacement_serotheque is not None:
        tube.emplacement_serotheque = payload.emplacement_serotheque
        if payload.emplacement_serotheque and tube.statut_tube != "Archivé en sérothèque":
            tube.statut_tube = "Archivé en sérothèque"
            tube.date_archivage = now
    if payload.remarques is not None:
        tube.remarques = payload.remarques

    db.commit()
    db.refresh(tube)
    return tube


@router.post("/{tube_id}/action/{action_name}", response_model=TubeResponse)
def execute_tube_action(tube_id: int, action_name: str, operateur: Optional[str] = "Équipe Laboratoire", db: Session = Depends(get_db)):
    """
    Raccourci pour avancer d'un clic dans la chaîne de traçabilité :
    - 'prelever' -> 'Prélevé'
    - 'receptionner' -> 'Reçu au Laboratoire'
    - 'centrifuger' -> 'Centrifugé'
    - 'automate' -> 'En cours sur automate'
    - 'analyser' -> 'Analysé'
    - 'rejeter' -> 'Rejeté / Hémolysé'
    """
    tube = db.query(EchantillonTube).filter(EchantillonTube.id == tube_id).first()
    if not tube:
        raise HTTPException(status_code=404, detail="Tube introuvable")

    now = datetime.datetime.now()

    if action_name == "prelever":
        tube.statut_tube = "Prélevé"
        tube.date_prelevement = now
        tube.preleve_par = operateur
    elif action_name == "receptionner":
        tube.statut_tube = "Reçu au Laboratoire"
        tube.date_reception_labo = now
        tube.receptionne_par = operateur
    elif action_name == "centrifuger":
        tube.statut_tube = "Centrifugé"
    elif action_name == "automate":
        tube.statut_tube = "En cours sur automate"
    elif action_name == "analyser":
        tube.statut_tube = "Analysé"
    elif action_name == "rejeter":
        tube.statut_tube = "Rejeté / Hémolysé"
        tube.conformite_preanalytique = "Hémolysé / Non-conforme"
    else:
        raise HTTPException(status_code=400, detail=f"Action inconnue: {action_name}")

    db.commit()
    db.refresh(tube)
    return tube


@router.delete("/{tube_id}")
def delete_tube(tube_id: int, db: Session = Depends(get_db)):
    """Supprime un tube."""
    tube = db.query(EchantillonTube).filter(EchantillonTube.id == tube_id).first()
    if not tube:
        raise HTTPException(status_code=404, detail="Tube introuvable")

    db.delete(tube)
    db.commit()
    return {"status": "success", "message": f"Tube {tube.code_tube} supprimé"}
