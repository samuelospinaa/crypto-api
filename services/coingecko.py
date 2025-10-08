# services/coingecko.py
import httpx
from cachetools import TTLCache
import asyncio

BASE_URL = "https://api.coingecko.com/api/v3"
# Cliente reutilizable con timeout razonable
client = httpx.AsyncClient(timeout=10.0)

# Cache: símbolo -> coin_id
coin_id_cache = TTLCache(maxsize=10000, ttl=3600)  # 1 hora
# Cache: simple/price responses (por ids+vs_currencies)
price_cache = TTLCache(maxsize=2000, ttl=20)  # 20s, evita demasiadas requests

# Conjunto de fiats comunes (expandir si quieres)
FIATS = {
    "usd", "eur", "mxn", "cop", "ars", "pen", "brl", "clp", "gbp", "jpy", "cad", "aud"
}


async def _fetch_json(url: str, params: dict):
    """Helper para llamadas HTTP seguras."""
    try:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


async def get_coin_id(symbol: str):
    """
    Resuelve SYMBOL -> CoinGecko ID (ej: BTC -> bitcoin).
    Usa /search primero (rápido), luego fallback a /coins/list.
    """
    if not symbol:
        return None
    s = symbol.lower()
    if s in coin_id_cache:
        return coin_id_cache[s]

    # 1) Try the /search endpoint (preferido)
    search = await _fetch_json(f"{BASE_URL}/search", {"query": s})
    if search and isinstance(search, dict):
        coins = search.get("coins", [])
        # Buscar coincidencia exacta por symbol (y preferir coin con mejor market_cap_rank)
        best = None
        best_rank = None
        for c in coins:
            # c keys: id, name, api_symbol, symbol, market_cap_rank (si existe)
            if c.get("symbol", "").lower() == s:
                rank = c.get("market_cap_rank")
                if rank is None:
                    best = c
                    break
                if best is None or (best_rank is None or rank < best_rank):
                    best = c
                    best_rank = rank
        if best is None and coins:
            best = coins[0]
        if best:
            cid = best.get("id")
            if cid:
                coin_id_cache[s] = cid
                return cid

    # 2) Fallback: descargar /coins/list (más pesado)
    lst = await _fetch_json(f"{BASE_URL}/coins/list", {})
    if lst and isinstance(lst, list):
        for c in lst:
            if c.get("symbol", "").lower() == s:
                cid = c.get("id")
                coin_id_cache[s] = cid
                return cid

    # No encontrado
    return None


async def _simple_price(ids: str, vs: str):
    """
    Llamada a /simple/price con caching.
    ids: comma-separated coin ids (ej: 'bitcoin,ethereum')
    vs: comma-separated vs_currencies (ej: 'usd' o 'usd,eur')
    """
    key = f"{ids}|{vs}"
    if key in price_cache:
        return price_cache[key]
    params = {"ids": ids, "vs_currencies": vs}
    data = await _fetch_json(f"{BASE_URL}/simple/price", params)
    if data is not None:
        price_cache[key] = data
    return data


async def convert_currency(from_symbol: str, to_symbol: str, amount: float, debug: bool = False):
    """
    Convertidor robusto:
    - Soporta: crypto->fiat, fiat->crypto, crypto->crypto (usa USD como intermediario).
    - Requiere al menos uno de los símbolos sea cripto.
    - Si debug=True devuelve info intermedia para diagnóstico.
    """
    if amount is None:
        return None

    f = from_symbol.strip().lower()
    t = to_symbol.strip().lower()

    # Detectar si son fiats simples
    from_is_fiat = f in FIATS
    to_is_fiat = t in FIATS

    result_debug = {
        "from": from_symbol,
        "to": to_symbol,
        "amount": amount,
        "from_is_fiat": from_is_fiat,
        "to_is_fiat": to_is_fiat,
        "notes": []
    }

    # Si ambos son fiat, no soportado aquí (podemos agregar after)
    if from_is_fiat and to_is_fiat:
        result_debug["notes"].append("Both sides are fiat - fiat->fiat not supported by this endpoint.")
        return (None if not debug else {"error": "fiat->fiat not supported", "debug": result_debug})

    # Resolver ids para lados cripto
    from_id = None
    to_id = None
    if not from_is_fiat:
        from_id = await get_coin_id(f)
        result_debug["from_id"] = from_id
        if not from_id:
            result_debug["notes"].append(f"Could not resolve coin id for '{from_symbol}'")
    if not to_is_fiat:
        to_id = await get_coin_id(t)
        result_debug["to_id"] = to_id
        if not to_id:
            result_debug["notes"].append(f"Could not resolve coin id for '{to_symbol}'")

    # Caso: crypto -> crypto
    if (not from_is_fiat) and (not to_is_fiat):
        if not from_id or not to_id:
            return (None if not debug else {"error": "missing_ids", "debug": result_debug})

        # Pedimos ambos precios en USD y hacemos ratio (más robusto)
        ids = f"{from_id},{to_id}"
        data = await _simple_price(ids=ids, vs="usd")
        result_debug["coin_usd_raw"] = data
        if not data or from_id not in data or to_id not in data:
            return (None if not debug else {"error": "no_price_usd", "debug": result_debug})

        price_from_usd = data[from_id].get("usd")
        price_to_usd = data[to_id].get("usd")
        if not price_from_usd or not price_to_usd:
            return (None if not debug else {"error": "missing_usd_prices", "debug": result_debug})

        rate = price_from_usd / price_to_usd
        converted = amount * rate

        out = {"from": from_symbol.upper(), "to": to_symbol.upper(), "amount": amount, "rate": rate, "converted": converted}
        if debug:
            out["debug"] = result_debug
        return out

    # Caso: crypto -> fiat (ej BTC -> COP)
    if (not from_is_fiat) and to_is_fiat:
        if not from_id:
            return (None if not debug else {"error": "missing_from_id", "debug": result_debug})

        data = await _simple_price(ids=from_id, vs=t)
        result_debug["raw"] = data
        if not data or from_id not in data or t not in data[from_id]:
            return (None if not debug else {"error": "no_rate_crypto_to_fiat", "debug": result_debug})

        rate = data[from_id][t]  # price of 1 from_symbol in to fiat
        converted = amount * rate
        out = {"from": from_symbol.upper(), "to": to_symbol.upper(), "amount": amount, "rate": rate, "converted": converted}
        if debug:
            out["debug"] = result_debug
        return out

    # Caso: fiat -> crypto (ej USD -> BTC) -> necesitamos precio del crypto en fiat y dividir
    if from_is_fiat and (not to_is_fiat):
        if not to_id:
            return (None if not debug else {"error": "missing_to_id", "debug": result_debug})

        data = await _simple_price(ids=to_id, vs=f)
        result_debug["raw"] = data
        if not data or to_id not in data or f not in data[to_id]:
            return (None if not debug else {"error": "no_rate_fiat_to_crypto", "debug": result_debug})

        price_one_coin_in_fiat = data[to_id][f]  # e.g. 1 BTC = 50000 USD
        if price_one_coin_in_fiat == 0:
            return (None if not debug else {"error": "zero_price", "debug": result_debug})

        converted = amount / price_one_coin_in_fiat
        rate = 1 / price_one_coin_in_fiat  # units of crypto per 1 fiat
        out = {"from": from_symbol.upper(), "to": to_symbol.upper(), "amount": amount, "rate": rate, "converted": converted}
        if debug:
            out["debug"] = result_debug
        return out

    # Fallback inseguro
    return (None if not debug else {"error": "unsupported_case", "debug": result_debug})
