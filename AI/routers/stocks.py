"""
Модуль маршрутов для работы с российскими акциями и облигациями.

Предоставляет API endpoints для получения рекомендаций по топ-10
акций и облигациям на Московской бирже с использованием модели Qwen2.5.
"""
import json
from datetime import datetime
from fastapi import HTTPException, APIRouter
from pydantic import BaseModel
import httpx
import ollama

router = APIRouter(
    prefix="/stocks",
    tags=["stocks"]
)

MODEL = "qwen2.5-coder:7b"


async def get_stock_prices(tickers: list[str]) -> dict[str, float]:
    """
    Получает текущие цены акций с Московской биржи.
    
    Args:
        tickers: Список тикеров акций (например, ['SBER', 'YNDX'])
    
    Returns:
        Словарь {тикер: цена} для найденных акций
    """
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


async def get_bond_prices(secids: list[str]) -> dict[str, float]:
    """
    Получает текущие цены облигаций с Московской биржи.
    
    Args:
        secids: Список идентификаторов облигаций (например, ['RU000A0JX0J2'])
    
    Returns:
        Словарь {secid: цена} для найденных облигаций
    """
    prices = {}
    async with httpx.AsyncClient() as http_client:
        for secid in secids:
            try:
                url = f"https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQOB/securities/{secid}.json"
                response = await http_client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    market_data = data.get("marketdata", {})
                    if market_data:
                        price = market_data.get("LAST")
                        if price:
                            prices[secid] = price
            except Exception:
                pass
    return prices


async def query_qwen(prompt: str, system_prompt: str) -> str:
    """
    Отправляет запрос к модели Qwen2.5 через Ollama.
    
    Args:
        prompt: Пользовательский запрос
        system_prompt: Системный промпт с инструкциями для модели
    
    Returns:
        Ответ модели в виде строки
    """
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        options={
            "temperature": 0.7,
            "num_ctx": 8192
        }
    )
    return response["message"]["content"]


class StockRecommendation(BaseModel):
    ticker: str
    name: str
    sector: str
    current_price: float | None = None
    reasoning: str
    sources: list[str]
    trading_plan: str


class BondRecommendation(BaseModel):
    secid: str
    name: str
    issuer: str
    coupon_rate: float | None = None
    maturity_date: str | None = None
    current_price: float | None = None
    yield_to_maturity: float | None = None
    reasoning: str
    sources: list[str]
    trading_plan: str


class StockResponse(BaseModel):
    recommendations: list[StockRecommendation]
    generated_at: str
    disclaimer: str


class BondResponse(BaseModel):
    recommendations: list[BondRecommendation]
    generated_at: str
    disclaimer: str


STOCKS_SYSTEM_PROMPT = """Ты - профессиональный финансовый аналитик с опытом работы на российском фондовом рынке (Московская биржа).

Твоя задача - предоставить ТОП-10 самых доходных ценных бумаг (акций) на российском рынке для покупки.

Для каждой акции предоставь:
1. Тикер (например, SBER, YNDX, GAZP, LKOH, NVTK, MGNT, POLY, ALRS, FLOT, CHMF)
2. Название компании
3. Сектор экономики
4. Краткое обоснование (фундаментальный анализ, технический анализ, дивидендная доходность, перспективы роста)
5. Ссылки на источники (Московская биржа, РБК, Коммерсант, Ведомости)
6. План торговли (точки входа, цели, стоп-лосс)

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
- Используй ТОЛЬКО акции с Московской биржи (T+)
- Учитывай санкционные риски
- Реалистичные оценки"""


BONDS_SYSTEM_PROMPT = """Ты - профессиональный финансовый аналитик с опытом работы на российском фондовом рынке (Московская биржа).

Твоя задача - предоставить ТОП-10 самых доходных облигаций на российском рынке для покупки.

Для каждой облигации предоставь:
1. Идентификатор (secid, например, RU000A0JX0J2, SU25018RMFS0)
2. Название облигации
3. Эмитент
4. Купонная ставка (%)
5. Дата погашения
6. Обоснование (доходность, кредитное качество, ликвидность)
7. Ссылки на источники
8. План покупки

Отвечай строго в JSON формате с массивом из 10 объектов.
Формат:
[{
  "secid": "RU000A0JX0J2",
  "name": "ОФЗ 26238",
  "issuer": "Минфин РФ",
  "coupon_rate": 6.0,
  "maturity_date": "2041-05-15",
  "reasoning": "Обоснование...",
  "sources": ["ссылка1"],
  "trading_plan": "План..."
}]

ВАЖНО:
- Только облигации с Московской биржи
- Государственные (ОФЗ) и корпоративные
- Учитывай кредитные риски"""


