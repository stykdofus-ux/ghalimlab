"""
Routes API pour la gestion des patients.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.database import get_db
from backend.app.models.core import Patient
from backend.app.schemas import PatientCreate, PatientResponse

router = APIRouter(prefix="/api/patients", tags=["Patients"])


@router.get("", response_model=List[PatientResponse])
def get_patients(
    search: Optional[str] = Query(None, description="Recherche par Nom, Prénom ou CIN"),
    db: Session = Depends(get_db)
):
    query = db.query(Patient)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter((Patient.nom.ilike(s)) | (Patient.prenom.ilike(s)) | (Patient.cin.ilike(s)))
    return query.order_by(Patient.nom.asc()).all()


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    return p


@router.post("", response_model=PatientResponse, status_code=201)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    # Vérifier l'unicité du CIN
    existing = db.query(Patient).filter(Patient.cin == payload.cin.strip().upper()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Un patient avec le CIN {payload.cin} existe déjà.")

    patient = Patient(
        cin=payload.cin.strip().upper(),
        nom=payload.nom.strip().upper(),
        prenom=payload.prenom.strip().capitalize(),
        date_naissance=payload.date_naissance.strip(),
        sexe=payload.sexe.strip().upper(),
        telephone=payload.telephone,
        adresse=payload.adresse,
        numero_securite_sociale=payload.numero_securite_sociale
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(patient_id: int, payload: PatientCreate, db: Session = Depends(get_db)):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient introuvable")

    p.nom = payload.nom.strip().upper()
    p.prenom = payload.prenom.strip().capitalize()
    p.date_naissance = payload.date_naissance.strip()
    p.sexe = payload.sexe.strip().upper()
    p.telephone = payload.telephone
    p.adresse = payload.adresse
    p.numero_securite_sociale = payload.numero_securite_sociale

    db.commit()
    db.refresh(p)
    return p
