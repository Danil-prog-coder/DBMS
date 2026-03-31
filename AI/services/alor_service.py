"""
Сервис для получения котировок через ALOR OpenAPI.
Документация: https://alor.dev/
Регистрация: https://alor.ru/open-account

ALOR даёт real-time данные и стакан заявок.
Для использования нужен refresh token (получается в личном кабинете).
"""
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict

from AI.config import settings


class AlorService:
    OAUTH_URL = "https://oauth.alor.ru"
    API_URL = "https://api.alor.ru"

    def __init__(self):
        self._jwt_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    @property
    def is_available(self) -> bool:
        """True если задан refresh token."""
        return bool(settings.ALOR_REFRESH_TOKEN)

    async def _refresh_jwt(self) -> Optional[str]:
        """Обменять refresh token на JWT access token."""
        if not settings.ALOR_REFRESH_TOKEN:
            return None
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.OAUTH_URL}/refresh",
                    params={"token": settings.ALOR_REFRESH_TOKEN},
                )
                resp.raise_for_status()
                data = resp.json()
                self._jwt_token = data.get("AccessToken")
                # JWT живёт ~30 минут, обновляем за 5 до истечения
                self._token_expires = datetime.now() + timedelta(minutes=25)
                return self._jwt_token
        except Exception as e:
            print(f"[ALOR] Ошибка аутентификации: {e}")
            return None

    async def get_token(self) -> Optional[str]:
        if not self.is_available:
            return None
        if not self._jwt_token or (
                self._token_expires and datetime.now() >= self._token_expires
        ):
            return await self._refresh_jwt()
        return self._jwt_token

    async def get_quote(self, ticker: str, exchange: str = "MOEX") -> Optional[Dict]:
        """Получить котировку инструмента через ALOR API."""
        token = await self.get_token()
        if not token:
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.API_URL}/md/v2/Securities/{exchange}/{ticker}/quotes",
                    headers={"Authorization": f"Bearer {token}"},
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            print(f"[ALOR] Ошибка получения котировки {ticker}: {e}")
            return None

    async def get_orderbook(
            self, ticker: str, exchange: str = "MOEX", depth: int = 5
    ) -> Optional[Dict]:
        """Получить стакан заявок."""
        token = await self.get_token()
        if not token:
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.API_URL}/md/v2/orderbooks/{exchange}/{ticker}",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"depth": depth},
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            print(f"[ALOR] Ошибка стакана {ticker}: {e}")
            return None


# Глобальный экземпляр сервиса
alor_service = AlorService()