"""
Tests unitaires pour la logique de bornes de référence biologiques par âge et sexe.
"""

from backend.app.models.core import AnalyseParameter, Patient


def test_param_reference_ranges():
    # Hémoglobine (HGB)
    param = AnalyseParameter(
        code="HGB",
        nom="Hémoglobine",
        unite="g/dL",
        male_min=13.0, male_max=17.5,
        female_min=12.0, female_max=16.0,
        child_min=11.5, child_max=14.5
    )

    # Homme adulte (30 ans)
    min_m, max_m, label_m = param.get_reference_range(30, "M")
    assert min_m == 13.0
    assert max_m == 17.5
    assert label_m == "Homme"

    # Femme adulte (28 ans)
    min_f, max_f, label_f = param.get_reference_range(28, "F")
    assert min_f == 12.0
    assert max_f == 16.0
    assert label_f == "Femme"

    # Enfant (8 ans)
    min_c, max_c, label_c = param.get_reference_range(8, "M")
    assert min_c == 11.5
    assert max_c == 14.5
    assert "Enfant" in label_c


def test_patient_age_calculation():
    p = Patient(
        cin="BK112233",
        nom="Test",
        prenom="Patient",
        date_naissance="1990-05-15",
        sexe="M"
    )
    # En 2026, l'âge est environ 36 ans
    assert p.age >= 35
