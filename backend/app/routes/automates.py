"""
Routes API pour la supervision et la simulation des automates de laboratoire (ASTM).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from backend.app.database import get_db
from backend.app.models.core import AutomateLog, Demande
from backend.astm.server import server_stats
from backend.astm.simulator import generate_sysmex_records, generate_cobas_records, send_astm_simulation
from backend.app.config import ASTM_PORT, ASTM_HOST

router = APIRouter(prefix="/api/automates", tags=["Automates & ASTM"])


class SimulationRequest(BaseModel):
    automate: str = "sysmex"  # 'sysmex' ou 'cobas'
    code_barres: str = "PREL-2026-002"
    port: Optional[int] = None


@router.get("/status")
def get_automate_status():
    """Retourne l'état de fonctionnement du serveur d'écoute ASTM et les statistiques."""
    return {
        "status": "Actif" if server_stats.get("is_running") else "Inactif",
        "host": server_stats.get("host", ASTM_HOST),
        "port": server_stats.get("port", ASTM_PORT),
        "total_connections": server_stats.get("total_connections", 0),
        "total_messages": server_stats.get("total_messages", 0),
        "total_frames_received": server_stats.get("total_frames_received", 0),
        "last_connection_time": server_stats.get("last_connection_time"),
        "last_automate": server_stats.get("last_automate"),
        "recent_logs": server_stats.get("recent_logs", [])[:20]
    }


@router.get("/logs")
def get_automate_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Retourne l'historique d'audit des réceptions d'automates enregistrées en base."""
    logs = db.query(AutomateLog).order_by(AutomateLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "timestamp": l.timestamp.strftime("%d/%m/%Y %H:%M:%S"),
            "automate_nom": l.automate_nom,
            "code_barres_detecte": l.code_barres_detecte,
            "nb_resultats_reçus": l.nb_resultats_reçus,
            "statut": l.statut,
            "details": l.details
        }
        for l in logs
    ]


@router.post("/simulate")
def simulate_automate_transmission(payload: SimulationRequest, db: Session = Depends(get_db)):
    """
    Déclenche une simulation réelle d'envoi de trames ASTM E1381/E1394
    via le socket TCP/IP local pour alimenter un prélèvement.
    """
    demande = db.query(Demande).filter(Demande.code_barres == payload.code_barres.strip()).first()
    if not demande:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune demande trouvée avec le code-barres '{payload.code_barres}'."
        )

    patient = demande.patient
    pat_name = f"{patient.nom}^{patient.prenom}"
    sexe = patient.sexe

    port_to_use = payload.port or ASTM_PORT

    if payload.automate.lower() == "sysmex":
        records = generate_sysmex_records(
            barcode=demande.code_barres,
            patient_name=pat_name,
            sexe=sexe
        )
    elif payload.automate.lower() == "cobas":
        records = generate_cobas_records(
            barcode=demande.code_barres,
            patient_name=pat_name,
            sexe=sexe
        )
    else:
        raise HTTPException(status_code=400, detail="Automate non reconnu (choisir 'sysmex' ou 'cobas').")

    # Exécution de la transmission socket
    result = send_astm_simulation(records, port=port_to_use)

    return {
        "status": "success" if result["success"] else "error",
        "automate": payload.automate.upper(),
        "code_barres": demande.code_barres,
        "frames_envoyees": result.get("frames_sent", 0),
        "transmission_logs": result.get("logs", []),
        "error": result.get("error")
    }