@router.get("/api/stocks/top10", response_model=StockResponse)
async def get_top10_stocks():
    """
    Возвращает топ-10 рекомендуемых акций на российском фондовом рынке.
    
    Запрос к модели Qwen2.5 для получения анализа акций с учетом:
    - Фундаментального анализа
    - Технического анализа
    - Дивидендной доходности
    - Перспектив роста
    
    Также получает текущие цены с Московской биржи.
    
    Returns:
        StockResponse: Список из 10 акций с описанием, ценами и планом торговли
    """
    try:
        result = await query_qwen(
            "Предоставь ТОП-10 самых доходных акций на российском фондовом рынке с полным обоснованием.",
            STOCKS_SYSTEM_PROMPT
        )

        data = json.loads(result)
        recommendations = data if isinstance(data, list) else data.get("recommendations", [])

        if recommendations:
            tickers = [r.get("ticker") for r in recommendations if r.get("ticker")]
            prices = await get_stock_prices(tickers)
            for rec in recommendations:
                ticker = rec.get("ticker")
                if ticker and ticker in prices:
                    rec["current_price"] = prices[ticker]

        return StockResponse(
            recommendations=recommendations,
            generated_at=datetime.now().isoformat(),
            disclaimer="Данная информация носит информационный характер и не является инвестиционной рекомендацией."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/api/bonds/top10", response_model=BondResponse)
async def get_top10_bonds():
    """
    Возвращает топ-10 рекомендуемых облигаций на российском рынке.
    
    Запрос к модели Qwen2.5 для получения анализа облигаций с учетом:
    - Доходности к погашению
    - Кредитного качества эмитента
    - Ликвидности на Московской бирже
    - Купонной ставки и срока погашения
    
    Также получает текущие цены с Московской биржи.
    
    Returns:
        BondResponse: Список из 10 облигаций с описанием, ценами и планом покупки
    """
    try:
        result = await query_qwen(
            "Предоставь ТОП-10 самых доходных облигаций на российском рынке с полным обоснованием.",
            BONDS_SYSTEM_PROMPT
        )

        data = json.loads(result)
        recommendations = data if isinstance(data, list) else data.get("recommendations", [])

        if recommendations:
            secids = [r.get("secid") for r in recommendations if r.get("secid")]
            prices = await get_bond_prices(secids)
            for rec in recommendations:
                secid = rec.get("secid")
                if secid and secid in prices:
                    rec["current_price"] = prices[secid]

        return BondResponse(
            recommendations=recommendations,
            generated_at=datetime.now().isoformat(),
            disclaimer="Данная информация носит информационный характер и не является инвестиционной рекомендацией."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/api/stocks/{ticker}")
async def get_stock_detail(ticker: str):
    """
    Возвращает подробную информацию об одной конкретной акции.
    
    Args:
        ticker: Тикер акции (например, 'SBER', 'YNDX')
    
    Запрос к модели Qwen2.5 для получения детального анализа акции,
    включая фундаментальный анализ, технический анализ и план торговли.
    
    Returns:
        Информация об акции с текущей ценой и рекомендациями
    """
    try:
        result = await query_qwen(
            f"Предоставь подробную информацию об акции {ticker} с обоснованием, источниками и планом торговли.",
            STOCKS_SYSTEM_PROMPT
        )

        data = json.loads(result)
        recommendations = data if isinstance(data, list) else data.get("recommendations", [])
        
        if recommendations and len(recommendations) > 0:
            data = recommendations[0]

        prices = await get_stock_prices([ticker])
        if ticker in prices:
            data["current_price"] = prices[ticker]

        data["disclaimer"] = "Данная информация носит информационный характер и не является инвестиционной рекомендацией."
        return data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/health")
async def health_check():
    return {"status": "healthy", "model": MODEL}
