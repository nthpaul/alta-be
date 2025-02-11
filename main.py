from fastapi import FastAPI, Query
from pydantic import BaseModel
# from typing import List
from openai import OpenAI
import os

app = FastAPI()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"),)

class SearchRequest(BaseModel):
    query: str

@app.post('/search')
async def search(request: SearchRequest):
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "Search for products related to " + request.query
            }
        ],
        model="gpt-4o",
    )
    print(response)
    return response.choices[0].message.content
