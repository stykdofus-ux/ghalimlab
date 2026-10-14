"""
Schémas Pydantic pour la validation des données d'API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PatientBase(BaseModel):
    cin: str = Field(..., description="Numéro CIN ou Identifiant National")
    nom: str = Field(..., description="Nom de famille")
    prenom: str = Field(..., description="Prénom")
    date_naissance: str = Field(..., description="Date de naissance (AAAA-MM-JJ)")
    sexe: str = Field(..., description="'M' ou 'F'")
    telephone: Optional[str] = None
    adresse: Optional[str] = None
    numero_securite_sociale: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientResponse(PatientBase):
    id: int
    date_creation: datetime
    age: int

    model_config = {"from_attributes": True}


class DemandeCreate(BaseModel):
    patient_id: int
    prescripteur: Optional[str] = "Dr. Externe"
    renseignements_cliniques: Optional[str] = None
    bilan_demande: Optional[str] = "NFS, Bilan Métabolique"
    code_barres: Optional[str] = None  # Si non fourni, auto-généré


class ResultatItem(BaseModel):
    parameter_id: int
    valeur: str
    automate_source: Optional[str] = "Manuel"
    commentaire: Optional[str] = None


class ValidationRequest(BaseModel):
    conclusion_biologique: Optional[str] = None
    valide_par: Optional[str] = "Dr. M. GHALIM"
    resultats_modifies: Optional[List[ResultatItem]] = None


class AntibiogrammeItem(BaseModel):
    antibiotique_nom: str
    famille: Optional[str] = None
    diametre_zone: Optional[float] = None
    cmi: Optional[float] = None
    sensibilite: str = "S"  # 'S', 'I', 'R'


class BacteriologieCreate(BaseModel):
    demande_id: int
    type_prelevement: str = "ECBU (Urine)"
    aspect_macroscopique: Optional[str] = "Trouble"
    cytologie_leucocytes: Optional[str] = None
    cytologie_hematies: Optional[str] = None
    cellules_epitheliales: Optional[str] = None
    coloration_gram: Optional[str] = None
    culture_resultat: Optional[str] = "Positive"
    germe_identifie: Optional[str] = None
    numeration_colonies: Optional[str] = None
    conclusion: Optional[str] = None
    antibiogrammes: Optional[List[AntibiogrammeItem]] = []


class ParasitologieCreate(BaseModel):
    demande_id: int
    type_analyse: str = "EPS (Selles)"
    consistance: Optional[str] = "Moulée"
    aspect_couleur: Optional[str] = "Brune"
    examen_direct: Optional[str] = "Absence d'éléments parasitaires"
    technique_concentration: Optional[str] = "Ritchie"
    parasite_identifie: Optional[str] = None
    frottis_goutte_epaisse: Optional[str] = None
    recherche_mycologique: Optional[str] = None
    culture_sabouraud: Optional[str] = "Négative"
    conclusion: Optional[str] = None


class TubeCreate(BaseModel):
    demande_id: int
    code_tube: Optional[str] = None
    type_tube: str = "EDTA K3 / K2"
    couleur_bouchon: str = "violet"
    analyses_associees: Optional[str] = "NFS Complète"
    volume_ml: Optional[float] = 3.0


class TubeUpdate(BaseModel):
    statut_tube: Optional[str] = None
    preleve_par: Optional[str] = None
    receptionne_par: Optional[str] = None
    conformite_preanalytique: Optional[str] = None
    emplacement_serotheque: Optional[str] = None
    remarques: Optional[str] = None


class TubeResponse(BaseModel):
    id: int
    demande_id: int
    code_tube: str
    type_tube: str
    couleur_bouchon: str
    analyses_associees: Optional[str] = None
    volume_ml: Optional[float] = None
    statut_tube: str
    conformite_preanalytique: str
    emplacement_serotheque: Optional[str] = None
    preleve_par: Optional[str] = None
    receptionne_par: Optional[str] = None
    remarques: Optional[str] = None
    date_creation: Optional[datetime] = None
    date_prelevement: Optional[datetime] = None
    date_reception_labo: Optional[datetime] = None
    date_archivage: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Schémas de Facturation & Nomenclature ---

class ActeBase(BaseModel):
    code: str
    nom: str
    coefficient: float
    categorie: Optional[str] = "Biochimie"
    prix_cnss: Optional[float] = None
    prix_normal: Optional[float] = None
    actif: Optional[bool] = True


class ActeCreate(ActeBase):
    pass


class ActeUpdate(BaseModel):
    nom: Optional[str] = None
    coefficient: Optional[float] = None
    categorie: Optional[str] = None
    prix_cnss: Optional[float] = None
    prix_normal: Optional[float] = None
    actif: Optional[bool] = None


class ActeResponse(ActeBase):
    id: int
    prix_cnss: float
    prix_normal: float
    date_creation: Optional[datetime] = None
    date_modification: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ParametresTarificationUpdate(BaseModel):
    taux_cnss_cnops: Optional[float] = None
    taux_normal_assurance: Optional[float] = None
    devise: Optional[str] = None
    tva_applicable: Optional[float] = None
    frais_prelevement: Optional[float] = None
    nom_laboratoire: Optional[str] = None
    ice: Optional[str] = None
    identifiant_fiscal: Optional[str] = None
    patente: Optional[str] = None
    cnss_affiliation: Optional[str] = None
    mentions_legales: Optional[str] = None
    recalculer_prix_actes: Optional[bool] = False  # Si True, recalcule les prix par défaut de tous les actes


class ParametresTarificationResponse(BaseModel):
    id: int
    taux_cnss_cnops: float
    taux_normal_assurance: float
    devise: str
    tva_applicable: float
    frais_prelevement: float
    nom_laboratoire: str
    ice: Optional[str] = None
    identifiant_fiscal: Optional[str] = None
    patente: Optional[str] = None
    cnss_affiliation: Optional[str] = None
    mentions_legales: Optional[str] = None
    date_modification: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FactureLigneItem(BaseModel):
    acte_id: Optional[int] = None
    code_acte: str
    nom_acte: str
    coefficient: float = 0.0
    prix_unitaire: float = 0.0
    quantite: int = 1


class FactureCreate(BaseModel):
    demande_id: Optional[int] = None
    patient_id: int
    type_prise_en_charge: str = "Normal"  # 'Normal', 'CNSS', 'CNOPS', 'Assurance Privée'
    organisme_nom: Optional[str] = None
    numero_prise_en_charge: Optional[str] = None
    remise_pourcent: Optional[float] = 0.0
    montant_paye: Optional[float] = 0.0
    mode_paiement: Optional[str] = "Espèces"
    reference_paiement: Optional[str] = None
    lignes: Optional[List[FactureLigneItem]] = []
    notes: Optional[str] = None


class FactureUpdate(BaseModel):
    type_prise_en_charge: Optional[str] = None
    organisme_nom: Optional[str] = None
    numero_prise_en_charge: Optional[str] = None
    montant_paye: Optional[float] = None
    statut_paiement: Optional[str] = None
    mode_paiement: Optional[str] = None
    reference_paiement: Optional[str] = None
    remise_pourcent: Optional[float] = None
    notes: Optional[str] = None


class FactureLigneResponse(BaseModel):
    id: int
    code_acte: str
    nom_acte: str
    coefficient: float
    prix_unitaire: float
    quantite: int
    total_ligne: float

    model_config = {"from_attributes": True}


class FactureResponse(BaseModel):
    id: int
    numero_facture: str
    demande_id: Optional[int] = None
    patient_id: int
    date_facture: datetime
    type_prise_en_charge: str
    taux_applique: float
    organisme_nom: Optional[str] = None
    numero_prise_en_charge: Optional[str] = None
    total_b: float
    montant_brut: float
    remise_pourcent: float
    remise_montant: float
    montant_net: float
    part_organisme: float
    part_patient: float
    montant_paye: float
    reste_a_payer: float
    statut_paiement: str
    mode_paiement: str
    reference_paiement: Optional[str] = None
    date_paiement: Optional[datetime] = None
    cree_par: str
    notes: Optional[str] = None
    lignes: List[FactureLigneResponse] = []

    model_config = {"from_attributes": True}


