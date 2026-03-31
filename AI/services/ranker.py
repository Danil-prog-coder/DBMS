"""
Базовый числовой скоринг ценных бумаг для предварительной фильтрации
перед подачей в AI. Используется как fallback при недоступности AI.
"""
from typing import List
from models.stock import Stock
from models.bond import Bond


def score_stock(stock: Stock) -> float:
    """Числовая оценка акции по доступным метрикам."""
    score = 0.0

    # Капитализация (крупные = стабильные)
    if stock.multipliers.market_cap:
        cap = stock.multipliers.market_cap
        if cap > 2000:  # > 2 трлн ₽
            score += 35
        elif cap > 500:  # > 500 млрд ₽
            score += 25
        elif cap > 100:  # > 100 млрд ₽
            score += 15
        elif cap > 10:
            score += 8
        else:
            score += 3

    # Ликвидность (объём торгов)
    if stock.volume:
        vol = stock.volume
        if vol > 10_000_000:
            score += 25
        elif vol > 1_000_000:
            score += 15
        elif vol > 100_000:
            score += 8

    # Оборот в рублях
    if stock.turnover:
        turn = stock.turnover
        if turn > 5_000_000_000:  # > 5 млрд ₽/день
            score += 20
        elif turn > 500_000_000:  # > 500 млн ₽/день
            score += 12
        elif turn > 50_000_000:  # > 50 млн ₽/день
            score += 6

    # Ценовой импульс
    if stock.change_percent is not None:
        chg = stock.change_percent
        if chg > 3:
            score += 8
        elif chg > 1:
            score += 5
        elif chg > 0:
            score += 2
        elif chg < -5:
            score -= 8

    return score


def score_bond(bond: Bond) -> float:
    """Числовая оценка облигации по доступным метрикам."""
    score = 0.0

    # Доходность к погашению (оптимальный диапазон 10-20%)
    if bond.yield_to_maturity:
        ytm = bond.yield_to_maturity
        if 10 <= ytm <= 18:  # Sweet spot: хорошая доходность + умеренный риск
            score += 35
        elif 18 < ytm <= 25:  # Высокая доходность, выше риск
            score += 22
        elif 8 <= ytm < 10:  # Консервативная доходность
            score += 18
        elif 25 < ytm <= 40:  # Очень высокий риск
            score += 10
        elif ytm > 40:  # Дефолтный риск
            score += 2

    # Ликвидность
    if bond.volume:
        vol = bond.volume
        if vol > 50_000:
            score += 25
        elif vol > 10_000:
            score += 16
        elif vol > 1_000:
            score += 8
        elif vol > 100:
            score += 3

    # Дюрация (предпочтительно 1-5 лет)
    if bond.duration:
        dur = bond.duration
        if 1 <= dur <= 3:
            score += 20
        elif 3 < dur <= 5:
            score += 15
        elif 0.25 <= dur < 1:
            score += 10
        elif 5 < dur <= 10:
            score += 8

    # ОФЗ — государственные облигации надёжнее
    if bond.sector == "ОФЗ":
        score += 12

    return score


def pre_rank_stocks(stocks: List[Stock]) -> List[Stock]:
    """Предварительное ранжирование акций (без AI)."""
    for s in stocks:
        s.rank_score = score_stock(s)
    return sorted(stocks, key=lambda s: s.rank_score, reverse=True)


def pre_rank_bonds(bonds: List[Bond]) -> List[Bond]:
    """Предварительное ранжирование облигаций (без AI)."""
    for b in bonds:
        b.rank_score = score_bond(b)
    return sorted(bonds, key=lambda b: b.rank_score, reverse=True)