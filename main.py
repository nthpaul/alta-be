from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os
import requests
import json

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
    print(data)
    products = []
    for item in data.get("shopping_results", []):
        products.append({
            "name": item.get("title"),
            "brand": item.get("source"),
            "price": item.get("price"),
            "source_url": item.get("product_link"),
            "image_url": item.get("thumbnail")
        })
    return products

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
                return fetch_products(query)

    return {"message": "No products found"}
