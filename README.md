# Local
```
source venv/bin/activate
pip install -r requirements.txt
```

Add API keys to `.env`

```
uvicorn main:app --reload
```

# What this is
A FastAPI server with simple AI orchestration to generate outfits based on a user's query.

## Features
- [x] Query based outfit generation (search for clothing & get recommendations)
- [x] Suggestions based on an existing outfit (pair complementary items)
- [x] Dynamic filters based on search results (brand, color, material, etc.)

## Enhancements for a full system:
- [ ] User Authentication (accounts, session management)
- [ ] Database Integration
    - Store user chat history, preferences, saved outfits, wishlist
    - `pgvector` for similarity-based recommendations
      - Store vector embeddings of product descriptions/images 
    - Cache chats, products for performance & lower API costs
    - Enable smarter outfit recommendations beyond text matching (vision, preferences, etc.)
    - Payments & E-commerce Integration (checkout, order tracking)
    - Social Features (share outfits, follow users, save favorite looks)
- [ ] Region-specific recommendations (local brands, weather, etc.)
