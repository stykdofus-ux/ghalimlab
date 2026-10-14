"""
Service d'initialisation des données cliniques de référence (Catalogue d'analyses)
et création de dossiers patients de démonstration.
"""

import datetime
from sqlalchemy.orm import Session
from backend.app.models.core import Patient, Demande, AnalyseParameter, Resultat, AutomateLog, DocumentScanne, EchantillonTube
from backend.app.models.bacteriology import ExamenBacteriologique, AntibiogrammeLigne
from backend.app.models.parasitology import ExamenParasitologique
from backend.app.config import UPLOAD_DIR


PARAMETRES_CATALOGUE = [
    # --- Hématologie (NFS / Hémogramme) ---
    {
        "code": "WBC",
        "nom": "Leucocytes (Globules Blancs)",
        "categorie": "Hématologie",
        "unite": "10^3/µL",
        "male_min": 4.0, "male_max": 10.0,
        "female_min": 4.0, "female_max": 10.0,
        "child_min": 5.0, "child_max": 13.0,
        "methode": "Impédancimétrie / Cytométrie en flux",
        "automate_prefere": "Sysmex XN-1000",
        "ordre_affichage": 1
    },
    {
        "code": "RBC",
        "nom": "Hématies (Globules Rouges)",
        "categorie": "Hématologie",
        "unite": "10^6/µL",
        "male_min": 4.5, "male_max": 5.9,
        "female_min": 4.0, "female_max": 5.2,
        "child_min": 4.0, "child_max": 5.3,
        "methode": "Impédancimétrie avec focalisation hydrodynamique",
        "automate_prefere": "Sysmex XN-1000",
        "ordre_affichage": 2
    },
    {
        "code": "HGB",
        "nom": "Hémoglobine",
        "categorie": "Hématologie",
        "unite": "g/dL",
        "male_min": 13.0, "male_max": 17.5,
        "female_min": 12.0, "female_max": 16.0,
        "child_min": 11.5, "child_max": 14.5,
        "methode": "Photométrie SLS sans cyanure",
        "automate_prefere": "Sysmex XN-1000",
        "ordre_affichage": 3
    },
    {
        "code": "HCT",
        "nom": "Hématocrite",
        "categorie": "Hématologie",
        "unite": "%",
        "male_min": 40.0, "male_max": 52.0,
        "female_min": 36.0, "female_max": 48.0,
        "child_min": 35.0, "child_max": 45.0,
        "methode": "Cumul des hauteurs d'impulsion",
        "automate_prefere": "Sysmex XN-1000",
        "ordre_affichage": 4
    },
    {
        "code": "MCV",
        "nom": "V.G.M. (Volume Globulaire Moyen)",
        "categorie": "Hématologie",
        "unite": "fL",
        "male_min": 80.0, "male_max": 100.0,
        "female_min": 80.0, "female_max": 100.0,
        "child_min": 75.0, "child_max": 95.0,
        "methode": "Calculé",
        "automate_prefere": "Sysmex XN-1000",
        "ordre_affichage": 5
    },
    {
        "code": "MCH",
        "nom": "T.C.M.H. (Teneur Corpusculaire Moyenne en Hb)",
        "categorie": "Hématologie",
        "unite": "pg",
        "male_min": 27.0, "male_max": 32.0,
        "female_min": 27.0, "female_max": 32.0,
        "child_min": 25.0, "child_max": 31.0,
        "methode": "Calculé",
        "automate_prefere": "Sysmex XN-1000",
        "ordre_affichage": 6
    },
    {
        "code": "MCHC",
        "nom": "C.C.M.H. (Concentration Corpusculaire Moyenne)",
        "categorie": "Hématologie",
        "unite": "g/dL",
        "male_min": 32.0, "male_max": 36.0,
        "female_min": 32.0, "female_max": 36.0,
        "child_min": 32.0, "child_max": 36.0,
        "methode": "Calculé",
        "automate_prefere": "Sysmex XN-1000",
        "ordre_affichage": 7
    },
    {
        "code": "PLT",
        "nom": "Plaquettes Sanguines",
        "categorie": "Hématologie",
        "unite": "10^3/µL",
        "male_min": 150.0, "male_max": 450.0,
        "female_min": 150.0, "female_max": 450.0,
        "child_min": 150.0, "child_max": 450.0,
        "methode": "Impédancimétrie",
        "automate_prefere": "Sysmex XN-1000",
        "ordre_affichage": 8
    },
    {
        "code": "NEUT",
        "nom": "Polynucléaires Neutrophiles (%)",
        "categorie": "Hématologie",
        "unite": "%",
        "male_min": 40.0, "male_max": 75.0,
        "female_min": 40.0, "female_max": 75.0,
        "child_min": 35.0, "child_max": 65.0,
        "methode": "Cytométrie en flux fluorescente",
        "automate_prefere": "Sysmex XN-1000",
        "ordre_affichage": 9
    },
    {
        "code": "LYMPH",
        "nom": "Lymphocytes (%)",
        "categorie": "Hématologie",
        "unite": "%",
        "male_min": 20.0, "male_max": 45.0,
        "female_min": 20.0, "female_max": 45.0,
        "child_min": 30.0, "child_max": 55.0,
        "methode": "Cytométrie en flux fluorescente",
        "automate_prefere": "Sysmex XN-1000",
        "ordre_affichage": 10
    },

    # --- Biochimie / Métabolisme & Bilan Rénal ---
    {
        "code": "GLU",
        "nom": "Glycémie à jeun",
        "categorie": "Biochimie",
        "unite": "g/L",
        "male_min": 0.70, "male_max": 1.10,
        "female_min": 0.70, "female_max": 1.10,
        "child_min": 0.60, "child_max": 1.05,
        "methode": "Hexokinase / UV",
        "automate_prefere": "Cobas 6000 c501",
        "ordre_affichage": 11
    },
    {
        "code": "UREE",
        "nom": "Urée Sanguine",
        "categorie": "Biochimie",
        "unite": "g/L",
        "male_min": 0.15, "male_max": 0.45,
        "female_min": 0.15, "female_max": 0.45,
        "child_min": 0.10, "child_max": 0.35,
        "methode": "Uréase - GLDH cinétique",
        "automate_prefere": "Cobas 6000 c501",
        "ordre_affichage": 12
    },
    {
        "code": "CREAT",
        "nom": "Créatinine Sanguine",
        "categorie": "Biochimie",
        "unite": "mg/L",
        "male_min": 7.0, "male_max": 13.0,
        "female_min": 5.0, "female_max": 10.0,
        "child_min": 3.0, "child_max": 7.0,
        "methode": "Jaffé cinétique compensée IDMS",
        "automate_prefere": "Cobas 6000 c501",
        "ordre_affichage": 13
    },
    {
        "code": "ACIDE_URIQUE",
        "nom": "Acide Urique",
        "categorie": "Biochimie",
        "unite": "mg/L",
        "male_min": 35.0, "male_max": 70.0,
        "female_min": 25.0, "female_max": 60.0,
        "child_min": 20.0, "child_max": 50.0,
        "methode": "Uricase enzymatique colorimétrique",
        "automate_prefere": "Cobas 6000 c501",
        "ordre_affichage": 14
    },
    {
        "code": "CRP",
        "nom": "Protéine C-Réactive (CRP)",
        "categorie": "Biochimie",
        "unite": "mg/L",
        "male_min": 0.0, "male_max": 6.0,
        "female_min": 0.0, "female_max": 6.0,
        "child_min": 0.0, "child_max": 5.0,
        "methode": "Immunoturbidimétrie amplifiée au latex",
        "automate_prefere": "Cobas 6000 c501",
        "ordre_affichage": 15
    },

    # --- Bilan Lipidique & Hépatique ---
    {
        "code": "CHOL",
        "nom": "Cholestérol Total",
        "categorie": "Biochimie",
        "unite": "g/L",
        "male_min": 1.50, "male_max": 2.00,
        "female_min": 1.50, "female_max": 2.00,
        "child_min": 1.20, "child_max": 1.90,
        "methode": "CHOD-PAP enzymatique colorimétrique",
        "automate_prefere": "Cobas 6000 c501",
        "ordre_affichage": 16
    },
    {
        "code": "TRIG",
        "nom": "Triglycérides",
        "categorie": "Biochimie",
        "unite": "g/L",
        "male_min": 0.50, "male_max": 1.50,
        "female_min": 0.50, "female_max": 1.50,
        "child_min": 0.40, "child_max": 1.30,
        "methode": "GPO-PAP enzymatique colorimétrique",
        "automate_prefere": "Cobas 6000 c501",
        "ordre_affichage": 17
    },
    {
        "code": "HDL",
        "nom": "Cholestérol HDL (Bon cholestérol)",
        "categorie": "Biochimie",
        "unite": "g/L",
        "male_min": 0.40, "male_max": 0.85,
        "female_min": 0.50, "female_max": 0.95,
        "child_min": 0.40, "child_max": 0.85,
        "methode": "Homogène direct sans précipitation",
        "automate_prefere": "Cobas 6000 c501",
        "ordre_affichage": 18
    },
    {
        "code": "LDL",
        "nom": "Cholestérol LDL (Mauvais cholestérol)",
        "categorie": "Biochimie",
        "unite": "g/L",
        "male_min": 0.90, "male_max": 1.30,
        "female_min": 0.90, "female_max": 1.30,
        "child_min": 0.70, "child_max": 1.20,
        "methode": "Direct enzymatique",
        "automate_prefere": "Cobas 6000 c501",
        "ordre_affichage": 19
    },
    {
        "code": "ASAT",
        "nom": "Transaminases ASAT / TGO",
        "categorie": "Biochimie",
        "unite": "UI/L",
        "male_min": 10.0, "male_max": 40.0,
        "female_min": 10.0, "female_max": 32.0,
        "child_min": 15.0, "child_max": 45.0,
        "methode": "IFCC sans pyridoxal phosphate",
        "automate_prefere": "Cobas 6000 c501",
        "ordre_affichage": 20
    },
    {
        "code": "ALAT",
        "nom": "Transaminases ALAT / TGP",
        "categorie": "Biochimie",
        "unite": "UI/L",
        "male_min": 10.0, "male_max": 45.0,
        "female_min": 10.0, "female_max": 35.0,
        "child_min": 10.0, "child_max": 35.0,
        "methode": "IFCC sans pyridoxal phosphate",
        "automate_prefere": "Cobas 6000 c501",
        "ordre_affichage": 21
    }
]


