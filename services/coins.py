from cachetools import TTLCache
import httpx

cache = TTLCache(maxsize=1, ttl=3600)  # 1 hour cache
COINPAPRIKA_BASE = "https://api.coinpaprika.com/v1"

cache = TTLCache(maxsize=1, ttl=3600)  # 1 hour cache

async def get_coins():
    """Obtiene la lista de monedas desde CoinPaprika."""
    try:
        url = f"{COINPAPRIKA_BASE}/coins"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            # Solo devolver monedas activas (filtramos tokens inactivos)
            active_coins = [
                {
                    "id": coin.get("id"),
                    "name": coin.get("name"),
                    "symbol": coin.get("symbol"),
                    "is_active": coin.get("is_active", False),
                    "type": coin.get("type"),
                }
                for coin in data if coin.get("is_active")
            ]
            return active_coins
    except Exception as e:
        print(f"⚠️ Error al obtener la lista de monedas: {e}")
        return []
