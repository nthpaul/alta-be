import json
import hashlib
from app.config import redis_client

# we'd probably want user-specific caching in the actual app
# to do that, we'd cache on the user's id as well 
# e.g. hash_key = hashlib.sha256(f"{user_id}:{normalized_query}".encode()).hexdigest()
# and return something like "search:{user_id}:{hash_key}:{max_results}"
def get_cache_key(query: str, max_results: int):
    """Creates a cache key based on query and max results"""
    normalized_query = query.lower().strip()
    hash_key = hashlib.sha256(normalized_query.encode()).hexdigest()
    return f"search:{hash_key}:{max_results}"

def fetch_products_and_filters_with_cache(query: str, max_results: int = 10):
    """Fetch results from cache"""
    cache_key = get_cache_key(query, max_results)
    cached_results = redis_client.get(cache_key)
    if cached_results:
        return json.loads(cached_results)

def cache_result(cache_key, data, ttl=600):
    """Store results in cache"""
    redis_client.setex(cache_key, ttl, json.dumps(data))

