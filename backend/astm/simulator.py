"""
Simulateur d'automates d'analyses médicales (Sysmex XN-1000 et Roche Cobas 6000).
Génère et transmet des trames ASTM E1381/E1394 conformes avec handshake TCP/IP réel.
"""

import socket
import time
import argparse
from typing import List, Dict, Any, Optional

from backend.app.config import ASTM_HOST, ASTM_PORT
from backend.astm.protocol import ENQ, ACK, NAK, EOT, build_frame


def generate_sysmex_records(barcode: str = "PREL-2026-002", patient_name: str = "EL AMRANI^Amina", sexe: str = "F") -> List[str]:
    """Génère un profil complet d'hémogramme (NFS) au format ASTM E1394."""
    timestamp = time.strftime("%Y%m%d%H%M%S")
    return [
        f"H|\\^&|||Sysmex^XN-1000^00-14||||||||{timestamp}",
        f"P|1||AE654321||{patient_name}||19920918|{sexe}",
        f"O|1|{barcode}||^^^NFS|R|{timestamp}|||||||||SERUM||||||||||F",
        f"R|1|^^^WBC|8.42|10^3/uL|4.0-10.0|N||F||biologist|{timestamp}|Sysmex_XN",
        f"R|2|^^^RBC|3.65|10^6/uL|4.0-5.2|L||F||biologist|{timestamp}|Sysmex_XN",
        f"R|3|^^^HGB|9.8|g/dL|12.0-16.0|L||F||biologist|{timestamp}|Sysmex_XN",   # Anémie
        f"R|4|^^^HCT|31.5|%|36.0-48.0|L||F||biologist|{timestamp}|Sysmex_XN",
        f"R|5|^^^MCV|86.3|fL|80.0-100.0|N||F||biologist|{timestamp}|Sysmex_XN",
        f"R|6|^^^MCH|26.8|pg|27.0-32.0|L||F||biologist|{timestamp}|Sysmex_XN",
        f"R|7|^^^MCHC|31.1|g/dL|32.0-36.0|L||F||biologist|{timestamp}|Sysmex_XN",
        f"R|8|^^^PLT|228.0|10^3/uL|150-450|N||F||biologist|{timestamp}|Sysmex_XN",
        f"R|9|^^^NEUT|62.4|%|40.0-75.0|N||F||biologist|{timestamp}|Sysmex_XN",
        f"R|10|^^^LYMPH|28.5|%|20.0-45.0|N||F||biologist|{timestamp}|Sysmex_XN",
        f"C|1|I|Anémie modérée normocytaire|I",
        "L|1|N"
    ]


def generate_cobas_records(barcode: str = "PREL-2026-002", patient_name: str = "EL AMRANI^Amina", sexe: str = "F") -> List[str]:
    """Génère un bilan biochimique au format ASTM E1394."""
    timestamp = time.strftime("%Y%m%d%H%M%S")
    return [
        f"H|\\^&|||Roche^Cobas-6000^c501||||||||{timestamp}",
        f"P|1||AE654321||{patient_name}||19920918|{sexe}",
        f"O|1|{barcode}||^^^BIOCHIMIE|R|{timestamp}|||||||||SERUM||||||||||F",
        f"R|1|^^^GLU|1.45|g/L|0.70-1.10|H||F||biologist|{timestamp}|Cobas_6000",   # Hyperglycémie
        f"R|2|^^^UREE|0.28|g/L|0.15-0.45|N||F||biologist|{timestamp}|Cobas_6000",
        f"R|3|^^^CREAT|8.2|mg/L|5.0-10.0|N||F||biologist|{timestamp}|Cobas_6000",
        f"R|4|^^^CRP|24.6|mg/L|0.0-6.0|H||F||biologist|{timestamp}|Cobas_6000",      # Syndrome inflammatoire
        f"R|5|^^^CHOL|2.15|g/L|1.50-2.00|H||F||biologist|{timestamp}|Cobas_6000",
        f"R|6|^^^TRIG|1.42|g/L|0.50-1.50|N||F||biologist|{timestamp}|Cobas_6000",
        f"R|7|^^^HDL|0.48|g/L|0.50-0.95|L||F||biologist|{timestamp}|Cobas_6000",
        f"R|8|^^^LDL|1.38|g/L|0.90-1.30|H||F||biologist|{timestamp}|Cobas_6000",
        f"R|9|^^^ASAT|22.0|UI/L|10-32|N||F||biologist|{timestamp}|Cobas_6000",
        f"R|10|^^^ALAT|26.0|UI/L|10-35|N||F||biologist|{timestamp}|Cobas_6000",
        f"C|1|I|Sérum limpide, CRP élevée|I",
        "L|1|N"
    ]


