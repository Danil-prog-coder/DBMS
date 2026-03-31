"""
Сервис для получения данных с Московской биржи через ISS MOEX API.
Документация: https://iss.moex.com/iss/reference/
"""
import httpx
from typing import List, Dict, Optional, Tuple

from models.stock import Stock, StockMultipliers
from models.bond import Bond, CreditRating, IssuerDebt


class MOEXService:
    BASE_URL = "https://iss.moex.com/iss"

    # Информация о компаниях: ticker -> (полное_название, сектор)
    COMPANY_INFO: Dict[str, Tuple[str, str]] = {
        "SBER": ("Сбербанк России", "Финансы"),
        "SBERP": ("Сбербанк России (прив.)", "Финансы"),
        "GAZP": ("Газпром", "Нефть и газ"),
        "LKOH": ("ЛУКОЙЛ", "Нефть и газ"),
        "NVTK": ("НОВАТЭК", "Нефть и газ"),
        "ROSN": ("Роснефть", "Нефть и газ"),
        "GMKN": ("ГМК Норильский Никель", "Металлы и добыча"),
        "SNGS": ("Сургутнефтегаз", "Нефть и газ"),
        "SNGSP": ("Сургутнефтегаз (прив.)", "Нефть и газ"),
        "YNDX": ("Яндекс", "Технологии"),
        "TATN": ("Татнефть", "Нефть и газ"),
        "TATNP": ("Татнефть (прив.)", "Нефть и газ"),
        "MGNT": ("Магнит", "Ритейл"),
        "MTSS": ("МТС", "Телекоммуникации"),
        "VTBR": ("ВТБ", "Финансы"),
        "ALRS": ("АЛРОСА", "Металлы и добыча"),
        "PHOR": ("ФосАгро", "Химия"),
        "CHMF": ("Северсталь", "Металлы и добыча"),
        "NLMK": ("НЛМК", "Металлы и добыча"),
        "MAGN": ("ММК", "Металлы и добыча"),
        "IRAO": ("Интер РАО", "Электроэнергетика"),
        "FEES": ("ФСК ЕЭС", "Электроэнергетика"),
        "RUAL": ("РУСАЛ", "Металлы и добыча"),
        "PLZL": ("Полюс", "Металлы и добыча"),
        "POLY": ("Полиметалл", "Металлы и добыча"),
        "PIKK": ("ПИК", "Строительство"),
        "AFLT": ("Аэрофлот", "Транспорт"),
        "FIVE": ("X5 Group", "Ритейл"),
        "OZON": ("Ozon", "Технологии/Ритейл"),
        "TCSG": ("Т-Банк (ТКС Холдинг)", "Финансы"),
        "POSI": ("Positive Technologies", "IT-безопасность"),
        "ASTR": ("ГК Астра", "Технологии"),
        "SMLT": ("Самолёт", "Строительство"),
        "WUSH": ("Whoosh", "Транспорт"),
        "HHRU": ("HeadHunter", "Технологии"),
        "VKCO": ("VK", "Технологии"),
        "BSPB": ("Банк Санкт-Петербург", "Финансы"),
        "RENI": ("Ренессанс Страхование", "Финансы"),
        "SELG": ("Селигдар", "Металлы и добыча"),
        "CBOM": ("МКБ", "Финансы"),
        "FLOT": ("Совкомфлот", "Транспорт"),
        "MOEX": ("Московская биржа", "Финансы"),
        "AQUA": ("Инарктика", "АПК"),
        "LSRG": ("ЛСР", "Строительство"),
        "BELU": ("НоваБев Груп", "Потребительские товары"),
        "SOFL": ("Softline", "Технологии"),
        "DIAS": ("Диасофт", "Технологии"),
        "DATA": ("Аренадата", "Технологии"),
        "TRNFP": ("Транснефть (прив.)", "Нефть и газ"),
        "EUTR": ("ЕвроТранс", "Нефть и газ"),
        "SFIN": ("ЭсЭфАй", "Финансы"),
        "FIXP": ("Fix Price", "Ритейл"),
        "NKNC": ("Нижнекамскнефтехим", "Химия"),
        "KZOS": ("Казаньоргсинтез", "Химия"),
        "MVID": ("М.Видео", "Ритейл"),
        "LENT": ("Лента", "Ритейл"),
        "GLTR": ("Globaltrans", "Транспорт"),
    }

    async def _get(self, url: str, params: dict = None) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    def _parse_iss(self, data: dict, key: str) -> List[Dict]:
        """Преобразует колончатый формат ISS в список словарей."""
        block = data.get(key, {})
        columns = block.get("columns", [])
        rows = block.get("data", [])
        return [dict(zip(columns, row)) for row in rows]

    async def get_stocks(self) -> List[Stock]:
        """Получить все акции с доски TQBR Московской биржи."""
        url = f"{self.BASE_URL}/engines/stock/markets/shares/boards/TQBR/securities.json"
        params = {"iss.meta": "off", "iss.only": "securities,marketdata"}

        try:
            data = await self._get(url, params)
        except Exception as e:
            raise RuntimeError(f"Ошибка MOEX ISS API (акции): {e}")

        securities = {r["SECID"]: r for r in self._parse_iss(data, "securities")}
        marketdata = {r["SECID"]: r for r in self._parse_iss(data, "marketdata")}

        stocks: List[Stock] = []
        for ticker, sec in securities.items():
            md = marketdata.get(ticker, {})

            # Цена: предпочитаем последнюю сделку, затем предыдущее закрытие
            price = md.get("LAST") or sec.get("PREVPRICE")
            if not price:
                continue
            try:
                price_f = float(price)
            except (TypeError, ValueError):
                continue
            if price_f <= 0:
                continue

            # Капитализация
            raw_cap = md.get("ISSUECAPITALIZATION") or sec.get("ISSUECAPITALIZATION")
            market_cap_bln: Optional[float] = None
            if raw_cap:
                try:
                    market_cap_bln = float(raw_cap) / 1_000_000_000
                except (TypeError, ValueError):
                    pass

            # Изменение за день %
            change_pct: Optional[float] = None
            chg_raw = md.get("LASTTOPREVPRICE")
            if chg_raw is not None:
                try:
                    change_pct = float(chg_raw)
                except (TypeError, ValueError):
                    pass

            # Объём и оборот
            vol_raw = md.get("VOLTODAY") or md.get("VOLUME")
            turn_raw = md.get("VALTODAY_RUR") or md.get("VALTODAY")
            volume: Optional[int] = None
            turnover: Optional[float] = None
            if vol_raw:
                try:
                    volume = int(float(vol_raw))
                except (TypeError, ValueError):
                    pass
            if turn_raw:
                try:
                    turnover = float(turn_raw)
                except (TypeError, ValueError):
                    pass

            issuer, sector = self.COMPANY_INFO.get(
                ticker, (sec.get("SHORTNAME", ticker), "Прочее")
            )

            stocks.append(Stock(
                ticker=ticker,
                name=sec.get("SHORTNAME", ticker),
                price=price_f,
                change_percent=change_pct,
                volume=volume,
                turnover=turnover,
                sector=sector,
                issuer=issuer,
                multipliers=StockMultipliers(market_cap=market_cap_bln),
            ))

        return stocks

    async def get_bonds(self) -> List[Bond]:
        """Получить корпоративные облигации и ОФЗ с Московской биржи."""
        bonds: List[Bond] = []

        for board, bond_sector in [("TQCB", "Корпоративные"), ("TQOB", "ОФЗ")]:
            url = (
                f"{self.BASE_URL}/engines/stock/markets/bonds"
                f"/boards/{board}/securities.json"
            )
            params = {"iss.meta": "off", "iss.only": "securities,marketdata"}

            try:
                data = await self._get(url, params)
            except Exception as e:
                print(f"[MOEX] Ошибка загрузки облигаций ({board}): {e}")
                continue

            securities = {r["SECID"]: r for r in self._parse_iss(data, "securities")}
            marketdata = {r["SECID"]: r for r in self._parse_iss(data, "marketdata")}

            for ticker, sec in securities.items():
                md = marketdata.get(ticker, {})

                # Цена (% от номинала)
                price_raw = md.get("LAST") or sec.get("PREVPRICE")
                if not price_raw:
                    continue
                try:
                    price_f = float(price_raw)
                except (TypeError, ValueError):
                    continue
                if price_f <= 0:
                    continue

                # YTM (доходность к погашению)
                ytm_raw = md.get("YIELD") or sec.get("YIELD")
                if not ytm_raw:
                    continue
                try:
                    ytm = float(ytm_raw)
                except (TypeError, ValueError):
                    continue
                if ytm <= 0 or ytm > 100:
                    continue

                # Объём торгов (фильтр неликвидных)
                vol_raw = md.get("VOLTODAY") or md.get("VOLUME")
                volume: Optional[int] = None
                if vol_raw:
                    try:
                        volume = int(float(vol_raw))
                    except (TypeError, ValueError):
                        pass
                if not volume or volume == 0:
                    continue

                # Дюрация (MOEX даёт в днях)
                dur_raw = md.get("DURATION") or sec.get("DURATION")
                duration_years: Optional[float] = None
                if dur_raw:
                    try:
                        d_days = float(dur_raw)
                        if d_days > 0:
                            duration_years = d_days / 365
                    except (TypeError, ValueError):
                        pass

                # Прочие поля
                coupon_raw = sec.get("COUPONPERCENT")
                coupon_rate: Optional[float] = None
                if coupon_raw:
                    try:
                        coupon_rate = float(coupon_raw)
                    except (TypeError, ValueError):
                        pass

                face_raw = sec.get("FACEVALUE", 1000)
                try:
                    face_value = float(face_raw) if face_raw else 1000.0
                except (TypeError, ValueError):
                    face_value = 1000.0

                maturity = sec.get("MATDATE")
                next_coupon = sec.get("NEXTCOUPON")
                isin = sec.get("ISIN")

                bonds.append(Bond(
                    ticker=ticker,
                    isin=str(isin) if isin else None,
                    name=sec.get("SHORTNAME", ticker),
                    price=price_f,
                    face_value=face_value,
                    yield_to_maturity=ytm,
                    coupon_rate=coupon_rate,
                    next_coupon_date=str(next_coupon) if next_coupon else None,
                    maturity_date=str(maturity) if maturity else None,
                    duration=duration_years,
                    volume=volume,
                    sector=bond_sector,
                    issuer=sec.get("SHORTNAME", ticker),
                ))

        return bonds