# pawonee-ai-models

Inti kecerdasan Pawonee — **Divisi Pawonee (AI Cooking Assistant)**, org `Coding-Skuy`. Berisi **bank resep grade-2** yang sudah dikurasi beserta skema dan evaluasi. Bagian dari arsitektur **Opsi A ChefGenie**.

- TownHall: [Coding-Skuy/Pawonee-TownHall](https://github.com/Coding-Skuy/Pawonee-TownHall).
- Modul `:shared:pantry-resep` adalah **milik Pawonee** (sumber: `pawonee-app-kmp/shared/pantry-resep`); skema JSON di sini (`models/schema.json`) adalah cermin lintas platform yang dijaga selaras dengan modul tersebut.
- Konsumen: `pawonee-backend-service` menyajikan bank ini lewat API; **Pedaree** memakai keluarannya sebagai sinyal rekomendasi.

## Arti grade-2

Setiap resep lolos kurasi dua lapis: (1) kelengkapan bahan + langkah yang dapat dimasak, (2) estimasi waktu, biaya, dan level pedas yang masuk akal. Ini **bukan stub** — `models/bank_resep_grade2.json` berisi 12 resep Indonesia asli yang langsung dipakai backend dan aplikasi.

## Isi

```
models/bank_resep_grade2.json   # bank 12 resep (R-01..R-12) + substitusi baku BR-103
models/schema.json              # skema JSON bank v1.0.0 (ADR-0002)
models/referensi_bahan.json     # gizi (kkal) dan harga referensi per bahan (ASUMSI kecuali harga Lumbung G2)
eval/evaluate.py                # pemeriksaan mutu otomatis terhadap skema + aturan grade-2
eval/requirements.txt           # dependensi evaluasi (jsonschema==4.23.0)
eval/metrics.md                 # hasil evaluasi terakhir
tests/                          # uji pytest (skema, isi bank)
requirements-dev.txt            # dependensi uji (pytest)
```

## Cara jalan (Python 3.12)

```bash
pip install -r requirements-dev.txt
python eval/evaluate.py
python -m pytest -q tests
```

Keluaran evaluasi yang diharapkan: `12/12 resep lolos grade-2`.

### QA gate rilis

`python eval/evaluate.py` keluar dengan kode 0 hanya bila 12/12 resep lolos dan substitusi baku sah; selain itu kode 1 (rilis diblokir). Gerbang di CI infra cukup menjalankan perintah itu dan `python -m pytest -q tests`.

Bukti QA gate dihasilkan, bukan disunting tangan:

```bash
python eval/evaluate.py --tulis eval/metrics.md   # tanggal hari ini; atau --tanggal YYYY-MM-DD
```

Uji `test_metrics_md_terbit_cocok_dengan_hasil_evaluasi` gagal bila `eval/metrics.md` tidak sama dengan hasil evaluasi saat ini.

## Menambah atau mengubah resep

Bank dikunci 12 resep pada v1.0.0 (resep ke-13 hanya v2.0.0). Untuk mengubah isi resep:

1. Ubah entri di `models/bank_resep_grade2.json` mengikuti `models/schema.json` (bahan gram integer, `kodeGrade` per bahan).
2. Jalankan `python -m pytest -q tests` dan `python eval/evaluate.py`; pastikan lolos.
3. Perbarui `eval/metrics.md` dengan tanggal dan hasil.
4. Perubahan skema atau bank = perubahan kontrak: bump versi, tulis ADR baru, selaraskan `:shared:pantry-resep`.
5. Sinkronkan ke database `pawonee` lewat migrasi di `pawonee-backend-service`.

## Repo terkait

- [pawonee-app-kmp](https://github.com/Coding-Skuy/pawonee-app-kmp)
- [pawonee-backend-service](https://github.com/Coding-Skuy/pawonee-backend-service)
- [pawonee-data-pipeline](https://github.com/Coding-Skuy/pawonee-data-pipeline)
