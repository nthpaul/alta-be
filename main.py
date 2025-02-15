from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os
import requests
import json
import re
from fastapi.middleware.cors import CORSMiddleware

import redis
import hashlib

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"),)
SERP_API_KEY = os.environ.get("SERP_API_KEY")

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# we'd probably want user-specific caching in the actual app
# to do that, we'd cache on the user's id as well e.g. hash_key = hashlib.sha256(f"{user_id}:{normalized_query}".encode()).hexdigest()
# and return something like "search:{user_id}:{hash_key}:{max_results}"
def get_cache_key(query: str, max_results: int):
    """Creates a cache key based on query and max_results"""
    normalized_query = query.lower().strip()
    hash_key = hashlib.sha256(normalized_query.encode()).hexdigest()
    return f"search:{hash_key}:{max_results}"

def fetch_products_and_filters_with_cache(query: str, max_results: int = 10):
    cache_key = get_cache_key(query, max_results)
    cached_results = redis_client.get(cache_key)
    if cached_results:
        return json.loads(cached_results)

def cache_result(cache_key, data, ttl=600):
    redis_client.setex(cache_key, ttl, json.dumps(data))

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

                print(response)

                return {
                    "brands": response["brands"],
                    "colors": response["colors"],
                    "types": response["types"],
                    "materials": response["materials"],
                    "min_price": min(valid_prices) if valid_prices else 0,
                    "max_price": max(valid_prices) if valid_prices else 0
                }
    return {"brands": [], "colors": [], "types": [], "materials": [], "min_price": 0, "max_price": 0}

class SearchRequest(BaseModel):
    query: str
    is_fetch_pairing: bool = False
    max_num_products: int = 10

@app.post('/search')
async def search(request: SearchRequest):
    # check if we have a cached result using the user's query
    cached_results = fetch_products_and_filters_with_cache(request.query, request.max_num_products)
    print(cached_results)
    if cached_results:
        return cached_results

    system_message = (
        "You are a shopping assistant and outfit picker extraordinaire. "
        "When given a query, return a JSON array of products. Each product should have a name, price, and source (store link)."
        "If you are given a user query which doesn't make sense, then make up your own random outfit query."
    )

    # for pairings, we could even use vision models to describe the product better and pass that output to get better suggestions
    # seems like gpt-4o and o1 tend to create a query for only one product most of the time
    # EDIT: it seems like asking the LLM to take its time to find the perfect pairings and then forming that into a query works a little better in getting a query for more than one product

    # it looks when it does generate a query for more than one product, serpapi/google shopping is pretty limited in terms of the number of products it can return
    # i.e. it can only return 100 products at a time but nearly all (usually all) of the items are dominated by the first product in the query
    # if it did return a variety of products then we could filter and return the top X products we think best fit by some strategy, but this doesn't seem to be the case
    # one alternative work around would be to make multiple calls to the api with different queries
    if request.is_fetch_pairing:
        system_message = (
            "You are a fashion stylist. Given a product name, suggest 2 complementary fashion products that pair well with it. "
            "Prioritize matching styles, colors, and trends."
            "Ensure the selections align with the item's style, color, and current fashion trends to create a cohesive look."
            "To ensure we can search for multiple products, you must follow this query format 'X or Y'"
            "Take your time to find the perfect pairings, then form that into a query to pass to the function call."
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
        model="gpt-4o"
    )
        
    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        for call in tool_calls:
            if call.function.name == "fetch_products":
                print(call.function.arguments) # the query that gpt comes up with
                query = json.loads(call.function.arguments)["query"]
                max_results = 5 if request.is_fetch_pairing else request.max_num_products

                # we don't cache pairings since they are saved in local storage atm
                if not request.is_fetch_pairing:
                    cached_results = fetch_products_and_filters_with_cache(query, max_results)
                    if cached_results:
                        return cached_results

                products = fetch_products(query, max_results=max_results)

                if products and request.is_fetch_pairing:
                    return products

                filters = extract_filters(products)
                response_data = {"products": products, "filters": filters}
                cache_key_with_gpt_query = get_cache_key(query, max_results)
                cache_key_with_user_query = get_cache_key(request.query, max_results)
                cache_result(cache_key_with_gpt_query, response_data)
                cache_result(cache_key_with_user_query, response_data)
                return response_data

    return {"message": "No products found"}
