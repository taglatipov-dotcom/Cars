import asyncio
from datetime import datetime

from aiohttp import ClientSession, ClientTimeout

from src.config import settings
from src.schemas import SCarAdd

ENGINE_TYPE_CODES = {
    "Бензиновый": 1,
    "Дизельный": 2,
    "Электрический": 4,
    "Последовательный гибрид": 5,
    "Параллельный гибрид": 6,
}


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
    @staticmethod
    def _resolve_age(year: int | None) -> str:
        if not year:
            return "0-3"
        age = datetime.now().year - year
        if 0 < age < 3:
            return "0-3"
        if age < 5:
            return "3-5"
        if age < 7:
            return "5-7"
        return "7-0"

    async def get_price(self, car: SCarAdd) -> dict:
        if not car.engine_type:
            raise ValueError("engine_type is required for calcus")
        if not car.china_price:
            raise ValueError("china_price is required for calcus")

        engine_code = ENGINE_TYPE_CODES.get(str(car.engine_type))
        if engine_code is None:
            raise ValueError(f"Unsupported engine_type: {car.engine_type}")

        if engine_code in (1, 2):  # бензин / дизель
            power = car.horsepower or car.engine_power
            power_unit = 1
        else:
            power = (car.engine_power or 0) * 0.4
            power_unit = 2

        value = int((car.engine_volume or 0) * 1000)

        session = await self._get_session()
        async with session.post(
            "v1/Customs",
            json={
                "owner": 1,
                "age": self._resolve_age(car.year),
                "engine": engine_code,
                "power": int(power or 0),
                "power_unit": power_unit,
                "value": value,
                "price": int(car.china_price),
                "curr": "CNY",
                "year": datetime.now().year,
                "usd_rate": 0,
                "eur_rate": 0,
                "cny_rate": 0,
                "jpy_rate": 0,
                "krw_rate": 0,
            },
        ) as response:
            response.raise_for_status()
            return await response.json()


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