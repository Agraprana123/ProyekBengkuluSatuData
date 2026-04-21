# -*- coding: utf-8 -*-
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint, request, send_from_directory, make_response
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import ckan.model as model
from sqlalchemy import text
import csv
import io

# ===== HELPER INFOGRAFIS =====
def ensure_infografis_table():
    try:
        engine = model.meta.engine
        if engine:
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS infografis (
                        id SERIAL PRIMARY KEY,
                        judul VARCHAR(500) NOT NULL,
                        kategori VARCHAR(100),
                        deskripsi TEXT,
                        gambar_file VARCHAR(500) NOT NULL,
                        file_pdf VARCHAR(500),
                        views INTEGER DEFAULT 0,
                        status VARCHAR(50) DEFAULT 'aktif',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
            return True
    except Exception as e:
        print(f"Error: {e}")
    return False

def get_kategori_list():
    return ['Penduduk', 'Perikanan & Kelautan', 'Ekonomi', 'Pendidikan', 'Kesehatan', 'Lainnya']

def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}
# ===== KONFIGURASI PUBLIKASI =====
ALLOWED_EXTENSIONS = {'pdf'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def get_file_size(file_path):
    if not os.path.exists(file_path):
        return "Unknown"
    size = os.path.getsize(file_path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def get_upload_dir():
    return '/srv/app/uploads/publikasi'

def ensure_publikasi_table():
    try:
        engine = model.meta.engine
        if engine:
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS publikasi (
                        id SERIAL PRIMARY KEY,
                        judul VARCHAR(500) NOT NULL,
                        tahun_terbit INTEGER NOT NULL,
                        deskripsi TEXT NOT NULL,
                        file_pdf VARCHAR(500) NOT NULL,
                        gambar_cover VARCHAR(500),
                        ukuran_file VARCHAR(50),
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
            return True
    except Exception as e:
        print(f"Error creating table: {e}")
    return False

# ===== HELPER UNTUK STANDAR DATA =====
def get_organisasi_list():
    """Ambil daftar organisasi/OPD"""
    try:
        session = model.Session
        result = session.execute(text("SELECT * FROM organisasi_opd ORDER BY nama"))
        return [dict(row._mapping) for row in result]
    except:
        return []

def ensure_standar_data_tables():
    """Pastikan tabel standar data ada"""
    try:
        engine = model.meta.engine
        if engine:
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS standar_data (
                        id SERIAL PRIMARY KEY,
                        kode VARCHAR(50) UNIQUE NOT NULL,
                        konsep VARCHAR(200) NOT NULL,
                        definisi TEXT NOT NULL,
                        klasifikasi TEXT,
                        ukuran VARCHAR(100),
                        satuan VARCHAR(100),
                        organisasi_id INTEGER,
                        file_dokumen VARCHAR(500),
                        status VARCHAR(50) DEFAULT 'aktif',
                        versi VARCHAR(20) DEFAULT '1.0',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS organisasi_opd (
                        id SERIAL PRIMARY KEY,
                        nama VARCHAR(200) NOT NULL,
                        kode VARCHAR(50) UNIQUE,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS standar_data_history (
                        id SERIAL PRIMARY KEY,
                        standar_data_id INTEGER NOT NULL,
                        versi VARCHAR(20) NOT NULL,
                        perubahan TEXT,
                        user_changed VARCHAR(100),
                        changed_at TIMESTAMP DEFAULT NOW()
                    )
                """))
            return True
    except Exception as e:
        print(f"Error creating tables: {e}")
    return False

# ===== HELPER JADWAL RILIS =====
def get_month_name(month_idx):
    months = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
              'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    if 1 <= month_idx <= 12:
        return months[month_idx - 1]
    return 'Januari'

def ensure_jadwal_rilis_table():
    try:
        engine = model.meta.engine
        if engine:
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS jadwal_rilis (
                        id SERIAL PRIMARY KEY,
                        indikator TEXT NOT NULL,
                        nama_data TEXT NOT NULL,
                        jenis_data VARCHAR(100),
                        organisasi_id INTEGER,
                        klasifikasi VARCHAR(100),
                        jadwal_bulan VARCHAR(50),
                        status VARCHAR(50) DEFAULT 'pending',
                        catatan_walidata TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
            return True
    except Exception as e:
        print(f"Error: {e}")
    return False


# ===== HELPER WALIDATA =====
def ensure_walidata_tables():
    """Buat tabel walidata_users dan walidata_catatan jika belum ada."""
    try:
        engine = model.meta.engine
        if engine:
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS walidata_users (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(100) UNIQUE NOT NULL,
                        user_name VARCHAR(100) NOT NULL,
                        ditunjuk_oleh VARCHAR(100),
                        catatan TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS walidata_catatan (
                        id SERIAL PRIMARY KEY,
                        dataset_id VARCHAR(100) NOT NULL,
                        dataset_name VARCHAR(500),
                        walidata_user VARCHAR(100) NOT NULL,
                        aksi VARCHAR(20) NOT NULL,
                        pesan TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
            return True
    except Exception as e:
        print(f"Error creating walidata tables: {e}")
    return False

def is_walidata(user):
    """Return True jika user adalah Walidata terdaftar atau Sysadmin."""
    if not user:
        return False
    if user.sysadmin:
        return True
    try:
        session = model.Session
        result = session.execute(
            text("SELECT id FROM walidata_users WHERE user_id = :uid"),
            {'uid': user.id}
        )
        return result.fetchone() is not None
    except:
        return False


def get_catatan_walidata_for_dataset(dataset_id):
    """Helper: Ambil catatan walidata terbaru untuk satu dataset.
    Digunakan di template package/read.html agar Produsen Data bisa melihat
    notifikasi catatan/penolakan dari Walidata secara langsung.
    """
    if not dataset_id:
        return []
    try:
        ensure_walidata_tables()
        sess = model.Session
        rows = sess.execute(
            text("""
                SELECT aksi, pesan, walidata_user, created_at
                FROM walidata_catatan
                WHERE dataset_id = :did
                ORDER BY created_at DESC
                LIMIT 5
            """),
            {'did': dataset_id}
        )
        return [dict(r._mapping) for r in rows]
    except Exception as e:
        print(f'get_catatan_walidata error: {e}')
        return []


def get_org_logo_url(package_dict):
    """Helper: Mengembalikan URL lengkap untuk logo organisasi dataset."""
    if not isinstance(package_dict, dict):
        return ''
    org = package_dict.get('organization')
    if not org:
        return ''
    
    # Prioritas 1: image_display_url (sudah absolut / lengkap)
    logo = org.get('image_display_url')
    if logo:
        # Tambahkan slash di awal jika path relatif agar browser mengambil dari root
        if not logo.startswith('http') and not logo.startswith('/'):
            logo = '/' + logo
        return logo
        
    # Prioritas 2: image_url (biasanya hanya nama file)
    logo = org.get('image_url')
    if not logo:
        return ''
        
    if logo.startswith('http') or logo.startswith('/'):
        return logo
        
    # Standar CKAN upload path untuk logo organisasi adalah di /uploads/group/
    return f'/uploads/group/{logo}'


class BengkuluSatuDataPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource('assets', 'ckanext_bengkulusatudata')

    def get_helpers(self):
        """Daftarkan custom template helpers agar bisa dipakai di Jinja2."""
        return {
            'get_catatan_walidata_for_dataset': get_catatan_walidata_for_dataset,
            'is_walidata': is_walidata,
            'get_org_logo_url': get_org_logo_url,
        }

    # ===== FORCE PRIVATE & REVISI TRACKING =====
    def _ensure_walidata_rules(self, entity, action):
        """Paksa dataset Private & catat otomatis revisi produsen."""
        try:
            import ckan.model as model
            from sqlalchemy import text
            
            user_name = getattr(toolkit.c, 'user', None)
            if not user_name: return
            
            user_obj = model.User.get(user_name)
            if not user_obj: return
            
            # Jika Walidata / Sysadmin, biarkan
            if user_obj.sysadmin or is_walidata(user_obj):
                return
                
            # PRODUSEN DATA: Paksa private apapun pilihan formnya
            entity.private = True
            
            # Jika Produsen update (revisi), catat revisi agar masuk ke dashboard Walidata kembali
            if action == 'edit':
                try:
                    ensure_walidata_tables()
                    with model.meta.engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO walidata_catatan
                                (dataset_id, dataset_name, walidata_user, aksi, pesan)
                            VALUES (:did, :dname, :wuser, 'revisi', 'Dataset telah diperbarui oleh Produsen (Revisi)')
                        """), {
                            'did': entity.id,
                            'dname': entity.title or entity.name,
                            'wuser': user_name
                        })
                except Exception as ex_db:
                    pass
        except Exception as e:
            print(f'Force private error: {e}')

    def create(self, entity):
        self._ensure_walidata_rules(entity, 'create')

    def edit(self, entity):
        self._ensure_walidata_rules(entity, 'edit')


    def get_blueprint(self):
        # ===== 1. BLUEPRINT INFOGRAFIS =====
        infografis_bp = Blueprint('infografis_bp', __name__)

                # ===== INFOGRAFIS ROUTES =====
        
        @infografis_bp.route('/infografis', strict_slashes=False, endpoint='index')
        def infografis_index():
            ensure_infografis_table()
            search = request.args.get('q', '')
            kategori = request.args.get('kategori', '')
            
            query = "SELECT * FROM infografis WHERE status = 'aktif'"
            params = {}
            if search:
                query += " AND (judul ILIKE :s OR deskripsi ILIKE :s)"
                params['s'] = f"%{search}%"
            if kategori and kategori != 'all':
                query += " AND kategori = :k"
                params['k'] = kategori
            query += " ORDER BY created_at DESC"
            
            session = model.Session
            try:
                result = session.execute(text(query), params)
                items = [{'id': r.id, 'judul': r.judul, 'kategori': r.kategori, 
                         'deskripsi': r.deskripsi, 'gambar_file': r.gambar_file,
                         'file_pdf': r.file_pdf, 'views': r.views, 'created_at': r.created_at} 
                        for r in result]
            except:
                items = []
            
            return toolkit.render('infografis/index.html', extra_vars={
                'infografis_list': items, 'kategori_list': get_kategori_list(),
                'search_query': search, 'selected_kategori': kategori
            })

        @infografis_bp.route('/api/stats/infografis-count', strict_slashes=False)
        def api_infografis_count():
            from flask import jsonify
            ensure_infografis_table()
            try:
                with toolkit.get_action('get_site_statistics')({}, {}) if False else __import__('contextlib').suppress():
                    pass
            except Exception:
                pass
            try:
                engine = __import__('ckan.model', fromlist=['meta']).meta.engine
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM infografis WHERE status = 'aktif'"))
                    count = result.scalar() or 0
            except Exception as e:
                print(f"Error counting infografis: {e}")
                count = 0
            return jsonify({'count': count})

        @infografis_bp.route('/admin/infografis/tambah', methods=['GET', 'POST'], strict_slashes=False)

        def tambah_infografis():
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')
            
            ensure_infografis_table()
            upload_dir = '/srv/app/uploads/infografis'
            os.makedirs(upload_dir, exist_ok=True)
            
            if request.method == 'POST':
                try:
                    judul = request.form.get('judul')
                    kategori = request.form.get('kategori')
                    deskripsi = request.form.get('deskripsi')
                    
                    if not all([judul, kategori]):
                        toolkit.h.flash_error('Judul dan Kategori wajib diisi!')
                        return toolkit.render('infografis/admin_form.html', extra_vars={'kategori_list': get_kategori_list(), 'mode': 'tambah'})
                    
                    gambar = request.files.get('gambar')
                    if not gambar or gambar.filename == '' or not allowed_image(gambar.filename):
                        toolkit.h.flash_error('Gambar wajib diunggah (PNG/JPG/JPEG)!')
                        return toolkit.render('infografis/admin_form.html', extra_vars={'kategori_list': get_kategori_list(), 'mode': 'tambah'})
                    
                    img_name = secure_filename(f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{gambar.filename}")
                    gambar.save(os.path.join(upload_dir, img_name))
                    
                    pdf_name = None
                    pdf = request.files.get('file_pdf')
                    if pdf and pdf.filename != '' and pdf.filename.endswith('.pdf'):
                        pdf_name = secure_filename(f"pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pdf.filename}")
                        pdf.save(os.path.join(upload_dir, pdf_name))
                    
                    with model.meta.engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO infografis (judul, kategori, deskripsi, gambar_file, file_pdf)
                            VALUES (:j, :k, :d, :g, :p)
                        """), {'j': judul, 'k': kategori, 'd': deskripsi, 'g': img_name, 'p': pdf_name})
                    
                    toolkit.h.flash_success(f'Berhasil! Infografis "{judul}" ditambahkan.')
                    return toolkit.redirect_to('/infografis')
                except Exception as e:
                    toolkit.h.flash_error(f'Error: {str(e)}')
            
            return toolkit.render('infografis/admin_form.html', extra_vars={'kategori_list': get_kategori_list(), 'mode': 'tambah'})

        @infografis_bp.route('/admin/infografis/edit/<int:id>', methods=['GET', 'POST'], strict_slashes=False)
        def edit_infografis(id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')
            
            ensure_infografis_table()
            upload_dir = '/srv/app/uploads/infografis'
            
            if request.method == 'GET':
                session = model.Session
                data = session.execute(text("SELECT * FROM infografis WHERE id = :id"), {'id': id}).fetchone()
                if not data:
                    return toolkit.redirect_to('/infografis')
                return toolkit.render('infografis/admin_form.html', extra_vars={
                    'data': dict(data._mapping), 'kategori_list': get_kategori_list(), 'mode': 'edit'
                })
            
            if request.method == 'POST':
                try:
                    judul = request.form.get('judul')
                    kategori = request.form.get('kategori')
                    deskripsi = request.form.get('deskripsi')
                    
                    session = model.Session
                    lama = session.execute(text("SELECT * FROM infografis WHERE id = :id"), {'id': id}).fetchone()
                    
                    img_name = lama.gambar_file
                    gambar = request.files.get('gambar')
                    if gambar and gambar.filename != '' and allowed_image(gambar.filename):
                        if img_name:
                            old = os.path.join(upload_dir, img_name)
                            if os.path.exists(old): os.remove(old)
                        img_name = secure_filename(f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{gambar.filename}")
                        gambar.save(os.path.join(upload_dir, img_name))
                    
                    pdf_name = lama.file_pdf
                    pdf = request.files.get('file_pdf')
                    if pdf and pdf.filename != '' and pdf.filename.endswith('.pdf'):
                        if pdf_name:
                            old = os.path.join(upload_dir, pdf_name)
                            if os.path.exists(old): os.remove(old)
                        pdf_name = secure_filename(f"pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pdf.filename}")
                        pdf.save(os.path.join(upload_dir, pdf_name))
                    
                    with model.meta.engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE infografis SET judul=:j, kategori=:k, deskripsi=:d, 
                            gambar_file=:g, file_pdf=:p, updated_at=NOW() WHERE id=:id
                        """), {'j': judul, 'k': kategori, 'd': deskripsi, 'g': img_name, 'p': pdf_name, 'id': id})
                    
                    toolkit.h.flash_success(f'Berhasil! Infografis "{judul}" diupdate.')
                    return toolkit.redirect_to('/infografis')
                except Exception as e:
                    toolkit.h.flash_error(f'Error: {str(e)}')
            
            return toolkit.render('infografis/admin_form.html', extra_vars={'data': {'id': id}, 'kategori_list': get_kategori_list(), 'mode': 'edit'})

        @infografis_bp.route('/admin/infografis/hapus/<int:id>', methods=['POST'], strict_slashes=False)
        def hapus_infografis(id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')
            
            session = model.Session
            data = session.execute(text("SELECT * FROM infografis WHERE id = :id"), {'id': id}).fetchone()
            if data:
                upload_dir = '/srv/app/uploads/infografis'
                for f in [data.gambar_file, data.file_pdf]:
                    if f:
                        path = os.path.join(upload_dir, f)
                        if os.path.exists(path): os.remove(path)
                with model.meta.engine.begin() as conn:
                    conn.execute(text("DELETE FROM infografis WHERE id = :id"), {'id': id})
                toolkit.h.flash_success(f'Infografis "{data.judul}" dihapus.')
            return toolkit.redirect_to('/infografis')

        @infografis_bp.route('/infografis/detail/<int:id>', strict_slashes=False)
        def detail_infografis(id):
            ensure_infografis_table()
            session = model.Session
            with model.meta.engine.begin() as conn:
                conn.execute(text("UPDATE infografis SET views = views + 1 WHERE id = :id"), {'id': id})
            data = session.execute(text("SELECT * FROM infografis WHERE id = :id"), {'id': id}).fetchone()
            if not data:
                return toolkit.redirect_to('/infografis')
            return toolkit.render('infografis/detail.html', extra_vars={'data': dict(data._mapping)})

        @infografis_bp.route('/infografis/download/<int:id>', strict_slashes=False)
        def download_infografis(id):
            session = model.Session
            data = session.execute(text("SELECT * FROM infografis WHERE id = :id"), {'id': id}).fetchone()
            if not data or not data.file_pdf:
                return toolkit.redirect_to('/infografis')
            return send_from_directory('/srv/app/uploads/infografis', data.file_pdf, as_attachment=True)

        @infografis_bp.route('/uploads/infografis/<filename>', strict_slashes=False)
        def serve_infografis(filename):
            return send_from_directory('/srv/app/uploads/infografis', filename)

        # ===== 2. BLUEPRINT STANDAR DATA =====
        standar_data_bp = Blueprint('standar_data_bp', __name__)

        # 2.1 Standar Data - Halaman Utama dengan Search & Filter
        @standar_data_bp.route('/standar-data', strict_slashes=False, endpoint='index')
        def standar_index():
            ensure_standar_data_tables()
            
            search_query = request.args.get('q', '')
            org_filter = request.args.get('organisasi', '')
            status_filter = request.args.get('status', '')
            
            query = """
                SELECT sd.*, oo.nama as organisasi_nama 
                FROM standar_data sd
                LEFT JOIN organisasi_opd oo ON sd.organisasi_id = oo.id
                WHERE 1=1
            """
            params = {}
            
            if search_query:
                query += " AND (sd.kode ILIKE :search OR sd.konsep ILIKE :search OR sd.definisi ILIKE :search)"
                params['search'] = f"%{search_query}%"
            
            if org_filter:
                query += " AND sd.organisasi_id = :org_id"
                params['org_id'] = int(org_filter)
            
            if status_filter:
                query += " AND sd.status = :status"
                params['status'] = status_filter
            
            query += " ORDER BY sd.kode ASC"
            
            session = model.Session
            try:
                result = session.execute(text(query), params)
                standar_list = []
                for row in result:
                    standar_list.append({
                        'id': row.id,
                        'kode': row.kode,
                        'konsep': row.konsep,
                        'definisi': row.definisi,
                        'klasifikasi': row.klasifikasi,
                        'ukuran': row.ukuran,
                        'satuan': row.satuan,
                        'organisasi_id': row.organisasi_id,
                        'organisasi_nama': row.organisasi_nama,
                        'file_dokumen': row.file_dokumen,
                        'status': row.status,
                        'versi': row.versi,
                        'created_at': row.created_at
                    })
            except Exception as e:
                standar_list = []
                print(f"Error: {e}")
            
            return toolkit.render('standar-data/index.html', extra_vars={
                'standar_list': standar_list,
                'organisasi_list': get_organisasi_list(),
                'search_query': search_query,
                'selected_organisasi': org_filter,
                'selected_status': status_filter
            })

        # 2.2 Admin Tambah Standar Data
        @standar_data_bp.route('/admin/standar-data/tambah', methods=['GET', 'POST'], strict_slashes=False)
        def tambah_standar_data():
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')

            ensure_standar_data_tables()
            upload_dir = '/srv/app/uploads/standar-data'
            os.makedirs(upload_dir, exist_ok=True)

            if request.method == 'POST':
                try:
                    kode = request.form.get('kode')
                    konsep = request.form.get('konsep')
                    definisi = request.form.get('definisi')
                    klasifikasi = request.form.get('klasifikasi')
                    ukuran = request.form.get('ukuran')
                    satuan = request.form.get('satuan')
                    organisasi_id = request.form.get('organisasi_id')
                    versi = request.form.get('versi', '1.0')
                    
                    if not all([kode, konsep, definisi]):
                        toolkit.h.flash_error('Field wajib (Kode, Konsep, Definisi) harus diisi!')
                        return toolkit.render('standar-data/admin_form.html', extra_vars={
                            'organisasi_list': get_organisasi_list(),
                            'mode': 'tambah'
                        })
                    
                    file_dokumen = request.files.get('file_dokumen')
                    file_filename = None
                    
                    if file_dokumen and file_dokumen.filename != '':
                        file_filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_dokumen.filename}")
                        file_path = os.path.join(upload_dir, file_filename)
                        file_dokumen.save(file_path)
                    
                    with model.meta.engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO standar_data 
                            (kode, konsep, definisi, klasifikasi, ukuran, satuan, organisasi_id, file_dokumen, versi)
                            VALUES (:kode, :konsep, :definisi, :klasifikasi, :ukuran, :satuan, :organisasi_id, :file_dokumen, :versi)
                        """), {
                            'kode': kode.upper(),
                            'konsep': konsep,
                            'definisi': definisi,
                            'klasifikasi': klasifikasi,
                            'ukuran': ukuran,
                            'satuan': satuan,
                            'organisasi_id': int(organisasi_id) if organisasi_id else None,
                            'file_dokumen': file_filename,
                            'versi': versi
                        })
                        
                        conn.execute(text("""
                            INSERT INTO standar_data_history (standar_data_id, versi, perubahan, user_changed)
                            VALUES (currval('standar_data_id_seq'), :versi, 'Data standar dibuat', :user)
                        """), {'versi': versi, 'user': user.name})
                    
                    toolkit.h.flash_success(f'Berhasil! Standar Data "{kode}" telah ditambahkan.')
                    return toolkit.redirect_to('/standar-data')
                    
                except Exception as e:
                    toolkit.h.flash_error(f'Terjadi kesalahan: {str(e)}')
                    return toolkit.render('standar-data/admin_form.html', extra_vars={
                        'organisasi_list': get_organisasi_list(),
                        'mode': 'tambah'
                    })

            return toolkit.render('standar-data/admin_form.html', extra_vars={
                'organisasi_list': get_organisasi_list(),
                'mode': 'tambah'
            })

        # 2.3 Admin Edit Standar Data
        @standar_data_bp.route('/admin/standar-data/edit/<int:id>', methods=['GET', 'POST'], strict_slashes=False)
        def edit_standar_data(id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')

            ensure_standar_data_tables()
            upload_dir = '/srv/app/uploads/standar-data'
            os.makedirs(upload_dir, exist_ok=True)

            if request.method == 'GET':
                session = model.Session
                result = session.execute(text("SELECT * FROM standar_data WHERE id = :id"), {'id': id})
                data = result.fetchone()
                
                if not data:
                    toolkit.h.flash_error('Data tidak ditemukan!')
                    return toolkit.redirect_to('/standar-data')
                
                return toolkit.render('standar-data/admin_form.html', extra_vars={
                    'data': dict(data._mapping),
                    'organisasi_list': get_organisasi_list(),
                    'mode': 'edit'
                })

            if request.method == 'POST':
                try:
                    kode = request.form.get('kode')
                    konsep = request.form.get('konsep')
                    definisi = request.form.get('definisi')
                    klasifikasi = request.form.get('klasifikasi')
                    ukuran = request.form.get('ukuran')
                    satuan = request.form.get('satuan')
                    organisasi_id = request.form.get('organisasi_id')
                    versi = request.form.get('versi', '1.0')
                    
                    session = model.Session
                    result = session.execute(text("SELECT * FROM standar_data WHERE id = :id"), {'id': id})
                    data_lama = result.fetchone()
                    
                    file_dokumen = request.files.get('file_dokumen')
                    file_filename = data_lama.file_dokumen
                    
                    if file_dokumen and file_dokumen.filename != '':
                        if file_filename:
                            old_path = os.path.join(upload_dir, file_filename)
                            if os.path.exists(old_path):
                                os.remove(old_path)
                        
                        file_filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_dokumen.filename}")
                        file_path = os.path.join(upload_dir, file_filename)
                        file_dokumen.save(file_path)
                    
                    with model.meta.engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE standar_data 
                            SET kode = :kode, konsep = :konsep, definisi = :definisi,
                                klasifikasi = :klasifikasi, ukuran = :ukuran, satuan = :satuan,
                                organisasi_id = :organisasi_id, file_dokumen = :file_dokumen,
                                versi = :versi, updated_at = NOW()
                            WHERE id = :id
                        """), {
                            'kode': kode.upper(),
                            'konsep': konsep,
                            'definisi': definisi,
                            'klasifikasi': klasifikasi,
                            'ukuran': ukuran,
                            'satuan': satuan,
                            'organisasi_id': int(organisasi_id) if organisasi_id else None,
                            'file_dokumen': file_filename,
                            'versi': versi,
                            'id': id
                        })
                        
                        conn.execute(text("""
                            INSERT INTO standar_data_history (standar_data_id, versi, perubahan, user_changed)
                            VALUES (:sd_id, :versi, 'Data standar diupdate', :user)
                        """), {'sd_id': id, 'versi': versi, 'user': user.name})
                    
                    toolkit.h.flash_success(f'Berhasil! Standar Data "{kode}" telah diupdate.')
                    return toolkit.redirect_to('/standar-data')
                    
                except Exception as e:
                    toolkit.h.flash_error(f'Terjadi kesalahan: {str(e)}')
                    return toolkit.render('standar-data/admin_form.html', extra_vars={
                        'data': {'id': id},
                        'organisasi_list': get_organisasi_list(),
                        'mode': 'edit'
                    })

        # 2.4 Admin Hapus Standar Data
        @standar_data_bp.route('/admin/standar-data/hapus/<int:id>', methods=['POST'], strict_slashes=False)
        def hapus_standar_data(id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')

            try:
                session = model.Session
                result = session.execute(text("SELECT * FROM standar_data WHERE id = :id"), {'id': id})
                data = result.fetchone()
                
                if data:
                    if data.file_dokumen:
                        file_path = os.path.join('/srv/app/uploads/standar-data', data.file_dokumen)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    
                    with model.meta.engine.begin() as conn:
                        conn.execute(text("DELETE FROM standar_data WHERE id = :id"), {'id': id})
                    
                    toolkit.h.flash_success(f'Standar Data "{data.kode}" berhasil dihapus.')
            except Exception as e:
                toolkit.h.flash_error(f'Error menghapus: {str(e)}')
            
            return toolkit.redirect_to('/standar-data')

        # 2.5 Export CSV
        @standar_data_bp.route('/admin/standar-data/export/csv', strict_slashes=False)
        def export_csv():
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')
            
            session = model.Session
            result = session.execute(text("""
                SELECT sd.kode, sd.konsep, sd.definisi, sd.klasifikasi, sd.ukuran, sd.satuan,
                       oo.nama as organisasi, sd.versi, sd.status
                FROM standar_data sd
                LEFT JOIN organisasi_opd oo ON sd.organisasi_id = oo.id
                ORDER BY sd.kode
            """))
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Kode', 'Konsep', 'Definisi', 'Klasifikasi', 'Ukuran', 'Satuan', 'Organisasi', 'Versi', 'Status'])
            
            for row in result:
                writer.writerow([row.kode, row.konsep, row.definisi, row.klasifikasi, row.ukuran, row.satuan, 
                               row.organisasi or '', row.versi, row.status])
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=standar_data.csv'
            
            return response

        # 2.6 Import CSV
        @standar_data_bp.route('/admin/standar-data/import', methods=['GET', 'POST'], strict_slashes=False)
        def import_csv():
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')
            
            if request.method == 'POST':
                try:
                    file = request.files.get('csv_file')
                    if not file:
                        toolkit.h.flash_error('File CSV harus dipilih!')
                        return toolkit.render('standar-data/admin_import.html')
                    
                    content = file.stream.read().decode('utf-8')
                    reader = csv.DictReader(io.StringIO(content))
                    
                    count = 0
                    with model.meta.engine.begin() as conn:
                        for row in reader:
                            conn.execute(text("""
                                INSERT INTO standar_data (kode, konsep, definisi, klasifikasi, ukuran, satuan, versi)
                                VALUES (:kode, :konsep, :definisi, :klasifikasi, :ukuran, :satuan, :versi)
                                ON CONFLICT (kode) DO UPDATE SET
                                    konsep = EXCLUDED.konsep,
                                    definisi = EXCLUDED.definisi,
                                    updated_at = NOW()
                            """), {
                                'kode': row.get('Kode', ''),
                                'konsep': row.get('Konsep', ''),
                                'definisi': row.get('Definisi', ''),
                                'klasifikasi': row.get('Klasifikasi', ''),
                                'ukuran': row.get('Ukuran', ''),
                                'satuan': row.get('Satuan', ''),
                                'versi': row.get('Versi', '1.0')
                            })
                            count += 1
                    
                    toolkit.h.flash_success(f'Berhasil import {count} data standar!')
                    return toolkit.redirect_to('/standar-data')
                    
                except Exception as e:
                    toolkit.h.flash_error(f'Error import: {str(e)}')
            
            return toolkit.render('standar-data/admin_import.html')

        # 2.7 View History
        @standar_data_bp.route('/admin/standar-data/history/<int:id>', strict_slashes=False)
        def view_history(id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')
            
            session = model.Session
            result = session.execute(text("""
                SELECT * FROM standar_data_history 
                WHERE standar_data_id = :id 
                ORDER BY changed_at DESC
            """), {'id': id})
            
            history_list = [dict(row._mapping) for row in result]
            
            return toolkit.render('standar-data/history.html', extra_vars={
                'history_list': history_list,
                'standar_data_id': id
            })

        # 2.8 Serve uploaded files untuk Standar Data
        @standar_data_bp.route('/uploads/standar-data/<filename>', strict_slashes=False)
        def serve_standar_file(filename):
            return send_from_directory('/srv/app/uploads/standar-data', filename)

        # 2.9 Detail Standar Data (Public Access)
        @standar_data_bp.route('/standar-data/detail/<int:id>', strict_slashes=False)
        def detail_standar_data(id):
            ensure_standar_data_tables()
            
            session = model.Session
            result = session.execute(text("""
                SELECT sd.*, oo.nama as organisasi_nama, oo.kode as organisasi_kode
                FROM standar_data sd
                LEFT JOIN organisasi_opd oo ON sd.organisasi_id = oo.id
                WHERE sd.id = :id
            """), {'id': id})
            
            data = result.fetchone()
            
            if not data:
                toolkit.h.flash_error('Standar Data tidak ditemukan!')
                return toolkit.redirect_to('/standar-data')
            
            # Get history jika ada
            history_result = session.execute(text("""
                SELECT * FROM standar_data_history 
                WHERE standar_data_id = :id 
                ORDER BY changed_at DESC
            """), {'id': id})
            history_list = [dict(row._mapping) for row in history_result]
            
            return toolkit.render('standar-data/detail.html', extra_vars={
                'data': dict(data._mapping),
                'history_list': history_list
            })

        # 2.10 Download CSV (Public Access)
        @standar_data_bp.route('/standar-data/export/csv', strict_slashes=False)
        def export_csv_public():
            ensure_standar_data_tables()
            
            session = model.Session
            result = session.execute(text("""
                SELECT sd.kode, sd.konsep, sd.definisi, sd.klasifikasi, sd.ukuran, sd.satuan,
                       oo.nama as organisasi, sd.versi, sd.status
                FROM standar_data sd
                LEFT JOIN organisasi_opd oo ON sd.organisasi_id = oo.id
                WHERE sd.status = 'aktif'
                ORDER BY sd.kode
            """))
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Kode', 'Konsep', 'Definisi', 'Klasifikasi', 'Ukuran', 'Satuan', 'Organisasi', 'Versi', 'Status'])
            
            for row in result:
                writer.writerow([row.kode, row.konsep, row.definisi, row.klasifikasi, row.ukuran, row.satuan, 
                               row.organisasi or '', row.versi, row.status])
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename=standar_data_bengkulu_{datetime.now().strftime("%Y%m%d")}.csv'
            
            return response
        
        # ===== 3. BLUEPRINT ARNOLD AI CHATBOT =====
        arnold_bp = Blueprint('arnold_bp', __name__)

        @arnold_bp.route('/arnold', strict_slashes=False)
        def arnold():
             return toolkit.render('bengkulusatudata/arnold.html')

        # ===== 4. BLUEPRINT PUBLIKASI - USER VIEW =====
        publikasi_bp = Blueprint('publikasi_bp', __name__)

        @publikasi_bp.route('/publikasi', strict_slashes=False, endpoint='index')
        def publikasi_index():
            ensure_publikasi_table()
            
            session = model.Session
            try:
                result = session.execute(text("SELECT * FROM publikasi ORDER BY tahun_terbit DESC, created_at DESC"))
                publikasi_list = []
                for row in result:
                    publikasi_list.append({
                        'id': row.id,
                        'judul': row.judul,
                        'tahun_terbit': row.tahun_terbit,
                        'deskripsi': row.deskripsi,
                        'file_pdf': row.file_pdf,
                        'gambar_cover': row.gambar_cover,
                        'ukuran_file': row.ukuran_file,
                        'created_at': row.created_at
                    })
            except Exception as e:
                publikasi_list = []
                print(f"Error fetching publikasi: {e}")
            
            return toolkit.render('publikasi/index.html', extra_vars={
                'publikasi_list': publikasi_list
            })

        @publikasi_bp.route('/api/stats/publikasi-count', strict_slashes=False)
        def api_publikasi_count():
            from flask import jsonify
            ensure_publikasi_table()
            try:
                engine = __import__('ckan.model', fromlist=['meta']).meta.engine
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM publikasi"))
                    count = result.scalar() or 0
            except Exception as e:
                print(f"Error counting publikasi: {e}")
                count = 0
            return jsonify({'count': count})

        # ===== 5. BLUEPRINT ADMIN PUBLIKASI =====
        publikasi_admin_bp = Blueprint('publikasi_admin_bp', __name__)


        @publikasi_admin_bp.route('/admin/publikasi/tambah', methods=['GET', 'POST'], strict_slashes=False)
        def tambah_publikasi():
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')

            ensure_publikasi_table()
            upload_dir = get_upload_dir()
            os.makedirs(upload_dir, exist_ok=True)

            if request.method == 'POST':
                try:
                    judul = request.form.get('judul')
                    tahun_terbit = request.form.get('tahun_terbit')
                    deskripsi = request.form.get('deskripsi')
                    
                    if not all([judul, tahun_terbit, deskripsi]):
                        toolkit.h.flash_error('Semua field wajib harus diisi!')
                        return toolkit.render('publikasi/admin_tambah.html')
                    
                    pdf_file = request.files.get('file_pdf')
                    pdf_filename = None
                    ukuran_file = None
                    
                    if pdf_file and pdf_file.filename != '':
                        if not allowed_file(pdf_file.filename, ALLOWED_EXTENSIONS):
                            toolkit.h.flash_error('File harus berformat PDF!')
                            return toolkit.render('publikasi/admin_tambah.html')
                        
                        pdf_filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pdf_file.filename}")
                        pdf_path = os.path.join(upload_dir, pdf_filename)
                        pdf_file.save(pdf_path)
                        ukuran_file = get_file_size(pdf_path)
                    else:
                        toolkit.h.flash_error('File PDF wajib diunggah!')
                        return toolkit.render('publikasi/admin_tambah.html')
                    
                    gambar_file = request.files.get('gambar_cover')
                    gambar_filename = None
                    
                    if gambar_file and gambar_file.filename != '':
                        if allowed_file(gambar_file.filename, ALLOWED_IMAGE_EXTENSIONS):
                            gambar_filename = secure_filename(f"cover_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{gambar_file.filename}")
                            gambar_path = os.path.join(upload_dir, gambar_filename)
                            gambar_file.save(gambar_path)
                    
                    with model.meta.engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO publikasi (judul, tahun_terbit, deskripsi, file_pdf, gambar_cover, ukuran_file)
                            VALUES (:judul, :tahun_terbit, :deskripsi, :file_pdf, :gambar_cover, :ukuran_file)
                        """), {
                            'judul': judul,
                            'tahun_terbit': int(tahun_terbit),
                            'deskripsi': deskripsi,
                            'file_pdf': pdf_filename,
                            'gambar_cover': gambar_filename,
                            'ukuran_file': ukuran_file
                        })
                    
                    toolkit.h.flash_success(f'Berhasil! Publikasi "{judul}" telah ditambahkan.')
                    return toolkit.redirect_to('/publikasi')
                    
                except Exception as e:
                    toolkit.h.flash_error(f'Terjadi kesalahan: {str(e)}')
                    return toolkit.render('publikasi/admin_tambah.html')

            return toolkit.render('publikasi/admin_tambah.html')

        # 5.2 Admin Edit Publikasi
        @publikasi_admin_bp.route('/admin/publikasi/edit/<int:id>', methods=['GET', 'POST'], strict_slashes=False)
        def edit_publikasi(id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')

            ensure_publikasi_table()
            upload_dir = get_upload_dir()
            os.makedirs(upload_dir, exist_ok=True)

            if request.method == 'GET':
                session = model.Session
                try:
                    result = session.execute(text("SELECT * FROM publikasi WHERE id = :id"), {'id': id})
                    publikasi = result.fetchone()
                    
                    if not publikasi:
                        toolkit.h.flash_error('Publikasi tidak ditemukan!')
                        return toolkit.redirect_to('/publikasi')
                    
                    return toolkit.render('publikasi/admin_edit.html', extra_vars={
                        'publikasi': {
                            'id': publikasi.id,
                            'judul': publikasi.judul,
                            'tahun_terbit': publikasi.tahun_terbit,
                            'deskripsi': publikasi.deskripsi,
                            'file_pdf': publikasi.file_pdf,
                            'gambar_cover': publikasi.gambar_cover,
                            'ukuran_file': publikasi.ukuran_file
                        }
                    })
                except Exception as e:
                    toolkit.h.flash_error(f'Error: {str(e)}')
                    return toolkit.redirect_to('/publikasi')

            if request.method == 'POST':
                try:
                    judul = request.form.get('judul')
                    tahun_terbit = request.form.get('tahun_terbit')
                    deskripsi = request.form.get('deskripsi')
                    
                    if not all([judul, tahun_terbit, deskripsi]):
                        toolkit.h.flash_error('Semua field wajib harus diisi!')
                        return toolkit.render('publikasi/admin_edit.html', extra_vars={'publikasi': {'id': id}})
                    
                    session = model.Session
                    result = session.execute(text("SELECT * FROM publikasi WHERE id = :id"), {'id': id})
                    publikasi_lama = result.fetchone()
                    
                    if not publikasi_lama:
                        toolkit.h.flash_error('Publikasi tidak ditemukan!')
                        return toolkit.redirect_to('/publikasi')
                    
                    pdf_filename = publikasi_lama.file_pdf
                    ukuran_file = publikasi_lama.ukuran_file
                    
                    pdf_file = request.files.get('file_pdf')
                    if pdf_file and pdf_file.filename != '':
                        if not allowed_file(pdf_file.filename, ALLOWED_EXTENSIONS):
                            toolkit.h.flash_error('File harus berformat PDF!')
                            return toolkit.render('publikasi/admin_edit.html', extra_vars={'publikasi': {'id': id}})
                        
                        old_pdf_path = os.path.join(upload_dir, publikasi_lama.file_pdf)
                        if os.path.exists(old_pdf_path):
                            os.remove(old_pdf_path)
                        
                        pdf_filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pdf_file.filename}")
                        pdf_path = os.path.join(upload_dir, pdf_filename)
                        pdf_file.save(pdf_path)
                        ukuran_file = get_file_size(pdf_path)
                    
                    gambar_filename = publikasi_lama.gambar_cover
                    gambar_file = request.files.get('gambar_cover')
                    
                    if gambar_file and gambar_file.filename != '':
                        if allowed_file(gambar_file.filename, ALLOWED_IMAGE_EXTENSIONS):
                            if gambar_filename:
                                old_gambar_path = os.path.join(upload_dir, gambar_filename)
                                if os.path.exists(old_gambar_path):
                                    os.remove(old_gambar_path)
                            
                            gambar_filename = secure_filename(f"cover_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{gambar_file.filename}")
                            gambar_path = os.path.join(upload_dir, gambar_filename)
                            gambar_file.save(gambar_path)
                    
                    with model.meta.engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE publikasi 
                            SET judul = :judul, 
                                tahun_terbit = :tahun_terbit, 
                                deskripsi = :deskripsi,
                                file_pdf = :file_pdf,
                                gambar_cover = :gambar_cover,
                                ukuran_file = :ukuran_file,
                                updated_at = NOW()
                            WHERE id = :id
                        """), {
                            'judul': judul,
                            'tahun_terbit': int(tahun_terbit),
                            'deskripsi': deskripsi,
                            'file_pdf': pdf_filename,
                            'gambar_cover': gambar_filename,
                            'ukuran_file': ukuran_file,
                            'id': id
                        })
                    
                    toolkit.h.flash_success(f'Berhasil! Publikasi "{judul}" telah diupdate.')
                    return toolkit.redirect_to('/publikasi')
                    
                except Exception as e:
                    toolkit.h.flash_error(f'Terjadi kesalahan: {str(e)}')
                    import traceback
                    traceback.print_exc()
                    return toolkit.render('publikasi/admin_edit.html', extra_vars={'publikasi': {'id': id}})

        # 5.3 Admin Hapus Publikasi
        @publikasi_admin_bp.route('/admin/publikasi/hapus/<int:id>', methods=['POST'], strict_slashes=False)
        def hapus_publikasi(id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')

            try:
                session = model.Session
                result = session.execute(text("SELECT * FROM publikasi WHERE id = :id"), {'id': id})
                publikasi = result.fetchone()
                
                if not publikasi:
                    toolkit.h.flash_error('Publikasi tidak ditemukan!')
                    return toolkit.redirect_to('/publikasi')
                
                if publikasi.file_pdf:
                    pdf_path = os.path.join(get_upload_dir(), publikasi.file_pdf)
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                
                if publikasi.gambar_cover:
                    gambar_path = os.path.join(get_upload_dir(), publikasi.gambar_cover)
                    if os.path.exists(gambar_path):
                        os.remove(gambar_path)
                
                with model.meta.engine.begin() as conn:
                    conn.execute(text("DELETE FROM publikasi WHERE id = :id"), {'id': id})
                
                toolkit.h.flash_success(f'Publikasi "{publikasi.judul}" berhasil dihapus.')
                
            except Exception as e:
                toolkit.h.flash_error(f'Error menghapus: {str(e)}')
            
            return toolkit.redirect_to('/publikasi')

        # 5.4 Serve uploaded files untuk Publikasi
        @publikasi_bp.route('/uploads/publikasi/<filename>', strict_slashes=False)
        def serve_upload(filename):
            upload_dir = get_upload_dir()
            return send_from_directory(upload_dir, filename)

        # ===== 6. BLUEPRINT WALIDATA =====
        walidata_bp = Blueprint('walidata_bp', __name__)

        # Redirect otomatis sebelum render portal utama
        @walidata_bp.before_app_request
        def seamless_walidata_redirect():
            if request.endpoint in ['user.dashboard', 'dashboard.datasets', 'dashboard.groups', 'dashboard.organizations', 'user.me', 'home.index']:
                user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
                if user and not user.sysadmin and is_walidata(user):
                    return toolkit.redirect_to('/walidata')

        @walidata_bp.route('/walidata', strict_slashes=False, endpoint='dashboard')
        def walidata_dashboard():
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user:
                return toolkit.redirect_to(toolkit.h.url_for('user.login'))
            ensure_walidata_tables()
            if not is_walidata(user):
                return toolkit.abort(403, 'Akses Ditolak: Anda bukan Walidata yang terdaftar.')

            selected_org = request.args.get('org', '')
            search_query = request.args.get('q', '')

            status_map = {}

            # Ambil semua dataset Private (ignore_auth agar bisa lihat semua OPD)
            try:
                context = {'ignore_auth': True, 'user': user.name}
                fq = 'capacity:private'
                if selected_org:
                    fq += f' +organization:"{selected_org}"'
                search_params = {
                    'fq': fq,
                    'rows': 200,
                    'start': 0,
                    'include_private': True,
                    'sort': 'metadata_created desc'
                }
                if search_query:
                    search_params['q'] = search_query
                result = toolkit.get_action('package_search')(context, search_params)
                raw_datasets = result.get('results', [])
                
                # Filter dataset yang ditolak (tidak muncul di antrian sampai direvisi produsen)
                with model.meta.engine.begin() as conn:
                    # Gunakan DISTINCT ON PostgreSQL untuk ambil status log terakhir per dataset
                    from sqlalchemy import text
                    rows = conn.execute(text("SELECT DISTINCT ON (dataset_id) dataset_id, aksi FROM walidata_catatan ORDER BY dataset_id, created_at DESC"))
                    status_map = {row.dataset_id: row.aksi for row in rows}
                
                datasets = []
                for ds in raw_datasets:
                    if status_map.get(ds['id']) == 'tolak':
                        continue # Sembunyikan yang masih ditolak
                    datasets.append(ds)
                
            except Exception as e:
                print(f"Walidata - Error fetching datasets: {e}")
                datasets = []

            # Daftar organisasi untuk filter
            try:
                ctx2 = {'ignore_auth': True}
                org_result = toolkit.get_action('organization_list')(ctx2, {
                    'all_fields': True, 'include_dataset_count': False
                })
                organisations = org_result
            except:
                organisations = []

            # Statistik
            try:
                ctx_stat = {'ignore_auth': True}
                total_all = toolkit.get_action('package_search')(
                    ctx_stat, {'rows': 0, 'include_private': True}
                ).get('count', 0)
                
                # Fetch all private to calculate true pending (excluding tolaks)
                global_private_res = toolkit.get_action('package_search')(
                    ctx_stat, {'fq': 'capacity:private', 'rows': 1000, 'include_private': True}
                ).get('results', [])
                total_pending = len([d for d in global_private_res if status_map.get(d['id']) != 'tolak'])

                sess = model.Session
                approved_count = sess.execute(
                    text("SELECT COUNT(*) FROM walidata_catatan WHERE aksi='approve'")
                ).scalar() or 0
                rejected_count = sess.execute(
                    text("SELECT COUNT(*) FROM walidata_catatan WHERE aksi='tolak'")
                ).scalar() or 0
                stats = {
                    'pending': total_pending,
                    'approved': approved_count,
                    'rejected': rejected_count,
                    'total': total_all
                }
            except Exception as e:
                print(f"Walidata - Error stats: {e}")
                stats = {'pending': 0, 'approved': 0, 'rejected': 0, 'total': 0}

            # Ambil Jadwal Rilis Pending
            try:
                ensure_jadwal_rilis_table()
                sess = model.Session
                jr_pending_rows = sess.execute(text("""
                    SELECT jr.*, oo.nama as organisasi_nama 
                    FROM jadwal_rilis jr
                    LEFT JOIN organisasi_opd oo ON jr.organisasi_id = oo.id
                    WHERE jr.status = 'pending'
                    ORDER BY jr.created_at ASC
                """))
                jadwal_rilis_pending = [dict(r._mapping) for r in jr_pending_rows]
            except Exception as e:
                print(f"Walidata - Error jr pending: {e}")
                jadwal_rilis_pending = []

            # Log verifikasi terbaru (20 entri)
            try:
                sess = model.Session
                log_rows = sess.execute(text(
                    "SELECT * FROM walidata_catatan ORDER BY created_at DESC LIMIT 20"
                ))
                log_list = [dict(r._mapping) for r in log_rows]
            except:
                log_list = []

            return toolkit.render('walidata/dashboard.html', extra_vars={
                'datasets': datasets,
                'organisations': organisations,
                'selected_org': selected_org,
                'search_query': search_query,
                'stats': stats,
                'log_list': log_list,
                'jadwal_rilis_pending': jadwal_rilis_pending
            })

        @walidata_bp.route('/walidata/approve/<dataset_id>', methods=['POST'], strict_slashes=False)
        def walidata_approve(dataset_id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user:
                return toolkit.abort(401, 'Login required')
            ensure_walidata_tables()
            if not is_walidata(user):
                return toolkit.abort(403, 'Akses Ditolak')

            pesan = request.form.get('pesan', '').strip()
            try:
                context = {'ignore_auth': True, 'user': user.name}
                pkg = toolkit.get_action('package_show')(context, {'id': dataset_id})
                dataset_name = pkg.get('title') or pkg.get('name', dataset_id)

                # Ubah private → public
                pkg['private'] = False
                toolkit.get_action('package_update')(context, pkg)

                # Log
                with model.meta.engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO walidata_catatan
                            (dataset_id, dataset_name, walidata_user, aksi, pesan)
                        VALUES (:did, :dname, :wuser, 'approve', :pesan)
                    """), {
                        'did': dataset_id,
                        'dname': dataset_name,
                        'wuser': user.name,
                        'pesan': pesan or None
                    })

                toolkit.h.flash_success(
                    f'Dataset "{dataset_name}" berhasil disetujui dan sekarang berstatus Publik!'
                )
            except Exception as e:
                toolkit.h.flash_error(f'Gagal approve dataset: {str(e)}')
                print(f"Walidata approve error: {e}")

            return toolkit.redirect_to('/walidata')

        @walidata_bp.route('/walidata/tolak/<dataset_id>', methods=['POST'], strict_slashes=False)
        def walidata_tolak(dataset_id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user:
                return toolkit.abort(401, 'Login required')
            ensure_walidata_tables()
            if not is_walidata(user):
                return toolkit.abort(403, 'Akses Ditolak')

            pesan = request.form.get('pesan', '').strip()
            if not pesan:
                toolkit.h.flash_error('Alasan penolakan wajib diisi!')
                return toolkit.redirect_to('/walidata')

            try:
                context = {'ignore_auth': True, 'user': user.name}
                pkg = toolkit.get_action('package_show')(context, {'id': dataset_id})
                dataset_name = pkg.get('title') or pkg.get('name', dataset_id)

                # Dataset tetap private, hanya simpan catatan
                with model.meta.engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO walidata_catatan
                            (dataset_id, dataset_name, walidata_user, aksi, pesan)
                        VALUES (:did, :dname, :wuser, 'tolak', :pesan)
                    """), {
                        'did': dataset_id,
                        'dname': dataset_name,
                        'wuser': user.name,
                        'pesan': pesan
                    })

                toolkit.h.flash_success(
                    f'Dataset "{dataset_name}" ditolak. Catatan revisi telah disimpan.'
                )
            except Exception as e:
                toolkit.h.flash_error(f'Gagal menyimpan penolakan: {str(e)}')
                print(f"Walidata tolak error: {e}")

            return toolkit.redirect_to('/walidata')

        @walidata_bp.route('/walidata/catatan/<dataset_id>', methods=['POST'], strict_slashes=False)
        def walidata_catatan(dataset_id):
            """Kirim notes/catatan ke produsen data tanpa mengubah status dataset."""
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user:
                return toolkit.abort(401, 'Login required')
            ensure_walidata_tables()
            if not is_walidata(user):
                return toolkit.abort(403, 'Akses Ditolak')

            pesan = request.form.get('pesan', '').strip()
            if not pesan:
                toolkit.h.flash_error('Isi notes tidak boleh kosong!')
                return toolkit.redirect_to('/walidata')

            try:
                context = {'ignore_auth': True}
                pkg = toolkit.get_action('package_show')(context, {'id': dataset_id})
                dataset_name = pkg.get('title') or pkg.get('name', dataset_id)

                with model.meta.engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO walidata_catatan
                            (dataset_id, dataset_name, walidata_user, aksi, pesan)
                        VALUES (:did, :dname, :wuser, 'catatan', :pesan)
                    """), {
                        'did': dataset_id,
                        'dname': dataset_name,
                        'wuser': user.name,
                        'pesan': pesan
                    })

                toolkit.h.flash_success(
                    f'Notes untuk dataset "{dataset_name}" berhasil disimpan.'
                )
            except Exception as e:
                toolkit.h.flash_error(f'Gagal menyimpan notes: {str(e)}')
                print(f"Walidata catatan error: {e}")

            return toolkit.redirect_to('/walidata')

        # ===== API: cek apakah user adalah Walidata terdaftar (bukan sysadmin) =====
        @walidata_bp.route('/api/walidata/check', strict_slashes=False)
        def api_walidata_check():
            from flask import jsonify
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            # Sysadmin TIDAK dianggap Walidata untuk keperluan redirect otomatis
            # Mereka tetap bisa akses /walidata via URL manual
            if not user or user.sysadmin:
                return jsonify({'is_walidata': False})
            return jsonify({'is_walidata': is_walidata(user)})

        # ===== CATATAN PRODUSEN: Produsen data lihat review Walidata =====
        @walidata_bp.route('/dataset/<dataset_name>/catatan-walidata', strict_slashes=False)
        def catatan_produsen(dataset_name):
            """Halaman bagi Produsen Data melihat catatan verifikasi dari Walidata."""
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user:
                return toolkit.redirect_to(toolkit.h.url_for('user.login'))
            try:
                ctx = {'user': user.name}
                pkg = toolkit.get_action('package_show')(ctx, {'id': dataset_name})
            except toolkit.NotAuthorized:
                return toolkit.abort(403, 'Anda tidak punya akses ke dataset ini')
            except Exception:
                return toolkit.abort(404, 'Dataset tidak ditemukan')

            ensure_walidata_tables()
            try:
                sess = model.Session
                rows = sess.execute(text(
                    "SELECT * FROM walidata_catatan WHERE dataset_id = :did ORDER BY created_at DESC"
                ), {'did': pkg['id']})
                catatan_list = [dict(r._mapping) for r in rows]
            except Exception as e:
                print(f"Catatan produsen error: {e}")
                catatan_list = []

            return toolkit.render('walidata/catatan_produsen.html', extra_vars={
                'pkg': pkg,
                'catatan_list': catatan_list,
                'is_walidata_user': is_walidata(user)
            })

        # ===== 7. BLUEPRINT ADMIN WALIDATA =====
        walidata_admin_bp = Blueprint('walidata_admin_bp', __name__)


        @walidata_admin_bp.route('/admin/walidata', strict_slashes=False)
        def admin_walidata():
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Hanya Sysadmin yang dapat mengelola Walidata.')

            ensure_walidata_tables()
            try:
                sess = model.Session
                rows = sess.execute(
                    text("SELECT * FROM walidata_users ORDER BY created_at DESC")
                )
                walidata_list = [dict(r._mapping) for r in rows]
            except:
                walidata_list = []

            return toolkit.render('walidata/admin_users.html', extra_vars={
                'walidata_list': walidata_list
            })

        @walidata_admin_bp.route('/admin/walidata/tambah', methods=['POST'], strict_slashes=False)
        def admin_tambah_walidata():
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')

            ensure_walidata_tables()
            user_name = request.form.get('user_name', '').strip()
            catatan   = request.form.get('catatan', '').strip()

            if not user_name:
                toolkit.h.flash_error('Username wajib diisi!')
                return toolkit.redirect_to('/admin/walidata')

            try:
                ctx = {'ignore_auth': True}
                ckan_user = toolkit.get_action('user_show')(ctx, {'id': user_name})
                uid = ckan_user['id']

                with model.meta.engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO walidata_users
                            (user_id, user_name, ditunjuk_oleh, catatan)
                        VALUES (:uid, :uname, :ditunjuk, :catatan)
                        ON CONFLICT (user_id) DO UPDATE SET
                            user_name    = EXCLUDED.user_name,
                            ditunjuk_oleh = EXCLUDED.ditunjuk_oleh,
                            catatan      = EXCLUDED.catatan
                    """), {
                        'uid': uid,
                        'uname': user_name,
                        'ditunjuk': user.name,
                        'catatan': catatan or None
                    })

                toolkit.h.flash_success(
                    f'User "{user_name}" berhasil ditunjuk sebagai Walidata!'
                )
            except toolkit.ObjectNotFound:
                toolkit.h.flash_error(
                    f'User "{user_name}" tidak ditemukan. Pastikan username sudah benar.'
                )
            except Exception as e:
                toolkit.h.flash_error(f'Gagal menambahkan Walidata: {str(e)}')
                print(f"admin tambah walidata error: {e}")

            return toolkit.redirect_to('/admin/walidata')

        @walidata_admin_bp.route('/admin/walidata/hapus/<user_id>', methods=['POST'], strict_slashes=False)
        def admin_hapus_walidata(user_id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not user.sysadmin:
                return toolkit.abort(403, 'Akses Ditolak')

            try:
                sess = model.Session
                target = sess.execute(
                    text("SELECT user_name FROM walidata_users WHERE user_id = :uid"),
                    {'uid': user_id}
                ).fetchone()

                with model.meta.engine.begin() as conn:
                    conn.execute(
                        text("DELETE FROM walidata_users WHERE user_id = :uid"),
                        {'uid': user_id}
                    )

                name = target.user_name if target else user_id
                toolkit.h.flash_success(f'Role Walidata dari user "{name}" berhasil dicabut.')
            except Exception as e:
                toolkit.h.flash_error(f'Gagal mencabut role: {str(e)}')

            return toolkit.redirect_to('/admin/walidata')

        # ===== 8. BLUEPRINT LAINNYA =====
        lainnya_bp = Blueprint('lainnya_bp', __name__)

        @lainnya_bp.route('/lainnya/sop', strict_slashes=False, endpoint='sop')
        def sop():
            return toolkit.render('lainnya/sop.html')

        @lainnya_bp.route('/lainnya/regulasi', strict_slashes=False, endpoint='regulasi')
        def regulasi():
            return toolkit.render('lainnya/regulasi.html')

        @lainnya_bp.route('/lainnya/survey-kepuasan', strict_slashes=False, endpoint='survey')
        def survey():
            return toolkit.render('lainnya/survey.html')

        # ===== 9. BLUEPRINT JADWAL RILIS =====
        jadwal_rilis_bp = Blueprint('jadwal_rilis_bp', __name__)

        @jadwal_rilis_bp.route('/jadwal-rilis', strict_slashes=False, endpoint='index')
        def jadwal_rilis_index():
            ensure_jadwal_rilis_table()
            search = request.args.get('q', '')
            org_filter = request.args.get('organisasi', '')
            
            user_name = getattr(toolkit.g, 'user', '') or getattr(toolkit.c, 'user', '')
            is_logged_in = bool(user_name)
            
            # Logged-in users melihat semua status (aktif + pending + ditolak)
            # agar produsen bisa melihat catatan penolakan dari Walidata
            if is_logged_in:
                query = """
                    SELECT jr.*, oo.nama as organisasi_nama 
                    FROM jadwal_rilis jr
                    LEFT JOIN organisasi_opd oo ON jr.organisasi_id = oo.id
                    WHERE 1=1
                """
            else:
                # Publik hanya melihat data yang sudah disetujui
                query = """
                    SELECT jr.*, oo.nama as organisasi_nama 
                    FROM jadwal_rilis jr
                    LEFT JOIN organisasi_opd oo ON jr.organisasi_id = oo.id
                    WHERE jr.status = 'aktif'
                """
            
            params = {}
            if search:
                query += " AND (jr.indikator ILIKE :s OR jr.nama_data ILIKE :s)"
                params['s'] = f"%{search}%"
            if org_filter:
                query += " AND jr.organisasi_id = :org_id"
                params['org_id'] = int(org_filter)
            
            query += " ORDER BY jr.created_at DESC"
            
            session = model.Session
            try:
                result = session.execute(text(query), params)
                items = [dict(r._mapping) for r in result]
            except Exception as e:
                print(f"Jadwal Rilis Index Error: {e}")
                items = []
            
            return toolkit.render('jadwal-rilis/index.html', extra_vars={
                'jadwal_list': items,
                'organisasi_list': get_organisasi_list(),
                'search_query': search,
                'selected_organisasi': org_filter,
                'is_logged_in': is_logged_in
            })

        @jadwal_rilis_bp.route('/admin/jadwal-rilis/tambah', methods=['GET', 'POST'], strict_slashes=False)
        def tambah_jadwal_rilis():
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user:
                return toolkit.redirect_to(toolkit.h.url_for('user.login'))
            
            ensure_jadwal_rilis_table()
            
            if request.method == 'POST':
                try:
                    indikator = request.form.get('indikator')
                    nama_data = request.form.get('nama_data')
                    jenis_data = request.form.get('jenis_data')
                    organisasi_id = request.form.get('organisasi_id')
                    klasifikasi = request.form.get('klasifikasi')
                    jadwal_bulan = request.form.get('jadwal_bulan')
                    
                    if not jadwal_bulan:
                        jadwal_bulan = get_month_name(datetime.now().month)
                    
                    with model.meta.engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO jadwal_rilis (indikator, nama_data, jenis_data, organisasi_id, klasifikasi, jadwal_bulan, status)
                            VALUES (:ind, :name, :type, :oid, :klas, :month, 'pending')
                        """), {
                            'ind': indikator, 'name': nama_data, 'type': jenis_data, 
                            'oid': organisasi_id, 'klas': klasifikasi, 'month': jadwal_bulan
                        })
                    
                    toolkit.h.flash_success('Berhasil! Jadwal rilis telah diajukan dan menunggu verifikasi Walidata.')
                    return toolkit.redirect_to('/jadwal-rilis')
                except Exception as e:
                    toolkit.h.flash_error(f'Error: {str(e)}')
            
            current_month = get_month_name(datetime.now().month)
            return toolkit.render('jadwal-rilis/admin_form.html', extra_vars={
                'mode': 'tambah', 
                'organisasi_list': get_organisasi_list(),
                'current_month': current_month
            })

        @jadwal_rilis_bp.route('/admin/jadwal-rilis/edit/<int:id>', methods=['GET', 'POST'], strict_slashes=False)
        def edit_jadwal_rilis(id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user:
                return toolkit.redirect_to(toolkit.h.url_for('user.login'))
            
            ensure_jadwal_rilis_table()
            session = model.Session
            data = session.execute(text("SELECT * FROM jadwal_rilis WHERE id = :id"), {'id': id}).fetchone()
            if not data:
                return toolkit.redirect_to('/jadwal-rilis')
            
            if request.method == 'POST':
                try:
                    indikator = request.form.get('indikator')
                    nama_data = request.form.get('nama_data')
                    jenis_data = request.form.get('jenis_data')
                    organisasi_id = request.form.get('organisasi_id')
                    klasifikasi = request.form.get('klasifikasi')
                    jadwal_bulan = request.form.get('jadwal_bulan')
                    
                    with model.meta.engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE jadwal_rilis SET 
                                indikator=:ind, nama_data=:name, jenis_data=:type, 
                                organisasi_id=:oid, klasifikasi=:klas, jadwal_bulan=:month,
                                status='pending', updated_at=NOW()
                            WHERE id=:id
                        """), {
                            'ind': indikator, 'name': nama_data, 'type': jenis_data, 
                            'oid': organisasi_id, 'klas': klasifikasi, 'month': jadwal_bulan, 'id': id
                        })
                    
                    toolkit.h.flash_success('Berhasil diupdate! Menunggu verifikasi ulang oleh Walidata.')
                    return toolkit.redirect_to('/jadwal-rilis')
                except Exception as e:
                    toolkit.h.flash_error(f'Error: {str(e)}')
            
            return toolkit.render('jadwal-rilis/admin_form.html', extra_vars={
                'data': dict(data._mapping), 'mode': 'edit', 'organisasi_list': get_organisasi_list()
            })

        @jadwal_rilis_bp.route('/admin/jadwal-rilis/hapus/<int:id>', methods=['POST'], strict_slashes=False)
        def hapus_jadwal_rilis(id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user: return toolkit.abort(403)
            
            try:
                with model.meta.engine.begin() as conn:
                    conn.execute(text("DELETE FROM jadwal_rilis WHERE id = :id"), {'id': id})
                toolkit.h.flash_success('Jadwal rilis dihapus.')
            except Exception as e:
                toolkit.h.flash_error(f'Error: {str(e)}')
            return toolkit.redirect_to('/jadwal-rilis')

        @jadwal_rilis_bp.route('/walidata/jadwal-rilis/approve/<int:id>', methods=['POST'], strict_slashes=False)
        def approve_jadwal_rilis(id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not is_walidata(user):
                return toolkit.abort(403)
            
            try:
                with model.meta.engine.begin() as conn:
                    conn.execute(text("UPDATE jadwal_rilis SET status = 'aktif', klasifikasi = 'Terbuka', catatan_walidata = NULL, updated_at = NOW() WHERE id = :id"), {'id': id})
                toolkit.h.flash_success('Jadwal rilis telah disetujui, diklasifikasikan sebagai Terbuka, dan kini publik.')
            except Exception as e:
                toolkit.h.flash_error(f'Gagal: {str(e)}')
            return toolkit.redirect_to('/walidata')

        @jadwal_rilis_bp.route('/walidata/jadwal-rilis/tolak/<int:id>', methods=['POST'], strict_slashes=False)
        def tolak_jadwal_rilis(id):
            user = getattr(toolkit.g, 'userobj', None) or getattr(toolkit.c, 'userobj', None)
            if not user or not is_walidata(user):
                return toolkit.abort(403)
            
            catatan = request.form.get('pesan', '').strip()
            try:
                with model.meta.engine.begin() as conn:
                    conn.execute(text("UPDATE jadwal_rilis SET status = 'ditolak', catatan_walidata = :c, updated_at = NOW() WHERE id = :id"), {'id': id, 'c': catatan})
                toolkit.h.flash_success('Jadwal rilis ditolak dengan catatan.')
            except Exception as e:
                toolkit.h.flash_error(f'Gagal: {str(e)}')
            return toolkit.redirect_to('/walidata')

        return [
            infografis_bp, standar_data_bp, arnold_bp,
            publikasi_bp, publikasi_admin_bp,
            walidata_bp, walidata_admin_bp, lainnya_bp,
            jadwal_rilis_bp
        ]



    def before_show(self, resource_dict):
        if resource_dict.get('format', '').upper() == 'WMS':
            nama_asli = resource_dict.get('name', '')
            if ':' in nama_asli:
                nama_bersih = nama_asli.split(':')[1]
            else:
                nama_bersih = nama_asli
            resource_dict['wms_layer'] = nama_bersih
        return resource_dict