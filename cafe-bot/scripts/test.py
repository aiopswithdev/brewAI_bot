from app.features.cafe_chatbot.query_understanding.constraint_extractor import (
    LLMConstraintExtractor
)    
from app.features.cafe_chatbot.retrieval.retriever import CafeRAGRetriever
from app.features.cafe_chatbot.llm.validator import validate_llm_response

retriever = CafeRAGRetriever("storage/cafe_faiss")
extractor = LLMConstraintExtractor()

from app.features.cafe_chatbot.llm.generator import GeminiLLMResponseGenerator
llm = GeminiLLMResponseGenerator(
    model_name="gemini-2.5-flash"   # fast + cheap
)
QUERY = "My budget is 200. Suggest vegan beverages"
constraints = extractor.extract(QUERY)
print(constraints)
items = retriever.search(   
    # query="cold non milk under 150",
    query=QUERY,
    max_price=constraints["max_price"],
    diet=constraints["diet"], # <--- Pass the extracted diet constraint here
    top_k=50
    # max_price=150
)
response = llm.generate(
    # user_query="cold non milk under 150",
    user_query=QUERY,
    items=items
)

# if not validate_llm_response(response, items):
#     response = (
#         "You can choose from: "
#         + ", ".join(f"{i['name']} (₹{i['price']})" for i in items)
#     )
print(items)
print(response)
