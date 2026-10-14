"""
Module d'extension: Bactériologie & Virologie
Modèles modulaires pour l'ECBU, les prélèvements superficiels/profonds,
l'identification des germes et les antibiogrammes (Sensible / Intermédiaire / Résistant).
"""

import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from backend.app.database import Base


class ExamenBacteriologique(Base):
    __tablename__ = "examens_bacteriologiques"

    id = Column(Integer, primary_key=True, index=True)
    demande_id = Column(Integer, ForeignKey("demandes.id"), nullable=False)
    type_prelevement = Column(
        String(100),
        default="ECBU (Urine)",
        doc="ECBU, Prélèvement Vaginal, Écouvillon de Gorge, Pus, Hémoculture, etc."
    )
    aspect_macroscopique = Column(String(100), default="Limpide", doc="Trouble, Hématique, Purulent, etc.")
    cytologie_leucocytes = Column(String(80), nullable=True, doc="ex: 15 000 / mL (< 10 000)")
    cytologie_hematies = Column(String(80), nullable=True, doc="ex: 5 000 / mL (< 5 000)")
    cellules_epitheliales = Column(String(100), nullable=True, doc="Rares, Assez nombreuses, Nombreuses")
    coloration_gram = Column(String(150), nullable=True, doc="Bacilles Gram Négatif, Cocci Gram Positif, etc.")
    
    culture_resultat = Column(String(100), default="En cours", doc="'Stérile', 'Positive', 'Flore polymorphe'")
    germe_identifie = Column(String(150), nullable=True, doc="ex: Escherichia coli, Staphylococcus aureus")
    numeration_colonies = Column(String(100), nullable=True, doc="ex: > 10^5 UFC/mL")
    
    conclusion = Column(Text, nullable=True)
    date_examen = Column(DateTime, default=datetime.datetime.now)

    # Relations
    antibiogrammes = relationship("AntibiogrammeLigne", back_populates="examen_bact", cascade="all, delete-orphan")


class AntibiogrammeLigne(Base):
    """Ligne d'antibiogramme pour tester la sensibilité d'un germe à différents antibiotiques."""
    __tablename__ = "antibiogramme_lignes"

    id = Column(Integer, primary_key=True, index=True)
    examen_bact_id = Column(Integer, ForeignKey("examens_bacteriologiques.id"), nullable=False)
    antibiotique_nom = Column(String(100), nullable=False, doc="ex: Amoxicilline, Ciprofloxacine, Gentamicine")
    famille = Column(String(80), nullable=True, doc="Bêta-lactamines, Fluoroquinolones, Aminosides, etc.")
    diametre_zone = Column(Float, nullable=True, doc="Diamètre de la zone d'inhibition en mm")
    cmi = Column(Float, nullable=True, doc="Concentration Minimale Inhibitrice en mg/L")
    sensibilite = Column(String(20), default="S", doc="'S' (Sensible), 'I' (Intermédiaire), 'R' (Résistant)")

    examen_bact = relationship("ExamenBacteriologique", back_populates="antibiogrammes")
