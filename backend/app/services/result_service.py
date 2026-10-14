"""
Service d'ingestion et d'évaluation biologique des résultats automates.
Assure la correspondance des codes-barres, le calcul des bornes de référence
et l'étiquetage des anomalies (Élevé / Bas / Normal).
"""

import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.core import Demande, AnalyseParameter, Resultat, AutomateLog, EchantillonTube


def ingest_astm_payload(db: Session, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingère en base de données un message ASTM préalablement parsé.
    Associe chaque mesure au prélèvement (Demande) via le Code-barres ou le Code Tube (YYMMDDNNN).
    """
    automate_nom = parsed_data.get("automate", "Automate ASTM")
    orders = parsed_data.get("orders", [])

    total_ingested = 0
    demandes_traitees = []
    messages = []

    for order in orders:
        barcode = order.get("code_barres", "").strip()
        results = order.get("results", [])

        if not barcode:
            messages.append("Ordre sans code-barres ignoré.")
            continue

        # Recherche de la demande correspondante en base de données :
        # 1. Soit par le code-barres du prélèvement (ex: PREL-2026-001)
        # 2. Soit directement par le code du tube scanné par l'automate (ex: 261015001)
        demande = db.query(Demande).filter(Demande.code_barres == barcode).first()
        matched_tube = None

        if not demande:
            matched_tube = db.query(EchantillonTube).filter(EchantillonTube.code_tube == barcode).first()
            if matched_tube and matched_tube.demande:
                demande = matched_tube.demande

        if not demande:
            log_entry = AutomateLog(
                automate_nom=automate_nom,
                code_barres_detecte=barcode,
                nb_resultats_reçus=len(results),
                statut="Code-barres Inconnu",
                details=f"Code-barres ou Code Tube {barcode} introuvable dans le système. Prélèvement non enregistré.",
                trame_brute=str(parsed_data.get("raw_records", []))[:1000]
            )
            db.add(log_entry)
            db.commit()
            messages.append(f"Code-barres / Tube '{barcode}' introuvable.")
            continue

        # Mise à jour du statut du tube si scanné directement
        if matched_tube:
            matched_tube.statut_tube = "Analysé"
            matched_tube.automate_id = automate_nom
            matched_tube.date_passage_automate = datetime.datetime.now()

        patient = demande.patient
        age = patient.age
        sexe = patient.sexe

        count_order_res = 0

        for r in results:
            param_code = r.get("param_code", "").strip().upper()
            valeur_str = r.get("valeur_str", "")
            valeur_num = r.get("valeur_num")
            automate_source = r.get("automate_source") or automate_nom

            if not param_code or not valeur_str:
                continue

            # Recherche du paramètre dans le catalogue
            param = db.query(AnalyseParameter).filter(AnalyseParameter.code == param_code).first()
            if not param:
                # Création automatique du paramètre s'il s'agit d'un nouveau code automate
                param = AnalyseParameter(
                    code=param_code,
                    nom=f"Analyse {param_code}",
                    categorie="Automate",
                    unite=r.get("unite", ""),
                    male_min=None, male_max=None,
                    female_min=None, female_max=None,
                    child_min=None, child_max=None,
                    automate_prefere=automate_nom
                )
                db.add(param)
                db.flush()

            # Calcul des valeurs de référence physiologiques selon Âge et Sexe
            ref_min, ref_max, label_ref = param.get_reference_range(age, sexe)

            hors_norme = False
            drapeau = "NORMAL"

            if valeur_num is not None:
                if ref_min is not None and valeur_num < ref_min:
                    hors_norme = True
                    drapeau = "BAS"
                elif ref_max is not None and valeur_num > ref_max:
                    hors_norme = True
                    drapeau = "ELEVE"
            else:
                # Évaluation d'après les drapeaux de l'automate si non numérique
                flag_automate = r.get("drapeau_automate", "N")
                if flag_automate in ("L", "LL"):
                    hors_norme = True
                    drapeau = "BAS"
                elif flag_automate in ("H", "HH", "A"):
                    hors_norme = True
                    drapeau = "ELEVE"

            # Recherche si un résultat existait déjà pour mettre à jour ou ajouter
            existing_res = db.query(Resultat).filter(
                Resultat.demande_id == demande.id,
                Resultat.parameter_id == param.id
            ).first()

            if existing_res:
                existing_res.valeur = valeur_str
                existing_res.valeur_num = valeur_num
                existing_res.automate_source = automate_source
                existing_res.hors_norme = hors_norme
                existing_res.drapeau = drapeau
                existing_res.ref_min_applique = ref_min
                existing_res.ref_max_applique = ref_max
                existing_res.date_analyse = datetime.datetime.now()
                if "commentaire" in r:
                    existing_res.commentaire = r["commentaire"]
            else:
                new_res = Resultat(
                    demande_id=demande.id,
                    parameter_id=param.id,
                    valeur=valeur_str,
                    valeur_num=valeur_num,
                    automate_source=automate_source,
                    hors_norme=hors_norme,
                    drapeau=drapeau,
                    ref_min_applique=ref_min,
                    ref_max_applique=ref_max,
                    date_analyse=datetime.datetime.now(),
                    commentaire=r.get("commentaire")
                )
                db.add(new_res)

            total_ingested += 1
            count_order_res += 1

        # Mise à jour du statut de la demande
        if demande.statut != "Validé":
            demande.statut = "Résultats reçus"

        demandes_traitees.append(barcode)

        # Journal d'audit
        log_entry = AutomateLog(
            automate_nom=automate_nom,
            code_barres_detecte=barcode,
            nb_resultats_reçus=count_order_res,
            statut="Succès",
            details=f"Intégration réussie de {count_order_res} paramètres pour le prélèvement {barcode}.",
            trame_brute=str(parsed_data.get("raw_records", []))[:1000]
        )
        db.add(log_entry)

    db.commit()

    return {
        "status": "success",
        "automate": automate_nom,
        "demandes_mises_a_jour": demandes_traitees,
        "total_resultats_ingérés": total_ingested,
        "messages": messages
    }
