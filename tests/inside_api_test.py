import requests

r = requests.post(
    "https://calcus.ru/api/v1/Customs",
    headers={
        "Api-Client-Id": "47147",
        "Api-Key": "09a98cb556d30a95",
    },
    json={
  "owner": 1,
  "age": "0-3",
  "engine": 1,
  "power": 150,
  "power_unit": 1,
  "value": 2000,
  "price": 5000000,
  "curr": "RUB",
  "year": 0,
  "usd_rate": 0,
  "eur_rate": 0,
  "cny_rate": 0,
  "jpy_rate": 0,
  "krw_rate": 0
}
)
print(r.json())
print("URL     :", r.url)
print("STATUS  :", r.status_code)
print("HEADERS :", dict(r.headers))
print("BODY    :", r.text[:2000])