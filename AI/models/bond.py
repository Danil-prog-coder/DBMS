from pydantic import BaseModel
from typing import Optional


class CreditRating(BaseModel):
    rating: Optional[str] = None  # AA, A+, BBB- и т.д.
    agency: Optional[str] = None  # АКРА, Эксперт РА, НКР
    outlook: Optional[str] = None  # Стабильный, Позитивный, Негативный


class IssuerDebt(BaseModel):
    total_debt_bln: Optional[float] = None  # Общий долг, млрд ₽
    debt_to_equity: Optional[float] = None  # Долг/Капитал
    net_debt_ebitda: Optional[float] = None  # Чистый долг/EBITDA
    interest_coverage: Optional[float] = None  # Коэффициент покрытия %


class Bond(BaseModel):
    ticker: str
    isin: Optional[str] = None
    name: str
    price: float  # % от номинала
    face_value: float = 1000.0
    currency: str = "RUB"
    yield_to_maturity: Optional[float] = None  # Доходность к погашению, %
    coupon_rate: Optional[float] = None  # Ставка купона, %
    coupon_frequency: Optional[int] = None  # Выплат в год
    next_coupon_date: Optional[str] = None
    maturity_date: Optional[str] = None
    duration: Optional[float] = None  # Дюрация, лет
    volume: Optional[int] = None
    sector: Optional[str] = None  # ОФЗ / Корпоративные
    issuer: Optional[str] = None
    credit_rating: CreditRating = CreditRating()
    issuer_debt: IssuerDebt = IssuerDebt()
    exchange: str = "MOEX"
    rank_score: float = 0.0
    rank_reason: Optional[str] = None

    def format_price(self) -> str:
        actual = self.price * self.face_value / 100
        return f"{actual:,.2f} ₽ ({self.price:.2f}%)"

    def format_yield(self) -> str:
        if self.yield_to_maturity is None:
            return "—"
        return f"{self.yield_to_maturity:.2f}% годовых"

    def format_rating(self) -> str:
        if not self.credit_rating.rating:
            return "—"
        r = self.credit_rating.rating
        if self.credit_rating.agency:
            r += f" ({self.credit_rating.agency})"
        if self.credit_rating.outlook:
            r += f", {self.credit_rating.outlook}"
        return r

    def to_telegram_card(self, position: int) -> str:
        lines = [f"<b>{position}. {self.ticker}</b> — {self.name}"]
        lines.append(f"💰 Цена: <b>{self.format_price()}</b>")
        lines.append(f"📈 Доходность (YTM): <b>{self.format_yield()}</b>")

        if self.coupon_rate:
            lines.append(f"🎫 Купон: {self.coupon_rate:.2f}%")
        if self.duration:
            lines.append(f"⏱ Дюрация: {self.duration:.2f} лет")
        if self.maturity_date:
            lines.append(f"📅 Погашение: {self.maturity_date}")
        if self.sector:
            lines.append(f"🏭 Тип: {self.sector}")
        if self.issuer:
            lines.append(f"🏢 Эмитент: {self.issuer}")

        rating = self.format_rating()
        if rating != "—":
            lines.append(f"⭐ Кредитный рейтинг: {rating}")

        d = self.issuer_debt
        if d.total_debt_bln:
            lines.append(f"💳 Долг эмитента: {d.total_debt_bln:.0f} млрд ₽")
        if d.net_debt_ebitda:
            lines.append(f"📊 Чистый долг/EBITDA: {d.net_debt_ebitda:.2f}x")

        if self.rank_reason:
            lines.append(f"\n💡 <i>{self.rank_reason}</i>")

        return "\n".join(lines)