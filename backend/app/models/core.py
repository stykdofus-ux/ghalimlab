"""
Modèles de base de données principaux pour le LIMS:
- Patient
- Demande (Échantillon / Prélèvement)
- AnalyseParameter (Catalogue d'analyses avec valeurs de référence par âge/sexe)
- Resultat (Mesures reçues des automates ou saisies manuellement)
- AutomateLog (Journal d'audit des réceptions ASTM)
"""

import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    cin = Column(String(50), unique=True, index=True, nullable=False, doc="CIN ou Identifiant National")
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    date_naissance = Column(String(20), nullable=False, doc="Format AAAA-MM-JJ")
    sexe = Column(String(10), nullable=False, doc="'M' pour Homme, 'F' pour Femme")
    telephone = Column(String(30), nullable=True)
    adresse = Column(String(255), nullable=True)
    numero_securite_sociale = Column(String(50), nullable=True, doc="Numéro CNSS, CNOPS ou Assurance")
    date_creation = Column(DateTime, default=datetime.datetime.now)

    # Relations
    demandes = relationship("Demande", back_populates="patient", cascade="all, delete-orphan")
    documents_scannes = relationship("DocumentScanne", back_populates="patient", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Patient {self.nom} {self.prenom} ({self.cin})>"

    @property
    def age(self) -> int:
        """Calcule l'âge approximatif du patient en années."""
        try:
            annee_naiss = int(self.date_naissance.split("-")[0])
            annee_actuelle = datetime.date.today().year
            return max(0, annee_actuelle - annee_naiss)
        except Exception:
            return 30


class AnalyseParameter(Base):
    __tablename__ = "analyse_parameters"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False, doc="Code ASTM ou interne (ex: WBC, HGB, GLU)")
    nom = Column(String(150), nullable=False, doc="Désignation complète du paramètre")
    categorie = Column(String(80), nullable=False, default="Hématologie", doc="Hématologie, Biochimie, etc.")
    unite = Column(String(30), nullable=True, doc="Unité biologique (ex: g/dL, 10^3/uL, g/L)")

    # Intervalles de référence biologiques par sexe et âge
    male_min = Column(Float, nullable=True)
    male_max = Column(Float, nullable=True)
    female_min = Column(Float, nullable=True)
    female_max = Column(Float, nullable=True)
    child_min = Column(Float, nullable=True)
    child_max = Column(Float, nullable=True)

    ordre_affichage = Column(Integer, default=0)
    methode = Column(String(120), nullable=True, doc="Méthode d'analyse (ex: Impédancimétrie, Enzymatique)")
    automate_prefere = Column(String(80), nullable=True, doc="Sysmex XN-1000, Cobas c501, etc.")

    # Relations
    resultats = relationship("Resultat", back_populates="parametre")

    def __repr__(self):
        return f"<AnalyseParameter {self.code} - {self.nom}>"

    def get_reference_range(self, age: int, sexe: str):
        """Retourne (min, max, label) selon l'âge et le sexe du patient."""
        sexe_up = (sexe or "").upper()
        if age < 15:
            # Enfant
            return (self.child_min, self.child_max, "Enfant (< 15 ans)")
        elif sexe_up == "F":
            # Femme
            return (self.female_min, self.female_max, "Femme")
        else:
            # Homme par défaut
            return (self.male_min, self.male_max, "Homme")


