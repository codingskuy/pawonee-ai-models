"""Uji implementasi rujukan (Python) rumus rekomendasi dan PorsiScaler (PWN-AI-004).

Rumus ditulis sekali di sini sebagai penghasil fixture; KMP dan web wajib meniru
hasilnya dengan selisih skor < 0,01 (lihat fixtures/README.md).
"""

import pytest

import rekomendasi_ref as rr


@pytest.fixture(scope="module")
def mesin(bank_asli, referensi):
    return rr.Mesin(bank_asli, referensi)


PROFIL = {
    "alergi": [],
    "pantangan": [],
    "budgetPerMakan": 35000,
    "levelPedas": 3,
    "alatMasak": ["kompor", "wajan", "panci", "kukusan", "blender"],
}


def stok(nama, jumlah, grade="G2-V", satuan="gram", hari=None):
    return {"nama": nama, "jumlah": jumlah, "satuan": satuan, "kodeGrade": grade, "kedaluwarsaHari": hari}


def minta(mesin, stok_, jiwa=4, menit=45, **profil):
    return mesin.rekomendasikan({**PROFIL, **profil}, stok_, jiwa, menit)


# ---------- PorsiScaler (BR-105, BR-106, BR-107) ----------

@pytest.mark.parametrize(
    "jiwa,faktor",
    [(1, 30), (2, 55), (3, 80), (4, 100), (5, 125), (6, 150), (8, 200)],
)
def test_faktor_bahan_sesuai_tabel_br105(jiwa, faktor):
    assert rr.FAKTOR_PORSI[jiwa][0] == faktor


def test_faktor_bumbu_dan_air_sesuai_standar_porsi():
    assert rr.FAKTOR_PORSI[1] == (30, 35, 35)
    assert rr.FAKTOR_PORSI[5] == (125, 115, 120)
    assert rr.FAKTOR_PORSI[8] == (200, 160, 180)


def test_faktor_jiwa_7_adalah_interpolasi_bertanda_asumsi():
    assert rr.FAKTOR_PORSI[7] == (175, 145, 160)
    assert 7 in rr.JIWA_ASUMSI


def test_skala_sayur_dibulatkan_ke_atas_kelipatan_50():
    # wortel 250 g x 1,25 = 312,5 -> 350 (contoh standar porsi bagian 5)
    assert rr.skala_jumlah(250, "sayur", 5) == 350
    assert rr.skala_jumlah(600, "sayur", 5) == 750
    assert rr.skala_jumlah(400, "sayur", 4) == 400


def test_skala_telur_ke_butir_genap():
    assert rr.skala_jumlah(4, "telur", 3) == 4  # 3,2 -> 4
    assert rr.skala_jumlah(4, "telur", 5) == 6  # 4 x 1,25 = 5 -> butir genap 6
    assert rr.skala_jumlah(4, "telur", 1) == 2  # 1,2 -> 2


def test_skala_santan_kelipatan_200_ml_memakai_faktor_air():
    # 400 ml x 1,20 = 480 -> 600 ml (contoh standar porsi bagian 5)
    assert rr.skala_jumlah(400, "santan", 5) == 600
    assert rr.skala_jumlah(200, "santan", 1) == 200


def test_skala_bumbu_memakai_faktor_bumbu_dan_dibulatkan_ke_atas():
    assert rr.skala_jumlah(60, "bumbu", 5) == 69  # 60 x 1,15
    assert rr.skala_jumlah(4, "bumbu", 1) == 2  # 1,4 -> 2


def test_skala_tidak_mengalami_galat_floating_point():
    # 500 x 0,30 = 150 tepat (float biasa memberi 150,00000000000003)
    assert rr.skala_jumlah(500, "protein", 1) == 150
    assert rr.skala_jumlah(1000, "karbo", 3) == 800


@pytest.mark.parametrize("jiwa", [0, 9, -1, 100])
def test_jiwa_di_luar_rentang_ditolak(mesin, jiwa):
    hasil = minta(mesin, [stok("wortel", 400)], jiwa=jiwa)
    assert hasil["galat"] == "JIWA_DI_LUAR_RENTANG"
    assert hasil["rekomendasi"] == []


# ---------- Filter keras (tahap 1) ----------

def kode_hasil(hasil):
    return [r["kode"] for r in hasil["rekomendasi"]]


def stok_kaya():
    return [
        stok("wortel", 500), stok("kentang", 600, "G2-U"), stok("bayam", 400, "G2-S"),
        stok("kangkung", 400, "G2-S"), stok("tomat", 300), stok("cabai merah", 150),
        stok("bawang merah", 200, "G2-U"), stok("jagung manis", 500, "G2-U"),
        stok("sawi hijau", 300, "G2-S"), stok("taoge", 200, "G2-S"), stok("kol", 300, "G2-U"),
    ]


def test_alergen_disaring_bukan_diturunkan(mesin):
    hasil = minta(mesin, stok_kaya(), alergi=["telur"])
    assert not {"R-03", "R-04", "R-10"} & set(kode_hasil(hasil))
    assert hasil["rekomendasi"]


