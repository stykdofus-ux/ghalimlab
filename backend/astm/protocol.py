"""
ASTM E1381 / E1394 Standard Protocol Engine for Clinical Automates (Sysmex, Cobas, etc.)
Conforme aux standards d'interfaces de communication de laboratoire d'analyses médicales.
"""

from typing import List, Dict, Any, Optional, Tuple
import datetime
import re

# Caractères de contrôle ASTM E1381 (ASCII)
ENQ = b'\x05'  # Enquiry (Demande d'établissement de liaison)
ACK = b'\x06'  # Acknowledge (Acquittement positif)
NAK = b'\x15'  # Negative Acknowledge (Acquittement négatif / Erreur)
STX = b'\x02'  # Start of Text (Début de trame)
ETX = b'\x03'  # End of Text (Fin de dernière trame d'un message)
ETB = b'\x17'  # End of Transmission Block (Fin de trame intermédiaire)
EOT = b'\x04'  # End of Transmission (Fin de session)
CR = b'\x0d'   # Carriage Return
LF = b'\x0a'   # Line Feed
CRLF = b'\x0d\x0a'


def calculate_checksum(data: bytes) -> str:
    """
    Calcule le checksum ASTM standard (modulo 256) sur les octets de trame
    depuis le numéro de trame jusqu'à ETX/ETB inclus.
    Retourne 2 caractères hexadécimaux en majuscules.
    """
    total = sum(data) % 256
    return f"{total:02X}"


def verify_checksum(frame_bytes: bytes) -> bool:
    """
    Vérifie la validité du checksum d'une trame ASTM:
    Format: <STX><Frame_Num><Data><ETX/ETB><CS1><CS2><CR><LF>
    """
    if not (frame_bytes.startswith(STX) and frame_bytes.endswith(CRLF)):
        return False
    
    # Trouver le délimiteur de fin ETX ou ETB
    etx_pos = frame_bytes.find(ETX)
    if etx_pos == -1:
        etx_pos = frame_bytes.find(ETB)
    
    if etx_pos == -1 or etx_pos + 3 >= len(frame_bytes):
        return False
    
    # Données couvertes par le checksum: depuis juste après STX jusqu'à ETX/ETB inclus
    data_for_checksum = frame_bytes[1:etx_pos + 1]
    expected_cs = calculate_checksum(data_for_checksum)
    
    actual_cs = frame_bytes[etx_pos + 1:etx_pos + 3].decode('ascii', errors='ignore').upper()
    return expected_cs == actual_cs


def build_frame(frame_num: int, record_data: str, is_last_frame: bool = True) -> bytes:
    """
    Construit une trame ASTM E1381 complète avec en-tête STX, checksum et délimiteurs CRLF.
    """
    fn_char = str(frame_num % 8)
    end_char = ETX if is_last_frame else ETB
    
    payload = fn_char.encode('latin1') + record_data.encode('latin1') + end_char
    cs = calculate_checksum(payload)
    
    return STX + payload + cs.encode('ascii') + CRLF


