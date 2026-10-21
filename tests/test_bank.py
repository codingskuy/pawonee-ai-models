"""Uji isi bank 12 resep grade-2 (PWN-AI-002): BR-101..BR-103, FSD 20."""

import jsonschema

KODE_ID = [
    ("R-01", "tempe-tumis-bawang"),
    ("R-02", "sayur-bening-bayam"),
    ("R-03", "telur-balado"),
    ("R-04", "nasi-goreng-kampung"),
    ("R-05", "sop-ayam-sederhana"),
    ("R-06", "tumis-kangkung"),
    ("R-07", "semur-tahu"),
    ("R-08", "pecel-sayur"),
    ("R-09", "ayam-kecap-rumahan"),
    ("R-10", "sop-jagung-telur"),
    ("R-11", "sambal-goreng-tempe-kentang"),
    ("R-12", "capcay-kuah"),
]
GRADE = {"G2-V", "G2-U", "G2-S", "NON-G2"}
ALERGEN_RESMI = {"udang", "telur", "kacang-tanah", "kedelai", "susu-sapi", "ikan", "gluten"}


def test_valid_terhadap_skema(bank, skema):
    jsonschema.validate(bank, skema)


def test_tepat_12_resep_urut_kode_dan_id(bank):
    assert [(r["kode"], r["id"]) for r in bank["resep"]] == KODE_ID


def test_tidak_ada_slug_lama(bank):
    assert "sop-benih-jagung" not in {r["id"] for r in bank["resep"]}


def test_setiap_bahan_punya_kode_grade_dan_gram_integer(bank):
    for r in bank["resep"]:
        for b in r["bahan"]:
            assert b["kodeGrade"] in GRADE, (r["id"], b)
            assert isinstance(b["jumlah"], int) and not isinstance(b["jumlah"], bool)
            assert b["jumlah"] > 0


def test_setiap_resep_menyerap_minimal_satu_bahan_g2(bank):
    for r in bank["resep"]:
        assert any(b["kodeGrade"].startswith("G2-") for b in r["bahan"]), r["id"]


def test_nama_bahan_unik_per_resep(bank):
    for r in bank["resep"]:
        nama = [b["nama"] for b in r["bahan"]]
        assert len(nama) == len(set(nama)), r["id"]


def test_capcay_sapu_stok_memakai_minimal_3_jenis_g2(bank):
    capcay = next(r for r in bank["resep"] if r["kode"] == "R-12")
    g2 = {b["nama"] for b in capcay["bahan"] if b["kodeGrade"].startswith("G2-")}
    assert len(g2) >= 3
    assert "sapu-stok" in capcay["flag"]


def test_g2_s_hanya_pada_sayur_layu_cepat(bank):
    for r in bank["resep"]:
        for b in r["bahan"]:
            if b["kodeGrade"] == "G2-S":
                assert b["nama"] in {"kangkung", "bayam", "taoge", "sawi hijau"}


def test_alergen_resep_mencakup_bahan_dan_lauk_pendamping(bank):
    peta = {
        "telur": "telur",
        "tempe": "kedelai",
        "tahu": "kedelai",
        "kecap manis": "kedelai",
        "bumbu pecel": "kacang-tanah",
    }
    for r in bank["resep"]:
        wajib = {peta[b["nama"]] for b in r["bahan"] if b["nama"] in peta}
        lauk = r["pendamping"]["lauk"]
        if lauk:
            wajib.add(peta[lauk])
        assert wajib <= set(r["alergen"]), (r["id"], wajib, r["alergen"])
        assert set(r["alergen"]) <= ALERGEN_RESMI


def test_flag_santan_dan_daging_konsisten_dengan_bahan(bank):
    for r in bank["resep"]:
        ada_santan = any(b["jenis"] == "santan" for b in r["bahan"])
        assert ada_santan == ("mengandung-santan" in r["flag"]), r["id"]
        ada_daging = any(b["nama"] in {"ayam", "bakso"} for b in r["bahan"])
        assert ada_daging == ("mengandung-daging" in r["flag"]), r["id"]
        if "varian-nabati" in r["flag"]:
            assert "mengandung-daging" in r["flag"]


