import os
import requests
from google import genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Config ─────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
CKAN_API       = os.environ.get("CKAN_API_URL", "http://ckan:5000/api/3/action")
CKAN_SITE_URL  = os.environ.get("CKAN_SITE_URL", "https://localhost:8443")

# Validate key — jangan pakai placeholder
_key_valid = (
    bool(GEMINI_API_KEY)
    and GEMINI_API_KEY != "ISI_API_KEY_GEMINI_ANDA_DISINI"
    and len(GEMINI_API_KEY) > 20
)

gemini_client = None
if _key_valid:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        print("✅ Gemini AI aktif (gemini-2.5-flash)")
    except Exception as e:
        print(f"❌ Gagal init Gemini: {e}")
else:
    print("⚠️  GEMINI_API_KEY belum diisi — mode fallback aktif")
    print("   → Isi GEMINI_API_KEY di file .env lalu rebuild chatbot")

# ── App ────────────────────────────────────────────────────────
app = FastAPI(title="Arnold AI — Bengkulu Satu Data")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    message: str


# ── CKAN Data Fetchers ─────────────────────────────────────────

def get_dataset_count() -> int:
    try:
        r = requests.get(f"{CKAN_API}/package_search", params={"rows": 0}, timeout=5)
        return r.json()["result"]["count"]
    except Exception:
        return 0

def get_organizations() -> list:
    try:
        r = requests.get(
            f"{CKAN_API}/organization_list",
            params={"all_fields": True, "include_dataset_count": True},
            timeout=5
        )
        return r.json().get("result", [])
    except Exception:
        return []

def search_dataset(keyword: str, rows: int = 5) -> list:
    try:
        r = requests.get(
            f"{CKAN_API}/package_search",
            params={"q": keyword, "rows": rows, "sort": "score desc"},
            timeout=5
        )
        return r.json()["result"]["results"]
    except Exception:
        return []

def get_latest_datasets(rows: int = 5) -> list:
    try:
        r = requests.get(
            f"{CKAN_API}/package_search",
            params={"sort": "metadata_created desc", "rows": rows},
            timeout=5
        )
        return r.json()["result"]["results"]
    except Exception:
        return []


# ── Context Builder (data real-time CKAN) ─────────────────────

def build_context(user_message: str) -> str:
    ctx_parts = []
    msg_lower = user_message.lower()

    if any(k in msg_lower for k in ["dataset", "data", "berapa", "jumlah", "total"]):
        count = get_dataset_count()
        ctx_parts.append(f"Jumlah dataset aktif di portal saat ini: {count} dataset.")

    if any(k in msg_lower for k in ["organisasi", "instansi", "opd", "dinas"]):
        orgs = get_organizations()
        if orgs:
            org_names = [o.get("title") or o.get("name", "") for o in orgs[:15]]
            ctx_parts.append(
                f"Terdapat {len(orgs)} organisasi di portal: "
                + ", ".join(org_names)
                + ("..." if len(orgs) > 15 else ".")
            )

    if any(k in msg_lower for k in ["terbaru", "baru", "latest", "terakhir"]):
        latest = get_latest_datasets(5)
        if latest:
            items = [f"  - {d['title']} → {CKAN_SITE_URL}/dataset/{d['name']}" for d in latest]
            ctx_parts.append("Dataset terbaru yang diunggah:\n" + "\n".join(items))

    # Pencarian dataset relevan
    datasets = search_dataset(user_message, rows=5)
    if datasets:
        items = [f"  - {d['title']} → {CKAN_SITE_URL}/dataset/{d['name']}" for d in datasets]
        ctx_parts.append("Dataset relevan yang ditemukan di portal:\n" + "\n".join(items))

    return "\n\n".join(ctx_parts) if ctx_parts else ""


# ── System Prompt (pengetahuan portal Bengkulu Satu Data) ──────

