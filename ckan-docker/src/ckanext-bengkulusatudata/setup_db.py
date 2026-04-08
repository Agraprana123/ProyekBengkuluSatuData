#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script untuk membuat tabel publikasi di database CKAN
Cara menjalankan:
    docker-compose exec ckan python /srv/app/src/ckanext-bengkulusatudata/setup_db.py
"""

import sys
import os

# Tambahkan path plugin ke sys.path dengan urutan prioritas
plugin_model_path = '/srv/app/src/ckanext-bengkulusatudata/ckanext/bengkulusatudata'
if plugin_model_path not in sys.path:
    sys.path.insert(0, plugin_model_path)

# Import CKAN model terlebih dahulu (untuk memastikan engine siap)
import ckan.model as ckan_model

# Import model plugin dengan path eksplisit
from ckanext.bengkulusatudata.model import Publikasi, Base, init_db

if __name__ == '__main__':
    print("=" * 50)
    print("Migrasi Database - Tabel Publikasi")
    print("=" * 50)
    
    try:
        # Pastikan engine CKAN sudah siap
        engine = ckan_model.meta.engine
        if engine is None:
            print("✗ Error: Database engine CKAN belum siap!")
            print("Tips: Pastikan CKAN sudah berjalan dan terinisialisasi.")
            sys.exit(1)
        
        # Buat tabel menggunakan engine CKAN
        Base.metadata.create_all(engine)
        print("✓ Tabel publikasi berhasil dibuat!")
        print("=" * 50)
        
        # Verifikasi tabel
        with engine.connect() as conn:
            result = conn.execute("SELECT COUNT(*) FROM publikasi")
            count = result.fetchone()[0]
            print(f"✓ Jumlah record saat ini: {count}")
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        print("=" * 50)
        import traceback
        traceback.print_exc()
        sys.exit(1)