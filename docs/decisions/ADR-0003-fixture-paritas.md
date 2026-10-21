# ADR-0003 — Fixture paritas 32 kasus sebagai kontrak lintas KMP dan web

Status: Diterima | Tanggal: 2026-10-21 | Tiket: PWN-AI-004

## Konteks

FSD 10 butir 2 menetapkan rumus skor ditulis sekali di Kotlin dan di-port ke TypeScript, dengan selisih skor 0,01 pada 32 kasus sebagai pemblokir rilis web. Dokumen modul KMP menyebut berkas uji bersama `kasus-uji.json` tetapi tidak mendefinisikan isinya, sehingga fixture harus ditetapkan di sini agar kedua sisi tidak menduplikasi definisi.

## Keputusan

1. Fixture diterbitkan di repo ini: `fixtures/paritas-32-kasus.json` (+ `fixtures/schema-kasus-uji.json`), JSON netral, mereferensikan resep lewat `kode` `R-NN` dari `models/bank_resep_grade2.json` dan mengunci bank lewat `bankSha256`.
2. 32 kasus = 12 per resep + 10 tepi + 10 skenario campuran. Ambang `ambangSelisih` = 0,01 pada tiap skor; urutan `kode`, `belanjaTambahanRp`, `bahanTerskala`, `galat` harus identik.
3. Skor harapan dihasilkan oleh implementasi rujukan Python (`eval/rekomendasi_ref.py`) memakai aritmetika integer, bukan oleh mesin produksi. Mesin produksi (Kotlin, lalu port TypeScript) wajib cocok dengan fixture; ketidakcocokan diselesaikan dengan ADR baru, bukan dengan menyunting fixture.
4. Fixture dibuat ulang hanya lewat `python eval/buat_fixture.py`; uji memaksa berkas terbit sama dengan hasil regenerasi. Perubahan fixture = perubahan kontrak: bump `versiFixture` dan ADR baru.

## Konsekuensi

- Asumsi rumus (F1..F6 di `fixtures/README.md`) harus dikonfirmasi pemilik `:shared:pantry-resep` sebelum fixture dianggap beku; faktor 7 jiwa belum ada di BR-105.
- Repo konsumen menyalin fixture dan bank bersama checksum; tidak ada definisi kasus yang diduplikasi.
- Implementasi Kotlin dan port TypeScript belum ada pada saat ADR ini; keberlakuan paritas baru terbukti setelah keduanya dijalankan terhadap fixture.