SYSTEM_PROMPT = f"""Kamu adalah Arnold AI 🤖, asisten cerdas resmi Portal Bengkulu Satu Data.

=== TENTANG PORTAL ===
Portal Bengkulu Satu Data adalah platform open data resmi Pemerintah Provinsi Bengkulu.
URL portal: {CKAN_SITE_URL}

=== FITUR-FITUR PORTAL ===

1. DATASET ({CKAN_SITE_URL}/dataset)
   - Kumpulan data terbuka dari berbagai OPD Pemerintah Provinsi Bengkulu
   - Format: CSV, Excel (XLSX/XLS), PDF, JSON, WMS, SHP, API
   - Bisa dicari, diunduh, dan digunakan publik secara gratis

2. ORGANISASI ({CKAN_SITE_URL}/organization)
   - Daftar OPD (Organisasi Perangkat Daerah) Pemerintah Provinsi Bengkulu
   - Setiap organisasi mempublikasikan dataset sesuai bidangnya
   - Contoh: Dinas Kesehatan, Dinas Pendidikan, Bappeda, dll.

3. INFOGRAFIS ({CKAN_SITE_URL}/infografis)
   - Visualisasi data dalam bentuk gambar/poster infografis
   - Dilengkapi analisis berupa bar chart dan donut chart
   - Pengguna bisa melihat detail gambar + statistik visual setiap infografis
   - Bisa diunduh sebagai PDF

4. STANDAR DATA ({CKAN_SITE_URL}/standar-data)
   - Halaman yang memuat standar, panduan, dan regulasi pengelolaan data
   - Referensi tata kelola data sesuai Satu Data Indonesia (SDI)
   - Berisi dokumen standar format, metadata, dan tatacara publikasi data

5. PUBLIKASI ({CKAN_SITE_URL}/publikasi)
   - Kumpulan dokumen publikasi resmi Pemerintah Provinsi Bengkulu
   - Berisi laporan, buku statistik, jurnal, dan dokumen resmi lainnya
   - Bisa dicari berdasarkan kategori dan tahun

6. GEOPORTAL ({CKAN_SITE_URL}/geoportal — atau menu Geoportal di navbar)
   - Peta interaktif berbasis GIS (Geographic Information System)
   - Menampilkan layer data spasial wilayah Provinsi Bengkulu
   - Mendukung format WMS dan GeoJSON

=== TENTANG SATU DATA INDONESIA ===
Bengkulu Satu Data merupakan implementasi kebijakan Satu Data Indonesia (SDI)
berdasarkan Perpres No. 39 Tahun 2019 tentang Satu Data Indonesia.
SDI bertujuan mengintegrasikan data pemerintah agar akurat, mutakhir, terpadu,
dapat dipertanggungjawabkan, dan mudah diakses.

=== CARA MENGGUNAKAN PORTAL ===
- Cari dataset: klik menu "Dataset" atau gunakan search bar di beranda
- Filter data: gunakan filter organisasi, tag, atau format di sidebar
- Unduh data: buka dataset, pilih resource, klik tombol unduh
- Lihat peta: klik menu "Geoportal" untuk peta interaktif
- Lihat infografis: klik menu "Infografis"
- Baca publikasi: klik menu "Publikasi"
- Standar data: klik menu "Standar Data"

=== ATURAN MENJAWAB ===
- Gunakan bahasa Indonesia yang ramah, profesional, dan informatif
- Tambahkan link yang relevan saat menyebut halaman portal
- Jika ada data real-time dari CKAN (disertakan di bawah), gunakan data tersebut
- Jawab singkat dan padat (3-5 kalimat) kecuali diminta penjelasan panjang
- Jangan mengarang data — gunakan hanya konteks yang diberikan
- Tambahkan emoji yang relevan dan sesuai
- Jika tidak tahu, arahkan pengguna ke halaman yang relevan di portal
"""


# ── AI Answer ─────────────────────────────────────────────────

def jawab_dengan_ai(user_message: str) -> str:
    context = build_context(user_message)

    full_prompt = SYSTEM_PROMPT
    if context:
        full_prompt += f"\n\n=== DATA REAL-TIME PORTAL ===\n{context}\n=== AKHIR DATA ===\n"
    full_prompt += f"\n\nPertanyaan pengguna: {user_message}"

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini error: {e}")
        return jawab_fallback(user_message)


# ── Fallback (tanpa Gemini) ────────────────────────────────────

