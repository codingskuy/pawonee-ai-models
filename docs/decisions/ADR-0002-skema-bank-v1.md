# ADR-0002 — Skema bank resep v1.0.0 dan data referensi

Status: Diterima | Tanggal: 2026-10-21 | Tiket: PWN-AI-002

## Konteks

ADR-0001 mensyaratkan id slug dan id kontrak `R-01`..`R-12` dipetakan eksplisit pada skema, serta pembaruan `:shared:pantry-resep` bila skema berubah. Skema templat awal (jumlah bahan berupa string, tanpa `kodeGrade`, tanpa substitusi) tidak memenuhi BR-101..BR-107 dan FSD 20 (bahan gram integer, kode grade enum, alergen, alat, flag).

## Keputusan

1. Skema `models/schema.json` berversi 1.0.0 (`versiSkema`); bank membawa `versiBank` 1.0.0. Bank dikunci tepat 12 resep (`minItems`=`maxItems`=12); resep ke-13 hanya v2.0.0.
2. Resep membawa `kode` (`R-01`..`R-12`) dan `id` (slug). Slug `sop-benih-jagung` diganti `sop-jagung-telur` mengikuti BRD 10.
3. Bahan: `jumlah` integer pada takaran dasar 4 porsi dengan `satuan` ∈ {`gram`, `ml`, `pcs`} (kg/liter/sdm/sdt disimpan sebagai gram/ml sesuai KONTEKS §6), `kodeGrade` ∈ {G2-V, G2-U, G2-S, NON-G2}, dan `jenis` ∈ {sayur, protein, telur, karbo, bumbu, santan, cair} yang menentukan faktor skala (bahan/bumbu/air) dan pembulatan belanja.
4. `levelPedas` resep 0..3 (sama dengan `ProfilKeluarga.pedas`); sebelumnya 0..5.
5. Substitusi baku BR-103 disimpan pada bank (`substitusi`): tiap aturan punya `hilang`, daftar `pengganti` alternatif (tiap alternatif berisi komponen, alergen, `tambahMenit`).
6. Gizi (kkal) dan harga referensi per bahan disimpan di `models/referensi_bahan.json`, dipakai evaluasi kecukupan kkal dan biaya serta fixture paritas. Hanya harga Lumbung G2 (BRD 10 / FSD 20) dan santan (modul pantry-resep) berasal dari dokumen; sisanya ASUMSI.

## Asumsi (belum ada kontrak; menunggu konfirmasi pemilik)

- A1: `estimasiBiaya` = rupiah satu makan keluarga 4 jiwa termasuk pendamping standar BR-104 (beras 360 g, atau lauk nabati bila resep tanpa protein), dibulatkan Rp500.
- A2: `pendamping.nasi`/`pendamping.lauk` mewakili standar BR-104 agar kecukupan 550–700 kkal per jiwa terukur pada paket makan, bukan pada resep sendirian.
- A3: Nilai kkal dan harga non-Lumbung pada `referensi_bahan.json` adalah perkiraan; perlu validasi ahli gizi/Lumbung sebelum produksi.
- A4: Bahan G2 yang ditandai pada resep tanpa sayur di dokumen lama (mis. bawang merah G2-U, cabai G2-V, tomat G2-V) adalah penentuan penulis bank; BR-101 hanya mewajibkan kode pada bahan utama.

## Konsekuensi

- `:shared:pantry-resep` (milik Pawonee), backend, dan fixture paritas wajib mengikuti bentuk ini; perubahan lanjutan lewat ADR baru dan bump `versiSkema`.
- Dokumen lama (24 resep, R-01..R-24, tabel substitusi 5 baris) tidak dipakai; BR-103 v1.0.0 hanya 3 aturan.
