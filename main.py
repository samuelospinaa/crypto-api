from fastapi import FastAPI
import os
import httpx
from dotenv import load_dotenv
from services.binance import get_binance_price
from services.coinbase import get_coinbase_price
from services.kraken import get_kraken_price
from services.kucoin import get_kucoin_price
from services.coingecko import convert_currency

load_dotenv()  # Cargar variables de entorno

COINGECKO_API = os.getenv("COINGECKO_API")
COINPAPRIKA_API = os.getenv("COINPAPRIKA_API")

app = FastAPI(
    title="Crypto Data API",
    description="API unificada para obtener precios de criptomonedas desde múltiples exchanges y convertir entre monedas.",
    version="2.0.0"
)

@app.get("/")
def root():
    return {
        "message": "🚀 Bienvenido a la Crypto Data API",
        "available_endpoints": [
            "/price/{symbol}?exchange=binance|coinbase|kraken|kucoin",
            "/convert?from_symbol=BTC&to_symbol=USD&amount=1"
        ]
    }

@app.get("/price/{symbol}")
async def get_price(symbol: str, exchange: str = "binance"):
    """
    Devuelve el precio actual de una criptomoneda desde el exchange seleccionado.
    - **symbol**: ejemplo BTCUSDT, ETHUSDT, ADAUSDT, etc.
    - **exchange**: binance, coinbase, kraken, kucoin
    """
    symbol = symbol.upper()

    if exchange == "binance":
        price = await get_binance_price(symbol)
    elif exchange == "coinbase":
        price = await get_coinbase_price(symbol)
    elif exchange == "kraken":
        price = await get_kraken_price(symbol)
    elif exchange == "kucoin":
        price = await get_kucoin_price(symbol)
    else:
        return {"error": "Exchange no soportado."}

    if price is None:
        return {"error": f"No se pudo obtener el precio de {symbol} en {exchange}."}

    return {"symbol": symbol, "exchange": exchange, "price": price}


@app.get("/convert")
async def convert(from_symbol: str, to_symbol: str, amount: float = 1.0, debug: bool = False):
    result = await convert_currency(from_symbol, to_symbol, amount, debug)
    if result is None:
        return {"error": "Conversion no disponible"}
    return result
