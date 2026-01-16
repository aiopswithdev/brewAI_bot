# CHANGED BELOW FOR GEMINI-3-FLASH-PREVIEW, USING SELF.HISTORY IN CHATBOT.PY
print("✅ main.py imported")

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List

# Import our Stateless Bot
from app.features.cafe_chatbot.chatbot import CafeChatbot

# 1. Global State
bot = None
user_sessions: Dict[str, List[Dict]] = {} # Memory Store (Use Redis in Prod)

# 2. Lifespan Manager
import os
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot
    print("🔄 Lifespan starting")

    print("📂 CWD:", os.getcwd())
    print("📂 Files:", os.listdir("."))
    
    if os.path.exists("storage"):
        print("📂 storage exists:", os.listdir("storage"))
    else:
        print("❌ storage folder missing")

    try:
        print("🚀 Creating CafeChatbot...")
        bot = CafeChatbot(storage_dir="storage/cafe_faiss")
        print("✅ CafeChatbot created")
    except Exception as e:
        print("❌ ERROR while loading bot:", repr(e))
        raise e

    yield

app = FastAPI(title="Cafe RAG API", lifespan=lifespan)

# Allow CORS for your ExpressJS/Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_user"

# @app.post("/chat/stream")
# async def stream_chat(request: ChatRequest):
#     if not bot:
#         raise HTTPException(status_code=503, detail="Bot starting up...")

#     # A. Retrieve or Initialize User History
#     if request.session_id not in user_sessions:
#         user_sessions[request.session_id] = []
    
#     # We pass this list to the bot. 
#     # Because lists are mutable, the bot updates this list IN-PLACE.
#     history = user_sessions[request.session_id]

#     async def response_generator():
#         try:
#             # The bot will generate text AND update 'history' automatically
#             for chunk in bot.chat_stream(request.message, chat_history=history):
#                 yield chunk
                
#         except Exception as e:
#             yield f"[Error: {str(e)}]"
#             return

#         # Optimization: Trim history if it gets too long (keep last 10 turns)
#         if len(history) > 20: 
#             # Slice in-place to keep the object reference valid
#             history[:] = history[-20:]

#     return StreamingResponse(response_generator(), media_type="text/plain")
from fastapi.concurrency import iterate_in_threadpool
from fastapi.responses import StreamingResponse

@app.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    if not bot:
        raise HTTPException(status_code=503, detail="Bot starting up...")

    # Session history
    history = user_sessions.setdefault(request.session_id, [])

    # IMPORTANT: run the blocking generator in a threadpool
    def sync_generator():
        try:
            for chunk in bot.chat_stream(request.message, chat_history=history):
                # 🔥 newline forces browser flush
                yield chunk + "\n"
        except Exception as e:
            yield f"[Error: {str(e)}]\n"

        # Trim history safely
        if len(history) > 20:
            history[:] = history[-20:]

    return StreamingResponse(
        iterate_in_threadpool(sync_generator()),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )

@app.post("/chat/clear")
async def clear_history(request: ChatRequest):
    if request.session_id in user_sessions:
        user_sessions[request.session_id] = []
    return {"status": "memory_cleared"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Render monitoring"""
    return {
        "status": "healthy",
        "bot_loaded": bot is not None,
        "service": "cafe-bot"
    }

if __name__ == "__main__":
    # Get port from environment (Render sets this automatically)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)