import asyncio

from aiohttp import ClientSession

from src.schemas import SCarAdd
from datetime import datetime


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
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


class CALCUSHttpClient(HttpClient):
    async def get_price(self, car: SCarAdd) -> dict:

        age_ = datetime.now().year - car.year_built
        if 0< age_ < 3:
            age = "0-3"
        elif 3 <= age_ < 5:
            age = "3-5"
        elif 5 <= age_ < 7:
            age = "5-7"
        elif 7 <= age_:
            age = "7-0"
        else:
            age = "0-3"

        engine_types = {
            "Бензиновый": 1,
            "Дизельный": 2,
            "Электрический": 4,
            "Последовательный гибрид": 5,
            "Параллельный гибрид": 6,
        }

        if engine_types[car.engine_type] == 1 or engine_types[car.engine_type] == 2:
            power = car.horsepower
            power_unit = 1
        else:
            power = car.engine_power * 0.4
            power_unit = 2

        value = car.engine_volume * 1000

        session = await self._get_session()
        async with session.post(
                "https://calcus.ru/api/v1/Customs",
            json={"owner": 1,
                    "age": str(age),
                    "engine": int(engine_types[car.engine_type]),
                    "power": int(power),
                    "power_unit": int(power_unit),
                    "value": int(value),
                    "price": int(car.china_price),
                    "curr": "CNY",
                    "year": datetime.now().year,
                    "usd_rate": 0,
                    "eur_rate": 0,
                    "cny_rate": 0,
                    "jpy_rate": 0,
                    "krw_rate": 0
                    }
        ) as response:
            print(response.status)
            print(
                str(age),
                int(engine_types[car.engine_type]),
                power,
                power_unit,
                value,
                car.china_price,
            )
            result = await response.json()
            return result


async def main():
    car_repo = SCarAdd(
        name="a3",
        mark="Audi",
        year_built=2024,
        description=None,
        china_price=90000,
        engine_type="Бензиновый",
        engine_volume=1.4,
        horsepower=155,
        engine_power=100
    )
    client = CALCUSHttpClient(
        base_url="https://calcus.ru/api/",
        api_client="47147",
        api_key="09a98cb556d30a95",
    )
    try:
        result = await client.get_price(car_repo)
        print(result)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())