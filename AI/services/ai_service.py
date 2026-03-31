"""
AI-сервис на базе Claude (Anthropic).
Выполняет ранжирование ценных бумаг и обогащение данных:
  - Акции: P/E, P/B, ROE, дивиденды, обоснование выбора
  - Облигации: кредитный рейтинг, задолженность эмитента, обоснование
"""
import anthropic
import json
from typing import List

from AI.config import settings
from models.stock import Stock, StockMultipliers
from models.bond import Bond, CreditRating, IssuerDebt


class AIService:
    def __init__(self):
        self._client: anthropic.AsyncAnthropic | None = None

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )
        return self._client

    # ------------------------------------------------------------------ #
    #  Акции                                                               #
    # ------------------------------------------------------------------ #

    async def rank_and_enrich_stocks(
            self, stocks: List[Stock], top_n: int = 10
    ) -> List[Stock]:
        """
        Ранжирует акции с помощью Claude и обогащает мультипликаторами.
        Возвращает упорядоченный список длиной top_n.
        """
        # Предварительная фильтрация: нужна капитализация и объём
        candidates = [s for s in stocks if s.multipliers.market_cap and s.volume]
        # Берём топ-60 по капитализации для подачи в AI
        candidates.sort(key=lambda s: s.multipliers.market_cap or 0, reverse=True)
        pool = candidates[:60]

        if not pool:
            return stocks[:top_n]

        payload = [
            {
                "ticker": s.ticker,
                "name": s.name,
                "price_rub": round(s.price, 2),
                "change_pct": round(s.change_percent, 2) if s.change_percent else None,
                "market_cap_bln_rub": (
                    round(s.multipliers.market_cap, 1) if s.multipliers.market_cap else None
                ),
                "sector": s.sector,
                "volume_lots": s.volume,
            }
            for s in pool
        ]

        prompt = f"""Ты опытный российский финансовый аналитик.
Ниже представлены актуальные данные с Московской биржи (MOEX).

Данные по акциям (JSON):
{json.dumps(payload, ensure_ascii=False, indent=2)}

Задача:
1. Выбери топ-{top_n} наиболее перспективных акций для долгосрочного инвестирования.
2. Для каждой укажи примерные мультипликаторы на основе своих знаний о компании.
3. Дай лаконичное обоснование выбора (1-2 предложения).

Критерии отбора:
- Фундаментальная недооценённость (P/E, P/B ниже отраслевых)
- Высокая дивидендная доходность
- Ликвидность и крупная капитализация
- Финансовая устойчивость и рыночная позиция

Верни ТОЛЬКО валидный JSON (без markdown, без пояснений):
{{
  "ranked": [
    {{
      "ticker": "SBER",
      "pe_ratio": 4.5,
      "pb_ratio": 0.85,
      "roe": 22.0,
      "dividend_yield": 10.5,
      "rank_reason": "Крупнейший банк РФ с высокой дивдоходностью и дешёвой оценкой"
    }}
  ]
}}

Используй только тикеры из списка выше. Верни ровно {top_n} позиций."""

        try:
            response = await self.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                thinking={"type": "adaptive"},
                messages=[{"role": "user", "content": prompt}],
            )
            text = next(
                (b.text for b in response.content if b.type == "text"), ""
            ).strip()

            result = json.loads(text)
            ranked_map = {item["ticker"]: item for item in result.get("ranked", [])}

            enriched: List[Stock] = []
            for ticker, data in ranked_map.items():
                stock = next((s for s in pool if s.ticker == ticker), None)
                if stock:
                    stock.multipliers.pe_ratio = data.get("pe_ratio")
                    stock.multipliers.pb_ratio = data.get("pb_ratio")
                    stock.multipliers.roe = data.get("roe")
                    stock.multipliers.dividend_yield = data.get("dividend_yield")
                    stock.rank_reason = data.get("rank_reason")
                    stock.rank_score = float(top_n - len(enriched))
                    enriched.append(stock)

            return enriched if enriched else pool[:top_n]

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[AI] Ошибка разбора ответа (акции): {e}")
            return pool[:top_n]
        except Exception as e:
            print(f"[AI] Ошибка ранжирования акций: {e}")
            return pool[:top_n]

    # ------------------------------------------------------------------ #
    #  Облигации                                                           #
    # ------------------------------------------------------------------ #

    async def rank_and_enrich_bonds(
            self, bonds: List[Bond], top_n: int = 10
    ) -> List[Bond]:
        """
        Ранжирует облигации и обогащает кредитными рейтингами и долговыми метриками.
        """
        candidates = [b for b in bonds if b.yield_to_maturity and b.volume]
        candidates.sort(key=lambda b: b.yield_to_maturity or 0, reverse=True)
        pool = candidates[:60]

        if not pool:
            return bonds[:top_n]

        payload = [
            {
                "ticker": b.ticker,
                "name": b.name,
                "price_pct": round(b.price, 2),
                "ytm_pct": round(b.yield_to_maturity, 2),
                "coupon_pct": b.coupon_rate,
                "maturity_date": b.maturity_date,
                "duration_years": round(b.duration, 2) if b.duration else None,
                "type": b.sector,
                "volume_lots": b.volume,
            }
            for b in pool
        ]

        prompt = f"""Ты опытный российский облигационный аналитик.
Ниже представлены актуальные данные с Московской биржи (MOEX).

Данные по облигациям (JSON):
{json.dumps(payload, ensure_ascii=False, indent=2)}

Задача:
1. Выбери топ-{top_n} наиболее привлекательных облигаций.
2. Для каждой укажи кредитный рейтинг эмитента и ключевые долговые показатели.
3. Дай лаконичное обоснование выбора (1-2 предложения).

Критерии отбора:
- Оптимальное соотношение доходность/риск
- Надёжность эмитента (кредитный рейтинг)
- Ликвидность
- Приемлемая дюрация (предпочтительно до 5 лет)

Верни ТОЛЬКО валидный JSON (без markdown, без пояснений):
{{
  "ranked": [
    {{
      "ticker": "RU000A107SM4",
      "credit_rating": "AA",
      "rating_agency": "АКРА",
      "rating_outlook": "Стабильный",
      "total_debt_bln_rub": 1500.0,
      "net_debt_ebitda": 2.1,
      "rank_reason": "Высокая доходность при инвестиционном рейтинге эмитента"
    }}
  ]
}}

Используй только тикеры из списка выше. Верни ровно {top_n} позиций."""

        try:
            response = await self.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                thinking={"type": "adaptive"},
                messages=[{"role": "user", "content": prompt}],
            )
            text = next(
                (b.text for b in response.content if b.type == "text"), ""
            ).strip()

            result = json.loads(text)
            ranked_map = {item["ticker"]: item for item in result.get("ranked", [])}

            enriched: List[Bond] = []
            for ticker, data in ranked_map.items():
                bond = next((b for b in pool if b.ticker == ticker), None)
                if bond:
                    bond.credit_rating = CreditRating(
                        rating=data.get("credit_rating"),
                        agency=data.get("rating_agency"),
                        outlook=data.get("rating_outlook"),
                    )
                    bond.issuer_debt = IssuerDebt(
                        total_debt_bln=data.get("total_debt_bln_rub"),
                        net_debt_ebitda=data.get("net_debt_ebitda"),
                    )
                    bond.rank_reason = data.get("rank_reason")
                    bond.rank_score = float(top_n - len(enriched))
                    enriched.append(bond)

            return enriched if enriched else pool[:top_n]

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[AI] Ошибка разбора ответа (облигации): {e}")
            return pool[:top_n]
        except Exception as e:
            print(f"[AI] Ошибка ранжирования облигаций: {e}")
            return pool[:top_n]

    # ------------------------------------------------------------------ #
    #  Итоговое объяснение                                                 #
    # ------------------------------------------------------------------ #

    async def generate_summary(
            self, securities: list, sec_type: str = "stocks"
    ) -> str:
        """Генерирует краткое резюме портфеля для инвестора."""
        if not securities:
            return ""

        if sec_type == "stocks":
            items = [
                f"{s.ticker} ({s.name}): {s.price:.2f} ₽, "
                f"P/E={s.multipliers.pe_ratio}, "
                f"дивиденды={s.multipliers.dividend_yield}%"
                for s in securities
            ]
            asset_type = "акций"
        else:
            items = [
                f"{b.ticker} ({b.name}): доходность {b.yield_to_maturity:.2f}%, "
                f"рейтинг {b.credit_rating.rating or 'н/д'}, "
                f"погашение {b.maturity_date or 'н/д'}"
                for b in securities
            ]
            asset_type = "облигаций"

        prompt = (
                f"Ты финансовый советник для частного инвестора. "
                f"Подготовь краткое резюме (3-4 предложения) о предложенном портфеле {asset_type}:\n\n"
                + "\n".join(items)
                + "\n\nОбъясни: общую идею портфеля, риск-профиль, ожидаемую доходность. "
                  "Пиши понятно, не более 120 слов. Отвечай на русском языке."
        )

        try:
            response = await self.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            return next(
                (b.text for b in response.content if b.type == "text"), ""
            )
        except Exception as e:
            print(f"[AI] Ошибка генерации резюме: {e}")
            return ""


# Глобальный экземпляр
ai_service = AIService()