from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: str
    is_fetch_pairing: bool = False
    max_num_products: int = 10
