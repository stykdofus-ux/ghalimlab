"""
Serveur Démon TCP/IP Asynchrone ASTM E1381 / E1394 pour Automates de Laboratoire.
Écoute sur le port configuré (ex: 5000) et gère le handshake ENQ/ACK/STX/ETX/EOT
avec ingestion directe dans la base de données GhalimLab.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.app.config import ASTM_HOST, ASTM_PORT
from backend.app.database import SessionLocal
from backend.astm.protocol import (
    ENQ, ACK, NAK, STX, ETX, ETB, EOT, CRLF,
    verify_checksum, ASTMRecordParser
)
from backend.app.services.result_service import ingest_astm_payload

# Configuration des logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [ASTM] %(message)s")
logger = logging.getLogger("ASTMServer")

# État global du serveur pour la télémétrie Web en temps réel
server_stats: Dict[str, Any] = {
    "is_running": False,
    "host": ASTM_HOST,
    "port": ASTM_PORT,
    "total_connections": 0,
    "total_messages": 0,
    "total_frames_received": 0,
    "last_connection_time": None,
    "last_automate": None,
    "recent_logs": []
}


def add_telemetry_log(message: str, level: str = "INFO"):
    """Ajoute un log dans la file de télémétrie en mémoire pour affichage Web."""
    entry = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "message": message
    }
    server_stats["recent_logs"].insert(0, entry)
    if len(server_stats["recent_logs"]) > 50:
        server_stats["recent_logs"].pop()


class ASTMProtocolHandler:
    """
    Gestionnaire de session de communication ASTM E1381 avec un automate.
    Gère la machine à états :
    INIT -> ESTABLISHED (après ENQ/ACK) -> RECEIVING_FRAMES -> CLOSED (après EOT)
    """

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.session_records: List[str] = []
        self.client_ip = writer.get_extra_info('peername')
        self.state = "INIT"

    async def handle_session(self):
        logger.info(f"Connexion automate acceptée depuis {self.client_ip}")
        add_telemetry_log(f"Nouvelle connexion entrante de l'automate : {self.client_ip}")
        server_stats["total_connections"] += 1
        server_stats["last_connection_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        buffer = bytearray()

        try:
            while True:
                # Lecture par bloc de 1024 octets ou caractère par caractère
                data = await self.reader.read(1024)
                if not data:
                    logger.info(f"L'automate {self.client_ip} a fermé la connexion TCP.")
                    add_telemetry_log(f"Fermeture de connexion par {self.client_ip}")
                    break

                buffer.extend(data)

                # Traitement du buffer
                while buffer:
                    # 1. Traitement du signal ENQ (Demande d'établissement de liaison)
                    if buffer.startswith(ENQ):
                        buffer = buffer[1:]
                        logger.info("Signal ENQ reçu -> Réponse ACK envoyée")
                        add_telemetry_log("Handshake : ENQ reçu -> Réponse ACK transmise")
                        self.writer.write(ACK)
                        await self.writer.drain()
                        self.state = "ESTABLISHED"
                        self.session_records = []
                        continue

                    # 2. Traitement du signal EOT (Fin de session de transmission)
                    if buffer.startswith(EOT):
                        buffer = buffer[1:]
                        logger.info("Signal EOT reçu -> Traitement et ingestion des données reçues")
                        add_telemetry_log("Signal EOT reçu : fin de transmission. Ingestion en base...")
                        self.state = "CLOSED"
                        server_stats["total_messages"] += 1
                        
                        # Traitement des lignes enregistrées
                        await self.process_complete_message()
                        continue

                    # 3. Traitement des trames avec données encadrées par STX et CRLF
                    if buffer.startswith(STX):
                        # Recherche de la fin de trame CRLF
                        crlf_pos = buffer.find(CRLF)
                        if crlf_pos == -1:
                            # Trame incomplète, attendre les octets suivants
                            break

                        frame_bytes = bytes(buffer[:crlf_pos + 2])
                        buffer = buffer[crlf_pos + 2:]

                        server_stats["total_frames_received"] += 1

                        # Vérification du checksum ASTM
                        if verify_checksum(frame_bytes):
                            # Acquittement positif
                            self.writer.write(ACK)
                            await self.writer.drain()

                            # Extraction de la ligne de données (ignorer STX + numéro de trame et délimiteur ETX/ETB + checksum + CRLF)
                            try:
                                # Le numéro de trame est à l'index 1
                                etx_pos = frame_bytes.find(ETX)
                                if etx_pos == -1:
                                    etx_pos = frame_bytes.find(ETB)

                                if etx_pos > 2:
                                    record_line = frame_bytes[2:etx_pos].decode('latin1', errors='replace')
                                    self.session_records.append(record_line)
                                    logger.debug(f"Trame validée : {record_line[:60]}")
                            except Exception as e:
                                logger.error(f"Erreur d'extraction du record : {e}")

                        else:
                            logger.warning(f"Erreur de Checksum sur la trame reçue : {frame_bytes!r}")
                            add_telemetry_log(f"Erreur Checksum trame rejetée", "WARN")
                            self.writer.write(NAK)
                            await self.writer.drain()
                        continue

                    # Si octet non reconnu au début du buffer, glisser d'un cran
                    buffer = buffer[1:]

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Exception dans la session ASTM {self.client_ip} : {e}")
            add_telemetry_log(f"Erreur session {self.client_ip} : {e}", "ERROR")
        finally:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass

    async def process_complete_message(self):
        """Parse les lignes reçues et insère les résultats dans la base."""
        if not self.session_records:
            return

        parsed = ASTMRecordParser.parse_message_lines(self.session_records)
        server_stats["last_automate"] = parsed.get("automate", "Automate")

        add_telemetry_log(
            f"Message analysé de {parsed.get('automate')} : {len(parsed.get('orders', []))} ordre(s)"
        )

        # Ingestion en base de données
        db = SessionLocal()
        try:
            report = ingest_astm_payload(db, parsed)
            logger.info(f"Rapport d'ingestion : {report}")
            add_telemetry_log(
                f"Ingestion réussie : {report.get('total_resultats_ingérés')} résultats pour {report.get('demandes_mises_a_jour')}"
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'ingestion en base : {e}")
            add_telemetry_log(f"Échec ingestion en base : {e}", "ERROR")
        finally:
            db.close()


async def start_astm_server(host: str = ASTM_HOST, port: int = ASTM_PORT):
    """Démarre le serveur d'écoute ASTM asynchrone."""
    server = await asyncio.start_server(
        lambda r, w: ASTMProtocolHandler(r, w).handle_session(),
        host,
        port
    )
    server_stats["is_running"] = True
    server_stats["host"] = host
    server_stats["port"] = port

    add_telemetry_log(f"Serveur ASTM actif sur {host}:{port}")
    logger.info(f"Serveur d'écoute ASTM opérationnel sur {host}:{port}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    print(f"Démarrage du démon ASTM GhalimLab sur le port {ASTM_PORT}...")
    try:
        asyncio.run(start_astm_server())
    except KeyboardInterrupt:
        print("\nArrêt du démon ASTM.")
