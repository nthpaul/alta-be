import json
from app.config import client

def extract_filters(products):
    """Use GPT-4o function calling to extract filters (brand, color, type, material)."""
    product_names = [p["name"] for p in products]

    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You extract structured fashion product attributes from product names."},
            {"role": "user", "content": json.dumps({"product_names": product_names})}
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "extract_filters",
                    "description": "Extracts brand, color, type, and material from product names.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "brands": {"type": "array", "items": {"type": "string"}, "description": "Unique brands in the product list."},
                            "colors": {"type": "array", "items": {"type": "string"}, "description": "Unique colors in the product list."},
                            "types": {"type": "array", "items": {"type": "string"}, "description": "Unique product types (e.g., 'Shoulder Bag', 'Sneakers')."},
                            "materials": {"type": "array", "items": {"type": "string"}, "description": "Unique materials used (e.g., 'Leather', 'Cotton')."}
                        },
                        "required": ["brands", "colors", "types", "materials"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        ],
    )

    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        for call in tool_calls:
            if call.function.name == "extract_filters":
                response = json.loads(call.function.arguments)

                valid_prices = [p["price"] for p in products if isinstance(p["price"], (int, float))]

                return {
                    "brands": response["brands"],
                    "colors": response["colors"],
                    "types": response["types"],
                    "materials": response["materials"],
                    "min_price": min(valid_prices) if valid_prices else 0,
                    "max_price": max(valid_prices) if valid_prices else 0
                }
    return {"brands": [], "colors": [], "types": [], "materials": [], "min_price": 0, "max_price": 0}

