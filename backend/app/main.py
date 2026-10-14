"""
Application Web Principale GhalimLab LIMS
FastAPI + Jinja2 + Moteur d'intégration automates ASTM E1381/E1394
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.app.config import BASE_DIR, LABO_NOM, LABO_DIRECTEUR, ASTM_PORT
from backend.app.database import engine, Base, SessionLocal, get_db
from backend.app.services.seed_data import seed_database
import backend.app.models
from backend.app.models.core import Patient, Demande, AnalyseParameter, Resultat, AutomateLog, DocumentScanne, EchantillonTube
from backend.app.models.billing import ActeBiologique, ParametreTarification, Facture, FactureLigne

# Routers
from backend.app.routes.patients import router as patients_router
from backend.app.routes.demandes import router as demandes_router
from backend.app.routes.validation import router as validation_router
from backend.app.routes.automates import router as automates_router
from backend.app.routes.bacteriology import router as bacteriology_router
from backend.app.routes.parasitology import router as parasitology_router
from backend.app.routes.pdf_export import router as pdf_router
from backend.app.routes.documents import router as documents_router
from backend.app.routes.tubes import router as tubes_router
from backend.app.routes.billing import router as billing_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.app.database import ensure_db_schema_up_to_date
    # Initialisation des tables de base de données
    Base.metadata.create_all(bind=engine)
    ensure_db_schema_up_to_date(engine)
    # Peuplement du catalogue et des données de démo
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="GhalimLab LIMS",
    description="Application de Gestion de Laboratoire d'Analyses Médicales avec intégration automates ASTM/HL7",
    version="1.0.0",
    lifespan=lifespan
)

# Montage des fichiers statiques, médias téléversés et templates
static_path = BASE_DIR / "frontend" / "static"
uploads_path = BASE_DIR / "uploads"
templates_path = BASE_DIR / "frontend" / "templates"

os.makedirs(uploads_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")
templates = Jinja2Templates(directory=str(templates_path))


def render_page(request: Request, template_name: str, context: dict = None):
    """Encapsule TemplateResponse en garantissant la compatibilité et l'injection dynamique des paramètres du laboratoire."""
    ctx = context or {}
    try:
        from backend.app.services.billing_service import get_or_create_tarification_params
        _db = SessionLocal()
        _params = get_or_create_tarification_params(_db)
        _db.close()
        ctx.setdefault("labo_nom", _params.nom_laboratoire or LABO_NOM)
        ctx.setdefault("labo_directeur", _params.directeur or LABO_DIRECTEUR)
        ctx.setdefault("labo_adresse", _params.adresse or LABO_ADRESSE)
        ctx.setdefault("labo_tel", _params.telephone or LABO_TEL)
        ctx.setdefault("labo_email", _params.email or LABO_EMAIL)
        ctx.setdefault("labo_logo", _params.logo_path or "/uploads/branding/logo.svg")
        ctx.setdefault("lab_params", _params)
    except Exception:
        ctx.setdefault("labo_nom", LABO_NOM)
        ctx.setdefault("labo_directeur", LABO_DIRECTEUR)
        ctx.setdefault("labo_adresse", LABO_ADRESSE)
        ctx.setdefault("labo_tel", LABO_TEL)
        ctx.setdefault("labo_email", LABO_EMAIL)
        ctx.setdefault("labo_logo", "/uploads/branding/logo.svg")

    ctx.setdefault("astm_port", ASTM_PORT)
    return templates.TemplateResponse(request=request, name=template_name, context=ctx)


# Inclusion des routes API
app.include_router(patients_router)
app.include_router(demandes_router)
app.include_router(validation_router)
app.include_router(automates_router)
app.include_router(bacteriology_router)
app.include_router(parasitology_router)
app.include_router(pdf_router)
app.include_router(documents_router)
app.include_router(tubes_router)
app.include_router(billing_router)


# ==============================================================================
# PAGES WEB (RENDU HTML JINJA2)
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
def page_dashboard(request: Request, db: Session = Depends(get_db)):
    """Tableau de bord de synthèse du laboratoire."""
    total_demandes = db.query(Demande).count()
    en_attente = db.query(Demande).filter(Demande.statut == "En attente").count()
    recus = db.query(Demande).filter(Demande.statut == "Résultats reçus").count()
    valides = db.query(Demande).filter(Demande.statut == "Validé").count()
    total_patients = db.query(Patient).count()
    from backend.app.models.core import DocumentScanne, EchantillonTube
    from backend.app.models.billing import Facture, ActeBiologique
    total_documents = db.query(DocumentScanne).count()
    total_tubes = db.query(EchantillonTube).count()
    total_factures = db.query(Facture).count()
    total_actes = db.query(ActeBiologique).count()

    from sqlalchemy import func
    total_recettes = db.query(func.sum(Facture.montant_paye)).scalar() or 0.0
    total_impayes = db.query(func.sum(Facture.reste_a_payer)).scalar() or 0.0

    recentes_demandes = db.query(Demande).order_by(Demande.date_reception.desc()).limit(8).all()
    recent_logs = db.query(AutomateLog).order_by(AutomateLog.timestamp.desc()).limit(5).all()

    return render_page(request, "dashboard.html", {
        "stats": {
            "total_demandes": total_demandes,
            "en_attente": en_attente,
            "recus": recus,
            "valides": valides,
            "total_patients": total_patients,
            "total_documents": total_documents,
            "total_tubes": total_tubes,
            "total_factures": total_factures,
            "total_actes": total_actes,
            "total_recettes": round(total_recettes, 2),
            "total_impayes": round(total_impayes, 2)
        },
        "recentes_demandes": recentes_demandes,
        "recent_logs": recent_logs
    })


