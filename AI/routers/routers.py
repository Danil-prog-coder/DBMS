import os
from fastapi import HTTPException, APIRouter
from pydantic import BaseModel
from openai import OpenAI
import httpx

router = APIRouter(
    prefix="/request",
    tags=["request"]
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def get_stock_prices(tickers: list[str]) -> dict[str, float]:
    prices = {}
    async with httpx.AsyncClient() as http_client:
        for ticker in tickers:
            try:
                url = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"
                response = await http_client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    market_data = data.get("marketdata", {})
                    if market_data:
                        price = market_data.get("LAST")
                        if price:
                            prices[ticker] = price
            except Exception:
                pass
    return prices


class StockRecommendation(BaseModel):
    ticker: str
    name: str
    sector: str
    current_price: float | None
    reasoning: str
    sources: list[str]
    trading_plan: str


class RecommendationsResponse(BaseModel):
    recommendations: list[StockRecommendation]
    generated_at: str
    disclaimer: str


SYSTEM_PROMPT = """Ты - профессиональный финансовый аналитик с опытом работы на российском фондовом рынке (Московская биржа).

Твоя задача - предоставить ТОП-10 лучших ценных бумаг на российском рынке для покупки.

Для каждой акции предоставь:
1. Тикер (например, SBER, YNDX, GAZP)
2. Название компании
3. Сектор экономики
4. Краткое, но полное обоснование, почему именно эта бумага лучше всего подходит для покупки (с учетом фундаментального анализа, технического анализа, дивидендной доходности, перспектив роста)
5. Ссылки на достоверные источники информации (сайты Московской биржи, финансовых изданий like "Коммерсант", "Ведомости", "РБК", аналитических агентств)
6. План для торговли (точки входа, цели по цене, уровни стоп-лосса)

Внимание: ВСЕГДА указывай реальные текущие цены (используй данные с Московской биржи iss.moex.com).

Отвечай строго в JSON формате с массивом из 10 объектов.
Формат:
[{
  "ticker": "SBER",
  "name": "Сбербанк",
  "sector": "Банковский сектор",
  "reasoning": "Подробное обоснование...",
  "sources": ["ссылка1", "ссылка2"],
  "trading_plan": "План торговли..."
}]

ВАЖНО: 
- Используй ТОЛЬКО акции, торгующиеся на Московской бирже (T+)
- Учитывай санкционные риски и ограничения
- Давай реалистичные оценки с учетом текущей ситуации на рынке
- Не рекомендуй компании под санкциями или с ограниченной ликвидностью"""


@router.get("/api/recommendations", response_model=RecommendationsResponse)
async def get_recommendations():
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "Предоставь ТОП-10 лучших ценных бумаг на российском фондовом рынке для покупки с полным обоснованием, ссылками на источники, текущими ценами и планом торговли."}
            ],
            temperature=0.7,
            max_tokens=8000,
            response_format={"type": "json_object"}
        )

        import json
        from datetime import datetime

        result_text = response.choices[0].message.content
        data = json.loads(result_text)

        recommendations = data.get("recommendations", data) if isinstance(data, dict) else data

        if isinstance(recommendations, list):
            tickers = [r.get("ticker") for r in recommendations if r.get("ticker")]
            prices = await get_stock_prices(tickers)

            for rec in recommendations:
                ticker = rec.get("ticker")
                if ticker and ticker in prices:
                    rec["current_price"] = prices[ticker]

        return RecommendationsResponse(
            recommendations=recommendations,
            generated_at=datetime.now().isoformat(),
            disclaimer="Данная информация носит информационный характер и не является инвестиционной рекомендацией. Все решения о покупке ценных бумаг принимаются самостоятельно. Ознакомьтесь с рисками."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@router.get("/api/recommendations/{ticker}")
async def get_single_recommendation(ticker: str):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Предоставь подробную информацию о покупке акций {ticker} с обоснованием, источниками, текущей ценой и планом торговли."}
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )

        import json
        from datetime import datetime

        result_text = response.choices[0].message.content
        data = json.loads(result_text)

        if isinstance(data, dict) and "recommendations" in data:
            recommendations = data["recommendations"]
            if isinstance(recommendations, list) and len(recommendations) > 0:
                data = recommendations[0]

        prices = await get_stock_prices([ticker])
        if ticker in prices:
            data["current_price"] = prices[ticker]

        data["disclaimer"] = "Данная информация носит информационный характер и не является инвестиционной рекомендацией."

        return data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendation: {str(e)}")


@router.get("/health")
async def health_check():
    return {"status": "healthy"}
