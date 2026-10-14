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
    from backend.app.database import ensure_db_schema_up_to_date
    Base.metadata.create_all(bind=engine)
    ensure_db_schema_up_to_date(engine)
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


def test_api_billing_nomenclature_and_rates():
    """Vérifie la présence des 492 actes de la nomenclature marocaine et les règles tarifaires (1.10 et 1.36)."""
    # 1. Vérifier la liste complète des actes
    resp = client.get("/api/billing/actes?limit=600")
    assert resp.status_code == 200
    actes = resp.json()
    assert len(actes) == 492, f"Attendu 492 actes de la nomenclature V4, obtenu {len(actes)}"

    # 2. Vérifier les paramètres de tarification globaux
    param_resp = client.get("/api/billing/parametres")
    assert param_resp.status_code == 200
    p = param_resp.json()
    assert p["taux_cnss_cnops"] == 1.10
    assert p["taux_normal_assurance"] == 1.36

    # 3. Vérifier la règle de calcul sur un échantillon d'actes
    for code in ["B100", "B110", "B118"]:
        found = [a for a in actes if a["code"] == code]
        assert len(found) == 1, f"Acte {code} introuvable"
        acte = found[0]
        coeff = acte["coefficient"]
        assert acte["prix_cnss"] == round(coeff * 1.10, 2)
        assert acte["prix_normal"] == round(coeff * 1.36, 2)


def test_api_billing_update_rates_and_recalculate():
    """Vérifie la mise à jour des taux par le biologiste et le recalcul automatique des actes."""
    # 1. Modifier temporairement les taux globaux
    new_rates = {
        "taux_cnss_cnops": 1.15,
        "taux_normal_assurance": 1.45,
        "devise": "DH",
        "recalculer_prix_actes": True
    }
    update_resp = client.put("/api/billing/parametres", json=new_rates)
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["taux_cnss_cnops"] == 1.15
    assert data["taux_normal_assurance"] == 1.45

    # Vérifier que les prix des actes ont bien été recalculés
    b110_resp = client.get("/api/billing/actes/code/B110")
    assert b110_resp.status_code == 200
    b110 = b110_resp.json()
    assert b110["prix_cnss"] == round(b110["coefficient"] * 1.15, 2)
    assert b110["prix_normal"] == round(b110["coefficient"] * 1.45, 2)

    # 2. Réinitialiser aux taux officiels (1.10 et 1.36)
    restore_resp = client.put("/api/billing/parametres", json={
        "taux_cnss_cnops": 1.10,
        "taux_normal_assurance": 1.36,
        "devise": "DH",
        "recalculer_prix_actes": True
    })
    assert restore_resp.status_code == 200


def test_api_billing_individual_acte_modification():
    """Vérifie qu'un biologiste peut ajuster individuellement le coefficient ou les prix d'un acte."""
    b100_resp = client.get("/api/billing/actes/code/B100")
    assert b100_resp.status_code == 200
    b100 = b100_resp.json()
    acte_id = b100["id"]

    # Modifier le coefficient individuel
    patch_resp = client.patch(f"/api/billing/actes/{acte_id}", json={
        "coefficient": 45.0,
        "prix_cnss": 50.00,
        "prix_normal": 62.00
    })
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["coefficient"] == 45.0
    assert updated["prix_cnss"] == 50.00
    assert updated["prix_normal"] == 62.00

    # Rétablir le coefficient original (40.0)
    restore_resp = client.patch(f"/api/billing/actes/{acte_id}", json={
        "coefficient": 40.0,
        "prix_cnss": round(40.0 * 1.10, 2),
        "prix_normal": round(40.0 * 1.36, 2)
    })
    assert restore_resp.status_code == 200


def test_api_billing_facture_creation_and_invoice_pdf():
    """Teste la création de facture, le calcul CNSS vs Normal, le paiement et le PDF."""
    db = SessionLocal()
    demande = db.query(Demande).filter(Demande.code_barres == "PREL-2026-001").first()
    assert demande is not None

    # 1. Génération automatique de facture pour cette demande en CNSS (taux 1.10)
    auto_resp = client.post(f"/api/billing/factures/auto/{demande.id}?type_prise_en_charge=CNSS")
    assert auto_resp.status_code in [200, 201]
    facture = auto_resp.json()
    facture_id = facture["id"]

    assert facture["type_prise_en_charge"] == "CNSS"
    assert facture["taux_applique"] == 1.10
    assert len(facture["lignes"]) >= 1
    assert facture["montant_net"] > 0

    # 2. Enregistrer un règlement partiel / complet
    reglement_resp = client.patch(f"/api/billing/factures/{facture_id}", json={
        "montant_paye": facture["montant_net"],
        "mode_paiement": "Carte Bancaire",
        "reference_paiement": "TPE-TEST-7788"
    })
    assert reglement_resp.status_code == 200
    reg = reglement_resp.json()
    assert reg["statut_paiement"] == "Payé intégralement"
    assert reg["reste_a_payer"] == 0.0

    # 3. Téléchargement et validation du PDF de la facture
    pdf_resp = client.get(f"/api/billing/factures/{facture_id}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")
    assert len(pdf_resp.content) > 1000

    db.close()