@app.get("/worklist", response_class=HTMLResponse)
def page_worklist(request: Request, statut: str = "Tous", search: str = "", db: Session = Depends(get_db)):
    """Liste de travail technique des prélèvements."""
    query = db.query(Demande).join(Demande.patient)
    if statut and statut != "Tous":
        query = query.filter(Demande.statut == statut)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (Demande.code_barres.ilike(s)) |
            (Patient.nom.ilike(s)) |
            (Patient.prenom.ilike(s)) |
            (Patient.cin.ilike(s))
        )

    demandes = query.order_by(Demande.date_reception.desc()).all()

    return render_page(request, "worklist.html", {
        "demandes": demandes,
        "statut_actif": statut,
        "search_term": search
    })


@app.get("/demande/nouvelle", response_class=HTMLResponse)
def page_nouvelle_demande(request: Request, db: Session = Depends(get_db)):
    """Formulaire de saisie d'un nouveau patient / prélèvement avec code-barres."""
    patients = db.query(Patient).order_by(Patient.nom.asc()).all()
    return render_page(request, "new_demande.html", {
        "patients": patients
    })


@app.get("/validation/{demande_id}", response_class=HTMLResponse)
def page_validation_dossier(demande_id: int, request: Request, db: Session = Depends(get_db)):
    """Écran complet de validation technique et biologique."""
    demande = db.query(Demande).filter(Demande.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    params_catalogue = db.query(AnalyseParameter).order_by(AnalyseParameter.ordre_affichage.asc()).all()

    return render_page(request, "validation_dossier.html", {
        "demande": demande,
        "catalogue": params_catalogue
    })


@app.get("/automates", response_class=HTMLResponse)
def page_automates(request: Request, db: Session = Depends(get_db)):
    """Console de supervision et test des automates ASTM."""
    logs = db.query(AutomateLog).order_by(AutomateLog.timestamp.desc()).limit(20).all()
    demandes_attente = db.query(Demande).filter(Demande.statut.in_(["En attente", "Résultats reçus"])).all()

    return render_page(request, "automates_monitor.html", {
        "logs": logs,
        "demandes": demandes_attente
    })


@app.get("/bacteriologie", response_class=HTMLResponse)
def page_bacteriologie(request: Request, db: Session = Depends(get_db)):
    """Module spécialisé Bactériologie & Antibiogrammes."""
    demandes = db.query(Demande).order_by(Demande.date_reception.desc()).limit(30).all()
    return render_page(request, "bacteriology.html", {
        "demandes": demandes
    })


@app.get("/parasitologie", response_class=HTMLResponse)
def page_parasitologie(request: Request, db: Session = Depends(get_db)):
    """Module spécialisé Parasitologie & Mycologie."""
    demandes = db.query(Demande).order_by(Demande.date_reception.desc()).limit(30).all()
    return render_page(request, "parasitology.html", {
        "demandes": demandes
    })


@app.get("/patients-annuaire", response_class=HTMLResponse)
def page_patients(request: Request, db: Session = Depends(get_db)):
    """Annuaire général des patients."""
    patients = db.query(Patient).order_by(Patient.nom.asc()).all()
    return render_page(request, "patients_list.html", {
        "patients": patients
    })


@app.get("/patient/{patient_id}", response_class=HTMLResponse)
def page_patient_detail(patient_id: int, request: Request, db: Session = Depends(get_db)):
    """Dossier complet du patient avec antécédents, prélèvements et documents scannés."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient introuvable")

    from backend.app.models.core import DocumentScanne
    docs = db.query(DocumentScanne).filter(DocumentScanne.patient_id == patient_id).order_by(DocumentScanne.date_televersement.desc()).all()
    demandes = db.query(Demande).filter(Demande.patient_id == patient_id).order_by(Demande.date_reception.desc()).all()

    return render_page(request, "patient_detail.html", {
        "patient": patient,
        "demandes": demandes,
        "documents": docs
    })


@app.get("/echantillons-serotheque", response_class=HTMLResponse)
def page_echantillons_serotheque(
    request: Request,
    statut: str = "Tous",
    conformite: str = "Tous",
    search: str = "",
    db: Session = Depends(get_db)
):
    """Console de gestion pré-analytique des tubes d'échantillons et sérothèque."""
    from backend.app.models.core import EchantillonTube
    query = db.query(EchantillonTube).join(EchantillonTube.demande).join(Demande.patient)

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

    tubes = query.order_by(EchantillonTube.date_creation.desc()).all()

    # Statistiques globales
    total_tubes = db.query(EchantillonTube).count()
    en_attente_prelevement = db.query(EchantillonTube).filter(EchantillonTube.statut_tube == "Non prélevé").count()
    en_cours_plateau = db.query(EchantillonTube).filter(
        EchantillonTube.statut_tube.in_(["Prélevé", "Reçu au Laboratoire", "Centrifugé", "En cours sur automate"])
    ).count()
    archives_serotheque = db.query(EchantillonTube).filter(EchantillonTube.statut_tube == "Archivé en sérothèque").count()
    non_conformes = db.query(EchantillonTube).filter(
        (EchantillonTube.conformite_preanalytique != "Conforme") | (EchantillonTube.statut_tube == "Rejeté / Hémolysé")
    ).count()

    return render_page(request, "serotheque_tubes.html", {
        "tubes": tubes,
        "statut_actif": statut,
        "conformite_actif": conformite,
        "search_term": search,
        "stats": {
            "total": total_tubes,
            "attente": en_attente_prelevement,
            "plateau": en_cours_plateau,
            "serotheque": archives_serotheque,
            "non_conformes": non_conformes
        }
    })


@app.get("/facturation", response_class=HTMLResponse)
def page_facturation(
    request: Request,
    statut: str = "Tous",
    prise_en_charge: str = "Tous",
    search: str = "",
    db: Session = Depends(get_db)
):
    """Console de facturation, suivi des règlements et caisse."""
    from backend.app.models.billing import Facture
    from sqlalchemy import func

    query = db.query(Facture).join(Facture.patient)

    if statut and statut != "Tous":
        query = query.filter(Facture.statut_paiement == statut)

    if prise_en_charge and prise_en_charge != "Tous":
        query = query.filter(Facture.type_prise_en_charge == prise_en_charge)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (Facture.numero_facture.ilike(s)) |
            (Patient.nom.ilike(s)) |
            (Patient.prenom.ilike(s)) |
            (Patient.cin.ilike(s))
        )

    factures = query.order_by(Facture.date_facture.desc()).all()

    # Statistiques financières globales
    total_factures = db.query(Facture).count()
    recettes_total = db.query(func.sum(Facture.montant_paye)).scalar() or 0.0
    impayes_total = db.query(func.sum(Facture.reste_a_payer)).scalar() or 0.0
    tiers_payant_total = db.query(func.sum(Facture.part_organisme)).scalar() or 0.0

    nb_paye = db.query(Facture).filter(Facture.statut_paiement == "Payé intégralement").count()
    nb_avance = db.query(Facture).filter(Facture.statut_paiement == "Avance versée").count()
    nb_non_paye = db.query(Facture).filter(Facture.statut_paiement == "Non payé").count()

    # Demandes récentes sans facture pour proposition de facturation rapide
    demandes_sans_facture = db.query(Demande).outerjoin(Demande.factures).filter(Facture.id == None).limit(10).all()

    return render_page(request, "billing_dashboard.html", {
        "factures": factures,
        "demandes_sans_facture": demandes_sans_facture,
        "statut_actif": statut,
        "prise_en_charge_actif": prise_en_charge,
        "search_term": search,
        "stats": {
            "total_factures": total_factures,
            "recettes": round(recettes_total, 2),
            "impayes": round(impayes_total, 2),
            "tiers_payant": round(tiers_payant_total, 2),
            "nb_paye": nb_paye,
            "nb_avance": nb_avance,
            "nb_non_paye": nb_non_paye
        }
    })