def jawab_fallback(user_message: str) -> str:
    """
    Fallback berbasis pengetahuan portal — aktif jika Gemini tidak tersedia.
    Mencakup semua fitur portal Bengkulu Satu Data.
    """
    msg = user_message.lower().strip()

    # Greeting
    if any(x in msg for x in ["halo", "hai", "hello", "hi", "selamat", "pagi", "siang", "malam"]):
        return (
            "Halo! Saya Arnold AI 🤖, asisten resmi Portal Bengkulu Satu Data. "
            "Saya bisa membantu Anda menemukan dataset, infografis, publikasi, standar data, "
            "atau menjawab pertanyaan seputar portal. Ada yang bisa saya bantu? 😊"
        )

    # Portal umum
    if any(x in msg for x in ["portal", "bengkulu satu data", "satu data"]):
        return (
            f"Portal Bengkulu Satu Data 🏛️ adalah platform open data resmi Pemerintah Provinsi Bengkulu. "
            f"Portal ini menyediakan dataset, infografis, publikasi, standar data, dan geoportal "
            f"yang bisa diakses secara terbuka di {CKAN_SITE_URL}."
        )

    # Dataset — jumlah
    if ("dataset" in msg or "data" in msg) and any(x in msg for x in ["berapa", "jumlah", "total", "banyak"]):
        count = get_dataset_count()
        return f"Saat ini terdapat **{count} dataset** 📊 yang tersedia di Portal Bengkulu Satu Data."

    # Dataset — definisi/apa itu
    if "dataset" in msg and any(x in msg for x in ["apa", "itu", "pengertian", "adalah", "definisi"]):
        return (
            "Dataset 📂 adalah kumpulan data terstruktur yang dipublikasikan oleh instansi pemerintah "
            "di Portal Bengkulu Satu Data. "
            f"Tersedia dalam berbagai format seperti CSV, Excel, PDF, JSON, dan WMS. "
            f"Anda bisa mengaksesnya di {CKAN_SITE_URL}/dataset"
        )

    # Dataset — terbaru
    if any(x in msg for x in ["terbaru", "baru", "terakhir", "latest"]) and any(x in msg for x in ["dataset", "data"]):
        latest = get_latest_datasets(5)
        if latest:
            lines = "\n".join([f"- [{d['title']}]({CKAN_SITE_URL}/dataset/{d['name']})" for d in latest])
            return f"Dataset terbaru di portal 📋:\n{lines}"
        return f"Silakan cek dataset terbaru langsung di {CKAN_SITE_URL}/dataset"

    # Infografis
    if "infografis" in msg:
        if any(x in msg for x in ["apa", "itu", "pengertian", "adalah", "definisi"]):
            return (
                "Infografis 📊 adalah visualisasi data dalam bentuk gambar/poster informatif "
                "yang disertai analisis berupa bar chart dan donut chart. "
                "Pengguna dapat melihat gambar penuh beserta statistik visual dari setiap infografis. "
                f"Akses halaman Infografis di: {CKAN_SITE_URL}/infografis"
            )
        return (
            f"Halaman Infografis ({CKAN_SITE_URL}/infografis) berisi visualisasi data Pemerintah "
            "Provinsi Bengkulu dalam format poster/gambar yang dilengkapi dengan analisis chart. "
            "Setiap infografis bisa diklik untuk melihat detail lengkap dan grafik analisis 📈."
        )

    # Standar Data
    if "standar" in msg and "data" in msg:
        if any(x in msg for x in ["apa", "itu", "pengertian", "adalah", "definisi"]):
            return (
                "Standar Data 📋 adalah halaman yang memuat panduan, regulasi, dan standar "
                "pengelolaan data Pemerintah Provinsi Bengkulu. "
                "Berisi dokumen standar format, metadata, dan tatacara publikasi data "
                "sesuai kebijakan Satu Data Indonesia (SDI). "
                f"Akses di: {CKAN_SITE_URL}/standar-data"
            )
        return (
            f"Halaman Standar Data ({CKAN_SITE_URL}/standar-data) berisi panduan dan regulasi "
            "tata kelola data pemerintah sesuai Perpres No. 39 Tahun 2019 tentang Satu Data Indonesia 📜."
        )

    # Standar data — hanya kata "standar"
    if msg.strip() in ["standar data", "standar-data", "standar"]:
        return (
            f"Standar Data 📋 adalah halaman panduan dan regulasi pengelolaan data pemerintah "
            f"di Portal Bengkulu Satu Data. Akses di: {CKAN_SITE_URL}/standar-data"
        )

    # Publikasi
    if "publikasi" in msg:
        if any(x in msg for x in ["apa", "itu", "pengertian", "adalah", "definisi"]):
            return (
                "Publikasi 📚 adalah kumpulan dokumen resmi Pemerintah Provinsi Bengkulu "
                "seperti laporan tahunan, buku statistik, jurnal, dan dokumen kebijakan. "
                "Tersedia untuk diunduh secara gratis oleh masyarakat. "
                f"Akses di: {CKAN_SITE_URL}/publikasi"
            )
        return (
            f"Halaman Publikasi ({CKAN_SITE_URL}/publikasi) berisi dokumen resmi dan laporan "
            "Pemerintah Provinsi Bengkulu yang bisa dicari berdasarkan kategori dan tahun 📕."
        )

    # Geoportal / peta
    if any(x in msg for x in ["geoportal", "peta", "gis", "spasial", "maps", "wms", "geojson"]):
        return (
            "Geoportal 🗺️ adalah fitur peta interaktif berbasis GIS (Geographic Information System) "
            "di Portal Bengkulu Satu Data. Menampilkan layer data spasial wilayah Provinsi Bengkulu "
            f"dalam format WMS dan GeoJSON. Akses melalui menu Geoportal atau di {CKAN_SITE_URL}/geoportal"
        )

    # Organisasi — daftar
    if any(x in msg for x in ["organisasi", "instansi", "opd", "dinas"]):
        if any(x in msg for x in ["berapa", "jumlah", "total"]):
            orgs = get_organizations()
            return f"Terdapat **{len(orgs)} organisasi** 🏛️ yang terdaftar di Portal Bengkulu Satu Data."
        orgs = get_organizations()
        if orgs:
            names = [o.get("title") or o.get("name", "") for o in orgs[:10]]
            extra = f" (dan {len(orgs)-10} lainnya)" if len(orgs) > 10 else ""
            return (
                f"Organisasi yang mempublikasikan data di portal ({len(orgs)} total{extra}) 🏛️:\n"
                + "\n".join([f"- {n}" for n in names])
            )

    # Satu Data Indonesia
    if any(x in msg for x in ["sdi", "perpres", "kebijakan", "regulasi"]):
        return (
            "Bengkulu Satu Data merupakan implementasi Kebijakan Satu Data Indonesia (SDI) 📜 "
            "berdasarkan Perpres No. 39 Tahun 2019. "
            "SDI bertujuan mengintegrasikan data pemerintah agar akurat, terpadu, "
            "dan mudah diakses oleh masyarakat luas."
        )

    # Cara menggunakan
    if any(x in msg for x in ["cara", "bagaimana", "gimana", "tutorial", "panduan", "petunjuk"]):
        return (
            "Berikut cara menggunakan Portal Bengkulu Satu Data 📖:\n"
            "1. **Cari Dataset** → klik menu 'Dataset' atau gunakan search bar di beranda\n"
            "2. **Filter Data** → gunakan filter organisasi/tag/format di sidebar\n"
            "3. **Unduh Data** → buka dataset, pilih resource, klik tombol unduh\n"
            "4. **Infografis** → klik menu 'Infografis' untuk visualisasi data\n"
            "5. **Publikasi** → klik menu 'Publikasi' untuk dokumen resmi\n"
            "6. **Peta** → klik menu 'Geoportal' untuk melihat data spasial"
        )

    # Fallback: cari dataset
    datasets = search_dataset(user_message, rows=5)
    if datasets:
        lines = "\n".join([f"- [{d['title']}]({CKAN_SITE_URL}/dataset/{d['name']})" for d in datasets])
        return f"Saya menemukan dataset yang mungkin relevan 🔍:\n{lines}"

    # Ultimate fallback
    return (
        "Maaf, saya belum bisa menjawab pertanyaan tersebut dengan tepat 🙏. "
        f"Silakan eksplorasi portal langsung di **{CKAN_SITE_URL}** atau tanyakan tentang:\n"
        "- 📊 Dataset\n- 🏛️ Organisasi\n- 📈 Infografis\n- 📚 Publikasi\n- 📋 Standar Data\n- 🗺️ Geoportal"
    )


# ── API Endpoints ──────────────────────────────────────────────

@app.get("/")
def home():
    return {
        "status": "Arnold AI berjalan",
        "ai_mode": "gemini-2.5-flash" if gemini_client else "fallback (isi GEMINI_API_KEY di .env)",
        "portal": CKAN_SITE_URL
    }

@app.post("/chat")
def chat(msg: Message):
    if not msg.message.strip():
        return {"reply": "Silakan ketik pertanyaan Anda 😊"}

    if gemini_client:
        reply = jawab_dengan_ai(msg.message)
    else:
        reply = jawab_fallback(msg.message)

    return {"reply": reply}

@app.get("/status")
def status():
    count = get_dataset_count()
    return {
        "ai_engine": "gemini-2.5-flash" if gemini_client else "fallback (no valid API key)",
        "api_key_configured": _key_valid,
        "ckan_connected": count > 0,
        "dataset_count": count,
    }