class Demande(Base):
    __tablename__ = "demandes"

    id = Column(Integer, primary_key=True, index=True)
    code_barres = Column(String(60), unique=True, index=True, nullable=False, doc="Identifiant unique de prélèvement")
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    date_reception = Column(DateTime, default=datetime.datetime.now)
    statut = Column(
        String(40),
        default="En attente",
        doc="'En attente' | 'Résultats reçus' | 'Validé'"
    )
    prescripteur = Column(String(120), nullable=True, default="Dr. Externe")
    renseignements_cliniques = Column(Text, nullable=True)
    bilan_demande = Column(String(200), default="NFS, Bilan Métabolique")

    date_validation = Column(DateTime, nullable=True)
    valide_par = Column(String(100), nullable=True)
    conclusion_biologique = Column(Text, nullable=True)

    # Relations
    patient = relationship("Patient", back_populates="demandes")
    resultats = relationship("Resultat", back_populates="demande", cascade="all, delete-orphan")
    documents_scannes = relationship("DocumentScanne", back_populates="demande")
    tubes = relationship("EchantillonTube", back_populates="demande", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Demande {self.code_barres} - Statut: {self.statut}>"


class Resultat(Base):
    __tablename__ = "resultats"

    id = Column(Integer, primary_key=True, index=True)
    demande_id = Column(Integer, ForeignKey("demandes.id"), nullable=False)
    parameter_id = Column(Integer, ForeignKey("analyse_parameters.id"), nullable=False)
    valeur = Column(String(50), nullable=False, doc="Valeur textuelle ou numérique brute")
    valeur_num = Column(Float, nullable=True)
    automate_source = Column(String(80), default="Manuel", doc="'Sysmex', 'Cobas', 'Manuel', etc.")

    # Évaluation biologique
    hors_norme = Column(Boolean, default=False)
    drapeau = Column(String(20), default="NORMAL", doc="'NORMAL' | 'ELEVE' | 'BAS'")
    ref_min_applique = Column(Float, nullable=True)
    ref_max_applique = Column(Float, nullable=True)

    date_analyse = Column(DateTime, default=datetime.datetime.now)
    commentaire = Column(Text, nullable=True)

    # Relations
    demande = relationship("Demande", back_populates="resultats")
    parametre = relationship("AnalyseParameter", back_populates="resultats")

    def __repr__(self):
        return f"<Resultat {self.parametre.code if self.parametre else self.parameter_id}: {self.valeur} ({self.drapeau})>"


class AutomateLog(Base):
    __tablename__ = "automate_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    automate_nom = Column(String(100), default="Sysmex/Cobas")
    code_barres_detecte = Column(String(60), nullable=True)
    nb_resultats_reçus = Column(Integer, default=0)
    statut = Column(String(40), default="Succès")  # 'Succès', 'Erreur Checksum', 'Code-barres Inconnu'
    details = Column(Text, nullable=True)
    trame_brute = Column(Text, nullable=True)


class DocumentScanne(Base):
    """Documents et bulletins scannés (Ordonnances, Scanners / Imagerie, Comptes-rendus externes)."""
    __tablename__ = "documents_scannes"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    demande_id = Column(Integer, ForeignKey("demandes.id"), nullable=True)
    titre = Column(String(150), nullable=False)
    type_document = Column(
        String(80),
        default="Ordonnance",
        doc="'Ordonnance' | 'Résultat d\'Imagerie / Scanner' | 'Bilan Antérieur' | 'Prise en charge' | 'Autre'"
    )
    nom_fichier_original = Column(String(255), nullable=False)
    nom_fichier_stocke = Column(String(255), nullable=False)
    chemin_fichier = Column(String(500), nullable=False)
    taille_octets = Column(Integer, default=0)
    mime_type = Column(String(100), default="application/pdf")
    date_televersement = Column(DateTime, default=datetime.datetime.now)
    ajoute_par = Column(String(100), default="Secrétariat Médical")
    notes = Column(Text, nullable=True)

    # Relations
    patient = relationship("Patient", back_populates="documents_scannes")
    demande = relationship("Demande", back_populates="documents_scannes")

    def __repr__(self):
        return f"<DocumentScanne {self.titre} ({self.type_document})>"


class EchantillonTube(Base):
    """
    Identification et traçabilité pré-analytique et analytique du tube échantillon.
    Gère l'étiquetage par code-barres et les statuts depuis le prélèvement jusqu'à l'archivage.
    """
    __tablename__ = "echantillons_tubes"

    id = Column(Integer, primary_key=True, index=True)
    demande_id = Column(Integer, ForeignKey("demandes.id"), nullable=False)
    code_tube = Column(String(80), unique=True, index=True, nullable=False, doc="Code-barres unique du tube (ex: PREL-2026-002-EDTA)")
    type_tube = Column(String(80), nullable=False, default="EDTA", doc="EDTA, Sec / Gel, Citrate, Héparine, Flacon Stérile")
    couleur_bouchon = Column(String(30), default="violet", doc="violet, jaune, bleu, vert, rouge, gris")
    analyses_associees = Column(String(200), default="NFS Complète")
    volume_ml = Column(Float, nullable=True, default=3.0)

    # Chaîne de traçabilité
    statut_tube = Column(
        String(50),
        default="Non prélevé",
        doc="'Non prélevé' | 'Prélevé' | 'Reçu au Laboratoire' | 'Centrifugé' | 'En cours sur automate' | 'Analysé' | 'Archivé en sérothèque' | 'Rejeté / Hémolysé'"
    )
    date_creation = Column(DateTime, default=datetime.datetime.now)
    date_prelevement = Column(DateTime, nullable=True)
    preleve_par = Column(String(100), nullable=True, doc="Infirmière ou préleveur")
    date_reception_labo = Column(DateTime, nullable=True)
    receptionne_par = Column(String(100), nullable=True)
    conformite_preanalytique = Column(String(50), default="Conforme", doc="'Conforme' | 'Hémolysé' | 'Coagulé' | 'Volume insuffisant'")
    emplacement_serotheque = Column(String(100), nullable=True, doc="ex: Frigo 2 - Rack A3")
    date_archivage = Column(DateTime, nullable=True)
    remarques = Column(Text, nullable=True)

    # Relations
    demande = relationship("Demande", back_populates="tubes")

    def __repr__(self):
        return f"<EchantillonTube {self.code_tube} ({self.type_tube}) - {self.statut_tube}>"
