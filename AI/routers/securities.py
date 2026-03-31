"""
FastAPI роутер для эндпоинтов ценных бумаг.

Эндпоинты:
  GET /api/v1/securities/top/stocks  — топ N акций
  GET /api/v1/securities/top/bonds   — топ N облигаций
  GET /api/v1/securities/top/all     — смешанный топ
  GET /api/v1/securities/summary     — AI-резюме текущего топа
"""
import asyncio
from typing import List

from fastapi import APIRouter, Query, HTTPException

from services.moex_service import MOEXService
from services.ai_service import ai_service
from services.ranker import pre_rank_stocks, pre_rank_bonds

router = APIRouter(prefix="/api/v1/securities", tags=["securities"])
moex = MOEXService()


@router.get("/top/stocks", summary="Топ N акций с AI-анализом")
async def get_top_stocks(
        n: int = Query(default=5, ge=1, le=50, description="Количество акций"),
        offset: int = Query(default=0, ge=0, description="Смещение для пагинации"),
        use_ai: bool = Query(default=True, description="Использовать AI для обогащения"),
):
    """
    Возвращает топ N российских акций с Московской биржи.

    - **n**: сколько бумаг вернуть (1–50)
    - **offset**: пропустить первые N бумаг (для постраничного вывода)
    - **use_ai**: если True — Claude анализирует и добавляет мультипликаторы
    """
    try:
        stocks = await moex.get_stocks()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not stocks:
        raise HTTPException(status_code=404, detail="Нет данных по акциям")

    if use_ai:
        ranked = await ai_service.rank_and_enrich_stocks(stocks, top_n=50)
    else:
        ranked = pre_rank_stocks(stocks)

    page = ranked[offset: offset + n]
    return {
        "total": len(ranked),
        "offset": offset,
        "count": len(page),
        "securities": [s.model_dump() for s in page],
    }


@router.get("/top/bonds", summary="Топ N облигаций с AI-анализом")
async def get_top_bonds(
        n: int = Query(default=5, ge=1, le=50),
        offset: int = Query(default=0, ge=0),
        use_ai: bool = Query(default=True),
):
    """
    Возвращает топ N российских облигаций (корпоративные + ОФЗ).

    Для каждой облигации AI добавляет кредитный рейтинг эмитента
    и ключевые долговые метрики.
    """
    try:
        bonds = await moex.get_bonds()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not bonds:
        raise HTTPException(status_code=404, detail="Нет данных по облигациям")

    if use_ai:
        ranked = await ai_service.rank_and_enrich_bonds(bonds, top_n=50)
    else:
        ranked = pre_rank_bonds(bonds)

    page = ranked[offset: offset + n]
    return {
        "total": len(ranked),
        "offset": offset,
        "count": len(page),
        "securities": [b.model_dump() for b in page],
    }


@router.get("/top/all", summary="Смешанный топ акций и облигаций")
async def get_top_all(
        n: int = Query(default=10, ge=1, le=50),
        offset: int = Query(default=0, ge=0),
):
    """
    Возвращает смешанный топ — акции и облигации чередуются.
    """
    try:
        stocks_raw, bonds_raw = await asyncio.gather(
            moex.get_stocks(),
            moex.get_bonds(),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    ranked_stocks, ranked_bonds = await asyncio.gather(
        ai_service.rank_and_enrich_stocks(stocks_raw, top_n=25),
        ai_service.rank_and_enrich_bonds(bonds_raw, top_n=25),
    )

    # Чередуем акции и облигации
    mixed: List[dict] = []
    for i in range(max(len(ranked_stocks), len(ranked_bonds))):
        if i < len(ranked_stocks):
            mixed.append({"type": "stock", "data": ranked_stocks[i].model_dump()})
        if i < len(ranked_bonds):
            mixed.append({"type": "bond", "data": ranked_bonds[i].model_dump()})

    page = mixed[offset: offset + n]
    return {
        "total": len(mixed),
        "offset": offset,
        "count": len(page),
        "securities": page,
    }


@router.get("/summary", summary="AI-резюме текущего топа")
async def get_summary(
        sec_type: str = Query(
            default="stocks",
            pattern="^(stocks|bonds)$",
            description="Тип: stocks или bonds",
        ),
        n: int = Query(default=5, ge=1, le=20),
):
    """
    Генерирует краткое AI-резюме рекомендуемого портфеля на русском языке.
    """
    if sec_type == "stocks":
        raw = await moex.get_stocks()
        ranked = await ai_service.rank_and_enrich_stocks(raw, top_n=n)
        summary = await ai_service.generate_summary(ranked[:n], sec_type="stocks")
    else:
        raw = await moex.get_bonds()
        ranked = await ai_service.rank_and_enrich_bonds(raw, top_n=n)
        summary = await ai_service.generate_summary(ranked[:n], sec_type="bonds")

    return {"sec_type": sec_type, "n": n, "summary": summary}

