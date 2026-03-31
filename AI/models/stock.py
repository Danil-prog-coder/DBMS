from pydantic import BaseModel
from typing import Optional


class StockMultipliers(BaseModel):
    pe_ratio: Optional[float] = None  # P/E
    pb_ratio: Optional[float] = None  # P/B
    ps_ratio: Optional[float] = None  # P/S
    ev_ebitda: Optional[float] = None  # EV/EBITDA
    roe: Optional[float] = None  # Рентабельность капитала, %
    dividend_yield: Optional[float] = None  # Дивидендная доходность, %
    market_cap: Optional[float] = None  # Капитализация, млрд ₽


class Stock(BaseModel):
    ticker: str
    name: str
    price: float
    currency: str = "RUB"
    change_percent: Optional[float] = None  # Изменение за день, %
    volume: Optional[int] = None  # Объём торгов (лоты)
    turnover: Optional[float] = None  # Оборот, ₽
    sector: Optional[str] = None
    issuer: Optional[str] = None
    multipliers: StockMultipliers = StockMultipliers()
    exchange: str = "MOEX"
    rank_score: float = 0.0
    rank_reason: Optional[str] = None

    def format_price(self) -> str:
        return f"{self.price:,.2f} ₽"

    def format_change(self) -> str:
        if self.change_percent is None:
            return "—"
        arrow = "▲" if self.change_percent >= 0 else "▼"
        return f"{arrow} {self.change_percent:+.2f}%"

    def to_telegram_card(self, position: int) -> str:
        lines = [f"<b>{position}. {self.ticker}</b> — {self.name}"]
        lines.append(f"💰 Цена: <b>{self.format_price()}</b>  {self.format_change()}")

        if self.issuer and self.issuer != self.name:
            lines.append(f"🏢 Эмитент: {self.issuer}")
        if self.sector:
            lines.append(f"🏭 Сектор: {self.sector}")

        m = self.multipliers
        if m.market_cap:
            lines.append(f"📊 Капитализация: {m.market_cap:.0f} млрд ₽")

        mults = []
        if m.pe_ratio:
            mults.append(f"P/E: {m.pe_ratio:.1f}")
        if m.pb_ratio:
            mults.append(f"P/B: {m.pb_ratio:.2f}")
        if m.roe:
            mults.append(f"ROE: {m.roe:.1f}%")
        if m.dividend_yield:
            mults.append(f"Дивиденды: {m.dividend_yield:.1f}%")
        if mults:
            lines.append(f"📈 Мультипликаторы: {' | '.join(mults)}")

        if self.rank_reason:
            lines.append(f"\n💡 <i>{self.rank_reason}</i>")

        return "\n".join(lines)