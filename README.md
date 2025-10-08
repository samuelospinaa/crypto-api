# Crypto Converter API

API que permite obtener precios y conversiones entre criptomonedas y monedas fiat, usando datos los exhange mas usados.

## Funcionalidades

- Precio en tiempo real de los exchange mas usados
- Conversión cripto ↔ cripto
- Conversión cripto ↔ fiat (USD, COP, EUR, MXN, etc.)
- Cache para respuestas rápidas
- Integración con APIs públicas

## Stack

- Python 3.11+
- FastAPI
- httpx
- cachetools

## Ejecución local

```bash
uvicorn main:app --reload
```
