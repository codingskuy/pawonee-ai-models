# CHANGELOG

Format: [Keep a Changelog](https://keepachangelog.com/id-ID/1.1.0/). Versi mengikuti `versions/` TownHall.

## [Belum dirilis]

### Diubah
- PWN-AI-002: `models/schema.json` menjadi skema bank v1.0.0 (kode `R-01`..`R-12`, bahan gram integer dengan `kodeGrade`, `substitusi`, `pendamping`, `flag`); `models/bank_resep_grade2.json` ditulis ulang menjadi 12 resep grade-2 (slug `sop-benih-jagung` menjadi `sop-jagung-telur`; `levelPedas` 0..3; biaya, alergen, alat per resep).

### Ditambahkan
- PWN-AI-003: `eval/evaluate.py` menjadi QA gate (waktu <= 45 menit, kompor tunggal, biaya Rp18.000-45.000, 550-700 kkal per jiwa, id unik, pemetaan R-NN, substitusi BR-103; exit 1 bila bukan 12/12) dengan opsi `--tulis`/`--tanggal`; `eval/metrics.md` dihasilkan otomatis (tanggal + versi bank) dan dijaga tidak basi oleh uji.
- PWN-AI-002: substitusi baku BR-103 (ayam, santan, kentang) pada bank; `models/referensi_bahan.json` (gizi dan harga referensi, berstatus ASUMSI kecuali harga Lumbung G2); uji `tests/` (pytest) dan `requirements-dev.txt`.

## [1.0.0] — 2026-10-14

### Ditambahkan
- Fondasi AI-dev v1.0.0: `AGENTS.md`, `CLAUDE.md`, ADR-0001, `40-TECHSTACK.md`, `60-BLAST-RADIUS.md`.
