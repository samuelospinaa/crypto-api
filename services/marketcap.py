import os 
from dotenv import load_dotenv
from cachetools import TTLCache
import httpx

load_dotenv()

CMC_API_KEY = os.getenv("MARKETCAP_APIKEY")
CMC_BASE = "https://pro-api.coinmarketcap.com/v2"
PAPRIKA_BASE = os.getenv("COINPAPRIKA_API")

# Cliente HTTP reutilizable
client = httpx.AsyncClient(timeout=10.0)

# Cache para reducir llamadas repetidas
price_cache = TTLCache(maxsize=2000, ttl=30)
id_cache = TTLCache(maxsize=2000, ttl=3600)

# Lista de monedas fiat comunes
FIATS = {"usd", "eur", "mxn", "cop", "ars", "pen", "brl", "clp", "gbp", "jpy", "cad", "aud"}


# ---------------------- 🔹 Funciones auxiliares ----------------------

async def _fetch_json(url, params=None, headers=None):
    """Llamada HTTP segura."""
    try:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


async def get_coin_id(symbol: str):
    """Busca el ID de una criptomoneda en CoinPaprika (fallback)."""
    s = symbol.lower()
    if s in id_cache:
        return id_cache[s]

    data = await _fetch_json(f"{PAPRIKA_BASE}/coins")
    if not data:
        return None

    for coin in data:
        if coin.get("symbol", "").lower() == s:
            cid = coin.get("id")
            id_cache[s] = cid
            return cid
    return None


# ---------------------- 🔹 Función principal ----------------------

async def convert_currency(from_symbol: str, to_symbol: str, amount: float, debug: bool = False):
    """
    Conversión robusta:
    - Intenta con CoinMarketCap (v2/tools/price-conversion)
    - Si falla, usa CoinPaprika (crypto->crypto o crypto->fiat vía USD)
    """
    from_symbol = from_symbol.upper().strip()
    to_symbol = to_symbol.upper().strip()
    result_debug = {
        "from": from_symbol,
        "to": to_symbol,
        "amount": amount,
        "attempts": [],
        "fallback_used": False
    }

    # ----------------- 1️⃣ Intentar con CoinMarketCap -----------------
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"amount": amount, "symbol": from_symbol, "convert": to_symbol}
    cmc_url = f"{CMC_BASE}/tools/price-conversion"

    cmc_data = await _fetch_json(cmc_url, params=params, headers=headers)
    result_debug["attempts"].append("coinmarketcap")

    if cmc_data and "data" in cmc_data:
        try:
            data = cmc_data["data"]
            price = data["quote"][to_symbol]["price"]
            out = {
                "from": from_symbol,
                "to": to_symbol,
                "amount": amount,
                "rate": price / amount,
                "converted": price,
            }
            if debug:
                out["debug"] = result_debug
            return out
        except Exception:
            result_debug["error_cmc"] = "Unexpected CMC response structure"

    # ----------------- 2️⃣ Fallback: CoinPaprika -----------------
    result_debug["fallback_used"] = True
    result_debug["attempts"].append("coinpaprika")

    from_id = await get_coin_id(from_symbol)
    to_id = await get_coin_id(to_symbol)
    result_debug["from_id"] = from_id
    result_debug["to_id"] = to_id

    if not from_id and not to_id:
        return {"error": "conversion_not_available", "debug": result_debug}

    # Caso crypto -> fiat
    if from_id and to_symbol.lower() in FIATS:
        data = await _fetch_json(f"{PAPRIKA_BASE}/tickers/{from_id}")
        if data and "quotes" in data and to_symbol in data["quotes"]:
            price = data["quotes"][to_symbol]["price"]
            converted = amount * price
            out = {
                "from": from_symbol,
                "to": to_symbol,
                "amount": amount,
                "rate": price,
                "converted": converted
            }
            if debug:
                out["debug"] = result_debug
            return out

    # Caso crypto -> crypto (vía USD)
    if from_id and to_id:
        from_data = await _fetch_json(f"{PAPRIKA_BASE}/tickers/{from_id}")
        to_data = await _fetch_json(f"{PAPRIKA_BASE}/tickers/{to_id}")

        if from_data and to_data:
            usd_from = from_data["quotes"]["USD"]["price"]
            usd_to = to_data["quotes"]["USD"]["price"]
            rate = usd_from / usd_to
            converted = amount * rate
            out = {
                "from": from_symbol,
                "to": to_symbol,
                "amount": amount,
                "rate": rate,
                "converted": converted
            }
            if debug:
                out["debug"] = result_debug
            return out

    return {"error": "conversion_not_available", "debug": result_debug}
