"""
Tests d'intégration end-to-end pour GhalimLab LIMS :
- Création Patient & Demande
- Ingestion ASTM E1394
- Évaluation biologique des bornes de référence
- Validation Biologique
- Génération de Rapport PDF
- Module Bactériologie & Antibiogramme
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal, Base, engine
from backend.app.services.seed_data import seed_database
from backend.app.services.pdf_service import generate_medical_report_pdf
from backend.app.models.core import Demande, Patient

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_database(db)
    db.close()
    yield


def test_api_patients_list():
    response = client.get("/api/patients")
    assert response.status_code == 200
    patients = response.json()
    assert len(patients) >= 3
    # Vérifier la présence du patient témoin
    cins = [p["cin"] for p in patients]
    assert "BK123456" in cins


def test_api_create_patient():
    import random
    cin_val = f"TEST{random.randint(10000, 99999)}"
    new_patient = {
        "cin": cin_val,
        "nom": "KADIRI",
        "prenom": "Mehdi",
        "date_naissance": "1995-07-20",
        "sexe": "M",
        "telephone": "+212 6 00 11 22 33",
        "adresse": "Rabat",
        "numero_securite_sociale": "19507209999"
    }
    response = client.post("/api/patients", json=new_patient)
    assert response.status_code == 201
    data = response.json()
    assert data["cin"] == cin_val
    assert data["nom"] == "KADIRI"
    assert data["age"] > 20


def test_api_create_demande_with_barcode():
    # Récupérer un patient existant
    pat_resp = client.get("/api/patients")
    pat_id = pat_resp.json()[0]["id"]

    new_demande = {
        "patient_id": pat_id,
        "prescripteur": "Dr. TEST",
        "bilan_demande": "NFS, Glycémie",
        "renseignements_cliniques": "Test unitaire automatisé"
    }
    response = client.post("/api/demandes", json=new_demande)
    assert response.status_code == 201
    data = response.json()
    assert "code_barres" in data
    assert data["code_barres"].startswith("PREL-")


def test_api_validation_and_pdf_generation():
    db = SessionLocal()
    # Récupérer la demande pré-seedée PREL-2026-001 (Mohammed Bennani)
    demande = db.query(Demande).filter(Demande.code_barres == "PREL-2026-001").first()
    assert demande is not None

    # Tester la validation biologique
    valid_payload = {
        "conclusion_biologique": "Validation automatisée par test unitaire. Bilan cohérent.",
        "valide_par": "Dr. M. GHALIM"
    }
    resp = client.post(f"/api/validation/{demande.id}/valider", json=valid_payload)
    assert resp.status_code == 200

    # Tester la génération directe du PDF via ReportLab
    pdf_bytes = generate_medical_report_pdf(demande)
    assert pdf_bytes is not None
    assert pdf_bytes.startswith(b"%PDF")  # Signature magique PDF

    # Tester l'endpoint de téléchargement PDF
    resp_pdf = client.get(f"/api/rapports/{demande.id}/pdf")
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert resp_pdf.content.startswith(b"%PDF")

    db.close()


def test_api_bacteriologie_and_antibiogramme():
    # Récupérer la demande PREL-2026-004
    db = SessionLocal()
    demande = db.query(Demande).filter(Demande.code_barres == "PREL-2026-004").first()
    assert demande is not None

    resp = client.get(f"/api/bacteriologie/{demande.id}")
    assert resp.status_code == 200
    bact_data = resp.json()
    assert bact_data is not None
    assert "Escherichia coli" in bact_data["germe_identifie"]
    assert len(bact_data["antibiogrammes"]) >= 5

    # Vérifier que les sensibilités S/R sont bien présentes
    sensibilites = [ab["sensibilite"] for ab in bact_data["antibiogrammes"]]
    assert "S" in sensibilites
    assert "R" in sensibilites

    db.close()


def test_api_scanned_documents_workflow():
    # 1. Tester la liste des documents pré-seedés pour le patient 1
    db = SessionLocal()
    p1 = db.query(Patient).filter(Patient.cin == "BK123456").first()
    assert p1 is not None

    resp = client.get(f"/api/documents/patient/{p1.id}")
    assert resp.status_code == 200
    docs = resp.json()
    assert len(docs) >= 1
    assert "Ordonnance" in docs[0]["type_document"]

    # 2. Tester l'upload d'un nouveau document scanné (ex: Scanner ou Bulletin)
    fake_pdf_content = b"%PDF-1.4 Mock scanned prescription or CT scan for test"
    files = {
        "file": ("Scanner_Thoracique_Test.pdf", fake_pdf_content, "application/pdf")
    }
    data = {
        "patient_id": p1.id,
        "titre": "Scanner Thoracique Test Unitaire",
        "type_document": "Résultat d'Imagerie / Scanner",
        "notes": "Téléversé par la secrétaire pour contrôle",
        "ajoute_par": "Secrétaire Test"
    }

    upload_resp = client.post("/api/documents/upload", files=files, data=data)
    assert upload_resp.status_code == 201
    created_doc = upload_resp.json()["document"]
    doc_id = created_doc["id"]
    assert created_doc["titre"] == "Scanner Thoracique Test Unitaire"

    # 3. Tester la visualisation en ligne du document scanné
    view_resp = client.get(f"/api/documents/{doc_id}/view")
    assert view_resp.status_code == 200
    assert view_resp.headers["content-type"] == "application/pdf"
    assert b"%PDF-1.4" in view_resp.content

    # 4. Tester la suppression du document
    del_resp = client.delete(f"/api/documents/{doc_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    db.close()


def test_api_tube_lifecycle_and_labels_generation():
    """Teste le cycle de vie complet des tubes d'échantillons et la génération des étiquettes code-barres thermiques."""
    db = SessionLocal()
    demande = db.query(Demande).filter(Demande.code_barres == "PREL-2026-001").first()
    assert demande is not None

    # 1. Vérifier la présence des tubes pré-analytiques
    resp = client.get(f"/api/tubes?demande_id={demande.id}")
    assert resp.status_code == 200
    tubes = resp.json()
    assert len(tubes) >= 2

    # Vérifier la présence du tube EDTA et du tube Sec
    codes_tubes = [t["code_tube"] for t in tubes]
    assert any("EDTA" in c for c in codes_tubes)
    assert any("SEC" in c for c in codes_tubes)

    tube_id = tubes[0]["id"]

    # 2. Tester l'avancement dans la chaîne de traçabilité
    act_resp = client.post(f"/api/tubes/{tube_id}/action/centrifuger")
    assert act_resp.status_code == 200
    assert act_resp.json()["statut_tube"] == "Centrifugé"

    # 3. Tester l'affectation à la sérothèque
    seroth_resp = client.patch(f"/api/tubes/{tube_id}", json={
        "emplacement_serotheque": "Frigo Sérothèque 2 - Rack B3 - Pos 01",
        "remarques": "Test unitaire traçabilité"
    })
    assert seroth_resp.status_code == 200
    assert seroth_resp.json()["emplacement_serotheque"] == "Frigo Sérothèque 2 - Rack B3 - Pos 01"
    assert seroth_resp.json()["statut_tube"] == "Archivé en sérothèque"

    # 4. Tester la génération du PDF d'étiquettes thermiques pour tous les tubes du dossier
    labels_resp = client.get(f"/api/rapports/demande/{demande.id}/etiquettes/pdf")
    assert labels_resp.status_code == 200
    assert labels_resp.headers["content-type"] == "application/pdf"
    assert labels_resp.content.startswith(b"%PDF")
    assert len(labels_resp.content) > 1000

    # 5. Tester la génération d'une étiquette individuelle
    single_label_resp = client.get(f"/api/rapports/tube/{tube_id}/etiquette/pdf")
    assert single_label_resp.status_code == 200
    assert single_label_resp.headers["content-type"] == "application/pdf"
    assert single_label_resp.content.startswith(b"%PDF")

    db.close()

