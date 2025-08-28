from abc import ABC, abstractmethod
from typing import Optional
import time


class PriceTick:
	"""Единичный тик цены: символ, цена, timestamp (секунды)."""

	def __init__(self, symbol: str, price: float, ts: Optional[float] = None) -> None:
		self.symbol = symbol
		self.price = float(price)
		self.ts = float(ts if ts is not None else time.time())

	def __repr__(self) -> str:
		return f"PriceTick(symbol={self.symbol!r}, price={self.price}, ts={self.ts})"


class PriceProvider(ABC):
	"""Базовый интерфейс поставщика цен."""

	@abstractmethod
	def get_price(self, symbol: str) -> PriceTick:
		"""Вернуть свежий тик цены для указанного символа."""
		raise NotImplementedError