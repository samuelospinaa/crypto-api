import httpx
import os 
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("COINBASE_API")

async def get_coinbase_price(symbol: str) -> float:
    # Coinbase usa formato BTC-USD en lugar de BTCUSDT
    if symbol.endswith("USDT"):
        pair = symbol.replace("USDT", "-USD")
    else:
        pair = symbol

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/{pair}/spot")
        data = response.json()
        return float(data["data"]["amount"])
