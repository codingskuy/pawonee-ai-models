"""Uji QA gate evaluasi bank (PWN-AI-003): kriteria, exit code, dan metrics.md."""

import copy
import re
from pathlib import Path

import pytest

import evaluate as ev

DASAR = Path(__file__).resolve().parent.parent


@pytest.fixture()
def hasil_asli(bank_asli, skema, referensi):
    return ev.evaluasi(bank_asli, skema, referensi)


def hasil_dari(bank, skema, referensi):
    return ev.evaluasi(bank, skema, referensi)


def nama_gagal(hasil, kode):
    return {n for n, ok, _ in next(r for r in hasil.resep if r.kode == kode).cek if not ok}


def test_bank_rilis_lolos_12_dari_12(hasil_asli):
    assert hasil_asli.lolos == 12
    assert hasil_asli.galat_bank == []
    assert hasil_asli.gerbang_lulus is True


def test_kriteria_wajib_dievaluasi_per_resep(hasil_asli):
    wajib = {"skema", "grade2", "waktu", "kompor", "biaya", "kkal"}
    for r in hasil_asli.resep:
        assert wajib <= {n for n, _, _ in r.cek}, r.kode


def test_kkal_per_jiwa_dalam_rentang_semua_resep(hasil_asli):
    for r in hasil_asli.resep:
        assert 550 <= r.kkal_per_jiwa <= 700, (r.kode, r.kkal_per_jiwa)


def test_waktu_lebih_dari_45_gagal(bank, skema, referensi):
    bank["resep"][0]["menit"] = 46
    assert "waktu" in nama_gagal(hasil_dari(bank, skema, referensi), "R-01")


def test_waktu_tepat_45_lolos(bank, skema, referensi):
    bank["resep"][0]["menit"] = 45
    assert "waktu" not in nama_gagal(hasil_dari(bank, skema, referensi), "R-01")


def test_oven_melanggar_kompor_tunggal(bank, skema, referensi):
    bank["resep"][0]["alat"] = ["kompor", "wajan", "oven"]
    assert "kompor" in nama_gagal(hasil_dari(bank, skema, referensi), "R-01")


def test_tanpa_kompor_gagal(bank, skema, referensi):
    bank["resep"][0]["alat"] = ["wajan"]
    assert "kompor" in nama_gagal(hasil_dari(bank, skema, referensi), "R-01")


@pytest.mark.parametrize("biaya,lolos", [(17999, False), (18000, True), (45000, True), (45001, False)])
def test_batas_biaya_porsi_keluarga(bank, skema, referensi, biaya, lolos):
    bank["resep"][0]["estimasiBiaya"] = biaya
    gagal = nama_gagal(hasil_dari(bank, skema, referensi), "R-01")
    assert ("biaya" not in gagal) is lolos


def test_kkal_terlalu_tinggi_gagal(bank, skema, referensi):
    for b in bank["resep"][0]["bahan"]:
        if b["nama"] == "tempe":
            b["jumlah"] = 900
    assert "kkal" in nama_gagal(hasil_dari(bank, skema, referensi), "R-01")


def test_kkal_terlalu_rendah_gagal(bank, skema, referensi):
    bank["resep"][0]["pendamping"]["nasi"] = False
    assert "kkal" in nama_gagal(hasil_dari(bank, skema, referensi), "R-01")


def test_resep_tanpa_bahan_g2_gagal_grade2(bank, skema, referensi):
    for b in bank["resep"][0]["bahan"]:
        b["kodeGrade"] = "NON-G2"
    assert "grade2" in nama_gagal(hasil_dari(bank, skema, referensi), "R-01")


def test_pelanggaran_skema_ditandai_per_resep(bank, skema, referensi):
    bank["resep"][2]["menit"] = 15.5
    assert "skema" in nama_gagal(hasil_dari(bank, skema, referensi), "R-03")


def test_id_ganda_memblokir_gerbang(bank, skema, referensi):
    bank["resep"][1]["id"] = bank["resep"][0]["id"]
    hasil = hasil_dari(bank, skema, referensi)
    assert not hasil.gerbang_lulus
    assert any("id ganda" in g for g in hasil.galat_bank)


def test_pemetaan_kode_ke_id_salah_memblokir(bank, skema, referensi):
    bank["resep"][0]["id"], bank["resep"][1]["id"] = bank["resep"][1]["id"], bank["resep"][0]["id"]
    hasil = hasil_dari(bank, skema, referensi)
    assert not hasil.gerbang_lulus


def test_kurang_dari_12_resep_memblokir(bank, skema, referensi):
    bank["resep"].pop()
    hasil = hasil_dari(bank, skema, referensi)
    assert hasil.lolos == 11
    assert not hasil.gerbang_lulus


def test_resep_ke_13_memblokir(bank, skema, referensi):
    bank["resep"].append(copy.deepcopy(bank["resep"][0]))
    assert not hasil_dari(bank, skema, referensi).gerbang_lulus


def test_substitusi_baku_rusak_memblokir(bank, skema, referensi):
    bank["substitusi"][0]["pengganti"][1]["komponen"][0]["jumlah"] = 250
    hasil = hasil_dari(bank, skema, referensi)
    assert not hasil.gerbang_lulus
    assert any("substitusi" in g for g in hasil.galat_bank)


def test_substitusi_hilang_memblokir(bank, skema, referensi):
    bank["substitusi"] = [s for s in bank["substitusi"] if s["hilang"]["nama"] != "santan"]
    assert not hasil_dari(bank, skema, referensi).gerbang_lulus


def test_main_exit_0_bila_12_12(capsys):
    assert ev.main([]) == 0
    assert "12/12 resep lolos grade-2" in capsys.readouterr().out


def test_main_exit_1_bila_gagal(tmp_path, bank, capsys):
    import json

    bank["resep"][0]["menit"] = 90
    f = tmp_path / "bank.json"
    f.write_text(json.dumps(bank))
    assert ev.main(["--bank", str(f)]) == 1
    keluaran = capsys.readouterr().out
    assert "11/12 resep lolos grade-2" in keluaran
    assert "GAGAL" in keluaran


def test_render_metrics_memuat_tanggal_versi_dan_hasil(hasil_asli):
    teks = ev.render_metrics(hasil_asli, "2026-10-21")
    assert "2026-10-21" in teks
    assert "Versi bank: 1.0.0" in teks
    assert "12/12" in teks
    for kode in [f"R-{n:02d}" for n in range(1, 13)]:
        assert kode in teks


def test_tulis_metrics_ke_berkas(tmp_path):
    keluar = tmp_path / "metrics.md"
    assert ev.main(["--tulis", str(keluar), "--tanggal", "2026-01-02"]) == 0
    assert "2026-01-02" in keluar.read_text()


def test_tanggal_tidak_valid_ditolak(tmp_path):
    with pytest.raises(SystemExit):
        ev.main(["--tulis", str(tmp_path / "m.md"), "--tanggal", "kemarin"])


def test_metrics_md_terbit_cocok_dengan_hasil_evaluasi(hasil_asli):
    """Bukti QA gate tidak boleh basi: eval/metrics.md harus identik dengan hasil evaluasi saat ini."""
    terbit = (DASAR / "eval" / "metrics.md").read_text(encoding="utf-8")
    tanggal = re.search(r"Evaluasi terakhir: (\d{4}-\d{2}-\d{2})", terbit).group(1)
    assert terbit == ev.render_metrics(hasil_asli, tanggal)
