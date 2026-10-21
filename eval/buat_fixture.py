"""Menghasilkan fixture paritas 32 kasus (PWN-AI-004) dari bank 12 resep.

  python eval/buat_fixture.py            # tulis fixtures/paritas-32-kasus.json
  python eval/buat_fixture.py --periksa  # keluar 1 bila berkas terbit berbeda dari hasil regenerasi

Keluaran deterministik (tanpa waktu/acak). Kasus: 12 per resep (A), 10 tepi (B),
10 skenario campuran (C). Skor harapan dihitung `rekomendasi_ref.Mesin`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import rekomendasi_ref as rr

DASAR = Path(__file__).resolve().parent.parent
BANK = DASAR / "models" / "bank_resep_grade2.json"
REFERENSI = DASAR / "models" / "referensi_bahan.json"
KELUARAN = DASAR / "fixtures" / "paritas-32-kasus.json"

VERSI_FIXTURE = "1.0.0"
AMBANG_SELISIH = 0.01

ALAT_LENGKAP = ["kompor", "wajan", "panci", "kukusan", "blender"]
ALAT_BAWAAN = ["kompor", "wajan", "panci"]  # BR-202


def profil(alergi=(), pantangan=(), budget=35000, pedas=3, alat=ALAT_LENGKAP):
    return {
        "alergi": list(alergi),
        "pantangan": list(pantangan),
        "budgetPerMakan": budget,
        "levelPedas": pedas,
        "alatMasak": list(alat),
    }


def item(nama, jumlah, grade="G2-V", satuan="gram", hari=None):
    return {"nama": nama, "jumlah": jumlah, "satuan": satuan, "kodeGrade": grade, "kedaluwarsaHari": hari}


def stok_resep(resep: dict, jiwa: int = 4) -> list[dict]:
    """Stok persis kebutuhan terskala resep (tanpa bahan dapur pokok); G2-S dengan kedaluwarsa aman (5 hari)."""
    hasil = []
    for b in resep["bahan"]:
        if b["nama"] in rr.BAHAN_DAPUR_POKOK:
            continue
        hari = 5 if b["kodeGrade"] == "G2-S" else None
        hasil.append(item(b["nama"], rr.skala_jumlah(b["jumlah"], b["jenis"], jiwa), b["kodeGrade"], b["satuan"], hari))
    return hasil


def stok_kaya() -> list[dict]:
    return [
        item("wortel", 500), item("kentang", 600, "G2-U"), item("bayam", 400, "G2-S", hari=4),
        item("kangkung", 400, "G2-S", hari=4), item("tomat", 300), item("cabai merah", 150),
        item("bawang merah", 200, "G2-U"), item("jagung manis", 500, "G2-U"),
        item("sawi hijau", 300, "G2-S", hari=4), item("taoge", 200, "G2-S", hari=4), item("kol", 300, "G2-U"),
        item("tempe", 300, "NON-G2"), item("telur", 6, "NON-G2", "pcs"),
    ]


def kasus_a(bank: dict) -> list[dict]:
    hasil = []
    for n, r in enumerate(bank["resep"], start=1):
        hasil.append(
            {
                "id": f"A-{n:02d}",
                "judul": f"Stok tepat {r['id']} menghasilkan {r['kode']} di peringkat 1",
                "masukan": {"profil": profil(), "stok": stok_resep(r), "jiwa": 4, "waktuMaksimalMenit": 45},
            }
        )
    return hasil


def kasus_b() -> list[dict]:
    def k(id_, judul, stok, jiwa=4, menit=45, **p):
        return {"id": id_, "judul": judul, "masukan": {"profil": profil(**p), "stok": stok, "jiwa": jiwa, "waktuMaksimalMenit": menit}}

    stok_09 = [  # stok condong ke sayur berkuah: tanpa batas kelompok, 3 resep kuah masuk 5 besar
        item("bayam", 400, "G2-S", hari=4), item("jagung manis", 500, "G2-U"), item("bawang merah", 50, "G2-U"),
        item("wortel", 250), item("kentang", 300, "G2-U"), item("kol", 150, "G2-U"), item("sawi hijau", 200, "G2-S", hari=4),
        item("taoge", 100, "G2-S", hari=4), item("telur", 4, "NON-G2", "pcs"),
    ]
    return [
        k("B-01", "Alergi telur menyaring R-03, R-04, R-10 (disaring, bukan diturunkan)", stok_kaya(), alergi=["telur"]),
        k("B-02", "Alat hanya kompor dan wajan menyaring resep berpanci", stok_kaya(), alat=["kompor", "wajan"]),
        k("B-03", "Waktu maksimal 15 menit menyaring resep lebih lama", stok_kaya(), menit=15),
        k("B-04", "Stok kosong: mode hemat, 5 resep termurah, tanpa skor", [], menit=45),
        k("B-05", "Jiwa 0 ditolak JIWA_DI_LUAR_RENTANG", [item("wortel", 400)], jiwa=0),
        k("B-06", "Jiwa 9 ditolak JIWA_DI_LUAR_RENTANG", [item("wortel", 400)], jiwa=9),
        k("B-07", "Bonus +5 G2-S kedaluwarsa tepat 2 hari (R-06; stok wortel tak terpakai agar skor tidak terpotong 50)", [item("kangkung", 400, "G2-S", hari=2), item("tomat", 200), item("cabai rawit", 15), item("wortel", 400)]),
        k("B-08", "Tanpa bonus G2-S kedaluwarsa 3 hari (batas atas bonus terlewati)", [item("kangkung", 400, "G2-S", hari=3), item("tomat", 200), item("cabai rawit", 15), item("wortel", 400)]),
        k("B-09", "Diversifikasi: maksimal 2 resep sekelompok di 5 besar (resep kuah ke-3 digeser)", stok_09),
        k("B-10", "Seri skor dimenangkan waktu terkecil, lalu belanja terkecil, lalu kode (tanpa stok G2)", [item("ayam", 50, "NON-G2")]),
    ]


def kasus_c() -> list[dict]:
    def k(id_, judul, stok, jiwa, menit=30, **p):
        return {"id": id_, "judul": judul, "masukan": {"profil": profil(**p), "stok": stok, "jiwa": jiwa, "waktuMaksimalMenit": menit}}

    return [
        k("C-01", "1 jiwa, profil bawaan BR-202, stok kecil dengan G2-S segera layu", [
            item("wortel", 100), item("kentang", 150, "G2-U"), item("kangkung", 150, "G2-S", hari=1), item("telur", 2, "NON-G2", "pcs"),
        ], 1, pedas=1, alat=ALAT_BAWAAN),
        k("C-02", "2 jiwa, sayur layu campur, pedas tinggi", [
            item("bayam", 200, "G2-S", hari=2), item("taoge", 100, "G2-S", hari=3), item("jagung manis", 250, "G2-U"), item("wortel", 150),
        ], 2),
        k("C-03", "3 jiwa, alergi kedelai (tempe, tahu, kecap tersaring)", stok_kaya(), 3, 45, alergi=["kedelai"]),
        k("C-04", "5 jiwa, profil bawaan (cabai >50 g tersaring), santan terbeli", [
            item("kentang", 700, "G2-U"), item("wortel", 400), item("kol", 300, "G2-U"), item("santan", 600, "NON-G2", "ml"),
            item("tempe", 400, "NON-G2"),
        ], 5, 45, pedas=1, alat=ALAT_BAWAAN),
        k("C-05", "6 jiwa, vegetarian-nabati: ayam diganti substitusi baku", [
            item("wortel", 400), item("kentang", 500, "G2-U"), item("sawi hijau", 300, "G2-S", hari=2), item("taoge", 150, "G2-S", hari=2),
        ], 6, 45, pantangan=["vegetarian-nabati"]),
        k("C-06", "7 jiwa (faktor ASUMSI interpolasi), stok kaya", stok_kaya(), 7, 45),
        k("C-07", "8 jiwa, budget Rp25.000 menyaring resep mahal", [
            item("wortel", 400), item("kentang", 600, "G2-U"), item("kol", 400, "G2-U"), item("tomat", 300),
        ], 8, 45, budget=25000),
        k("C-08", "4 jiwa, lunak-lansia dan tanpa-santan", [
            item("bayam", 400, "G2-S", hari=3), item("jagung manis", 500, "G2-U"), item("wortel", 300), item("kentang", 300, "G2-U"),
        ], 4, 45, pantangan=["lunak-lansia", "tanpa-santan"]),
        k("C-09", "4 jiwa, budget Rp12.000: skor budget pita 8 dan penyaringan belanja", [
            item("kangkung", 400, "G2-S", hari=3), item("tomat", 200),
        ], 4, 30, budget=12000),
        k("C-10", "3 jiwa, vegetarian + alergi telur dan kacang-tanah: pengganti ayam beralih ke tahu", [
            item("tahu", 400, "NON-G2"), item("wortel", 250), item("kentang", 300, "G2-U"),
        ], 3, 30, alergi=["telur", "kacang-tanah"], pantangan=["vegetarian-nabati"], alat=["kompor", "wajan"]),
    ]


def _bulat(nilai):
    if isinstance(nilai, float):
        return round(nilai, 4)
    if isinstance(nilai, dict):
        return {k: _bulat(v) for k, v in nilai.items()}
    if isinstance(nilai, list):
        return [_bulat(v) for v in nilai]
    return nilai


def _harapan(hasil: dict) -> dict:
    rek = []
    for r in hasil["rekomendasi"]:
        rek.append(
            {
                "kode": r["kode"],
                "id": r["id"],
                "skorTotal": r["skorTotal"],
                "skorSerapan": r["skorSerapan"],
                "skorKecocokanStok": r["skorKecocokanStok"],
                "skorBudget": r["skorBudget"],
                "skorWaktu": r["skorWaktu"],
                "belanjaTambahanRp": r["belanjaTambahanRp"],
                "belanjaTambahan": r["belanjaTambahan"],
                "bahanTerskala": r["bahanTerskala"],
            }
        )
    return _bulat({"galat": hasil["galat"], "modeTanpaStok": hasil["modeTanpaStok"], "rekomendasi": rek})


def bangun() -> dict:
    bank_bytes = BANK.read_bytes()
    bank = json.loads(bank_bytes)
    referensi = json.loads(REFERENSI.read_text(encoding="utf-8"))
    mesin = rr.Mesin(bank, referensi)

    kasus = kasus_a(bank) + kasus_b() + kasus_c()
    for c in kasus:
        m = c["masukan"]
        c["harapan"] = _harapan(mesin.rekomendasikan(m["profil"], m["stok"], m["jiwa"], m["waktuMaksimalMenit"]))

    bahan_dipakai = sorted({b["nama"] for r in bank["resep"] for b in r["bahan"]})
    return {
        "versiFixture": VERSI_FIXTURE,
        "versiBank": bank["versiBank"],
        "versiSkema": bank["versiSkema"],
        "bankSha256": hashlib.sha256(bank_bytes).hexdigest(),
        "bankBerkas": "models/bank_resep_grade2.json",
        "ambangSelisih": AMBANG_SELISIH,
        "konfigurasi": {
            "faktorPorsiPersen": {
                str(j): {"bahan": f[0], "bumbu": f[1], "air": f[2], **({"asumsi": True} if j in rr.JIWA_ASUMSI else {})}
                for j, f in sorted(rr.FAKTOR_PORSI.items())
            },
            "kelipatanPembulatan": rr.KELIPATAN,
            "jenisFaktorBumbu": sorted(rr.FAKTOR_BUMBU),
            "jenisFaktorAir": sorted(rr.FAKTOR_AIR),
            "bahanDapurPokok": rr.BAHAN_DAPUR_POKOK,
            "harga": {n: {k: referensi["bahan"][n][k] for k in ("satuan", "per", "harga")} for n in bahan_dipakai},
        },
        "kasus": kasus,
    }


def _tulis(o, indent: int = 0, lebar: int = 118) -> str:
    """JSON rapi: objek/larik yang muat satu baris ditulis inline, sisanya diperluas."""
    datar = json.dumps(o, ensure_ascii=False)
    if not isinstance(o, (dict, list)) or len(datar) + indent <= lebar:
        return datar
    pad = " " * (indent + 2)
    if isinstance(o, dict):
        isi = [f"{pad}{json.dumps(k, ensure_ascii=False)}: {_tulis(v, indent + 2, lebar)}" for k, v in o.items()]
        return "{\n" + ",\n".join(isi) + "\n" + " " * indent + "}"
    isi = [f"{pad}{_tulis(v, indent + 2, lebar)}" for v in o]
    return "[\n" + ",\n".join(isi) + "\n" + " " * indent + "]"


def render() -> str:
    return _tulis(bangun()) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Hasilkan fixture paritas 32 kasus")
    p.add_argument("--periksa", action="store_true", help="gagal bila berkas terbit berbeda dari regenerasi")
    a = p.parse_args(argv)
    teks = render()
    if a.periksa:
        ada = KELUARAN.read_text(encoding="utf-8") if KELUARAN.exists() else None
        if ada != teks:
            print("Fixture usang: jalankan `python eval/buat_fixture.py` lalu commit hasilnya.")
            return 1
        print("Fixture terbit sama dengan hasil regenerasi.")
        return 0
    KELUARAN.parent.mkdir(parents=True, exist_ok=True)
    KELUARAN.write_text(teks, encoding="utf-8")
    print(f"Ditulis: {KELUARAN} ({len(json.loads(teks)['kasus'])} kasus)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
