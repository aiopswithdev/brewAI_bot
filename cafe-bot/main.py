"""
Entry point for Render deployment.
This file allows Render to run the FastAPI app from the cafe-bot root directory.
"""
import uvicorn
import os

# Get port from environment variable (Render sets this automatically)
port = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False  # Disable reload in production
    )
