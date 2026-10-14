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
    import datetime
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(target_engine)
        if "parametres_tarification" in inspector.get_table_names():
            existing_cols = {col["name"] for col in inspector.get_columns("parametres_tarification")}
            columns_to_add = {
                "sous_titre": "VARCHAR(200) DEFAULT 'Biologie Médicale - Hématologie, Biochimie, Bactériologie, Parasitologie'",
                "directeur": "VARCHAR(150) DEFAULT 'Dr. Kawtar GHALIM'",
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
                # Mettre à jour les informations du laboratoire par défaut si non personnalisées
                try:
                    conn.execute(text("""
                        UPDATE parametres_tarification 
                        SET nom_laboratoire = 'Laboratoire d''analyses médicales GhalimLab',
                            directeur = 'Dr. Kawtar GHALIM',
                            sous_titre = 'Biologie Médicale - Hématologie, Biochimie, Bactériologie, Parasitologie'
                        WHERE directeur LIKE '%M. GHALIM%' OR directeur IS NULL OR nom_laboratoire IS NULL OR nom_laboratoire = 'GhalimLab'
                    """))
                    conn.commit()
                except Exception:
                    pass

        # Migration du système d'identification des tubes vers YYMMDDNNN (ex: 261015001)
        if "echantillons_tubes" in inspector.get_table_names():
            with target_engine.connect() as conn:
                try:
                    rows = conn.execute(text("SELECT id, code_tube, date_creation FROM echantillons_tubes ORDER BY id ASC")).fetchall()
                    day_counters = {}
                    for row in rows:
                        c_tube = str(row[1] or "")
                        if len(c_tube) >= 9 and c_tube[:6].isdigit() and c_tube[6:].isdigit():
                            pfx = c_tube[:6]
                            seq = int(c_tube[6:])
                            day_counters[pfx] = max(day_counters.get(pfx, 0), seq)

                    for row in rows:
                        t_id = row[0]
                        c_tube = str(row[1] or "")
                        if not (len(c_tube) >= 9 and c_tube[:6].isdigit() and c_tube[6:].isdigit()):
                            d_creat = row[2]
                            d_obj = None
                            if d_creat:
                                try:
                                    if isinstance(d_creat, str):
                                        d_obj = datetime.datetime.fromisoformat(d_creat)
                                    else:
                                        d_obj = d_creat
                                except Exception:
                                    pass
                            if not d_obj:
                                d_obj = datetime.datetime.now()
                            pfx = d_obj.strftime("%y%m%d")
                            nxt = day_counters.get(pfx, 0) + 1
                            day_counters[pfx] = nxt
                            new_code = f"{pfx}{nxt:03d}"
                            conn.execute(text("UPDATE echantillons_tubes SET code_tube = :nc WHERE id = :tid"), {"nc": new_code, "tid": t_id})
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
