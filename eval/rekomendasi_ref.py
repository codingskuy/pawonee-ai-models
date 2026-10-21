"""Implementasi RUJUKAN rumus rekomendasi dan PorsiScaler Pawonee (PWN-AI-004).

Hanya untuk menghasilkan skor harapan pada fixture paritas 32 kasus. Mesin
produksi tetap ditulis di Kotlin (`:shared:pantry-resep`) lalu di-port ke
TypeScript; keduanya wajib cocok dengan fixture dengan selisih skor < 0,01.

Sumber aturan: PRD alur rekomendasi (lima tahap), BRD 10 BR-104..BR-107, BRD 20
BR-205. Bagian yang tidak ditetapkan dokumen ditandai ASUMSI dan dicatat di
`fixtures/README.md`. Seluruh hitungan jumlah memakai integer (tanpa float)
agar identik di Python, Kotlin, dan TypeScript.
"""

from __future__ import annotations

from typing import Any

# Faktor skala dalam persen: (bahan, bumbu, air). Sumber: BR-105 + standar porsi bagian 2.
FAKTOR_PORSI: dict[int, tuple[int, int, int]] = {
    1: (30, 35, 35),
    2: (55, 60, 60),
    3: (80, 80, 85),
    4: (100, 100, 100),
    5: (125, 115, 120),
    6: (150, 130, 140),
    7: (175, 145, 160),  # ASUMSI: 7 jiwa tidak ada di tabel BR-105; interpolasi tengah 6 dan 8 jiwa
    8: (200, 160, 180),
}
JIWA_ASUMSI = {7}

# Kelipatan pembulatan belanja per jenis bahan (BR-106); jenis lain dibulatkan ke integer ke atas.
KELIPATAN = {"sayur": 50, "telur": 2, "santan": 200}
# Jenis yang memakai faktor bumbu / faktor air; selain itu faktor bahan.
FAKTOR_BUMBU = {"bumbu"}
FAKTOR_AIR = {"cair", "santan"}

# ASUMSI: bahan dapur pokok dianggap selalu ada; tidak dihitung pada kecocokan stok maupun belanja.
BAHAN_DAPUR_POKOK = ["air", "garam", "gula", "merica", "minyak goreng"]

MAKS_REKOMENDASI = 5
MAKS_PER_KELOMPOK = 2
BATAS_CABAI_GRAM = 50
BOBOT_SERAPAN = 50
BOBOT_KECOCOKAN = 25
BONUS_G2S = 5
HARI_BONUS_MAKS = 2
ARAH_SKOR = 10000  # perbandingan seri pada 4 desimal


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def skala_jumlah(jumlah: int, jenis: str, jiwa: int) -> int:
    """PorsiScaler.skala untuk satu bahan: faktor persen lalu pembulatan ke atas ke kelipatan jenisnya."""
    bahan, bumbu, air = FAKTOR_PORSI[jiwa]
    persen = bumbu if jenis in FAKTOR_BUMBU else air if jenis in FAKTOR_AIR else bahan
    kelipatan = KELIPATAN.get(jenis, 1)
    return _ceil_div(jumlah * persen, 100 * kelipatan) * kelipatan


def _bulat_setengah_naik(pembilang: int, penyebut: int) -> int:
    return (2 * pembilang + penyebut) // (2 * penyebut)


def _kunci_skor(skor: float) -> int:
    return int(skor * ARAH_SKOR + 0.5)


def urutkan(daftar: list[dict]) -> list[dict]:
    """Skor menurun (seri pada 4 desimal), lalu waktu terkecil, belanja terkecil, kode."""
    return sorted(
        daftar,
        key=lambda r: (-_kunci_skor(r["skorTotal"]), r["menit"], r["belanjaTambahanRp"], r["kode"]),
    )


def _g2(kode_grade: str) -> bool:
    return kode_grade.startswith("G2-")


