# -*- coding: utf-8 -*-
"""
Model database untuk fitur Publikasi
"""
import logging
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
import ckan.model as model

log = logging.getLogger(__name__)
Base = declarative_base()

class Publikasi(Base):
    """Model untuk tabel publikasi"""
    __tablename__ = 'publikasi'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    judul = Column(String(500), nullable=False)
    tahun_terbit = Column(Integer, nullable=False)
    deskripsi = Column(Text, nullable=False)
    file_pdf = Column(String(500), nullable=False)
    gambar_cover = Column(String(500), nullable=True)
    ukuran_file = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Konversi object ke dictionary untuk template"""
        return {
            'id': self.id,
            'judul': self.judul,
            'tahun_terbit': self.tahun_terbit,
            'deskripsi': self.deskripsi,
            'file_pdf': self.file_pdf,
            'gambar_cover': self.gambar_cover,
            'ukuran_file': self.ukuran_file,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

def init_publikasi_table():
    """Inisialisasi tabel publikasi di database"""
    try:
        engine = model.meta.engine
        if engine:
            Base.metadata.create_all(engine)
            log.info("Tabel publikasi berhasil dibuat!")
            return True
    except Exception as e:
        log.error(f"Gagal membuat tabel publikasi: {str(e)}")
    return False