def send_astm_simulation(
    records: List[str],
    host: str = ASTM_HOST,
    port: int = ASTM_PORT,
    delay_between_frames: float = 0.05
) -> Dict[str, Any]:
    """
    Exécute le cycle complet de transmission ASTM E1381 vers le serveur LIMS:
    1. Connexion TCP
    2. Envoi <ENQ> -> Attente <ACK>
    3. Pour chaque ligne, envoi <STX><fn><record><ETX><checksum><CR><LF> -> Attente <ACK>
    4. Envoi <EOT>
    5. Déconnexion
    """
    logs = []
    
    # Remplacer 0.0.0.0 par 127.0.0.1 pour la connexion locale client
    client_host = "127.0.0.1" if host in ("0.0.0.0", "") else host

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((client_host, port))
        logs.append(f"Connecté au serveur ASTM {client_host}:{port}")

        # 1. Handshake ENQ
        s.sendall(ENQ)
        logs.append("Émission : <ENQ>")
        resp = s.recv(1024)
        if resp != ACK:
            logs.append(f"Erreur Handshake : reçu {resp!r} au lieu de <ACK>")
            s.close()
            return {"success": False, "logs": logs, "error": "Handshake ENQ refusé"}

        logs.append("Réception : <ACK> (Liaison établie)")

        # 2. Transmission des trames
        frame_num = 1
        for line in records:
            frame = build_frame(frame_num, line, is_last_frame=True)
            s.sendall(frame)
            logs.append(f"Émission trame {frame_num % 8} : {line[:50]}...")

            resp = s.recv(1024)
            if resp != ACK:
                logs.append(f"Erreur Trame {frame_num} : reçu {resp!r} au lieu de <ACK>")
                s.close()
                return {"success": False, "logs": logs, "error": f"Trame {frame_num} refusée"}

            frame_num = (frame_num + 1) % 8
            time.sleep(delay_between_frames)

        # 3. Fin de session EOT
        s.sendall(EOT)
        logs.append("Émission : <EOT> (Transmission terminée)")
        time.sleep(0.1)
        s.close()
        logs.append("Session ASTM clôturée avec succès.")

        return {"success": True, "logs": logs, "frames_sent": len(records)}

    except Exception as e:
        logs.append(f"Exception réseau : {e}")
        return {"success": False, "logs": logs, "error": str(e)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulateur d'automates Sysmex & Cobas pour GhalimLab LIMS")
    parser.add_argument("--automate", choices=["sysmex", "cobas"], default="sysmex", help="Type d'automate à simuler")
    parser.add_argument("--barcode", default="PREL-2026-002", help="Code-barres du prélèvement à alimenter")
    parser.add_argument("--port", type=int, default=ASTM_PORT, help="Port ASTM")
    args = parser.parse_args()

    print(f"=== Simulation Automate {args.automate.upper()} pour le code-barres {args.barcode} ===")
    if args.automate == "sysmex":
        recs = generate_sysmex_records(barcode=args.barcode)
    else:
        recs = generate_cobas_records(barcode=args.barcode)

    res = send_astm_simulation(recs, port=args.port)
    print("\n--- Journal de transmission ---")
    for l in res["logs"]:
        print("  >", l)
    if res["success"]:
        print(f"\n[SUCCÈS] {res['frames_sent']} trames transmises avec succès !")
    else:
        print(f"\n[ÉCHEC] {res.get('error')}")
