"""
FastAPI приложение — AI-советник по российским ценным бумагам.

Запуск:
    cd /path/to/DBMS
    uvicorn AI.main:app --reload --host 0.0.0.0 --port 8000

Swagger UI: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.securities import router as securities_router
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 AI Securities Advisor запущен")
    print(f"   MOEX ISS: {settings.MOEX_BASE_URL}")
    print(f"   ALOR API: {'включён' if settings.ALOR_REFRESH_TOKEN else 'отключён'}")
    yield
    print("⏹  Остановка сервера")


app = FastAPI(
    title="Russian Securities AI Advisor",
    description=(
        "FastAPI + Claude AI для анализа российских ценных бумаг.\n\n"
        "Источники данных:\n"
        "- **MOEX ISS** — актуальные котировки, объёмы, доходности\n"
        "- **ALOR OpenAPI** — real-time данные (опционально)\n"
        "- **Claude (Anthropic)** — AI-ранжирование и обогащение мультипликаторами"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(securities_router)


@app.get("/health", tags=["system"])
async def health_check():
    """Проверка работоспособности сервиса."""
    return {
        "status": "ok",
        "moex_url": settings.MOEX_BASE_URL,
        "alor_enabled": bool(settings.ALOR_REFRESH_TOKEN),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "AI.main:app",
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        reload=True,
    )