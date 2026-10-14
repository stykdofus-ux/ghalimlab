"""
Service Métier de Facturation & Tarification Médicale :
- Ingestion des 492 actes de biologie médicale depuis la nomenclature officielle
- Calcul des tarifs conventionnés (CNSS/CNOPS = Coeff x 1.10, Normal/Assurances = Coeff x 1.36)
- Génération et suivi des factures et règlements
"""

import os
import json
import random
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models.billing import ActeBiologique, ParametreTarification, Facture, FactureLigne
from backend.app.models.core import Demande, Patient
from backend.app.config import BASE_DIR

JSON_ACTES_PATH = BASE_DIR / "backend" / "app" / "services" / "actes_extracted.json"


def get_or_create_tarification_params(db: Session) -> ParametreTarification:
    """Retourne les paramètres de tarification uniques du laboratoire ou les initialise."""
    params = db.query(ParametreTarification).first()
    if not params:
        params = ParametreTarification(
            taux_cnss_cnops=1.10,
            taux_normal_assurance=1.36,
            devise="DH",
            tva_applicable=0.0,
            frais_prelevement=0.0,
            nom_laboratoire="Laboratoire d'Analyses Médicales GhalimLab",
            ice="002847192000045",
            identifiant_fiscal="40291823",
            patente="32194850",
            cnss_affiliation="7849201",
            mentions_legales="Laboratoire conventionné CNSS / CNOPS et compagnies d'assurances privées. Facture établie selon la nomenclature marocaine des actes de biologie médicale."
        )
        db.add(params)
        db.commit()
        db.refresh(params)
    return params


def seed_all_actes_from_json(db: Session, force_update: bool = False) -> int:
    """
    Charge l'intégralité des 492 actes de biologie depuis le fichier JSON extrait du PDF officiel
    et initialise leurs coefficients et tarifs (CNSS x 1.10 / Normal x 1.36).
    """
    params = get_or_create_tarification_params(db)
    taux_cnss = params.taux_cnss_cnops or 1.10
    taux_normal = params.taux_normal_assurance or 1.36

    count_existing = db.query(ActeBiologique).count()
    if count_existing >= 490 and not force_update:
        return count_existing

    if not JSON_ACTES_PATH.exists():
        return 0

    with open(JSON_ACTES_PATH, "r", encoding="utf-8") as f:
        actes_data = json.load(f)

    inserted = 0
    updated = 0

    for item in actes_data:
        code = item["code"].strip()
        nom = item["nom"].strip()
        coeff = float(item.get("coefficient", 0.0))
        section = item.get("section", "Biochimie").strip() or "Biochimie"

        # Tarification réglementaire
        p_cnss = round(coeff * taux_cnss, 2)
        p_normal = round(coeff * taux_normal, 2)

        existing = db.query(ActeBiologique).filter(ActeBiologique.code == code).first()
        if existing:
            if force_update:
                existing.nom = nom
                existing.coefficient = coeff
                existing.categorie = section
                existing.prix_cnss = p_cnss
                existing.prix_normal = p_normal
                updated += 1
        else:
            acte = ActeBiologique(
                code=code,
                nom=nom,
                coefficient=coeff,
                categorie=section,
                prix_cnss=p_cnss,
                prix_normal=p_normal,
                actif=True
            )
            db.add(acte)
            inserted += 1

    db.commit()
    return inserted + updated


def recalculate_all_actes_prices(db: Session, taux_cnss: float, taux_normal: float):
    """Met à jour les tarifs par défaut de tous les actes en fonction des nouveaux multiplicateurs."""
    actes = db.query(ActeBiologique).all()
    for a in actes:
        a.prix_cnss = round(a.coefficient * taux_cnss, 2)
        a.prix_normal = round(a.coefficient * taux_normal, 2)
    db.commit()


def generate_unique_facture_number(db: Session) -> str:
    """Génère un numéro unique de facture séquentiel (ex: FAC-2026-0001)."""
    annee = datetime.date.today().year
    count_today = db.query(Facture).count() + 1
    for _ in range(100):
        candidat = f"FAC-{annee}-{count_today:04d}"
        if not db.query(Facture).filter(Facture.numero_facture == candidat).first():
            return candidat
        count_today += 1
    return f"FAC-{annee}-{int(datetime.datetime.now().timestamp()) % 10000:04d}"