def test_alat_hilang_menyaring(mesin):
    hasil = minta(mesin, stok_kaya(), alatMasak=["kompor", "wajan"])
    assert not {"R-02", "R-03", "R-05", "R-08", "R-10"} & set(kode_hasil(hasil))


def test_waktu_melebihi_menyaring(mesin):
    hasil = minta(mesin, stok_kaya(), menit=15)
    menit = {r["kode"]: r for r in mesin.bank["resep"]}
    assert all(menit[k]["menit"] <= 15 for k in kode_hasil(hasil))


def test_cabai_lebih_50_g_hanya_untuk_pedas_minimal_2(mesin):
    stok_balado = [
        stok("telur", 4, "NON-G2", "pcs"), stok("cabai merah", 100), stok("bawang merah", 50, "G2-U"), stok("tomat", 160),
    ]
    assert kode_hasil(minta(mesin, stok_balado, levelPedas=2))[0] == "R-03"
    assert "R-03" not in kode_hasil(minta(mesin, stok_balado, levelPedas=1))
    assert "R-11" not in kode_hasil(minta(mesin, stok_balado, levelPedas=1))


def test_vegetarian_menyaring_resep_daging_tanpa_varian(mesin):
    hasil = minta(mesin, stok_kaya(), pantangan=["vegetarian-nabati"])
    assert "R-12" not in kode_hasil(hasil)  # bakso: tanpa substitusi baku


def test_vegetarian_mengganti_ayam_dengan_substitusi_baku(mesin):
    hasil = mesin.rekomendasikan(
        {**PROFIL, "pantangan": ["vegetarian-nabati"]}, [stok("wortel", 250), stok("kentang", 300, "G2-U")], 4, 45
    )
    sop = next(r for r in hasil["rekomendasi"] if r["kode"] == "R-05")
    nama = {b["nama"] for b in sop["bahanTerskala"]}
    assert "ayam" not in nama
    assert "telur" in nama  # alternatif pertama BR-103, 400 g ayam -> 8 butir
    telur = next(b for b in sop["bahanTerskala"] if b["nama"] == "telur")
    assert telur["jumlah"] == 8 and telur["satuan"] == "pcs"


def test_vegetarian_alergi_telur_memakai_alternatif_berikutnya(mesin):
    hasil = mesin.rekomendasikan(
        {**PROFIL, "pantangan": ["vegetarian-nabati"], "alergi": ["telur"]},
        [stok("wortel", 250), stok("kentang", 300, "G2-U")], 4, 45,
    )
    sop = next(r for r in hasil["rekomendasi"] if r["kode"] == "R-05")
    pengganti = next(b for b in sop["bahanTerskala"] if b["nama"] in {"tahu", "tempe"})
    assert pengganti["nama"] == "tahu" and pengganti["jumlah"] == 800


def test_tanpa_santan_menyaring(mesin):
    assert "R-11" not in kode_hasil(minta(mesin, stok_kaya(), pantangan=["tanpa-santan"]))


def test_lunak_lansia_hanya_resep_lunak(mesin):
    lunak = {r["kode"] for r in mesin.bank["resep"] if "lunak-lansia" in r["flag"]}
    hasil = minta(mesin, stok_kaya(), pantangan=["lunak-lansia"])
    assert set(kode_hasil(hasil)) <= lunak


def test_belanja_melebihi_budget_menyaring(mesin):
    hasil = minta(mesin, [stok("wortel", 100)], budgetPerMakan=3000)
    assert hasil["rekomendasi"] == []


# ---------- Skor (tahap 2-3) ----------

def test_stok_tepat_resep_menghasilkan_skor_penuh(mesin):
    # R-06 tumis kangkung: semua bahan non-pokok ada di stok, jiwa 4
    hasil = minta(
        mesin,
        [stok("kangkung", 400, "G2-S"), stok("cabai rawit", 15), stok("tomat", 200), stok("bawang putih", 20, "NON-G2")],
    )
    r = hasil["rekomendasi"][0]
    assert r["kode"] == "R-06"
    assert r["skorSerapan"] == 50.0  # seluruh stok G2 (kangkung 400, tomat 200, cabai 15 g) terpakai
    assert r["skorKecocokanStok"] == 25.0
    assert r["skorBudget"] == 15
    assert r["skorWaktu"] == 10
    assert r["belanjaTambahanRp"] == 0


def test_bonus_g2s_kedaluwarsa_maks_2_hari_plus_5(mesin):
    dasar = [stok("kangkung", 400, "G2-S", hari=3), stok("tomat", 200), stok("cabai rawit", 15)]
    cepat = [stok("kangkung", 400, "G2-S", hari=2), stok("tomat", 200), stok("cabai rawit", 15)]
    a = next(r for r in minta(mesin, dasar)["rekomendasi"] if r["kode"] == "R-06")
    b = next(r for r in minta(mesin, cepat)["rekomendasi"] if r["kode"] == "R-06")
    assert b["skorSerapan"] == pytest.approx(min(50.0, a["skorSerapan"] + 5))


