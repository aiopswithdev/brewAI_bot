# app/features/cafe_chatbot/llm/validator.py

def validate_llm_response(response: str, items: list[dict]) -> bool:
    """
    Ensure LLM did not mention items or prices outside retrieved context.
    """
    allowed_names = {item["name"].lower() for item in items}
    allowed_prices = {str(item["price"]) for item in items}

    response_lower = response.lower()

    for word in response_lower.split():
        # price hallucination check
        if word.isdigit() and word not in allowed_prices:
            return False

    # item name hallucination check
    for token in response_lower.split(","):
        token = token.strip()
        if token and any(char.isalpha() for char in token):
            if token in allowed_names:
                continue

    return True
