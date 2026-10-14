"""
Configuration SQLAlchemy et gestion des sessions de base de données.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import DATABASE_URL

# Configuration pour SQLite (gestion des threads) ou PostgreSQL
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_db_schema_up_to_date(target_engine):
    """Vérifie et applique les migrations incrémentales de colonnes pour SQLite / PostgreSQL."""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(target_engine)
        if "parametres_tarification" in inspector.get_table_names():
            existing_cols = {col["name"] for col in inspector.get_columns("parametres_tarification")}
            columns_to_add = {
                "sous_titre": "VARCHAR(200) DEFAULT 'Biologie Médicale - Hématologie, Biochimie, Bactériologie, Parasitologie'",
                "directeur": "VARCHAR(150) DEFAULT 'Dr. M. GHALIM - Biologiste Médical Diplômé d''État'",
                "adresse": "VARCHAR(255) DEFAULT '124 Avenue Hassan II, Casablanca, Maroc'",
                "telephone": "VARCHAR(50) DEFAULT '+212 5 22 45 67 89'",
                "email": "VARCHAR(100) DEFAULT 'contact@ghalimlab.ma'",
                "site_web": "VARCHAR(100) DEFAULT 'www.ghalimlab.ma'",
                "agrement": "VARCHAR(100) DEFAULT 'Agrément Ministère de la Santé N° 8492/BM'",
                "titre_rapport": "VARCHAR(150) DEFAULT 'COMPTE-RENDU D''ANALYSES BIOMÉDICALES'",
                "logo_path": "VARCHAR(255) DEFAULT '/uploads/branding/logo.svg'",
                "cachet_path": "VARCHAR(255) DEFAULT '/uploads/branding/cachet.png'",
                "signature_path": "VARCHAR(255) DEFAULT '/uploads/branding/signature.png'",
                "auto_signer_validation": "BOOLEAN DEFAULT 1"
            }
            with target_engine.connect() as conn:
                for col_name, col_type in columns_to_add.items():
                    if col_name not in existing_cols:
                        try:
                            conn.execute(text(f"ALTER TABLE parametres_tarification ADD COLUMN {col_name} {col_type}"))
                            conn.commit()
                        except Exception:
                            pass
    except Exception:
        pass


def get_db():
    """Dépendance FastAPI pour obtenir une session de base de données."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
