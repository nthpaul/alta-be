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
    is_fetch_pairing: bool = False
    max_num_products: int = 10

def fetch_products(query: str, max_results: int = 10):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": SERP_API_KEY,
        "number": max_results,
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch products")

    data = response.json()
    products = []

    for item in data.get("shopping_results", [])[:max_results]:
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
    system_message = (
        "You are a shopping assistant and outfit picker extraordinaire. "
        "When given a query, return a JSON array of products. Each product should have a name, price, and source (store link)."
    )

    # for pairings, we could even use vision models to describe the product better and pass that output to get better suggestions
    # seems like gpt-4o tends to create a query for only one product most of the time 
    # and it looks when it does generate a query for more than one product, serpapi/google shopping is pretty limited in terms of the number of products it can return
    # i.e. it can only return 100 products at a time but nearly all (usually all) of the items are dominated by the first product in the query
    # if it did return a variety of products then we could filter and return the top X products we think best fit by some strategy, but this doesn't seem to be the case
    # one alternative work around would be to make multiple calls to the api with different queries
    if request.is_fetch_pairing:
        system_message = (
            "You are a fashion stylist. Given a product name, suggest 2 complementary fashion products that pair well with it. "
            "Prioritize matching styles, colors, and trends."
            "Ensure the selections align with the item's style, color, and current fashion trends to create a cohesive look."
            "To ensure we can search for multiple products, you must follow this query format 'X or Y'"
        )

    response = client.beta.chat.completions.parse(
        messages=[
            {
                "role": "system",
                "content": system_message
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
                max_results = 5 if request.is_fetch_pairing else request.max_num_products
                products = fetch_products(query, max_results=max_results)

                print(request)
                print(request.is_fetch_pairing == True)

                if products and request.is_fetch_pairing:
                    return {"products": products}

                filters = extract_filters(products)
                return {"products": products, "filters": filters}


    return {"message": "No products found"}