def test_varian_nabati_hanya_bila_daging_punya_substitusi_baku(bank):
    for r in bank["resep"]:
        daging = {b["nama"] for b in r["bahan"] if b["nama"] in {"ayam", "bakso"}}
        assert ("varian-nabati" in r["flag"]) == (daging == {"ayam"}), r["id"]


def test_substitusi_baku_br103(bank):
    sub = {s["hilang"]["nama"]: s for s in bank["substitusi"]}
    assert set(sub) == {"ayam", "santan", "kentang"}

    ayam = sub["ayam"]
    assert ayam["hilang"] == {"nama": "ayam", "jumlah": 100, "satuan": "gram"}
    pilihan = {
        tuple((k["nama"], k["jumlah"], k["satuan"]) for k in p["komponen"])
        for p in ayam["pengganti"]
    }
    assert pilihan == {
        (("telur", 2, "pcs"),),
        (("tahu", 200, "gram"),),
        (("tempe", 150, "gram"),),
    }

    santan = sub["santan"]
    assert santan["hilang"] == {"nama": "santan", "jumlah": 400, "satuan": "ml"}
    assert len(santan["pengganti"]) == 1
    assert [(k["nama"], k["jumlah"], k["satuan"]) for k in santan["pengganti"][0]["komponen"]] == [
        ("susu kedelai", 400, "ml"),
        ("minyak kelapa", 10, "ml"),
    ]

    kentang = sub["kentang"]
    assert kentang["hilang"] == {"nama": "kentang", "jumlah": 500, "satuan": "gram"}
    assert len(kentang["pengganti"]) == 1
    p = kentang["pengganti"][0]
    assert [(k["nama"], k["jumlah"], k["satuan"]) for k in p["komponen"]] == [("ubi kuning", 500, "gram")]
    assert p["tambahMenit"] == 5


def test_alergen_pengganti_sesuai_komponen(bank):
    peta = {"telur": "telur", "tahu": "kedelai", "tempe": "kedelai", "susu kedelai": "kedelai"}
    for s in bank["substitusi"]:
        for p in s["pengganti"]:
            wajib = {peta[k["nama"]] for k in p["komponen"] if k["nama"] in peta}
            assert set(p["alergen"]) == wajib, (s["id"], p)


def test_referensi_bahan_mencakup_semua_bahan_dan_pengganti(bank, referensi):
    ada = set(referensi["bahan"])
    perlu = {b["nama"] for r in bank["resep"] for b in r["bahan"]}
    perlu |= {k["nama"] for s in bank["substitusi"] for p in s["pengganti"] for k in p["komponen"]}
    perlu |= {"beras", "tahu", "tempe", "telur"}  # nasi dan lauk pendamping BR-104
    assert perlu <= ada, perlu - ada


def test_satuan_bahan_sama_dengan_referensi(bank, referensi):
    for r in bank["resep"]:
        for b in r["bahan"]:
            assert referensi["bahan"][b["nama"]]["satuan"] == b["satuan"], (r["id"], b["nama"])


def test_harga_lumbung_g2_sesuai_brd(referensi):
    lumbung = {"wortel": 1200, "kentang": 1500, "tomat": 1800, "kangkung": 1000, "cabai merah": 4000}
    for nama, harga in lumbung.items():
        ref = referensi["bahan"][nama]
        assert (ref["per"], ref["harga"]) == (100, harga), nama
    assert referensi["bahan"]["santan"]["harga"] == 1500  # Rp3.000 per 200 ml


def test_bentuk_entri_referensi_bahan(referensi):
    for nama, e in referensi["bahan"].items():
        assert set(e) == {"satuan", "per", "harga", "kkal", "sumber"}, nama
        assert e["satuan"] in {"gram", "ml", "pcs"}
        assert e["per"] == (1 if e["satuan"] == "pcs" else 100), nama
        assert isinstance(e["harga"], int) and e["harga"] >= 0
        assert isinstance(e["kkal"], int) and e["kkal"] >= 0
