import os 
import httpx
from dotenv import load_dotenv

load_dotenv()

CMC_BASE = "https://pro-api.coinmarketcap.com/v2"
CMC_API_KEY = os.getenv("MARKETCAP_APIKEY")

async def get_coins():
    """Obtiene la lista de monedas disponibles en CoinMarketCap."""
    url = f"{CMC_BASE}/cryptocurrency/map"
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
    except Exception as e:
        print(f"⚠️ Error al obtener las monedas: {e}")
        return []