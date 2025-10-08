import httpx

BASE_URL = "https://api.kucoin.com/api/v1/market/orderbook/level1"

async def get_kucoin_price(symbol: str) -> float:
    if symbol.endswith("USDT") and "-" not in symbol:
        symbol = symbol.replace("USDT", "-USDT")

    async with httpx.AsyncClient() as client:
        r = await client.get(BASE_URL, params={"symbol": symbol})
        data = r.json()
        try:
            return float(data["data"]["price"])
        except (KeyError, TypeError):
            return None