@app.get("/parametres", response_class=HTMLResponse)
@app.get("/parametres-tarifs", response_class=HTMLResponse)
def page_parametres_laboratoire(
    request: Request,
    tab: str = "identite",
    categorie: str = "Toutes",
    search: str = "",
    db: Session = Depends(get_db)
):
    """Page complète de paramétrage du laboratoire : identité, mentions légales, branding & nomenclature."""
    from backend.app.models.billing import ActeBiologique, ParametreTarification
    from backend.app.services.billing_service import get_or_create_tarification_params

    params = get_or_create_tarification_params(db)

    # Si l'URL demandée est /parametres-tarifs sans onglet précisé, ouvrir directement l'onglet nomenclature
    if request.url.path == "/parametres-tarifs" and tab == "identite":
        tab = "tarifs"

    query = db.query(ActeBiologique).filter(ActeBiologique.actif == True)

    if categorie and categorie != "Toutes":
        query = query.filter(ActeBiologique.categorie == categorie)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter((ActeBiologique.code.ilike(s)) | (ActeBiologique.nom.ilike(s)))

    actes = query.order_by(ActeBiologique.code.asc()).all()
    categories = [r[0] for r in db.query(ActeBiologique.categorie).distinct().all() if r[0]]

    return render_page(request, "billing_settings.html", {
        "actes": actes,
        "params": params,
        "tab_actif": tab,
        "categories": categories,
        "categorie_actif": categorie,
        "search_term": search,
        "total_actes": db.query(ActeBiologique).count()
    })