class Mesin:
    def __init__(self, bank: dict, referensi: dict):
        self.bank = bank
        self.ref = referensi["bahan"]
        self.pengganti_ayam = next(s for s in bank["substitusi"] if s["hilang"]["nama"] == "ayam")

    # ---- tahap 0/1 -------------------------------------------------------------------

    def _bahan_efektif(self, resep: dict, profil: dict) -> tuple[list[dict], set[str]] | None:
        """Bahan resep setelah substitusi vegetarian; None bila resep tidak boleh tampil."""
        bahan = [dict(b) for b in resep["bahan"]]
        alergen = set(resep["alergen"])
        if "vegetarian-nabati" in profil["pantangan"] and "mengandung-daging" in resep["flag"]:
            if "varian-nabati" not in resep["flag"]:
                return None
            ayam = next(b for b in bahan if b["nama"] == "ayam")
            for alt in self.pengganti_ayam["pengganti"]:
                if set(alt["alergen"]) & set(profil["alergi"]):
                    continue
                komponen = []
                for k in alt["komponen"]:
                    # Substitusi baku per 100 g ayam; kelipatan integer (ayam 400 g -> 4x).
                    jumlah = _bulat_setengah_naik(ayam["jumlah"] * k["jumlah"], 100)
                    komponen.append(
                        {
                            "nama": k["nama"],
                            "jumlah": jumlah,
                            "satuan": k["satuan"],
                            "kodeGrade": k["kodeGrade"],
                            "jenis": "telur" if k["nama"] == "telur" else "protein",
                        }
                    )
                idx = bahan.index(ayam)
                bahan[idx : idx + 1] = komponen
                alergen |= set(alt["alergen"])
                break
            else:
                return None
        return bahan, alergen

    def _lolos_filter(self, resep: dict, profil: dict, alergen: set[str], bahan: list[dict], waktu_maks: int) -> bool:
        if alergen & set(profil["alergi"]):
            return False
        if "tanpa-santan" in profil["pantangan"] and "mengandung-santan" in resep["flag"]:
            return False
        if "lunak-lansia" in profil["pantangan"] and "lunak-lansia" not in resep["flag"]:
            return False
        if not set(resep["alat"]) <= set(profil["alatMasak"]):
            return False
        if resep["menit"] > waktu_maks:
            return False
        cabai = sum(b["jumlah"] for b in bahan if b["nama"].startswith("cabai"))
        if cabai > BATAS_CABAI_GRAM and profil["levelPedas"] < 2:
            return False
        return True

    # ---- tahap 2-3 -------------------------------------------------------------------

    def _harga(self, nama: str, jumlah: int) -> int:
        e = self.ref[nama]
        return _bulat_setengah_naik(jumlah * e["harga"], e["per"])

    def _hitung(self, resep: dict, bahan: list[dict], profil: dict, stok: dict[str, dict], jiwa: int) -> dict | None:
        terskala = []
        for b in bahan:
            terskala.append(
                {
                    "nama": b["nama"],
                    "jumlah": skala_jumlah(b["jumlah"], b["jenis"], jiwa),
                    "satuan": b["satuan"],
                    "kodeGrade": b["kodeGrade"],
                }
            )

        g2_tersedia = sum(s["jumlah"] for s in stok.values() if s["satuan"] == "gram" and _g2(s["kodeGrade"]))
        g2_terpakai = 0
        bonus = False
        dimiliki = 0
        total = 0
        belanja = []
        for b in terskala:
            s = stok.get(b["nama"])
            ada = s["jumlah"] if s and s["satuan"] == b["satuan"] else 0
            if b["nama"] in BAHAN_DAPUR_POKOK:
                continue
            total += 1
            if ada >= b["jumlah"]:
                dimiliki += 1
            kurang = max(0, b["jumlah"] - ada)
            if kurang:
                belanja.append({"nama": b["nama"], "jumlah": kurang, "satuan": b["satuan"], "rupiah": self._harga(b["nama"], kurang)})
            if s and _g2(b["kodeGrade"]) and b["satuan"] == "gram" and _g2(s["kodeGrade"]) and ada > 0:
                g2_terpakai += min(b["jumlah"], ada)
                if s["kodeGrade"] == "G2-S" and s["kedaluwarsaHari"] is not None and s["kedaluwarsaHari"] <= HARI_BONUS_MAKS:
                    bonus = True

        belanja_rp = sum(x["rupiah"] for x in belanja)
        if belanja_rp > profil["budgetPerMakan"]:
            return None  # BR-205: belanja tambahan tidak boleh melebihi budget

        serapan = BOBOT_SERAPAN * g2_terpakai / g2_tersedia if g2_tersedia > 0 else 0.0
        serapan = min(float(BOBOT_SERAPAN), serapan + (BONUS_G2S if bonus else 0))
        kecocokan = BOBOT_KECOCOKAN * dimiliki / total if total else 0.0
        skor_budget = 15 if belanja_rp * 10 <= profil["budgetPerMakan"] * 6 else 8
        skor_waktu = 10 if resep["menit"] <= 15 else 7 if resep["menit"] <= 30 else 4
        return {
            "kode": resep["kode"],
            "id": resep["id"],
            "kelompok": resep["kelompok"],
            "menit": resep["menit"],
            "skorTotal": serapan + kecocokan + skor_budget + skor_waktu,
            "skorSerapan": serapan,
            "skorKecocokanStok": kecocokan,
            "skorBudget": skor_budget,
            "skorWaktu": skor_waktu,
            "belanjaTambahanRp": belanja_rp,
            "belanjaTambahan": belanja,
            "bahanTerskala": [{k: b[k] for k in ("nama", "jumlah", "satuan")} for b in terskala],
        }

    # ---- api -------------------------------------------------------------------------

    @staticmethod
    def _gabung_stok(stok: list[dict]) -> dict[str, dict]:
        """Satu entri per nama: jumlah dijumlahkan, kedaluwarsa terkecil, grade entri pertama."""
        hasil: dict[str, dict] = {}
        for s in stok:
            if s["nama"] not in hasil:
                hasil[s["nama"]] = dict(s)
                continue
            h = hasil[s["nama"]]
            h["jumlah"] += s["jumlah"]
            if s["kedaluwarsaHari"] is not None:
                h["kedaluwarsaHari"] = (
                    s["kedaluwarsaHari"] if h["kedaluwarsaHari"] is None else min(h["kedaluwarsaHari"], s["kedaluwarsaHari"])
                )
        return hasil

    def rekomendasikan(self, profil: dict, stok: list[dict], jiwa: int, waktu_maks: int = 30) -> dict[str, Any]:
        if not isinstance(jiwa, int) or jiwa not in FAKTOR_PORSI:
            return {"galat": "JIWA_DI_LUAR_RENTANG", "modeTanpaStok": False, "rekomendasi": []}

        gabung = self._gabung_stok(stok)
        kandidat = []
        for resep in self.bank["resep"]:
            efektif = self._bahan_efektif(resep, profil)
            if efektif is None:
                continue
            bahan, alergen = efektif
            if not self._lolos_filter(resep, profil, alergen, bahan, waktu_maks):
                continue
            hitung = self._hitung(resep, bahan, profil, gabung, jiwa)
            if hitung is None:
                continue
            hitung["estimasiBiaya"] = resep["estimasiBiaya"]
            kandidat.append(hitung)

        if not stok:
            kandidat.sort(key=lambda r: (r["estimasiBiaya"], r["menit"], r["kode"]))
            pilihan = kandidat[:MAKS_REKOMENDASI]
            for r in pilihan:  # mode hemat: skor tidak dihitung
                r.update(skorTotal=0.0, skorSerapan=0.0, skorKecocokanStok=0.0, skorBudget=0, skorWaktu=0)
            return {"galat": None, "modeTanpaStok": True, "rekomendasi": pilihan}

        pilihan: list[dict] = []
        per_kelompok: dict[str, int] = {}
        for r in urutkan(kandidat):
            if per_kelompok.get(r["kelompok"], 0) >= MAKS_PER_KELOMPOK:
                continue
            per_kelompok[r["kelompok"]] = per_kelompok.get(r["kelompok"], 0) + 1
            pilihan.append(r)
            if len(pilihan) == MAKS_REKOMENDASI:
                break
        return {"galat": None, "modeTanpaStok": False, "rekomendasi": pilihan}
