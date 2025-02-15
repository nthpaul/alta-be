import os
import redis
from openai import OpenAI

SERP_API_KEY = os.environ.get("SERP_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
