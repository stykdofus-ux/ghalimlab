"""
Modèles de Facturation, Tarification et Nomenclature des Actes de Biologie Médicale.
Conforme à la nomenclature officielle marocaine des actes de biologie médicale (Arrêté 1796-03 & 1968-16).
Prise en charge différenciée :
- CNSS / CNOPS : Prix = Coefficient B x 1.10 DH
- Normal / Assurances privées : Prix = Coefficient B x 1.36 DH
"""

import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base


class ActeBiologique(Base):
    """
    Nomenclature officielle des actes d'analyses biomédicales (ex: B100, B216, etc.)
    avec coefficient B et tarifs calculés selon le type de couverture.
    """
    __tablename__ = "actes_biologiques"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, index=True, nullable=False, doc="Code officiel ex: B100, B216")
    nom = Column(String(255), index=True, nullable=False, doc="Désignation complète de l'analyse")
    coefficient = Column(Float, nullable=False, default=30.0, doc="Valeur du coefficient B")
    categorie = Column(String(100), default="Biochimie", index=True, doc="Biochimie, Hématologie, etc.")
    
    # Prix calculés ou personnalisés par le biologiste
    prix_cnss = Column(Float, nullable=False, default=33.0, doc="Tarif conventionné CNSS / CNOPS (Coeff x 1.10)")
    prix_normal = Column(Float, nullable=False, default=40.8, doc="Tarif privé / Assurances (Coeff x 1.36)")
    
    actif = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.datetime.now)
    date_modification = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    def __repr__(self):
        return f"<Acte {self.code} - {self.nom[:25]} (B{self.coefficient})>"

    def calculer_prix(self, type_prise_en_charge: str = "Normal", taux_custom: float = None) -> float:
        """Calcule le tarif selon le type de prise en charge."""
        type_norm = (type_prise_en_charge or "").strip().lower()
        if "cnss" in type_norm or "cnops" in type_norm:
            if taux_custom is not None:
                return round(self.coefficient * taux_custom, 2)
            return round(self.prix_cnss, 2)
        else:
            if taux_custom is not None:
                return round(self.coefficient * taux_custom, 2)
            return round(self.prix_normal, 2)


class ParametreTarification(Base):
    """
    Paramètres globaux de tarification configurables par le biologiste médical.
    """
    __tablename__ = "parametres_tarification"

    id = Column(Integer, primary_key=True, index=True)
    taux_cnss_cnops = Column(Float, default=1.10, doc="Multiplicateur officiel CNSS / CNOPS (1.10 DH par unité B)")
    taux_normal_assurance = Column(Float, default=1.36, doc="Multiplicateur privé / assurances (1.36 DH par unité B)")
    devise = Column(String(10), default="DH")
    tva_applicable = Column(Float, default=0.0, doc="Taux de TVA (%) si applicable (0% pour actes médicaux exonérés)")
    frais_prelevement = Column(Float, default=0.0, doc="Frais de prélèvement à domicile ou acte spécifique")
    
    # Mentions légales sur les factures et reçus
    nom_laboratoire = Column(String(150), default="Laboratoire d'Analyses Médicales GhalimLab")
    ice = Column(String(50), default="002847192000045", doc="Identifiant Commun de l'Entreprise")
    identifiant_fiscal = Column(String(50), default="40291823")
    patente = Column(String(50), default="32194850")
    cnss_affiliation = Column(String(50), default="7849201")
    mentions_legales = Column(
        Text,
        default="Laboratoire d'analyses médicales conventionné avec la CNSS, la CNOPS et les compagnies d'assurances privées. Facture établie conformément aux tarifs réglementaires."
    )
    date_modification = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)


class Facture(Base):
    """
    Facture / Reçu de règlement émis pour un dossier de prélèvement.
    """
    __tablename__ = "factures"

    id = Column(Integer, primary_key=True, index=True)
    numero_facture = Column(String(50), unique=True, index=True, nullable=False, doc="ex: FAC-2026-0001")
    demande_id = Column(Integer, ForeignKey("demandes.id"), nullable=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    date_facture = Column(DateTime, default=datetime.datetime.now)
    
    # Couverture médicale
    type_prise_en_charge = Column(
        String(50),
        default="Normal",
        doc="'Normal' | 'CNSS' | 'CNOPS' | 'Assurance Privée'"
    )
    taux_applique = Column(Float, default=1.36, doc="1.10 pour CNSS/CNOPS ou 1.36 pour Normal/Assurances")
    organisme_nom = Column(String(100), nullable=True, doc="ex: CNSS, CNOPS, Wafa Assurance, RMA, Saham")
    numero_prise_en_charge = Column(String(100), nullable=True, doc="N° d'accord ou d'immatriculation")

    # Décomposition financière
    total_b = Column(Float, default=0.0, doc="Somme des coefficients B")
    montant_brut = Column(Float, default=0.0, doc="Total brut en DH")
    remise_pourcent = Column(Float, default=0.0)
    remise_montant = Column(Float, default=0.0)
    montant_net = Column(Float, default=0.0, doc="Montant net à payer en DH")
    
    # Tiers-payant
    part_organisme = Column(Float, default=0.0, doc="Montant couvert par CNSS / CNOPS / Assurance")
    part_patient = Column(Float, default=0.0, doc="Ticket modérateur à la charge du patient")
    
    # Paiement & Recouvrement
    montant_paye = Column(Float, default=0.0, doc="Montant effectivement encaissé")
    reste_a_payer = Column(Float, default=0.0, doc="Solde débiteur")
    
    statut_paiement = Column(
        String(50),
        default="Non payé",
        doc="'Non payé' | 'Avance versée' | 'Payé intégralement' | 'Tiers-Payant / Prise en charge'"
    )
    mode_paiement = Column(
        String(50),
        default="Espèces",
        doc="'Espèces' | 'Carte Bancaire' | 'Chèque' | 'Virement' | 'Tiers-Payant'"
    )
    reference_paiement = Column(String(100), nullable=True, doc="Numéro du chèque, autorisation TPE, etc.")
    date_paiement = Column(DateTime, nullable=True)

    cree_par = Column(String(100), default="Secrétariat Facturation")
    notes = Column(Text, nullable=True)

    # Relations
    demande = relationship("Demande", backref="factures")
    patient = relationship("Patient", backref="factures")
    lignes = relationship("FactureLigne", back_populates="facture", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Facture {self.numero_facture} - {self.montant_net} DH ({self.statut_paiement})>"


class FactureLigne(Base):
    """
    Ligne de détail d'une facture correspondant à une analyse facturée.
    """
    __tablename__ = "factures_lignes"

    id = Column(Integer, primary_key=True, index=True)
    facture_id = Column(Integer, ForeignKey("factures.id"), nullable=False, index=True)
    acte_id = Column(Integer, ForeignKey("actes_biologiques.id"), nullable=True)
    
    code_acte = Column(String(30), nullable=False, doc="ex: B100")
    nom_acte = Column(String(255), nullable=False)
    coefficient = Column(Float, default=0.0)
    prix_unitaire = Column(Float, default=0.0)
    quantite = Column(Integer, default=1)
    total_ligne = Column(Float, default=0.0)

    facture = relationship("Facture", back_populates="lignes")
    acte = relationship("ActeBiologique")

    def __repr__(self):
        return f"<FactureLigne {self.code_acte} x{self.quantite} = {self.total_ligne} DH>"
