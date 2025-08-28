from dataclasses import dataclass
from typing import Optional
import time
from ..config import HLConfig


@dataclass
class OrderRequest:
	"""Запрос на размещение ордера."""

	symbol: str
	side: str  # "SELL" для шорта, "BUY" для лонга
	quantity: float  # кол-во монет
	leverage: float = 1.0


@dataclass
class OrderResult:
	"""Результат размещения ордера (dry-run или реальный)."""

	success: bool
	order_id: Optional[str]
	message: str
	ts: float


class HyperliquidClient:
	"""Минималистичный клиент Hyperliquid. По умолчанию dry_run=True.

	В реальной интеграции потребуется REST/WS протокол HL,
	подпись запросов, маржинальные параметры и т.д.
	Здесь задача — изолировать слой размещения ордеров от стратегии.
	"""

	def __init__(self, config: Optional[HLConfig] = None) -> None:
		self._cfg = config or HLConfig()

	def _validate(self, req: OrderRequest) -> Optional[str]:
		if req.side not in ("SELL", "BUY"):
			return "side must be 'SELL' or 'BUY'"
		if req.quantity <= 0:
			return "quantity must be positive"
		if req.leverage <= 0:
			return "leverage must be positive"
		if not req.symbol or not isinstance(req.symbol, str):
			return "symbol must be a non-empty string"
		return None

	def place_order(self, req: OrderRequest) -> OrderResult:
		err = self._validate(req)
		if err:
			return OrderResult(success=False, order_id=None, message=err, ts=time.time())

		# Dry-run поведение: просто логируем и возвращаем фиктивный order_id
		if self._cfg.dry_run or not self._cfg.api_key or not self._cfg.api_secret:
			order_id = f"dry-{int(time.time()*1000)}"
			msg = f"DRY_RUN: placed {req.side} {req.quantity} {req.symbol} x{req.leverage}"
			return OrderResult(success=True, order_id=order_id, message=msg, ts=time.time())

		# Реальный вызов API HL должен быть здесь.
		# Для целей ТЗ оставим NotImplementedError, чтобы явно не отправлять сетью.
		raise NotImplementedError("Real Hyperliquid API integration is not implemented in this example")