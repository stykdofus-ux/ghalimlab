"""
Lanceur unifié GhalimLab LIMS
Démarre simultanément :
1. Le serveur d'écoute ASTM E1381/E1394 (Port 5000) pour les automates Sysmex & Cobas
2. L'application Web FastAPI & API REST (Port 8000)
"""

import asyncio
import uvicorn
import logging
from backend.app.config import API_HOST, API_PORT, ASTM_HOST, ASTM_PORT
from backend.astm.server import start_astm_server
from backend.app.main import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GhalimLabRunner")


async def main():
    logger.info("=" * 70)
    logger.info("   GHALIMLAB LIMS - SYSTÈME DE GESTION DE LABORATOIRE MÉDICAL   ")
    logger.info("   Intégration Automates ASTM E1381/E1394 (Sysmex, Cobas, etc.)  ")
    logger.info("=" * 70)

    # Configuration du serveur web Uvicorn
    config = uvicorn.Config(
        app=app,
        host=API_HOST,
        port=API_PORT,
        log_level="info",
        loop="asyncio"
    )
    server = uvicorn.Server(config)

    logger.info(f"-> Application Web & API : http://{API_HOST}:{API_PORT}")
    logger.info(f"-> Démon d'écoute ASTM   : {ASTM_HOST}:{ASTM_PORT}")
    logger.info("Démarrage des services...")

    async def safe_astm():
        try:
            await start_astm_server(host=ASTM_HOST, port=ASTM_PORT)
        except Exception as e:
            logger.warning(f"Note: Démon ASTM non démarré ({e}). L'application Web reste 100% fonctionnelle.")

    # Exécution conjointe des deux serveurs asynchrones
    await asyncio.gather(
        safe_astm(),
        server.serve()
    )



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Arrêt propre de GhalimLab LIMS.")
