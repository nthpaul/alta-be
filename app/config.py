import os
import redis
from openai import OpenAI

SERP_API_KEY = os.environ.get("SERP_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0") 

client = OpenAI(api_key=OPENAI_API_KEY)

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
