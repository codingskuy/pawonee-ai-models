# Metrik evaluasi bank resep grade-2

Evaluasi terakhir: 2026-10-21
Versi bank: 1.0.0 | Versi skema: 1.0.0
QA gate: LULUS (12/12 resep lolos grade-2)

Dihasilkan oleh `python eval/evaluate.py --tulis eval/metrics.md`; jangan disunting tangan.

| Kriteria | Aturan | Hasil |
|---|---|---|
| Jumlah resep | tepat 12 | 12 |
| Skema `models/schema.json` | valid | 12/12 |
| Grade-2 | grade 2, kode grade sah, menyerap bahan G2 | 12/12 |
| Waktu | <= 45 menit | 12/12 |
| Kompor tunggal | kompor, tanpa oven/air-fryer | 12/12 |
| Biaya keluarga 4 jiwa | Rp18.000 sampai Rp45.000 | 12/12 |
| Kecukupan | 550 sampai 700 kkal per jiwa per makan berat | 12/12 |
| Substitusi baku BR-103 dan id unik | sesuai BRD 10 | lulus |

## Rincian per resep

| Kode | Id | Menit | Biaya (Rp) | kkal per jiwa | Lolos |
|---|---|---|---|---|---|
| R-01 | tempe-tumis-bawang | 15 | 19.500 | 581.4 | ya |
| R-02 | sayur-bening-bayam | 10 | 19.000 | 561.6 | ya |
| R-03 | telur-balado | 25 | 24.000 | 576.3 | ya |
| R-04 | nasi-goreng-kampung | 15 | 20.500 | 555.4 | ya |
| R-05 | sop-ayam-sederhana | 30 | 25.500 | 630.5 | ya |
| R-06 | tumis-kangkung | 10 | 19.500 | 567.9 | ya |
| R-07 | semur-tahu | 20 | 19.500 | 571.7 | ya |
| R-08 | pecel-sayur | 15 | 20.000 | 633.5 | ya |
| R-09 | ayam-kecap-rumahan | 30 | 23.000 | 622.9 | ya |
| R-10 | sop-jagung-telur | 20 | 20.500 | 578.7 | ya |
| R-11 | sambal-goreng-tempe-kentang | 30 | 24.500 | 676.9 | ya |
| R-12 | capcay-kuah | 15 | 22.500 | 561.2 | ya |

Catatan: kkal dan harga bersumber `models/referensi_bahan.json` (ASUMSI kecuali harga Lumbung G2); kkal dihitung pada paket makan (resep + pendamping BR-104). Lihat ADR-0002.

Cara mereproduksi:

```bash
pip install -r eval/requirements.txt
python eval/evaluate.py
```
