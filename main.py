from re import M
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List

app = FastAPI()


# MOCK SEARCH
class Product(BaseModel):
    id: int
    name: str
    brand: str
    price: float
    image_url: str
    source_url: str

MOCK_PRODUCTS = [
    {"id": 1, "name": "Black T-Shirt", "brand": "Nike", "price": 29.99, 
     "image_url": "https://via.placeholder.com/150", "source_url": "https://nike.com"},
    {"id": 2, "name": "White Sneakers", "brand": "Adidas", "price": 79.99, 
     "image_url": "https://via.placeholder.com/150", "source_url": "https://adidas.com"},
    {"id": 3, "name": "Blue Jeans", "brand": "Levi's", "price": 59.99, 
     "image_url": "https://via.placeholder.com/150", "source_url": "https://levis.com"},
]

@app.get('/')
def read_root():
    return {'message': 'the server is running'}

@app.get('/search', response_model=List[Product])
def search_products(query: str = Query(..., description="Search query for products")):
    results = [p for p in MOCK_PRODUCTS if query.lower() in p['name'].lower()]
    return results if results else MOCK_PRODUCTS

