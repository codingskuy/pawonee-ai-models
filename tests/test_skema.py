"""Uji skema models/schema.json: penolakan data yang melanggar kontrak v1.0.0."""

import jsonschema
import pytest


def valid(bank, skema):
    jsonschema.validate(bank, skema)


def galat(bank, skema):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bank, skema)


def test_skema_sendiri_sah(skema):
    jsonschema.Draft7Validator.check_schema(skema)


def test_bank_asli_valid(bank, skema):
    valid(bank, skema)


def test_tolak_resep_ke_13(bank, skema):
    ekstra = dict(bank["resep"][0], kode="R-13", id="resep-ketigabelas")
    bank["resep"].append(ekstra)
    galat(bank, skema)


def test_tolak_kurang_dari_12(bank, skema):
    bank["resep"].pop()
    galat(bank, skema)


def test_tolak_kode_di_luar_r01_r12(bank, skema):
    bank["resep"][0]["kode"] = "R-13"
    galat(bank, skema)


@pytest.mark.parametrize("nilai", ["G2", "g2-v", "A", ""])
def test_tolak_kode_grade_tak_dikenal(bank, skema, nilai):
    bank["resep"][0]["bahan"][0]["kodeGrade"] = nilai
    galat(bank, skema)


@pytest.mark.parametrize("nilai", [12.5, "300", 0, -5])
def test_tolak_jumlah_bahan_bukan_integer_positif(bank, skema, nilai):
    bank["resep"][0]["bahan"][0]["jumlah"] = nilai
    galat(bank, skema)


def test_tolak_satuan_tak_baku(bank, skema):
    bank["resep"][0]["bahan"][0]["satuan"] = "ikat"
    galat(bank, skema)


def test_tolak_biaya_pecahan(bank, skema):
    bank["resep"][0]["estimasiBiaya"] = 18000.5
    galat(bank, skema)


def test_tolak_menit_pecahan(bank, skema):
    bank["resep"][0]["menit"] = 15.5
    galat(bank, skema)


def test_tolak_level_pedas_di_atas_3(bank, skema):
    bank["resep"][0]["levelPedas"] = 4
    galat(bank, skema)


def test_tolak_alergen_di_luar_daftar_resmi(bank, skema):
    bank["resep"][0]["alergen"] = ["udang-karang"]
    galat(bank, skema)


def test_tolak_alat_di_luar_daftar_resmi(bank, skema):
    bank["resep"][0]["alat"] = ["kompor", "microwave"]
    galat(bank, skema)


def test_tolak_grade_selain_2(bank, skema):
    bank["resep"][0]["grade"] = 1
    galat(bank, skema)


def test_tolak_properti_tak_dikenal(bank, skema):
    bank["resep"][0]["bonus"] = True
    galat(bank, skema)


def test_tolak_substitusi_tanpa_pengganti(bank, skema):
    bank["substitusi"][0]["pengganti"] = []
    galat(bank, skema)


def test_tolak_versi_bank_bukan_semver(bank, skema):
    bank["versiBank"] = "satu"
    galat(bank, skema)
