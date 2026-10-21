# Fixture paritas 32 kasus (PWN-AI-004)

Satu sumber kebenaran untuk uji paritas skor rekomendasi dan skala porsi antara KMP (Kotlin, `:shared:pantry-resep`) dan web (TypeScript, `src/lib/server/rekomendasi.ts`). JSON netral: tanpa tipe khusus bahasa.

| Berkas | Isi |
|---|---|
| `paritas-32-kasus.json` | 32 kasus: masukan (profil, stok, jiwa, waktu maksimal) dan harapan (skor per komponen, belanja tambahan, bahan terskala) |
| `schema-kasus-uji.json` | JSON Schema fixture (draft-07) |
| `../models/bank_resep_grade2.json` | Bank 12 resep; kasus mereferensikan resep lewat `kode` `R-NN` (definisi resep TIDAK diduplikasi di fixture) |

Bidang tingkat atas: `versiFixture`, `versiBank`, `versiSkema`, `bankSha256` (SHA-256 berkas bank pada saat fixture dibuat), `ambangSelisih` (0,01), `konfigurasi` (faktor porsi, pembulatan, bahan dapur pokok, harga), `kasus`.

## Ambang selisih (pemblokir rilis)

Selisih absolut tiap skor (`skorTotal`, `skorSerapan`, `skorKecocokanStok`, `skorBudget`, `skorWaktu`) antara hasil klien dan `harapan` harus **< 0,01** (`ambangSelisih`). Daftar `kode` hasil harus sama persis dan berurutan; `belanjaTambahanRp`, `bahanTerskala`, `galat`, dan `modeTanpaStok` harus sama persis. Pelanggaran memblokir rilis web (FSD 10 butir 2, FSD 30). Skor di fixture dibulatkan 4 desimal.

## Cara memakai di KMP dan web

1. Salin dua berkas ke repo konsumen dan jangan disunting: `fixtures/paritas-32-kasus.json` dan `models/bank_resep_grade2.json`.
   - KMP: `shared/pantry-resep/src/commonTest/fixtures/` (path berkas uji bersama pada dokumen modul: `.../fixtures/kasus-uji.json`; boleh disalin dengan nama itu).
   - Web: mis. `src/lib/server/__fixtures__/`, dibaca oleh `bun run test`.
2. Uji pertama: hitung SHA-256 berkas bank salinan dan bandingkan dengan `bankSha256`; berbeda berarti bank dan fixture tidak sepaket.
3. Untuk tiap kasus: panggil mesin dengan `masukan` lalu bandingkan dengan `harapan` memakai aturan ambang di atas. Kasus `jiwa` 0 dan 9 mengharapkan `galat: "JIWA_DI_LUAR_RENTANG"` dan `rekomendasi: []`.
4. `alasan` (dua kalimat teks) tidak termasuk fixture karena bergantung bahasa/templat; ia bukan bagian paritas skor.

## Komposisi kasus

- **A-01..A-12** satu per resep: stok persis kebutuhan resep (jiwa 4); resep itu wajib peringkat 1.
- **B-01..B-10** tepi: alergi, alat hilang, waktu melebihi, stok kosong (mode hemat), jiwa 0 dan 9, bonus G2-S kedaluwarsa tepat 2 hari lawan 3 hari, diversifikasi maksimal 2 sekelompok, seri skor (menit, lalu belanja, lalu kode).
- **C-01..C-10** skenario campuran: jiwa 1, 2, 3, 5, 6, 7, 8; vegetarian-nabati (substitusi ayam), tanpa-santan, lunak-lansia, alergi ganda, budget ketat.

## Spesifikasi rumus (ringkas; rujukan: `eval/rekomendasi_ref.py`)

Seluruh jumlah memakai aritmetika integer; faktor porsi dalam persen.

**PorsiScaler** per bahan: `persen` = faktor bumbu bila `jenis` = `bumbu`; faktor air bila `jenis` ∈ {`cair`, `santan`}; selain itu faktor bahan. Hasil = `ceil(jumlah * persen / (100 * k)) * k`, dengan `k` dari `kelipatanPembulatan` (sayur 50, telur 2, santan 200) atau 1.