class ASTMRecordParser:
    """
    Parseur pour les enregistrements ASTM E1394
    Supporte Header (H), Patient (P), Order (O), Result (R), Comment (C), Terminator (L).
    """

    @staticmethod
    def clean_field(val: Optional[str]) -> str:
        return val.strip() if val else ""

    @staticmethod
    def extract_param_code(raw_code: str) -> str:
        """
        Extrait le code paramètre nettoyé à partir d'un champ ASTM universel (ex: '^^^WBC^1' -> 'WBC')
        """
        if not raw_code:
            return ""
        parts = raw_code.split('^')
        # Souvent dans le 4ème composant (^^^WBC) ou le premier si non préfixé
        for p in parts:
            p_clean = p.strip()
            if p_clean:
                return p_clean
        return raw_code.strip()

    @classmethod
    def parse_message_lines(cls, lines: List[str]) -> Dict[str, Any]:
        """
        Analyse une séquence complète de lignes d'enregistrements ASTM E1394
        et retourne un dictionnaire structuré prêt pour l'ingestion en base de données.
        """
        result_data: Dict[str, Any] = {
            "automate": "Inconnu",
            "timestamp": datetime.datetime.now().isoformat(),
            "patient": None,
            "orders": [],
            "raw_records": lines
        }

        current_order: Optional[Dict[str, Any]] = None
        current_patient: Optional[Dict[str, Any]] = None

        for line in lines:
            if not line:
                continue
            fields = line.split('|')
            record_type = fields[0].strip().upper()

            if record_type == 'H':  # Header Record
                # H|\^&|||Sysmex^XN-1000||||||||20261014193000
                sender = fields[4] if len(fields) > 4 else ""
                clean_sender = sender.replace('^', ' ').strip()
                result_data["automate"] = clean_sender or "Automate ASTM"
                if len(fields) > 13 and fields[13]:
                    result_data["timestamp"] = fields[13].strip()

            elif record_type == 'P':  # Patient Record
                # P|1||CIN12345||DUPONT^Jean||19850615|M
                patient_cin = fields[3].strip() if len(fields) > 3 else ""
                full_name = fields[5].strip() if len(fields) > 5 else ""
                name_parts = full_name.split('^')
                nom = name_parts[0].strip() if len(name_parts) > 0 else ""
                prenom = name_parts[1].strip() if len(name_parts) > 1 else ""
                dob = fields[7].strip() if len(fields) > 7 else ""
                sexe = fields[8].strip().upper() if len(fields) > 8 else "U"

                current_patient = {
                    "cin": patient_cin,
                    "nom": nom,
                    "prenom": prenom,
                    "date_naissance": dob,
                    "sexe": sexe
                }
                result_data["patient"] = current_patient

            elif record_type == 'O':  # Order Record
                # O|1|BARCODE_12345||^^^NFS|R|20261014180000|||||||||SERUM
                barcode = fields[2].strip() if len(fields) > 2 else ""
                # Parfois le code barre est dans le champ 3 si spécifié comme instrument specimen id
                if not barcode and len(fields) > 3:
                    barcode = fields[3].strip()

                test_battery = fields[4].strip() if len(fields) > 4 else ""

                current_order = {
                    "code_barres": barcode,
                    "test_battery": test_battery,
                    "results": []
                }
                result_data["orders"].append(current_order)

            elif record_type == 'R':  # Result Record
                # R|1|^^^WBC|7.45|10^3/uL|4.0-10.0|N||F||biologist|20261014190500|Sysmex
                if current_order is None:
                    # Si aucun ordre préalable n'a été déclaré, en initialiser un par défaut
                    current_order = {
                        "code_barres": "AUTO_DETECT",
                        "test_battery": "INCONNU",
                        "results": []
                    }
                    result_data["orders"].append(current_order)

                raw_param = fields[2].strip() if len(fields) > 2 else ""
                param_code = cls.extract_param_code(raw_param)
                value_str = fields[3].strip() if len(fields) > 3 else ""
                units = fields[4].strip() if len(fields) > 4 else ""
                ref_range = fields[5].strip() if len(fields) > 5 else ""
                flag = fields[6].strip().upper() if len(fields) > 6 else "N"
                status = fields[8].strip() if len(fields) > 8 else "F"
                instrument = fields[13].strip() if len(fields) > 13 else result_data["automate"]

                try:
                    val_numeric = float(value_str.replace(',', '.'))
                except (ValueError, TypeError):
                    val_numeric = None

                current_order["results"].append({
                    "param_code": param_code.upper(),
                    "valeur_str": value_str,
                    "valeur_num": val_numeric,
                    "unite": units,
                    "valeurs_reference": ref_range,
                    "drapeau_automate": flag,  # 'N', 'L', 'H', 'LL', 'HH', 'A'
                    "statut": status,
                    "automate_source": instrument or result_data["automate"]
                })

            elif record_type == 'C':  # Comment Record
                # C|1|I|Plasma limpide|G
                comment_text = fields[3].strip() if len(fields) > 3 else ""
                if current_order and current_order["results"]:
                    # Associer le commentaire au dernier résultat
                    current_order["results"][-1]["commentaire"] = comment_text

            elif record_type == 'L':  # Terminator Record
                pass

        return result_data
