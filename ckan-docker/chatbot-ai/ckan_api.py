import requests

CKAN_URL = "http://ckan:5000/api/3/action/package_search"

def search_dataset(query):

    try:

        r = requests.get(
            CKAN_URL,
            params={"q": query}
        )

        data = r.json()

        results = data["result"]["results"]

        datasets = []

        for d in results[:5]:

            datasets.append({
                "title": d["title"],
                "url": "/dataset/" + d["name"]
            })

        return datasets

    except:
        return []