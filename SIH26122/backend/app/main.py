import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.database import check_db_connection

load_dotenv()

app = FastAPI(title="SIH26122 - KaryaSetu")

# CORS configuration
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    db_connected = await check_db_connection()
    return {
        "status": "ok",
        "database": "connected" if db_connected else "unavailable"
    }
