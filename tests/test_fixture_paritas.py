"""Uji fixture paritas 32 kasus (PWN-AI-004)."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import jsonschema
import pytest

import buat_fixture
import rekomendasi_ref as rr

DASAR = Path(__file__).resolve().parent.parent
BERKAS = DASAR / "fixtures" / "paritas-32-kasus.json"
SKEMA_FIXTURE = DASAR / "fixtures" / "schema-kasus-uji.json"
SKOR = ("skorTotal", "skorSerapan", "skorKecocokanStok", "skorBudget", "skorWaktu")


@pytest.fixture(scope="module")
def fixture():
    return json.loads(BERKAS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def mesin(bank_asli, referensi):
    return rr.Mesin(bank_asli, referensi)


def test_valid_terhadap_skema_fixture(fixture):
    skema = json.loads(SKEMA_FIXTURE.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(skema)
    jsonschema.validate(fixture, skema)


def test_tepat_32_kasus_id_unik(fixture):
    ids = [k["id"] for k in fixture["kasus"]]
    assert len(ids) == 32 and len(set(ids)) == 32


def test_komposisi_kasus_per_resep_tepi_skenario(fixture):
    awal = Counter(k["id"][0] for k in fixture["kasus"])
    assert awal == {"A": 12, "B": 10, "C": 10}


def test_versi_dan_checksum_bank_cocok(fixture, bank_asli):
    assert fixture["versiBank"] == bank_asli["versiBank"]
    assert fixture["versiSkema"] == bank_asli["versiSkema"]
    sha = hashlib.sha256((DASAR / "models" / "bank_resep_grade2.json").read_bytes()).hexdigest()
    assert fixture["bankSha256"] == sha


def test_ambang_selisih_001(fixture):
    assert fixture["ambangSelisih"] == 0.01


def test_harga_konfigurasi_sama_dengan_referensi(fixture, referensi):
    for nama, e in fixture["konfigurasi"]["harga"].items():
        r = referensi["bahan"][nama]
        assert (e["satuan"], e["per"], e["harga"]) == (r["satuan"], r["per"], r["harga"]), nama
    assert set(fixture["konfigurasi"]["harga"]) >= {
        b["nama"] for r in json.loads((DASAR / "models" / "bank_resep_grade2.json").read_text())["resep"] for b in r["bahan"]
    }


def test_konfigurasi_faktor_porsi_sama_dengan_mesin(fixture):
    for jiwa, f in fixture["konfigurasi"]["faktorPorsiPersen"].items():
        assert (f["bahan"], f["bumbu"], f["air"]) == rr.FAKTOR_PORSI[int(jiwa)]
    assert fixture["konfigurasi"]["faktorPorsiPersen"]["7"]["asumsi"] is True


def test_regenerasi_identik_dengan_berkas_terbit():
    """Fixture terbit harus persis hasil `python eval/buat_fixture.py` (tanpa edit tangan)."""
    assert BERKAS.read_text(encoding="utf-8") == buat_fixture.render()


def test_harapan_dapat_direproduksi_oleh_mesin_rujukan(fixture, mesin):
    for k in fixture["kasus"]:
        m = k["masukan"]
        hasil = mesin.rekomendasikan(m["profil"], m["stok"], m["jiwa"], m["waktuMaksimalMenit"])
        h = k["harapan"]
        assert h["galat"] == hasil["galat"], k["id"]
        assert h["modeTanpaStok"] == hasil["modeTanpaStok"], k["id"]
        assert [r["kode"] for r in h["rekomendasi"]] == [r["kode"] for r in hasil["rekomendasi"]], k["id"]
        for exp, got in zip(h["rekomendasi"], hasil["rekomendasi"]):
            for f in SKOR:
                assert abs(exp[f] - got[f]) < 1e-4, (k["id"], exp["kode"], f)
            assert exp["belanjaTambahanRp"] == got["belanjaTambahanRp"], (k["id"], exp["kode"])
            assert exp["bahanTerskala"] == got["bahanTerskala"], (k["id"], exp["kode"])


def test_kasus_per_resep_menempatkan_resep_target_di_peringkat_1(fixture):
    for n, k in enumerate((k for k in fixture["kasus"] if k["id"].startswith("A-")), start=1):
        assert k["harapan"]["rekomendasi"][0]["kode"] == f"R-{n:02d}", k["id"]


def test_skor_total_adalah_jumlah_komponen(fixture):
    for k in fixture["kasus"]:
        for r in k["harapan"]["rekomendasi"]:
            jumlah = r["skorSerapan"] + r["skorKecocokanStok"] + r["skorBudget"] + r["skorWaktu"]
            assert abs(jumlah - r["skorTotal"]) < 1e-3, (k["id"], r["kode"])


def test_maksimal_5_item_dan_urutan_menurun(fixture):
    for k in fixture["kasus"]:
        rek = k["harapan"]["rekomendasi"]
        assert len(rek) <= 5
        if not k["harapan"]["modeTanpaStok"]:
            skor = [r["skorTotal"] for r in rek]
            assert skor == sorted(skor, reverse=True), k["id"]


def test_cakupan_perilaku_wajib(fixture):
    kasus = {k["id"]: k for k in fixture["kasus"]}
    jiwa = {k["masukan"]["jiwa"] for k in kasus.values()}
    assert {0, 1, 2, 3, 4, 5, 6, 7, 8, 9} <= jiwa
    galat = {k["harapan"]["galat"] for k in kasus.values()}
    assert galat == {None, "JIWA_DI_LUAR_RENTANG"}
    assert any(k["harapan"]["modeTanpaStok"] for k in kasus.values())
    assert any(k["masukan"]["profil"]["alergi"] for k in kasus.values())
    assert any("vegetarian-nabati" in k["masukan"]["profil"]["pantangan"] for k in kasus.values())
    assert any("tanpa-santan" in k["masukan"]["profil"]["pantangan"] for k in kasus.values())
    assert any("lunak-lansia" in k["masukan"]["profil"]["pantangan"] for k in kasus.values())
    kode_muncul = {r["kode"] for k in kasus.values() for r in k["harapan"]["rekomendasi"]}
    assert kode_muncul == {f"R-{n:02d}" for n in range(1, 13)}


def test_kasus_bonus_g2s_selisih_5_poin_pada_batas_2_hari(fixture):
    kasus = {k["id"]: k for k in fixture["kasus"]}
    def serapan(i):
        return next(r for r in kasus[i]["harapan"]["rekomendasi"] if r["kode"] == "R-06")["skorSerapan"]
    assert serapan("B-07") > serapan("B-08")
    assert kasus["B-07"]["masukan"]["stok"][0]["kedaluwarsaHari"] == 2
    assert kasus["B-08"]["masukan"]["stok"][0]["kedaluwarsaHari"] == 3


def test_kasus_diversifikasi_benar_benar_menggeser(fixture, bank_asli, mesin, monkeypatch):
    k = next(k for k in fixture["kasus"] if k["id"] == "B-09")
    kelompok = {r["kode"]: r["kelompok"] for r in bank_asli["resep"]}
    got = Counter(kelompok[r["kode"]] for r in k["harapan"]["rekomendasi"])
    assert max(got.values()) == 2
    m = k["masukan"]
    monkeypatch.setattr(rr, "MAKS_PER_KELOMPOK", 5)
    tanpa = mesin.rekomendasikan(m["profil"], m["stok"], m["jiwa"], m["waktuMaksimalMenit"])
    assert max(Counter(kelompok[r["kode"]] for r in tanpa["rekomendasi"]).values()) >= 3


def test_kasus_seri_dimenangkan_waktu(fixture):
    k = next(k for k in fixture["kasus"] if k["id"] == "B-10")
    rek = k["harapan"]["rekomendasi"]
    kunci = [rr._kunci_skor(r["skorTotal"]) for r in rek]
    menit = {r["id"]: r["menit"] for r in json.loads((DASAR / "models" / "bank_resep_grade2.json").read_text())["resep"]}
    seri = [(kunci[i], menit[rek[i]["id"]], rek[i]["belanjaTambahanRp"], rek[i]["kode"]) for i in range(len(rek))]
    assert len(set(kunci)) < len(kunci)  # ada skor seri
    assert seri == sorted(seri, key=lambda t: (-t[0], t[1], t[2], t[3]))


def selisih_maks(harapan, hasil):
    return max(abs(a[f] - b[f]) for a, b in zip(harapan, hasil) for f in SKOR)


def test_ambang_paritas_memblokir_selisih_001_atau_lebih(fixture):
    asli = fixture["kasus"][0]["harapan"]["rekomendasi"]
    ok = [dict(r, skorTotal=r["skorTotal"] + 0.009) for r in asli]
    buruk = [dict(r, skorTotal=r["skorTotal"] + 0.011) for r in asli]
    assert selisih_maks(asli, ok) < fixture["ambangSelisih"]
    assert selisih_maks(asli, buruk) >= fixture["ambangSelisih"]
