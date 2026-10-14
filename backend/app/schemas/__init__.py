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

