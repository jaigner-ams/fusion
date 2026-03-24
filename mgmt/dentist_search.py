import csv
import os
import re

import requests

ZIPCODES_DB = os.path.join(os.path.dirname(__file__), "zipcodes_db.csv")
_coords_cache = {}

FIELDNAMES = ["name", "phone", "address", "rating", "zip_code", "maps_url"]

SERPAPI_URL = "https://serpapi.com/search"


def load_coords(db_path=ZIPCODES_DB):
    """Load zip→(lat, lon) mapping from CSV into memory. Returns dict.

    Module-level _coords_cache is intentional: loads once per Apache worker
    process. Returns {} silently if the CSV is missing (search falls back
    to query-based mode without coordinates).
    """
    if _coords_cache:
        return _coords_cache
    if not os.path.exists(db_path):
        return {}
    with open(db_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            _coords_cache[row["zip_code"]] = (float(row["latitude"]), float(row["longitude"]))
    return _coords_cache


def search_dentists(api_key, zip_code, num=25):
    """Search SerpApi google_maps for dentists in a zip code.

    Returns list of dicts with keys: name, phone, address, rating, zip_code, maps_url.
    Raises RuntimeError on network or API failure.
    """
    coords = load_coords()
    params = {
        "engine": "google_maps",
        "q": f"dentist {zip_code}",
        "type": "search",
        "num": num,
        "api_key": api_key,
    }
    if zip_code in coords:
        lat, lon = coords[zip_code]
        params["ll"] = f"@{lat},{lon},14z"

    try:
        response = requests.get(SERPAPI_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API error for zip {zip_code}: {e}")

    results = []
    for item in data.get("local_results", []):
        address = item.get("address", "")
        if not re.search(zip_code + r'(?:-\d{4})?\s*$', address):
            continue
        types = item.get("types", [])
        if types and not any("dentist" in t.lower() for t in types):
            continue
        place_id = item.get("place_id", "")
        maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else ""
        results.append({
            "name": item.get("title", ""),
            "phone": item.get("phone", ""),
            "address": address,
            "rating": item.get("rating", ""),
            "zip_code": zip_code,
            "maps_url": maps_url,
        })
    return results


def deduplicate(results):
    """Remove duplicate results by phone number. Rows with no phone are kept as-is."""
    seen_phones = set()
    deduped = []
    for row in results:
        phone = row.get("phone", "")
        if phone and phone in seen_phones:
            continue
        if phone:
            seen_phones.add(phone)
        deduped.append(row)
    return deduped
