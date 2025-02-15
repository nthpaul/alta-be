import requests
import re
from fastapi import HTTPException
from app.config import SERP_API_KEY

def fetch_products(query: str, max_results: int = 10):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": SERP_API_KEY,
        # `num` has been deprecated for the new google shopping layout, but you could use it for regions still using the old layout
        "num": max_results,
        # active issue with serpAPI where direct_link is not being returned https://github.com/serpapi/public-roadmap/issues/1889
        # one alternative for the actual product would be to directly use google's custom search JSON API https://developers.google.com/custom-search/v1/overview
        "direct_link": "true"
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch products")

    data = response.json()
    products = []

    for item in data.get("shopping_results", [])[:max_results]:
        price = item.get("price", "")

        price_match = re.search(r"[\d,]+\.?\d*", price)
        price_value = float(price_match.group().replace(",", "")) if price_match else None

        products.append({
            "name": item.get("title"),
            "shop": item.get("source"),
            "price": price_value,  # Store as a number
            "source_url": item.get("product_link"),
            "image_url": item.get("thumbnail"),
        })

    return products
