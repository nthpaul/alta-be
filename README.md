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

## Considerations for a full app:
- [ ] User Authentication (accounts, session management)
- [ ] Database Integration
    - Store user chat history, preferences, saved outfits, wishlist
    - `pgvector` for similarity-based recommendations
      - Store vector embeddings of product descriptions/images 
    - Cache chats, products for performance & lower API costs
    - Enable smarter outfit recommendations beyond text matching (vision, preferences, etc.)
    - Payments & E-commerce Integration (checkout, order tracking)
    - Social Features (share outfits, follow users, save favorite looks)
- [ ] Region-specific recommendations (local brands, weather, currency, etc.)

## On simulating AI chain of thought in the UI
A naive approach would be to pass the user's query to an AI that outputs a structured response that fills the blanks in a template for steps that take place in the AI orchestration pipeline.
E.g. For instance, if a user searches for 'affordable minimalist sneakers,' the AI might structure its thought process like: 1) Prioritizing budget-friendly options, 2) Filtering for minimalist styles, 3) Highlighting brands you've interacted with before.
