from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os
import requests
import json
import re

app = FastAPI()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"),)
SERP_API_KEY = os.environ.get("SERP_API_KEY")

class SearchRequest(BaseModel):
    query: str

def fetch_products(query: str):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": SERP_API_KEY,
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch products")

    data = response.json()
    products = []

    for item in data.get("shopping_results", []):
        price = item.get("price", "")

        # Extract price as a float (e.g., "$120" → 120.0)
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

def extract_filters(products):
    """Use GPT-4o function calling to extract filters (brand, color, type, material)."""
    product_names = [p["name"] for p in products]

    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You extract structured fashion product attributes from product names."},
            {"role": "user", "content": json.dumps({"product_names": product_names})}
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "extract_filters",
                    "description": "Extracts brand, color, type, and material from product names.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "brands": {"type": "array", "items": {"type": "string"}, "description": "Unique brands in the product list."},
                            "colors": {"type": "array", "items": {"type": "string"}, "description": "Unique colors in the product list."},
                            "types": {"type": "array", "items": {"type": "string"}, "description": "Unique product types (e.g., 'Shoulder Bag', 'Sneakers')."},
                            "materials": {"type": "array", "items": {"type": "string"}, "description": "Unique materials used (e.g., 'Leather', 'Cotton')."}
                        },
                        "required": ["brands", "colors", "types", "materials"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        ],
    )

    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        for call in tool_calls:
            if call.function.name == "extract_filters":
                response = json.loads(call.function.arguments)

                valid_prices = [p["price"] for p in products if isinstance(p["price"], (int, float))]

                return {
                    "brands": response["brands"],
                    "colors": response["colors"],
                    "types": response["types"],
                    "materials": response["materials"],
                    "min_price": min(valid_prices) if valid_prices else 0,
                    "max_price": max(valid_prices) if valid_prices else 0
                }
    return {"brands": [], "colors": [], "types": [], "materials": [], "min_price": 0, "max_price": 0}


@app.post('/search')
async def search(request: SearchRequest):
    response = client.beta.chat.completions.parse(
        messages=[
            {
                "role": "system",
                "content": "You are a shopping assistant and outfit picker extraordinaire. When given a query, return a JSON array of products. Each product should have a name, price, and source (store link)."
            },
            {
                "role": "user",
                "content": request.query
            }
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "fetch_products",
                    "description": "Search for products online using Google Shopping.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Product search query."}
                        },
                        "required": ["query"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        ],
        model="gpt-4o",
    )
    
    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        for call in tool_calls:
            if call.function.name == "fetch_products":
                print(call.function.arguments)
                query = json.loads(call.function.arguments)["query"]
                products = fetch_products(query)
                filters = extract_filters(products)
                return {"products": products, "filters": filters}

    return {"message": "No products found"}
