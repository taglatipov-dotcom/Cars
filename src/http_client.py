import asyncio
from datetime import datetime

from aiohttp import ClientSession, ClientTimeout

from src.config import settings
from src.schemas import SCarAdd

from src.customs import ENGINE_TYPE_CODES, OWNER_PERSONAL, build_customs_payload  # noqa: F401


class HttpClient:
    def __init__(self, base_url: str, api_client: str, api_key: str):
        self._base_url = base_url
        self._headers = {
            "Api-Client-Id": api_client,
            "Api-Key": api_key,
        }
        self._session: ClientSession | None = None

    async def _get_session(self) -> ClientSession:
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                base_url=self._base_url,
                headers=self._headers,
                timeout=ClientTimeout(total=15),  # без таймаута запрос мог висеть минутами
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


class CALCUSHttpClient(HttpClient):
    async def calc(self, payload: dict) -> dict:
        """POST v1/Customs с готовым телом (см. src/customs.py)."""
        session = await self._get_session()
        async with session.post("v1/Customs", json=payload) as response:
            response.raise_for_status()
            return await response.json()

    async def get_price(self, car: SCarAdd) -> dict:
        """Расчёт для машины из каталога — всегда как физлицо для себя (owner=1)."""
        if not car.engine_type:
            raise ValueError("engine_type is required for calcus")
        if not car.china_price:
            raise ValueError("china_price is required for calcus")

        engine_type = getattr(car.engine_type, "value", car.engine_type)
        if ENGINE_TYPE_CODES.get(str(engine_type)) in (1, 2):  # бензин / дизель
            power = car.horsepower or car.engine_power
            power_unit = 1
        else:
            power = (car.engine_power or 0) * 0.4
            power_unit = 2

        payload = build_customs_payload(
            price=car.china_price,
            engine_type=str(engine_type),
            power=power or 0,
            power_unit=power_unit,
            engine_volume=car.engine_volume,
            year=car.year,
            owner=OWNER_PERSONAL,
            curr="CNY",
            strict=False,
        )
        return await self.calc(payload)


async def _main():
    car = SCarAdd(
        brend="Audi",
        model="A3",
        year=2024,
        china_price=90000,
        engine_type="Бензиновый",
        engine_volume=1.4,
        horsepower=155,
        engine_power=100,
    )
    client = CALCUSHttpClient(
        base_url="https://calcus.ru/api/",
        api_client=settings.API_CLIENT_ID,
        api_key=settings.CALCUS_API_KEY,
    )
    try:
        print(await client.get_price(car))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(_main())