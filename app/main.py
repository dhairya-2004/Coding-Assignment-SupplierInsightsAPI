import os
import logging
from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.models import InsightRequest, InsightResponse, HealthResponse
from app.llm_service import GeminiService, FallbackInsightGenerator


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

llm_service: Optional[GeminiService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm_service
    
    logger.info("Starting Supplier Insights API...")
    
    groq_key = os.getenv("GROQ_API_KEY")
    
    if groq_key:
        try:
            llm_service = GeminiService(api_key=groq_key)
            logger.info(f"✅ Groq initialized: {llm_service.model}")
        except Exception as e:
            logger.warning(f"Gemini init failed: {e}")
    else:
        logger.warning("⚠️ No GOOGLE_API_KEY found. Using fallback mode.")
        logger.warning("Set GOOGLE_API_KEY in .env file or environment variable.")
    
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Supplier Sourcing Insights API",
    description="Generate procurement insights using AI",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Supplier Insights API - Visit /docs"}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        llm_provider="Google Gemini" if llm_service else "Fallback"
    )


@app.post("/generate-insights", response_model=InsightResponse)
async def generate_insights(request: InsightRequest) -> InsightResponse:
    logger.info(f"Request: {request.category}, {len(request.suppliers)} suppliers")
    
    try:
        if llm_service:
            response = await llm_service.generate_insights(request)
        else:
            response = FallbackInsightGenerator.generate(request)
        return response
    except Exception as e:
        logger.error(f"Error: {e}")
        try:
            return FallbackInsightGenerator.generate(request)
        except:
            raise HTTPException(status_code=500, detail="Failed to generate insights")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)