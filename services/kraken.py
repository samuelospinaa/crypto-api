import httpx

BASE_URL = "https://api.kraken.com/0/public/Ticker"

async def get_kraken_price(symbol: str) -> float:
    # Kraken usa formato diferente: BTCUSDT → XBTUSDT
    if symbol.startswith("BTC"):
        symbol = "X" + symbol[0:3] + symbol[3:]
    async with httpx.AsyncClient() as client:
        r = await client.get(BASE_URL, params={"pair": symbol})
        data = r.json()
        try:
            key = list(data["result"].keys())[0]
            return float(data["result"][key]["c"][0])
        except (KeyError, IndexError):
            return None