# Table de correspondance rapide entre mots-clés du bilan médical et codes d'actes
MAPPING_BILAN_ACTES = [
    # Hématologie
    (["nfs", "hémogramme", "hemogramme", "formule"], ["B216"]),  # Numération Formule B80
    (["plaquettes"], ["B217"]),  # Numération plaquettes B30
    (["vitesse de sédimentation", "vs"], ["B222"]),  # VS B20
    (["frottis"], ["B221"]),  # Frottis sanguin B30
    (["goutte épaisse", "paludisme"], ["B213"]),  # Goutte épaisse B50
    # Biochimie
    (["glycémie", "glycemie", "glucose"], ["B132"]),  # Glycémie B20
    (["urée", "uree"], ["B149"]),  # Urée sanguine B20
    (["créatinine", "creatinine", "créat"], ["B111"]),  # Créatinine B30
    (["acide urique", "uricémie"], ["B100"]),  # Acide urique B30
    (["calcium", "calcémie"], ["B104"]),  # Calcium B30
    (["chlore", "chlorémie"], ["B105"]),  # Chlore B30
    (["potassium", "sodium", "ionogramme", "iono"], ["B145", "B146"]),  # Sodium B25, Potassium B25
    (["crp", "protéine c-réactive"], ["B125"]),  # CRP B60
    # Bilan Lipidique
    (["cholestérol total", "cholesterol"], ["B106"]),  # Cholestérol total B30
    (["triglycérides", "triglycerides"], ["B152"]),  # Triglycérides B40
    (["hdl"], ["B108"]),  # Cholestérol HDL B50
    (["ldl"], ["B109"]),  # Cholestérol LDL B50
    (["bilan lipidique", "profil lipidique"], ["B106", "B108", "B109", "B152"]),
    # Hépatique
    (["transaminases", "alat", "asat", "tgo", "tgp"], ["B153", "B154"]),  # Transaminases
    (["bilirubine"], ["B103"]),  # Bilirubine Totale Directe B70
    # Hémostase
    (["tp", "inr", "prothrombine"], ["B227"]),  # Taux de prothrombine B50
    (["tca", "céphaline"], ["B232"]),  # TCA B50
    (["hémostase", "coagulation"], ["B227", "B232"]),
    # Bactériologie & Urines
    (["ecbu", "urine", "bactériologie"], ["B248"]),  # ECBU B120
    (["antibiogramme"], ["B254"]),  # Antibiogramme standard B80
    (["hémoculture"], ["B245"]),  # Hémoculture B150
    # Parasitologie
    (["eps", "selles", "parasitologie"], ["B257"]),  # Examen parasitologique selles B60
]


def match_actes_from_bilan_text(bilan_text: str, db: Session) -> List[ActeBiologique]:
    """Analyse le texte du bilan demandé et retourne les actes suggérés."""
    text_lower = (bilan_text or "").lower()
    selected_codes = set()

    for keywords, codes in MAPPING_BILAN_ACTES:
        if any(kw in text_lower for kw in keywords):
            for c in codes:
                selected_codes.add(c)

    # Si rien n'est détecté, suggérer au moins NFS et Glycémie par défaut
    if not selected_codes:
        selected_codes = {"B216", "B132"}

    return db.query(ActeBiologique).filter(ActeBiologique.code.in_(list(selected_codes))).all()


