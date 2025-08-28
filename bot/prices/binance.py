import requests
import time
from typing import Optional
from bot.prices.base import PriceProvider, PriceTick


class BinancePriceProvider(PriceProvider):
	"""Простой REST-провайдер цен с Binance (public endpoint)."""

	def __init__(self, base_url: str = "https://api.binance.com") -> None:
		self.base_url = base_url.rstrip("/")

	def get_price(self, symbol: str) -> PriceTick:
		# Binance использует, например, BTCUSDT
		url = f"{self.base_url}/api/v3/ticker/price"
		params = {"symbol": symbol}
		resp = requests.get(url, params=params, timeout=5)
		resp.raise_for_status()
		data = resp.json()
		price = float(data["price"])  # {'symbol': 'BTCUSDT', 'price': '68000.00'}
		return PriceTick(symbol=symbol, price=price, ts=time.time())