def test_serapan_dibatasi_50(mesin):
    hasil = minta(mesin, [stok("kangkung", 400, "G2-S", hari=1), stok("tomat", 160), stok("cabai rawit", 15)])
    r = next(r for r in hasil["rekomendasi"] if r["kode"] == "R-06")
    assert r["skorSerapan"] <= 50.0


def test_skor_waktu_per_pita(mesin):
    waktu = {r["kode"]: r["menit"] for r in mesin.bank["resep"]}
    assert waktu["R-02"] <= 15 and 16 <= waktu["R-03"] <= 30 and waktu["R-03"] == 25
    hasil = minta(mesin, stok_kaya(), levelPedas=3)
    skor = {r["kode"]: r["skorWaktu"] for r in hasil["rekomendasi"]}
    for k, v in skor.items():
        m = waktu[k]
        assert v == (10 if m <= 15 else 7 if m <= 30 else 4)


def test_skor_budget_pita_60_persen(mesin):
    # budget besar -> belanja <= 60% -> 15
    hasil = minta(mesin, [stok("kangkung", 400, "G2-S")], budgetPerMakan=100000)
    assert all(r["skorBudget"] == 15 for r in hasil["rekomendasi"])
    # budget pas-pasan -> 8
    ketat = minta(mesin, [stok("kangkung", 400, "G2-S")], budgetPerMakan=8000)
    r = next(r for r in ketat["rekomendasi"] if r["kode"] == "R-06")
    assert r["belanjaTambahanRp"] * 10 > 8000 * 6
    assert r["skorBudget"] == 8


def test_belanja_tambahan_rincian_menjumlah_ke_total(mesin):
    hasil = minta(mesin, [stok("wortel", 100)])
    for r in hasil["rekomendasi"]:
        assert sum(x["rupiah"] for x in r["belanjaTambahan"]) == r["belanjaTambahanRp"]


def test_bahan_dapur_pokok_tidak_dibelanjakan(mesin):
    hasil = minta(mesin, [stok("kangkung", 400, "G2-S")])
    for r in hasil["rekomendasi"]:
        assert not {"air", "garam", "gula", "merica", "minyak goreng"} & {x["nama"] for x in r["belanjaTambahan"]}


# ---------- Ranking dan diversifikasi (tahap 4) ----------

def test_maksimal_lima_item_dan_diversifikasi_maks_2_per_kelompok(mesin):
    hasil = minta(mesin, stok_kaya())
    assert len(hasil["rekomendasi"]) <= 5
    kelompok = {r["kode"]: r["kelompok"] for r in mesin.bank["resep"]}
    from collections import Counter

    assert max(Counter(kelompok[k] for k in kode_hasil(hasil)).values()) <= 2


def test_urutan_menurun_menurut_skor(mesin):
    skor = [r["skorTotal"] for r in minta(mesin, stok_kaya())["rekomendasi"]]
    assert skor == sorted(skor, reverse=True)


def test_seri_dimenangkan_waktu_lalu_belanja_lalu_kode():
    urut = rr.urutkan(
        [
            {"kode": "R-09", "skorTotal": 50.0, "menit": 30, "belanjaTambahanRp": 0},
            {"kode": "R-02", "skorTotal": 50.0, "menit": 10, "belanjaTambahanRp": 900},
            {"kode": "R-03", "skorTotal": 50.0, "menit": 10, "belanjaTambahanRp": 100},
            {"kode": "R-01", "skorTotal": 50.0, "menit": 10, "belanjaTambahanRp": 100},
            {"kode": "R-07", "skorTotal": 50.00004, "menit": 99, "belanjaTambahanRp": 99},  # 50,00004 dan 50,0 seri pada 4 desimal
        ]
    )
    assert [r["kode"] for r in urut] == ["R-01", "R-03", "R-02", "R-09", "R-07"]


def test_stok_kosong_mode_hemat_lima_termurah(mesin):
    hasil = minta(mesin, [])
    assert hasil["modeTanpaStok"] is True
    biaya = {r["kode"]: r["estimasiBiaya"] for r in mesin.bank["resep"]}
    got = [biaya[k] for k in kode_hasil(hasil)]
    assert len(got) == 5 and got == sorted(got)
    assert all(r["skorTotal"] == 0 for r in hasil["rekomendasi"])


def test_hasil_deterministik(mesin):
    assert minta(mesin, stok_kaya()) == minta(mesin, stok_kaya())


def test_serapan_proporsional_terhadap_stok_g2_total(mesin):
    # R-06 memakai 400 g kangkung + 200 g tomat + 15 g cabai; stok G2 total 1015 g (400 g wortel tak terpakai)
    hasil = minta(
        mesin,
        [stok("kangkung", 400, "G2-S", hari=9), stok("tomat", 200), stok("cabai rawit", 15), stok("wortel", 400)],
    )
    r = next(r for r in hasil["rekomendasi"] if r["kode"] == "R-06")
    assert r["skorSerapan"] == pytest.approx(50 * 615 / 1015)