**Tahap 1 filter keras** (resep dibuang): alergen resep beririsan dengan `alergi`; `tanpa-santan` dan resep bertanda `mengandung-santan`; `lunak-lansia` dan resep tanpa flag `lunak-lansia`; alat resep bukan himpunan bagian `alatMasak`; `menit` > `waktuMaksimalMenit`; total gram bahan berawalan `cabai` > 50 dan `levelPedas` < 2; belanja tambahan > `budgetPerMakan`. Pantangan `vegetarian-nabati`: resep `mengandung-daging` tanpa `varian-nabati` dibuang; resep `varian-nabati` memakai alternatif pertama substitusi `ayam` (BR-103) yang alerginya tidak beririsan dengan `alergi`, dengan jumlah `ayam * komponen / 100` (dibulatkan setengah naik), lalu diskala; tanpa alternatif sah resep dibuang. `halal-selalu`, `rendah-garam`, `rendah-gula` tidak mengubah hasil.

**Tahap 2 serapan** (maks 50): stok digabung per nama (jumlah dijumlah, kedaluwarsa terkecil). `terpakai` = jumlah `min(terskala, stok)` untuk bahan berkode G2 bersatuan gram yang stoknya juga berkode G2; `tersedia` = jumlah gram seluruh stok berkode G2. `serapan = 50 * terpakai / tersedia` (0 bila `tersedia` = 0), `+5` bila ada stok `G2-S` terpakai dengan `kedaluwarsaHari` <= 2, lalu dibatasi 50.

**Tahap 3 kemudahan**: `skorKecocokanStok = 25 * dimiliki / total` (bahan dapur pokok tidak dihitung; dimiliki bila stok >= terskala). Belanja per bahan = `round_half_up(kekurangan * harga / per)`; `skorBudget` = 15 bila `belanja * 10 <= budget * 6`, selain itu 8. `skorWaktu` = 10 (<=15 menit), 7 (<=30), 4 (<=45).

**Tahap 4**: urut skor menurun (dibandingkan pada 4 desimal), lalu `menit`, `belanjaTambahanRp`, `kode` menaik; ambil sampai 5 dengan maksimal 2 per `kelompok`. **Stok kosong**: `modeTanpaStok` true, 5 resep lolos filter dengan `estimasiBiaya` termurah (lalu `menit`, `kode`), seluruh skor 0.

## Asumsi (ditandai; belum ada kontrak)

- F1: rumus tahap 2-4 ditafsirkan dari `produk/10-alur-rekomendasi.md` (Varian 1, 24 resep). "Maksimal 55 lalu dinormalkan ke 50" ditafsirkan sebagai batas atas 50 (bukan penskalaan 50/55).
- F2: faktor 7 jiwa tidak ada pada BR-105 (hanya 1-6 dan 8); dipakai interpolasi 175/145/160 persen dan ditandai `asumsi: true`. Kasus C-06 mengunci asumsi ini.
- F3: bahan dapur pokok (`air`, `garam`, `gula`, `merica`, `minyak goreng`) dianggap selalu ada.
- F4: pembulatan bahan selain sayur/telur/santan adalah ke atas ke integer; contoh dokumen "69 g menjadi 70 g" tidak diikuti (tidak ada aturan kelipatan 10).
- F5: harga non-Lumbung bersumber `models/referensi_bahan.json` (ASUMSI); fixture membawa salinannya pada `konfigurasi.harga`.
- F6: rumus ini harus dikonfirmasi pemilik `:shared:pantry-resep`; bila implementasi Kotlin berbeda, selaraskan lewat ADR dan regenerasi fixture (bump versi).

## Regenerasi

```bash
pip install -r requirements-dev.txt
python eval/buat_fixture.py            # menulis fixtures/paritas-32-kasus.json dari models/*.json
python eval/buat_fixture.py --periksa  # gagal (kode 1) bila berkas terbit usang
python -m pytest -q tests
```

Regenerasi wajib dijalankan setiap kali `models/bank_resep_grade2.json`, `models/referensi_bahan.json`, atau `eval/rekomendasi_ref.py` berubah. Perubahan fixture adalah perubahan kontrak: bump `versiFixture`, tulis ADR baru, dan beri tahu konsumen KMP dan web (uji `test_regenerasi_identik_dengan_berkas_terbit` memaksa berkas terbit selalu sama dengan hasil regenerasi).
