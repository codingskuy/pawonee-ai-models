"""Evaluasi mutu bank resep grade-2 Pawonee (QA gate rilis, PWN-AI-003).

Kriteria per resep (BRD 10, SRS QA, PRD US-005):
  skema   valid terhadap models/schema.json
  grade2  kode grade sah, grade == 2, menyerap minimal satu bahan G2
  waktu   <= 45 menit
  kompor  kompor tunggal (ada kompor, tanpa oven/air-fryer)
  biaya   Rp18.000..Rp45.000 untuk satu makan keluarga 4 jiwa
  kkal    550..700 kkal per jiwa per makan berat (resep + pendamping BR-104)

Kriteria tingkat bank: tepat 12 resep, id unik, pemetaan kode R-NN <-> slug, dan
substitusi baku BR-103. Gerbang lulus hanya bila 12/12 resep lolos DAN tidak ada
galat tingkat bank; selain itu keluar dengan kode 1 (rilis diblokir).

Pemakaian:
  python eval/evaluate.py                       # evaluasi, cetak ringkasan
  python eval/evaluate.py --tulis eval/metrics.md [--tanggal YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover
    print("Pasang dependensi dahulu: pip install -r eval/requirements.txt")
    sys.exit(2)

DASAR = Path(__file__).resolve().parent.parent
BANK = DASAR / "models" / "bank_resep_grade2.json"
SKEMA = DASAR / "models" / "schema.json"
REFERENSI = DASAR / "models" / "referensi_bahan.json"
METRICS = DASAR / "eval" / "metrics.md"

TARGET_RESEP = 12
MENIT_MAKS = 45
BIAYA_MIN, BIAYA_MAKS = 18000, 45000
KKAL_MIN, KKAL_MAKS = 550, 700
JIWA_DASAR = 4
ALAT_TERLARANG_KOMPOR_TUNGGAL = {"oven", "air-fryer"}

# BR-104: pendamping standar per 4 jiwa
NASI_BERAS_GRAM = 360
LAUK_PENDAMPING = {"tahu": (400, "gram"), "tempe": (300, "gram"), "telur": (4, "pcs")}

# BRD 10 v1.0.0: kode, slug (urut R-01..R-12)
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

# BR-103: substitusi baku. nama hilang -> (jumlah, satuan, {alternatif: tuple komponen}, tambahMenit per alternatif)
SUBSTITUSI_BAKU = {
    "ayam": (
        100,
        "gram",
        {
            (("telur", 2, "pcs"),): 0,
            (("tahu", 200, "gram"),): 0,
            (("tempe", 150, "gram"),): 0,
        },
    ),
    "santan": (
        400,
        "ml",
        {(("susu kedelai", 400, "ml"), ("minyak kelapa", 10, "ml")): 0},
    ),
    "kentang": (500, "gram", {(("ubi kuning", 500, "gram"),): 5}),
}


@dataclass
class HasilResep:
    kode: str
    id: str
    menit: int
    biaya: int
    kkal_per_jiwa: float
    cek: list = field(default_factory=list)  # (nama, lolos, pesan)

    @property
    def lolos(self) -> bool:
        return all(ok for _, ok, _ in self.cek)

    @property
    def galat(self) -> list[str]:
        return [f"{self.kode} {self.id}: {n}: {p}" for n, ok, p in self.cek if not ok]


@dataclass
class HasilBank:
    versi_bank: str
    versi_skema: str
    resep: list
    galat_bank: list

    @property
    def lolos(self) -> int:
        return sum(1 for r in self.resep if r.lolos)

    @property
    def gerbang_lulus(self) -> bool:
        return self.lolos == TARGET_RESEP and len(self.resep) == TARGET_RESEP and not self.galat_bank


def kkal_per_jiwa(resep: dict, referensi: dict) -> float:
    """kkal per jiwa untuk satu paket makan berat: bahan resep + pendamping standar BR-104."""
    bahan = referensi["bahan"]

    def kkal(nama: str, jumlah: int) -> float:
        e = bahan[nama]
        return jumlah / e["per"] * e["kkal"]

    total = sum(kkal(b["nama"], b["jumlah"]) for b in resep["bahan"])
    pend = resep["pendamping"]
    if pend["nasi"]:
        total += kkal("beras", NASI_BERAS_GRAM)
    if pend["lauk"]:
        total += kkal(pend["lauk"], LAUK_PENDAMPING[pend["lauk"]][0])
    return total / JIWA_DASAR


def _periksa_resep(r: dict, validator_resep, referensi: dict) -> HasilResep:
    cek = []

    galat_skema = sorted(validator_resep.iter_errors(r), key=lambda e: list(e.path))
    cek.append(("skema", not galat_skema, "; ".join(e.message for e in galat_skema[:3])))

    kode_ok = {"G2-V", "G2-U", "G2-S", "NON-G2"}
    bahan = r.get("bahan", [])
    pesan = []
    if r.get("grade") != 2:
        pesan.append("grade harus 2")
    if any(b.get("kodeGrade") not in kode_ok for b in bahan):
        pesan.append("kodeGrade bahan tidak sah")
    if not any(str(b.get("kodeGrade", "")).startswith("G2-") for b in bahan):
        pesan.append("tidak menyerap bahan G2")
    cek.append(("grade2", not pesan, "; ".join(pesan)))

    menit = r.get("menit")
    cek.append(("waktu", isinstance(menit, int) and 1 <= menit <= MENIT_MAKS, f"menit={menit}, maksimal {MENIT_MAKS}"))

    alat = set(r.get("alat", []))
    pesan = []
    if "kompor" not in alat:
        pesan.append("tanpa kompor")
    if alat & ALAT_TERLARANG_KOMPOR_TUNGGAL:
        pesan.append("memakai " + "/".join(sorted(alat & ALAT_TERLARANG_KOMPOR_TUNGGAL)))
    if r.get("jumlahKompor") != 1:
        pesan.append("jumlahKompor bukan 1")
    cek.append(("kompor", not pesan, "; ".join(pesan)))

    biaya = r.get("estimasiBiaya")
    cek.append(
        (
            "biaya",
            isinstance(biaya, int) and BIAYA_MIN <= biaya <= BIAYA_MAKS,
            f"estimasiBiaya={biaya}, wajib Rp{BIAYA_MIN}..Rp{BIAYA_MAKS}",
        )
    )

    try:
        kk = kkal_per_jiwa(r, referensi)
        cek.append(("kkal", KKAL_MIN <= kk <= KKAL_MAKS, f"{kk:.1f} kkal per jiwa, wajib {KKAL_MIN}..{KKAL_MAKS}"))
    except (KeyError, TypeError) as e:
        kk = 0.0
        cek.append(("kkal", False, f"tidak dapat dihitung ({e!r})"))

    return HasilResep(
        kode=str(r.get("kode")),
        id=str(r.get("id")),
        menit=menit if isinstance(menit, int) else 0,
        biaya=biaya if isinstance(biaya, int) else 0,
        kkal_per_jiwa=kk,
        cek=cek,
    )


def _periksa_substitusi(bank: dict) -> list[str]:
    galat = []
    ada = {}
    for s in bank.get("substitusi", []):
        ada.setdefault(s["hilang"]["nama"], []).append(s)
    for nama, (jumlah, satuan, alternatif) in SUBSTITUSI_BAKU.items():
        aturan = ada.get(nama, [])
        if len(aturan) != 1:
            galat.append(f"substitusi {nama}: harus tepat satu aturan baku (ada {len(aturan)})")
            continue
        s = aturan[0]
        if (s["hilang"]["jumlah"], s["hilang"]["satuan"]) != (jumlah, satuan):
            galat.append(f"substitusi {nama}: takaran hilang harus {jumlah} {satuan}")
        diperoleh = {
            tuple((k["nama"], k["jumlah"], k["satuan"]) for k in p["komponen"]): p["tambahMenit"]
            for p in s["pengganti"]
        }
        if diperoleh != alternatif:
            galat.append(f"substitusi {nama}: pengganti/tambahMenit tidak sesuai BR-103")
    return galat


def evaluasi(bank: dict, skema: dict, referensi: dict) -> HasilBank:
    resep_skema = {"$ref": "#/definitions/resep", "definitions": skema["definitions"]}
    validator_resep = jsonschema.Draft7Validator(resep_skema)

    daftar = bank.get("resep", [])
    hasil = [_periksa_resep(r, validator_resep, referensi) for r in daftar]

    galat_bank = []
    if len(daftar) != TARGET_RESEP:
        galat_bank.append(f"jumlah resep {len(daftar)}, wajib tepat {TARGET_RESEP}")
    terlihat = set()
    for r in daftar:
        if r.get("id") in terlihat:
            galat_bank.append(f"id ganda: {r.get('id')}")
        terlihat.add(r.get("id"))
    if [(r.get("kode"), r.get("id")) for r in daftar] != KODE_ID and len(daftar) == TARGET_RESEP:
        galat_bank.append("pemetaan kode R-01..R-12 ke id resep tidak sesuai BRD 10")
    galat_bank.extend(_periksa_substitusi(bank))
    # Skema tingkat bank (versi, substitusi, properti tak dikenal); resep sudah diperiksa per resep di atas.
    skema_bank = dict(skema)
    skema_bank["required"] = [k for k in skema["required"] if k != "resep"]
    skema_bank["properties"] = {k: v for k, v in skema["properties"].items() if k != "resep"}
    skema_bank["additionalProperties"] = True
    for e in jsonschema.Draft7Validator(skema_bank).iter_errors({k: v for k, v in bank.items() if k != "resep"}):
        galat_bank.append(f"skema: {'/'.join(map(str, e.path)) or '(akar)'}: {e.message}")

    return HasilBank(
        versi_bank=str(bank.get("versiBank", "?")),
        versi_skema=str(bank.get("versiSkema", "?")),
        resep=hasil,
        galat_bank=galat_bank,
    )


def ringkasan(hasil: HasilBank) -> str:
    baris = [f"{hasil.lolos}/{TARGET_RESEP} resep lolos grade-2."]
    for r in hasil.resep:
        for g in r.galat:
            baris.append(f"GAGAL: {g}")
    for g in hasil.galat_bank:
        baris.append(f"GAGAL: bank: {g}")
    return "\n".join(baris)


def render_metrics(hasil: HasilBank, tanggal: str) -> str:
    def hitung(nama: str) -> int:
        return sum(1 for r in hasil.resep for n, ok, _ in r.cek if n == nama and ok)

    status = "LULUS" if hasil.gerbang_lulus else "GAGAL (rilis diblokir)"
    baris = [
        "# Metrik evaluasi bank resep grade-2",
        "",
        f"Evaluasi terakhir: {tanggal}",
        f"Versi bank: {hasil.versi_bank} | Versi skema: {hasil.versi_skema}",
        f"QA gate: {status} ({hasil.lolos}/{TARGET_RESEP} resep lolos grade-2)",
        "",
        "Dihasilkan oleh `python eval/evaluate.py --tulis eval/metrics.md`; jangan disunting tangan.",
        "",
        "| Kriteria | Aturan | Hasil |",
        "|---|---|---|",
        f"| Jumlah resep | tepat {TARGET_RESEP} | {len(hasil.resep)} |",
        f"| Skema `models/schema.json` | valid | {hitung('skema')}/{TARGET_RESEP} |",
        f"| Grade-2 | grade 2, kode grade sah, menyerap bahan G2 | {hitung('grade2')}/{TARGET_RESEP} |",
        f"| Waktu | <= {MENIT_MAKS} menit | {hitung('waktu')}/{TARGET_RESEP} |",
        f"| Kompor tunggal | kompor, tanpa oven/air-fryer | {hitung('kompor')}/{TARGET_RESEP} |",
        f"| Biaya keluarga 4 jiwa | Rp{BIAYA_MIN:,} sampai Rp{BIAYA_MAKS:,} | {hitung('biaya')}/{TARGET_RESEP} |".replace(",", "."),
        f"| Kecukupan | {KKAL_MIN} sampai {KKAL_MAKS} kkal per jiwa per makan berat | {hitung('kkal')}/{TARGET_RESEP} |",
        f"| Substitusi baku BR-103 dan id unik | sesuai BRD 10 | {'lulus' if not hasil.galat_bank else 'gagal'} |",
        "",
        "## Rincian per resep",
        "",
        "| Kode | Id | Menit | Biaya (Rp) | kkal per jiwa | Lolos |",
        "|---|---|---|---|---|---|",
    ]
    for r in hasil.resep:
        baris.append(
            f"| {r.kode} | {r.id} | {r.menit} | {r.biaya:,} | {r.kkal_per_jiwa:.1f} | {'ya' if r.lolos else 'TIDAK'} |".replace(
                ",", "."
            )
        )
    baris += [
        "",
        "Catatan: kkal dan harga bersumber `models/referensi_bahan.json` (ASUMSI kecuali harga Lumbung G2); kkal dihitung pada paket makan (resep + pendamping BR-104). Lihat ADR-0002.",
        "",
        "Cara mereproduksi:",
        "",
        "```bash",
        "pip install -r eval/requirements.txt",
        "python eval/evaluate.py",
        "```",
        "",
    ]
    return "\n".join(baris)


def _tanggal(teks: str) -> str:
    try:
        datetime.date.fromisoformat(teks)
    except ValueError:
        raise argparse.ArgumentTypeError(f"tanggal harus YYYY-MM-DD: {teks!r}")
    return teks


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="QA gate evaluasi bank resep grade-2 Pawonee")
    p.add_argument("--bank", type=Path, default=BANK)
    p.add_argument("--skema", type=Path, default=SKEMA)
    p.add_argument("--referensi", type=Path, default=REFERENSI)
    p.add_argument("--tulis", type=Path, help="tulis bukti metrik (eval/metrics.md) ke berkas ini")
    p.add_argument("--tanggal", type=_tanggal, default=None, help="tanggal evaluasi YYYY-MM-DD (bawaan: hari ini)")
    a = p.parse_args(argv)

    muat = lambda f: json.loads(f.read_text(encoding="utf-8"))  # noqa: E731
    hasil = evaluasi(muat(a.bank), muat(a.skema), muat(a.referensi))
    print(ringkasan(hasil))
    if a.tulis:
        tanggal = a.tanggal or datetime.date.today().isoformat()
        a.tulis.write_text(render_metrics(hasil, tanggal), encoding="utf-8")
        print(f"Bukti ditulis: {a.tulis}")
    return 0 if hasil.gerbang_lulus else 1


if __name__ == "__main__":
    sys.exit(main())
