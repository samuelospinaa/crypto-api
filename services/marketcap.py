import os 
from dotenv import load_dotenv
from cachetools import TTLCache
import httpx

load_dotenv()

CMC_API_KEY = os.getenv("MARKETCAP_APIKEY")
CMC_BASE = "https://pro-api.coinmarketcap.com/v2"
PAPRIKA_BASE = os.getenv("COINPAPRIKA_API")

client = httpx.AsyncClient(timeout=10.0)
price_cache = TTLCache(maxsize=2000, ttl=30)
id_cache = TTLCache(maxsize=2000, ttl=3600)

FIATS = {"usd", "eur", "mxn", "cop", "ars", "pen", "brl", "clp", "gbp", "jpy", "cad", "aud"}


async def _fetch_json(url, params=None, headers=None):
    try:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"⚠️ Error en fetch {url}: {e}")
        return None


async def get_coin_id(symbol: str):
    """Obtiene el ID de una moneda en CoinPaprika."""
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


async def convert_currency(from_symbol: str, to_symbol: str, amount: float, debug: bool = False):
    from_symbol = from_symbol.upper().strip()
    to_symbol = to_symbol.upper().strip()

    result_debug = {
        "from": from_symbol,
        "to": to_symbol,
        "amount": amount,
        "attempts": [],
        "fallback_used": False,
    }

    # 1️⃣ Intentar CoinMarketCap
    try:
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        params = {"amount": amount, "symbol": from_symbol, "convert": to_symbol}
        cmc_url = f"{CMC_BASE}/tools/price-conversion"

        cmc_data = await _fetch_json(cmc_url, params=params, headers=headers)
        result_debug["attempts"].append("coinmarketcap")

        if cmc_data and "data" in cmc_data:
            data = cmc_data["data"]

            # CoinMarketCap puede devolver un dict o una lista
            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            if isinstance(data, dict):
                quote = data.get("quote", {}).get(to_symbol)
                if quote:
                    price = quote["price"]
                    return {
                        "from": from_symbol,
                        "to": to_symbol,
                        "amount": amount,
                        "rate": price / amount,
                        "converted": price,
                        "source": "coinmarketcap",
                        "debug": result_debug if debug else None,
                    }
    except Exception as e:
        result_debug["cmc_error"] = str(e)

    # 2️⃣ Fallback a CoinPaprika
    result_debug["fallback_used"] = True
    result_debug["attempts"].append("coinpaprika")

    from_id = await get_coin_id(from_symbol)
    to_id = await get_coin_id(to_symbol)
    result_debug["from_id"] = from_id
    result_debug["to_id"] = to_id

    # Caso crypto → fiat
    if from_id and to_symbol.lower() in FIATS:
        data = await _fetch_json(f"{PAPRIKA_BASE}/tickers/{from_id}")
        if data and "quotes" in data and to_symbol.upper() in data["quotes"]:
            price = data["quotes"][to_symbol.upper()]["price"]
            converted = amount * price
            return {
                "from": from_symbol,
                "to": to_symbol,
                "amount": amount,
                "rate": price,
                "converted": converted,
                "source": "coinpaprika",
                "debug": result_debug if debug else None,
            }

    # Caso fiat → crypto
    if to_id and from_symbol.lower() in FIATS:
        data = await _fetch_json(f"{PAPRIKA_BASE}/tickers/{to_id}")
        if data and "quotes" in data and from_symbol.upper() in data["quotes"]:
            price = data["quotes"][from_symbol.upper()]["price"]
            rate = 1 / price
            converted = amount * rate
            return {
                "from": from_symbol,
                "to": to_symbol,
                "amount": amount,
                "rate": rate,
                "converted": converted,
                "source": "coinpaprika",
                "debug": result_debug if debug else None,
            }

    # Caso crypto → crypto
    if from_id and to_id:
        from_data = await _fetch_json(f"{PAPRIKA_BASE}/tickers/{from_id}")
        to_data = await _fetch_json(f"{PAPRIKA_BASE}/tickers/{to_id}")
        if from_data and to_data:
            usd_from = from_data["quotes"]["USD"]["price"]
            usd_to = to_data["quotes"]["USD"]["price"]
            rate = usd_from / usd_to
            converted = amount * rate
            return {
                "from": from_symbol,
                "to": to_symbol,
                "amount": amount,
                "rate": rate,
                "converted": converted,
                "source": "coinpaprika",
                "debug": result_debug if debug else None,
            }

    return {"error": "conversion_not_available", "debug": result_debug}