def create_or_update_facture(
    db: Session,
    patient_id: int,
    demande_id: Optional[int] = None,
    type_prise_en_charge: str = "Normal",
    organisme_nom: Optional[str] = None,
    numero_prise_en_charge: Optional[str] = None,
    lignes_data: Optional[List[Dict[str, Any]]] = None,
    remise_pourcent: float = 0.0,
    montant_paye: float = 0.0,
    mode_paiement: str = "Espèces",
    reference_paiement: Optional[str] = None,
    notes: Optional[str] = None,
    cree_par: str = "Secrétariat Facturation"
) -> Facture:
    """
    Crée ou met à jour une facture médicale avec calculs stricts des coefficients et montants.
    """
    params = get_or_create_tarification_params(db)

    # Déterminer le coefficient multiplicateur (1.10 si CNSS/CNOPS, 1.36 si Normal/Assurance)
    type_norm = (type_prise_en_charge or "Normal").strip().lower()
    if "cnss" in type_norm or "cnops" in type_norm:
        taux_applique = params.taux_cnss_cnops or 1.10
    else:
        taux_applique = params.taux_normal_assurance or 1.36

    # Vérifier si une facture existe déjà pour cette demande
    facture = None
    if demande_id:
        facture = db.query(Facture).filter(Facture.demande_id == demande_id).first()

    if not facture:
        num_fac = generate_unique_facture_number(db)
        facture = Facture(
            numero_facture=num_fac,
            demande_id=demande_id,
            patient_id=patient_id,
            date_facture=datetime.datetime.now(),
            type_prise_en_charge=type_prise_en_charge,
            taux_applique=taux_applique,
            organisme_nom=organisme_nom,
            numero_prise_en_charge=numero_prise_en_charge,
            cree_par=cree_par,
            notes=notes
        )
        db.add(facture)
        db.flush()
    else:
        facture.type_prise_en_charge = type_prise_en_charge
        facture.taux_applique = taux_applique
        facture.organisme_nom = organisme_nom
        facture.numero_prise_en_charge = numero_prise_en_charge
        if notes:
            facture.notes = notes

    # Si des lignes sont spécifiées, vider les anciennes et recréer
    if lignes_data is not None:
        # Supprimer les lignes existantes
        db.query(FactureLigne).filter(FactureLigne.facture_id == facture.id).delete()
        db.flush()

        total_b = 0.0
        total_brut = 0.0

        for item in lignes_data:
            code = item.get("code_acte", "").strip()
            nom = item.get("nom_acte", "").strip()
            coeff = float(item.get("coefficient", 0.0))
            qte = int(item.get("quantite", 1))

            # Prix unitaire selon le type de prise en charge
            prix_unit = item.get("prix_unitaire")
            if prix_unit is None or float(prix_unit) <= 0:
                prix_unit = round(coeff * taux_applique, 2)
            else:
                prix_unit = float(prix_unit)

            total_ligne = round(prix_unit * qte, 2)

            total_b += (coeff * qte)
            total_brut += total_ligne

            ligne = FactureLigne(
                facture_id=facture.id,
                acte_id=item.get("acte_id"),
                code_acte=code,
                nom_acte=nom,
                coefficient=coeff,
                prix_unitaire=prix_unit,
                quantite=qte,
                total_ligne=total_ligne
            )
            db.add(ligne)

        facture.total_b = round(total_b, 2)
        facture.montant_brut = round(total_brut, 2)

    # Calcul de la remise et du net
    facture.remise_pourcent = remise_pourcent
    remise_val = round((facture.montant_brut * (remise_pourcent / 100.0)), 2)
    facture.remise_montant = remise_val
    facture.montant_net = round(facture.montant_brut - remise_val, 2)

    # Répartition Tiers-Payant / Ticket Modérateur Patient
    if "cnss" in type_norm or "cnops" in type_norm or "assurance" in type_norm:
        # En règle générale pour les caisses conventionnées, prise en charge partielle ou totale
        if "cnss" in type_norm or "cnops" in type_norm:
            facture.part_organisme = round(facture.montant_net * 0.80, 2)  # 80% organisme
            facture.part_patient = round(facture.montant_net - facture.part_organisme, 2)  # 20% ticket modérateur
        else:
            facture.part_organisme = round(facture.montant_net, 2)
            facture.part_patient = 0.0
    else:
        facture.part_organisme = 0.0
        facture.part_patient = facture.montant_net

    # Gestion des règlements
    if montant_paye is not None and montant_paye > 0:
        facture.montant_paye = float(montant_paye)
        facture.mode_paiement = mode_paiement
        facture.reference_paiement = reference_paiement
        if not facture.date_paiement:
            facture.date_paiement = datetime.datetime.now()

    # Reste à payer
    facture.reste_a_payer = max(0.0, round(facture.montant_net - (facture.montant_paye or 0.0), 2))

    # Statut
    if facture.reste_a_payer <= 0 and facture.montant_net > 0:
        facture.statut_paiement = "Payé intégralement"
    elif (facture.montant_paye or 0.0) > 0:
        facture.statut_paiement = "Avance versée"
    elif facture.part_organisme > 0 and facture.part_patient == 0:
        facture.statut_paiement = "Tiers-Payant / Prise en charge"
    else:
        facture.statut_paiement = "Non payé"

    db.commit()
    db.refresh(facture)
    return facture
