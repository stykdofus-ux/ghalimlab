"""
Tests unitaires pour le protocole ASTM E1381/E1394 et la validation du checksum.
"""

import pytest
from backend.astm.protocol import (
    calculate_checksum, verify_checksum, build_frame, ASTMRecordParser,
    STX, ETX, CRLF
)


def test_calculate_checksum():
    # Exemple classique ASTM: 1H|\^&|||Sysmex<ETX>
    data = b"1H|\\^&|||Sysmex\x03"
    cs = calculate_checksum(data)
    assert len(cs) == 2
    assert cs.isupper()


def test_build_and_verify_frame():
    record_text = "R|1|^^^WBC|7.45|10^3/uL|4.0-10.0|N||F"
    frame = build_frame(1, record_text, is_last_frame=True)
    
    assert frame.startswith(STX)
    assert frame.endswith(CRLF)
    assert verify_checksum(frame) is True


def test_verify_corrupted_checksum():
    record_text = "R|1|^^^WBC|7.45|10^3/uL"
    frame = build_frame(1, record_text, is_last_frame=True)
    
    # Altérer un octet
    corrupted_frame = frame[:-3] + b"FF" + CRLF
    assert verify_checksum(corrupted_frame) is False


def test_astm_parser_full_message():
    lines = [
        "H|\\^&|||Sysmex^XN-1000||||||||20261014193000",
        "P|1||CIN9988||BENNANI^Ali||19800101|M",
        "O|1|BARCODE_TEST_01||^^^NFS|R|20261014190000",
        "R|1|^^^WBC|6.50|10^3/uL|4.0-10.0|N||F||op|20261014190500|Sysmex_XN",
        "R|2|^^^HGB|14.2|g/dL|13.0-17.5|N||F||op|20261014190500|Sysmex_XN",
        "L|1|N"
    ]
    parsed = ASTMRecordParser.parse_message_lines(lines)

    assert "Sysmex" in parsed["automate"]
    assert parsed["patient"]["nom"] == "BENNANI"
    assert parsed["patient"]["prenom"] == "Ali"
    assert len(parsed["orders"]) == 1
    assert parsed["orders"][0]["code_barres"] == "BARCODE_TEST_01"
    assert len(parsed["orders"][0]["results"]) == 2
    assert parsed["orders"][0]["results"][0]["param_code"] == "WBC"
    assert parsed["orders"][0]["results"][0]["valeur_num"] == 6.50
    assert parsed["orders"][0]["results"][1]["param_code"] == "HGB"
    assert parsed["orders"][0]["results"][1]["valeur_num"] == 14.2
