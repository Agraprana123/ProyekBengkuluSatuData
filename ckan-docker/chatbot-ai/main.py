from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Arnold AI Bengkulu Satu Data berjalan"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    message: str


CKAN_API = "http://ckan:5000/api/3/action"


# ===============================
# GET DATA REALTIME
# ===============================

def get_dataset_count():

    r = requests.get(f"{CKAN_API}/package_search", params={"rows":0})
    data = r.json()

    return data["result"]["count"]


def get_organizations():

    r = requests.get(f"{CKAN_API}/organization_list")

    data = r.json()

    return data["result"]


def search_dataset(keyword):

    r = requests.get(
        f"{CKAN_API}/package_search",
        params={
            "q": keyword,
            "rows": 5
        }
    )

    data = r.json()

    return data["result"]["results"]


def get_latest_datasets():

    r = requests.get(
        f"{CKAN_API}/package_search",
        params={
            "sort":"metadata_created desc",
            "rows":5
        }
    )

    data = r.json()

    return data["result"]["results"]


# ===============================
# CHATBOT LOGIC
# ===============================

def jawab(msg):

    msg = msg.lower().strip()


    # ====================
    # GREETING
    # ====================

    if any(x in msg for x in ["hi","halo","hello","hai","hi arnold","halo arnold"]):
        return "Halo! Saya Arnold AI 🤖 asisten Portal Bengkulu Satu Data. Kamu bisa bertanya tentang dataset, organisasi, atau data terbaru."


    # ====================
    # PORTAL
    # ====================

    if "portal bengkulu satu data" in msg or "bengkulu satu data" in msg:
        return "Portal Bengkulu Satu Data adalah portal resmi pemerintah untuk berbagi dataset terbuka kepada masyarakat."


    # ====================
    # DEFINISI DATASET
    # ====================

    if "dataset" in msg and any(x in msg for x in ["apa","itu","pengertian"]):
        return "Dataset adalah kumpulan data yang dipublikasikan oleh instansi pemerintah melalui portal data."


    # ====================
    # JUMLAH DATASET
    # ====================

    if "dataset" in msg and any(x in msg for x in ["berapa","jumlah","banyak","total"]):

        count = get_dataset_count()

        return f"Saat ini terdapat {count} dataset di portal Bengkulu Satu Data."


    # ====================
    # ORGANISASI LIST
    # ====================

    if "organisasi" in msg and not any(x in msg for x in ["berapa","jumlah","total"]):

        orgs = get_organizations()

        text = "Organisasi yang tersedia di portal:\n"

        for o in orgs:
            text += f"- {o}\n"

        return text


    # ====================
    # JUMLAH ORGANISASI
    # ====================

    if "organisasi" in msg and any(x in msg for x in ["berapa","jumlah","total"]):

        orgs = get_organizations()

        return f"Saat ini terdapat {len(orgs)} organisasi di portal."


    # ====================
    # DATASET TERBARU
    # ====================

    if "dataset terbaru" in msg or "data terbaru" in msg:

        datasets = get_latest_datasets()

        text = "Dataset terbaru di portal:\n"

        for d in datasets:

            link = f"https://localhost:8443/dataset/{d['name']}"

            text += f"- {d['title']}\n  {link}\n"

        return text


    # ====================
    # DATASET ORGANISASI
    # ====================

    if "dataset" in msg and "organisasi" in msg:

        org = msg.split("organisasi")[-1].strip()

        r = requests.get(
            f"{CKAN_API}/package_search",
            params={
                "fq": f"organization:{org}",
                "rows": 100
            }
        )

        data = r.json()

        count = data["result"]["count"]

        return f"Organisasi {org} memiliki {count} dataset."


    # ====================
    # SEARCH DATASET
    # ====================

    if "dataset tentang" in msg or "data tentang" in msg:

        keyword = msg.replace("dataset tentang","").replace("data tentang","").strip()

        datasets = search_dataset(keyword)

        if not datasets:
            return "Maaf saya tidak menemukan dataset tersebut."

        text = f"Dataset tentang {keyword}:\n"

        for d in datasets:

            link = f"https://localhost:8443/dataset/{d['name']}"

            text += f"- {d['title']}\n  {link}\n"

        return text


    # ====================
    # INFOGRAFIS
    # ====================

    if "infografis" in msg:
        return "Infografis adalah visualisasi data dalam bentuk grafik atau gambar agar informasi lebih mudah dipahami."


    # ====================
    # FALLBACK SEARCH
    # ====================

    datasets = search_dataset(msg)

    if datasets:

        text = "Saya menemukan dataset terkait:\n"

        for d in datasets:

            link = f"https://localhost:8443/dataset/{d['name']}"

            text += f"- {d['title']}\n  {link}\n"

        return text


    return "Maaf saya belum memahami pertanyaan itu."


@app.post("/chat")
def chat(msg: Message):

    return {"reply": jawab(msg.message)}