def seed_database(db: Session):
    """Initialise le catalogue d'analyses et des patients/dossiers de test s'ils n'existent pas."""
    # 1. Peupler le catalogue d'analyses
    existing_codes = {p.code: p for p in db.query(AnalyseParameter).all()}
    
    for p_data in PARAMETRES_CATALOGUE:
        if p_data["code"] not in existing_codes:
            param = AnalyseParameter(**p_data)
            db.add(param)
    db.commit()

    # Recharger les paramètres à jour
    params_by_code = {p.code: p for p in db.query(AnalyseParameter).all()}

    # 2. Patients et Demandes de démonstration
    if db.query(Patient).count() == 0:
        # Patient 1 : M. Mohammed Bennani (Validé)
        p1 = Patient(
            cin="BK123456",
            nom="BENNANI",
            prenom="Mohammed",
            date_naissance="1978-04-12",
            sexe="M",
            telephone="+212 6 61 23 45 67",
            adresse="Quartier Racine, Boulevard d'Anfa, Casablanca",
            numero_securite_sociale="18765432109"
        )
        db.add(p1)
        db.flush()

        demande1 = Demande(
            code_barres="PREL-2026-001",
            patient_id=p1.id,
            date_reception=datetime.datetime.now() - datetime.timedelta(hours=5),
            statut="Validé",
            prescripteur="Dr. Chakir (Cardiologie)",
            renseignements_cliniques="Bilan de contrôle annuel cardiovasculaire. Patient hypertendu traité.",
            bilan_demande="NFS, Glycémie, Bilan Rénal, Bilan Lipidique",
            date_validation=datetime.datetime.now() - datetime.timedelta(hours=2),
            valide_par="Dr. M. GHALIM (Biologiste Médical)",
            conclusion_biologique="Hémogramme normal. Bilan lipidique satisfaisant sous statine. Fonction rénale et glycémie dans les limites physiologiques."
        )
        db.add(demande1)
        db.flush()

        # Résultats pour Demande 1
        valeurs_p1 = [
            ("WBC", 6.8, "Sysmex XN-1000"),
            ("RBC", 4.95, "Sysmex XN-1000"),
            ("HGB", 15.2, "Sysmex XN-1000"),
            ("HCT", 45.1, "Sysmex XN-1000"),
            ("MCV", 91.1, "Sysmex XN-1000"),
            ("MCH", 30.7, "Sysmex XN-1000"),
            ("MCHC", 33.7, "Sysmex XN-1000"),
            ("PLT", 245.0, "Sysmex XN-1000"),
            ("GLU", 0.95, "Cobas 6000 c501"),
            ("UREE", 0.32, "Cobas 6000 c501"),
            ("CREAT", 9.5, "Cobas 6000 c501"),
            ("CHOL", 1.82, "Cobas 6000 c501"),
            ("TRIG", 1.15, "Cobas 6000 c501"),
            ("HDL", 0.52, "Cobas 6000 c501"),
            ("LDL", 1.07, "Cobas 6000 c501"),
            ("CRP", 1.8, "Cobas 6000 c501")
        ]

        for code, val, automate in valeurs_p1:
            if code in params_by_code:
                param = params_by_code[code]
                min_ref, max_ref, _ = param.get_reference_range(p1.age, p1.sexe)
                hors_norme = False
                drapeau = "NORMAL"
                if min_ref is not None and val < min_ref:
                    hors_norme = True
                    drapeau = "BAS"
                elif max_ref is not None and val > max_ref:
                    hors_norme = True
                    drapeau = "ELEVE"

                res = Resultat(
                    demande_id=demande1.id,
                    parameter_id=param.id,
                    valeur=str(val),
                    valeur_num=val,
                    automate_source=automate,
                    hors_norme=hors_norme,
                    drapeau=drapeau,
                    ref_min_applique=min_ref,
                    ref_max_applique=max_ref,
                    date_analyse=datetime.datetime.now() - datetime.timedelta(hours=3)
                )
                db.add(res)

        # Patient 2 : Mme Amina El Amrani (En attente d'automate)
        p2 = Patient(
            cin="AE654321",
            nom="EL AMRANI",
            prenom="Amina",
            date_naissance="1992-09-18",
            sexe="F",
            telephone="+212 6 72 88 99 00",
            adresse="Résidence Les Jardins, Agdal, Rabat",
            numero_securite_sociale="29210987654"
        )
        db.add(p2)
        db.flush()

        demande2 = Demande(
            code_barres="PREL-2026-002",
            patient_id=p2.id,
            date_reception=datetime.datetime.now() - datetime.timedelta(minutes=45),
            statut="En attente",
            prescripteur="Dr. Tahiri (Médecine Interne)",
            renseignements_cliniques="Suspicion d'anémie et asthénie intense depuis 3 semaines.",
            bilan_demande="NFS Complète, Glycémie, CRP"
        )
        db.add(demande2)

        # Patient 3 : Enfant Youssef Tazi (Pédiatrie, En attente)
        p3 = Patient(
            cin="ET998877",
            nom="TAZI",
            prenom="Youssef",
            date_naissance="2017-02-14",
            sexe="M",
            telephone="+212 6 63 11 22 33",
            adresse="Derb Sultan, Casablanca",
            numero_securite_sociale="11709812345"
        )
        db.add(p3)
        db.flush()

        demande3 = Demande(
            code_barres="PREL-2026-003",
            patient_id=p3.id,
            date_reception=datetime.datetime.now() - datetime.timedelta(minutes=20),
            statut="En attente",
            prescripteur="Dr. Benjelloun (Pédiatre)",
            renseignements_cliniques="Fièvre à 39°C inexpliquée. Bilan infectieux.",
            bilan_demande="NFS, CRP, Bilan Rénal"
        )
        db.add(demande3)

        # Patient 4 : Mme Fatima Zahra Mansouri (Résultats reçus + Bactériologie ECBU)
        p4 = Patient(
            cin="FZ443322",
            nom="MANSOURI",
            prenom="Fatima Zahra",
            date_naissance="1997-11-05",
            sexe="F",
            telephone="+212 6 65 44 33 22",
            adresse="Bourgogne, Casablanca",
            numero_securite_sociale="29705443322"
        )
        db.add(p4)
        db.flush()

        demande4 = Demande(
            code_barres="PREL-2026-004",
            patient_id=p4.id,
            date_reception=datetime.datetime.now() - datetime.timedelta(hours=2),
            statut="Résultats reçus",
            prescripteur="Dr. Alami (Gynécologie - Obstétrique)",
            renseignements_cliniques="Dysurie, brûlures mictionnelles et pesanteur pelvienne.",
            bilan_demande="NFS, CRP, ECBU avec Antibiogramme"
        )
        db.add(demande4)
        db.flush()

        # Résultats automate pour Demande 4 (CRP élevée, Leucocytose)
        valeurs_p4 = [
            ("WBC", 12.8, "Sysmex XN-1000"),
            ("HGB", 13.1, "Sysmex XN-1000"),
            ("PLT", 310.0, "Sysmex XN-1000"),
            ("CRP", 48.5, "Cobas 6000 c501")  # Très élevé
        ]
        for code, val, automate in valeurs_p4:
            if code in params_by_code:
                param = params_by_code[code]
                min_ref, max_ref, _ = param.get_reference_range(p4.age, p4.sexe)
                hors_norme = False
                drapeau = "NORMAL"
                if min_ref is not None and val < min_ref:
                    hors_norme = True
                    drapeau = "BAS"
                elif max_ref is not None and val > max_ref:
                    hors_norme = True
                    drapeau = "ELEVE"

                res = Resultat(
                    demande_id=demande4.id,
                    parameter_id=param.id,
                    valeur=str(val),
                    valeur_num=val,
                    automate_source=automate,
                    hors_norme=hors_norme,
                    drapeau=drapeau,
                    ref_min_applique=min_ref,
                    ref_max_applique=max_ref,
                    date_analyse=datetime.datetime.now() - datetime.timedelta(hours=1)
                )
                db.add(res)

        # Création de l'ECBU associé
        ecbu = ExamenBacteriologique(
            demande_id=demande4.id,
            type_prelevement="ECBU (Urine du 2ème jet)",
            aspect_macroscopique="Trouble, odeur fétide",
            cytologie_leucocytes="125 000 / mL (Normal < 10 000)",
            cytologie_hematies="15 000 / mL (Normal < 5 000)",
            cellules_epitheliales="Quelques cellules épithéliales",
            coloration_gram="Nombreux Bacilles Gram Négatif (BGN)",
            culture_resultat="Positive",
            germe_identifie="Escherichia coli",
            numeration_colonies="> 10^6 UFC/mL",
            conclusion="Infection urinaire franche à Escherichia coli. Antibiogramme ci-après."
        )
        db.add(ecbu)
        db.flush()

        # Antibiogramme
        ab_data = [
            ("Amoxicilline", "Bêta-lactamines", 8.0, 32.0, "R"),
            ("Amoxicilline + Acide Clavulanique", "Bêta-lactamines", 22.0, 4.0, "S"),
            ("Céfotaxime (C3G)", "Céphalosporines", 28.0, 0.5, "S"),
            ("Ciprofloxacine", "Fluoroquinolones", 26.0, 0.25, "S"),
            ("Gentamicine", "Aminosides", 21.0, 1.0, "S"),
            ("Cotrimoxazole", "Sulfamides", 12.0, 16.0, "R"),
            ("Fosfomycine", "Phosphoniques", 30.0, 2.0, "S"),
            ("Nitrofurantoïne", "Furanes", 24.0, 8.0, "S")
        ]
        for nom_ab, fam, zone, cmi, sens in ab_data:
            ab_line = AntibiogrammeLigne(
                examen_bact_id=ecbu.id,
                antibiotique_nom=nom_ab,
                famille=fam,
                diametre_zone=zone,
                cmi=cmi,
                sensibilite=sens
            )
            db.add(ab_line)

        db.commit()

    # 3. Documents scannés de démonstration (Ordonnances scannées, Scanners, Antériorités)
    if db.query(DocumentScanne).count() == 0:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet

            def make_demo_pdf(path, title, content_lines):
                doc = SimpleDocTemplate(str(path), pagesize=A4)
                styles = getSampleStyleSheet()
                story = [
                    Paragraph(f"<b>{title}</b>", styles['Title']),
                    Spacer(1, 15),
                ]
                for line in content_lines:
                    story.append(Paragraph(line, styles['Normal']))
                    story.append(Spacer(1, 6))
                doc.build(story)

            p1 = db.query(Patient).filter(Patient.cin == "BK123456").first()
            demande1 = db.query(Demande).filter(Demande.code_barres == "PREL-2026-001").first()
            p2 = db.query(Patient).filter(Patient.cin == "AE654321").first()
            demande2 = db.query(Demande).filter(Demande.code_barres == "PREL-2026-002").first()
            p4 = db.query(Patient).filter(Patient.cin == "FZ443322").first()
            demande4 = db.query(Demande).filter(Demande.code_barres == "PREL-2026-004").first()

            if p1 and demande1:
                # Document 1 : Ordonnance scannée pour Patient 1
                f1_name = "DEMO_Ordonnance_Dr_Chakir_Bennani.pdf"
                f1_path = UPLOAD_DIR / f1_name
                make_demo_pdf(f1_path, "ORDONNANCE MÉDICALE SCANNÉE", [
                    "<b>Cabinet Médical de Cardiologie - Dr. H. Chakir</b>",
                    "Patient : M. Mohammed BENNANI (Âge : 48 ans)",
                    "Date de prescription : 14/10/2026",
                    "<br/><b>Analyses demandées en urgence relative :</b>",
                    "- Hémogramme complet (NFS)",
                    "- Bilan métabolique : Glycémie à jeun, Urée, Créatininémie",
                    "- Profil lipidique complet (Cholestérol Total, HDL, LDL, Triglycérides)",
                    "- Protéine C-Réactive (CRP)",
                    "<br/><i>Note du secrétariat : Ordonnance originale numérisée lors de l'enregistrement à l'accueil.</i>"
                ])
                doc1 = DocumentScanne(
                    patient_id=p1.id,
                    demande_id=demande1.id,
                    titre="Ordonnance Médicale - Dr. Chakir (Cardiologie)",
                    type_document="Ordonnance",
                    nom_fichier_original="Ordonnance_Dr_Chakir.pdf",
                    nom_fichier_stocke=f1_name,
                    chemin_fichier=str(f1_path),
                    taille_octets=f1_path.stat().st_size,
                    mime_type="application/pdf",
                    ajoute_par="Mme Salma (Secrétaire Médicale)",
                    notes="Ordonnance originale vérifiée et conforme."
                )
                db.add(doc1)

            if p2 and demande2:
                # Document 2 : Résultat de Scanner scanné pour Patient 2 (Mme Amina El Amrani)
                f2_name = "DEMO_Scanner_Abdominal_Amina_ElAmrani.pdf"
                f2_path = UPLOAD_DIR / f2_name
                make_demo_pdf(f2_path, "COMPTE-RENDU D'IMAGERIE MÉDICALE SCANNÉ", [
                    "<b>Centre d'Imagerie Médicale & Radiologie Al Amal</b>",
                    "Patiente : Mme Amina EL AMRANI (34 ans) - Réf: AE654321",
                    "Date de l'examen : 10/10/2026",
                    "Examen réalisé : <b>Scanner abdomino-pelvien sans puis avec injection</b>",
                    "<br/><b>Indication :</b> Asthénie inexpliquée, douleurs fosse iliaque droite.",
                    "<b>Résultats :</b> Foie de taille et morphologie normales sans lésion focale.",
                    "Rate de taille normale (11 cm). Pas d'épanchement péritonéal décelable.",
                    "Reins de taille normale, bon index cortico-médullaire.",
                    "Conclusion : Absence d'anomalie morphologique évolutive au scanner.",
                    "<br/><i>Document numérisé par le secrétariat à la demande du médecin traitant.</i>"
                ])
                doc2 = DocumentScanne(
                    patient_id=p2.id,
                    demande_id=demande2.id,
                    titre="Scanner Abdomino-Pelvien - Centre Al Amal",
                    type_document="Résultat d'Imagerie / Scanner",
                    nom_fichier_original="Compte_Rendu_Scanner_Pelvien.pdf",
                    nom_fichier_stocke=f2_name,
                    chemin_fichier=str(f2_path),
                    taille_octets=f2_path.stat().st_size,
                    mime_type="application/pdf",
                    ajoute_par="Mme Salma (Secrétaire Médicale)",
                    notes="Scanner antérieur apporté par la patiente lors du prélèvement."
                )
                db.add(doc2)

            if p4 and demande4:
                # Document 3 : Bilan Antérieur pour Patient 4 (Mme Fatima Zahra Mansouri)
                f3_name = "DEMO_Bilan_Anterieur_Mansouri.pdf"
                f3_path = UPLOAD_DIR / f3_name
                make_demo_pdf(f3_path, "ANCIEN BILAN BIOLOGIQUE EXTERNE", [
                    "<b>Laboratoire Central d'Analyses Médicales</b>",
                    "Patiente : Mme Fatima Zahra MANSOURI (29 ans)",
                    "Date : 15/09/2025",
                    "Hémoglobine antérieure : 13.4 g/dL",
                    "Leucocytes antérieurs : 6.8 10^3/µL",
                    "CRP antérieure : 2.1 mg/L (Négative)",
                    "<br/><i>Renseigné pour suivi d'antériorité biologique par le biologiste.</i>"
                ])
                doc3 = DocumentScanne(
                    patient_id=p4.id,
                    demande_id=demande4.id,
                    titre="Bilan Antérieur Externe (Septembre 2025)",
                    type_document="Bilan Antérieur",
                    nom_fichier_original="Ancien_Bilan_2025.pdf",
                    nom_fichier_stocke=f3_name,
                    chemin_fichier=str(f3_path),
                    taille_octets=f3_path.stat().st_size,
                    mime_type="application/pdf",
                    ajoute_par="Secrétariat Accueil",
                    notes="Antériorité utile pour corrélation avec l'ECBU actuel."
                )
                db.add(doc3)

            db.commit()
        except Exception as e:
            print("Erreur création PDF démo :", e)

    # 4. Tubes d'échantillons et traçabilité sérothèque de démonstration
    if db.query(EchantillonTube).count() == 0:
        d1 = db.query(Demande).filter(Demande.code_barres == "PREL-2026-001").first()
        d2 = db.query(Demande).filter(Demande.code_barres == "PREL-2026-002").first()
        d3 = db.query(Demande).filter(Demande.code_barres == "PREL-2026-003").first()
        d4 = db.query(Demande).filter(Demande.code_barres == "PREL-2026-004").first()

        now = datetime.datetime.now()

        if d1:
            # Tubes pour Demande 1 (Dossier validé et archivé en sérothèque)
            t1_edta = EchantillonTube(
                demande_id=d1.id,
                code_tube=f"{d1.code_barres}-EDTA",
                type_tube="EDTA K3 / K2",
                couleur_bouchon="violet",
                analyses_associees="Hémogramme complet (NFS), Plaquettes",
                volume_ml=3.0,
                statut_tube="Archivé en sérothèque",
                conformite_preanalytique="Conforme",
                emplacement_serotheque="Frigo Sérothèque 1 - Rack A1 - Pos 04",
                date_prelevement=d1.date_reception,
                preleve_par="Inf. Hasnaa (Salle 2)",
                date_reception_labo=d1.date_reception + datetime.timedelta(minutes=15),
                receptionne_par="Karim (Plateau Technique)",
                date_archivage=d1.date_validation
            )
            t1_sec = EchantillonTube(
                demande_id=d1.id,
                code_tube=f"{d1.code_barres}-SEC",
                type_tube="Sec avec gel séparateur",
                couleur_bouchon="jaune",
                analyses_associees="Glycémie, Bilan Rénal, Bilan Lipidique",
                volume_ml=5.0,
                statut_tube="Archivé en sérothèque",
                conformite_preanalytique="Conforme",
                emplacement_serotheque="Frigo Sérothèque 1 - Rack A1 - Pos 05",
                date_prelevement=d1.date_reception,
                preleve_par="Inf. Hasnaa (Salle 2)",
                date_reception_labo=d1.date_reception + datetime.timedelta(minutes=15),
                receptionne_par="Karim (Plateau Technique)",
                date_archivage=d1.date_validation
            )
            db.add_all([t1_edta, t1_sec])

        if d2:
            # Tubes pour Demande 2 (En attente d'automate, prélèvements faits et reçus)
            t2_edta = EchantillonTube(
                demande_id=d2.id,
                code_tube=f"{d2.code_barres}-EDTA",
                type_tube="EDTA K3 / K2",
                couleur_bouchon="violet",
                analyses_associees="NFS Complète - Sysmex XN",
                volume_ml=3.0,
                statut_tube="En cours sur automate",
                conformite_preanalytique="Conforme",
                date_prelevement=d2.date_reception,
                preleve_par="Inf. Fatima (Accueil)",
                date_reception_labo=d2.date_reception + datetime.timedelta(minutes=10),
                receptionne_par="Salma (Technicienne)"
            )
            t2_sec = EchantillonTube(
                demande_id=d2.id,
                code_tube=f"{d2.code_barres}-SEC",
                type_tube="Sec avec gel séparateur",
                couleur_bouchon="jaune",
                analyses_associees="Glycémie, CRP - Cobas 6000",
                volume_ml=5.0,
                statut_tube="Centrifugé",
                conformite_preanalytique="Conforme",
                date_prelevement=d2.date_reception,
                preleve_par="Inf. Fatima (Accueil)",
                date_reception_labo=d2.date_reception + datetime.timedelta(minutes=10),
                receptionne_par="Salma (Technicienne)"
            )
            db.add_all([t2_edta, t2_sec])

        if d3:
            # Tubes pour Demande 3 (Pédiatrie, non encore reçus au plateau)
            t3_edta = EchantillonTube(
                demande_id=d3.id,
                code_tube=f"{d3.code_barres}-EDTA",
                type_tube="EDTA K3 / K2",
                couleur_bouchon="violet",
                analyses_associees="NFS Pédiatrique (Micro-méthode)",
                volume_ml=1.5,
                statut_tube="Prélevé",
                conformite_preanalytique="Conforme",
                date_prelevement=d3.date_reception,
                preleve_par="Inf. Hasnaa (Pédiatrie)"
            )
            t3_sec = EchantillonTube(
                demande_id=d3.id,
                code_tube=f"{d3.code_barres}-SEC",
                type_tube="Sec avec gel séparateur",
                couleur_bouchon="jaune",
                analyses_associees="CRP Pédiatrique",
                volume_ml=2.0,
                statut_tube="Prélevé",
                conformite_preanalytique="Conforme",
                date_prelevement=d3.date_reception,
                preleve_par="Inf. Hasnaa (Pédiatrie)"
            )
            db.add_all([t3_edta, t3_sec])

        if d4:
            # Tubes pour Demande 4 (ECBU + NFS)
            t4_edta = EchantillonTube(
                demande_id=d4.id,
                code_tube=f"{d4.code_barres}-EDTA",
                type_tube="EDTA K3 / K2",
                couleur_bouchon="violet",
                analyses_associees="Hémogramme & Leucocytose",
                volume_ml=3.0,
                statut_tube="Analysé",
                conformite_preanalytique="Conforme",
                date_prelevement=d4.date_reception,
                preleve_par="Inf. Fatima",
                date_reception_labo=d4.date_reception + datetime.timedelta(minutes=10)
            )
            t4_ecbu = EchantillonTube(
                demande_id=d4.id,
                code_tube=f"{d4.code_barres}-ECBU",
                type_tube="Flacon stérile urinaire",
                couleur_bouchon="rouge",
                analyses_associees="ECBU + Antibiogramme",
                volume_ml=30.0,
                statut_tube="Archivé en sérothèque",
                conformite_preanalytique="Conforme",
                emplacement_serotheque="Chambre Froide Bactério - Bac B2",
                date_prelevement=d4.date_reception,
                preleve_par="Inf. Fatima",
                date_reception_labo=d4.date_reception + datetime.timedelta(minutes=10),
                date_archivage=now
            )
            db.add_all([t4_edta, t4_ecbu])

        db.commit()