def test_api_lab_customization_and_branding_uploads():
    """Teste la personnalisation complète du laboratoire, l'upload des médias (logo, cachet, signature) et l'auto-signature."""
    # 1. Mise à jour de l'identité et coordonnées du laboratoire
    custom_params = {
        "nom_laboratoire": "Laboratoire Central de Biologie GhalimLab",
        "sous_titre": "Hématologie & Biochimie Spécialisée",
        "directeur": "Dr. Mohammed GHALIM - Directeur Médical",
        "adresse": "Boulevard Mohammed V, Casablanca",
        "telephone": "+212 5 22 99 88 77",
        "email": "direction@ghalimlab.ma",
        "ice": "009988776655443",
        "identifiant_fiscal": "99887766",
        "patente": "55443322",
        "cnss_affiliation": "1122334",
        "auto_signer_validation": True
    }
    patch_resp = client.patch("/api/billing/parametres", json=custom_params)
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["nom_laboratoire"] == "Laboratoire Central de Biologie GhalimLab"
    assert data["directeur"] == "Dr. Mohammed GHALIM - Directeur Médical"
    assert data["ice"] == "009988776655443"
    assert data["auto_signer_validation"] is True

    # 2. Upload Logo (SVG ou PNG)
    fake_logo = b"<svg xmlns='http://www.w3.org/2000/svg'><circle cx='10' cy='10' r='5'/></svg>"
    logo_resp = client.post(
        "/api/billing/parametres/upload/logo",
        files={"file": ("test_logo.svg", fake_logo, "image/svg+xml")}
    )
    assert logo_resp.status_code == 200
    assert "logo_path" in logo_resp.json()
    assert logo_resp.json()["logo_path"].startswith("/uploads/branding/logo_")

    # 3. Upload Cachet (PNG)
    import io
    from PIL import Image as PILImage
    _png_buf = io.BytesIO()
    PILImage.new("RGBA", (60, 60), (200, 30, 30, 200)).save(_png_buf, format="PNG")
    valid_png_bytes = _png_buf.getvalue()

    cachet_resp = client.post(
        "/api/billing/parametres/upload/cachet",
        files={"file": ("test_cachet.png", valid_png_bytes, "image/png")}
    )
    assert cachet_resp.status_code == 200
    assert cachet_resp.json()["cachet_path"].startswith("/uploads/branding/cachet_")

    # 4. Upload Signature (PNG)
    sign_resp = client.post(
        "/api/billing/parametres/upload/signature",
        files={"file": ("test_signature.png", valid_png_bytes, "image/png")}
    )
    assert sign_resp.status_code == 200
    assert sign_resp.json()["signature_path"].startswith("/uploads/branding/signature_")

    # 5. Valider un prélèvement et vérifier l'apposition automatique de la signature
    db = SessionLocal()
    demande = db.query(Demande).filter(Demande.code_barres == "PREL-2026-002").first()
    assert demande is not None

    valid_resp = client.post(f"/api/validation/{demande.id}/valider", json={
        "conclusion_biologique": "Bilan biologique certifié et signé automatiquement."
    })
    assert valid_resp.status_code == 200
    assert valid_resp.json()["auto_signed"] is True
    assert "Dr. Mohammed GHALIM" in valid_resp.json()["valide_par"]

    # 6. Vérifier la génération du rapport PDF avec les paramètres personnalisés
    report_pdf_resp = client.get(f"/api/rapports/{demande.id}/pdf")
    assert report_pdf_resp.status_code == 200
    assert report_pdf_resp.content.startswith(b"%PDF")
    assert len(report_pdf_resp.content) > 1000

    # 7. Vérifier la page HTML /parametres
    page_resp = client.get("/parametres")
    assert page_resp.status_code == 200
    assert "Laboratoire Central de Biologie" in page_resp.text

    db.close()

