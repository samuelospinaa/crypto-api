import httpx

BASE_URL = "https://api.binance.com/api/v3/ticker/price"

async def get_binance_price(symbol: str) -> float:
    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL, params={"symbol": symbol})
        data = response.json()
        return float(data["price"])
