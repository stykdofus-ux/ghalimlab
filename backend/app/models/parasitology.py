"""
Module d'extension: Parasitologie & Mycologie
Modèles modulaires pour l'Examen Parasitologique des Selles (EPS),
les frottis sanguins (Goutte épaisse/Paludisme), et les cultures mycologiques (Candida, Dermatophytes).
"""

import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from backend.app.database import Base


class ExamenParasitologique(Base):
    __tablename__ = "examens_parasitologiques"

    id = Column(Integer, primary_key=True, index=True)
    demande_id = Column(Integer, ForeignKey("demandes.id"), nullable=False)
    type_analyse = Column(
        String(100),
        default="EPS (Selles)",
        doc="EPS (Selles), Frottis sanguin (Paludisme), Scotch-test de Graham, Prélèvement unguéal (Ongles), etc."
    )
    consistance = Column(String(50), default="Moulée", doc="Moulée, Pâteuse, Liquide, Glaireuse")
    aspect_couleur = Column(String(50), default="Brune", doc="Brune, Décolorée, Sanglante")
    
    examen_direct = Column(String(200), default="Absence d'éléments parasitaires", doc="Kystes, trophozoïtes, œufs")
    technique_concentration = Column(String(100), default="Ritchie / Faust", doc="Méthode de concentration")
    parasite_identifie = Column(String(150), nullable=True, doc="ex: Entamoeba histolytica, Giardia lamblia, Ascaris")
    
    frottis_goutte_epaisse = Column(String(150), nullable=True, doc="Absence d'hématozoaires de Plasmodium")
    recherche_mycologique = Column(String(150), nullable=True, doc="Filaments mycéliens, Spores ou Levures")
    culture_sabouraud = Column(String(100), default="Négative", doc="Candida albicans, Trichophyton rubrum, etc.")
    
    conclusion = Column(Text, nullable=True)
    date_examen = Column(DateTime, default=datetime.datetime.now)
