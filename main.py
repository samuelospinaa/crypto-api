from fastapi import FastAPI
from services.binance import get_binance_price
from services.coinbase import get_coinbase_price
from services.kraken import get_kraken_price
from services.kucoin import get_kucoin_price
from services.coingecko import convert_currency

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
            "/convert?from=BTC&to=USD&amount=1"
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
async def convert(from_symbol: str, to_symbol: str, amount: float = 1):
    """
    Convierte un monto de una moneda (cripto o fiat) a otra usando CoinGecko.
    - **from_symbol**: ejemplo BTC o USD
    - **to_symbol**: ejemplo ETH o EUR
    - **amount**: cantidad a convertir
    """
    result = await convert_currency(from_symbol.upper(), to_symbol.upper(), amount)
    if result is None:
        return {"error": "Conversión no disponible."}
    return result
