=========================================
PANDUAN UNGGAH FILE SOP SECARA MANUAL
=========================================

Folder ini (`public/base/sop/`) dibuat secara khusus untuk menampung gambar sampul (cover) dan file dokumen PDF Standar Operasional Prosedur (SOP).

Cara menambah / mengubah SOP:
1. Pindahkan file PDF SOP Anda (misal: `surat_izin.pdf`) ke dalam folder ini.
2. Pindahkan file gambar cover (misal: `cover_surat.png`) ke dalam folder ini juga.
3. Buka file `templates/lainnya/sop.html`
4. Di sana terdapat modul-modul HTML dengan komentar. Ubah nama file pada atribut `src="..."` (untuk gambar) dan `href="..."` (untuk tombol unduh) sesuai dengan nama file yang baru Anda masukkan ke folder ini.
5. Selesai! Jangan lupa restart container CKAN agar perubahan langsung termuat.
