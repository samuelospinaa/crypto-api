import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BINANCE_API")

async def get_binance_price(symbol: str) -> float:
    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL, params={"symbol": symbol})
        data = response.json()
        return float(data["price"])
