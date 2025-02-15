from fastapi import APIRouter
from app.models import SearchRequest
from app.utils.caching import get_cache_key, fetch_products_and_filters_with_cache, cache_result
from app.utils.search import fetch_products
from app.utils.filters import extract_filters
from app.config import client
import json

router = APIRouter()

@router.post('/search')
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
