from typing import Optional
import time
from .base import PriceProvider, PriceTick


class ManualPriceProvider(PriceProvider):
	"""Ручной провайдер: позволяет задать и обновлять цену для символа."""

	def __init__(self, initial_prices: Optional[dict[str, float]] = None) -> None:
		self._prices: dict[str, float] = dict(initial_prices or {})

	def set_price(self, symbol: str, price: float) -> None:
		self._prices[symbol] = float(price)

	def get_price(self, symbol: str) -> PriceTick:
		if symbol not in self._prices:
			raise KeyError(f"Price for symbol {symbol} is not set in ManualPriceProvider")
		return PriceTick(symbol=symbol, price=self._prices[symbol], ts=time.time())