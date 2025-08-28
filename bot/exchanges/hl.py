from dataclasses import dataclass
from typing import Optional
import time
import hmac
import hashlib
import requests

from ..config import HLConfig


@dataclass
class OrderRequest:
	"""Запрос на размещение ордера."""

	symbol: str
	side: str  # "SELL" для шорта, "BUY" для лонга
	quantity: float  # кол-во монет
	leverage: float = 1.0
	price: Optional[float] = None  # при необходимости лимитная цена


@dataclass
class OrderResult:
	"""Результат размещения ордера (dry-run или реальный)."""

	success: bool
	order_id: Optional[str]
	message: str
	ts: float


class HyperliquidClient:
	"""Минималистичный клиент Hyperliquid. По умолчанию dry_run=True.

	В реальной интеграции потребуется проверить актуальную спецификацию HL API.
	Ниже приведены REST-заготовки (эндпоинты/хедеры могут отличаться). Используйте только после сверки с документацией HL.
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

	def _sign(self, payload: dict) -> dict:
		assert self._cfg.api_secret is not None
		msg = str(payload).encode()
		sig = hmac.new(self._cfg.api_secret.encode(), msg, hashlib.sha256).hexdigest()
		return {
			"X-HL-APIKEY": self._cfg.api_key or "",
			"X-HL-SIGNATURE": sig,
		}

	def place_order(self, req: OrderRequest) -> OrderResult:
		err = self._validate(req)
		if err:
			return OrderResult(success=False, order_id=None, message=err, ts=time.time())

		if self._cfg.dry_run or not self._cfg.api_key or not self._cfg.api_secret:
			order_id = f"dry-{int(time.time()*1000)}"
			msg = f"DRY_RUN: placed {req.side} {req.quantity} {req.symbol} x{req.leverage} price={req.price}"
			return OrderResult(success=True, order_id=order_id, message=msg, ts=time.time())

		# ВНИМАНИЕ: Ниже — пример. Убедитесь в правильных эндпоинтах/параметрах в официальной доке HL.
		endpoint = "/v1/order"
		url = f"{self._cfg.base_url}{endpoint}"
		ts_ms = int(time.time() * 1000)
		payload = {
			"symbol": req.symbol,
			"side": req.side,
			"type": "MARKET" if req.price is None else "LIMIT",
			"quantity": req.quantity,
			"price": req.price,
			"leverage": req.leverage,
			"timestamp": ts_ms,
		}
		headers = self._sign(payload)
		resp = requests.post(url, json=payload, headers=headers, timeout=10)
		resp.raise_for_status()
		data = resp.json()
		order_id = str(data.get("orderId") or data.get("id") or "")
		return OrderResult(success=True, order_id=order_id, message=str(data), ts=time.time())

	def close_position(self, symbol: str, quantity: float, side: str) -> OrderResult:
		# Для шорта закрытие — это покупка BUY, для лонга — продажа SELL
		close_side = "BUY" if side == "SELL" else "SELL"
		return self.place_order(OrderRequest(symbol=symbol, side=close_side, quantity=quantity, leverage=1.0))

	def get_balance(self) -> Optional[dict]:
		if self._cfg.dry_run or not self._cfg.api_key or not self._cfg.api_secret:
			# Возврат фиктивного баланса для отображения
			return {"equity": 10000.0, "available": 9500.0, "currency": "USD"}
			
		endpoint = "/v1/account/balance"
		url = f"{self._cfg.base_url}{endpoint}"
		ts_ms = int(time.time() * 1000)
		payload = {"timestamp": ts_ms}
		headers = self._sign(payload)
		resp = requests.get(url, headers=headers, timeout=10)
		resp.raise_for_status()
		return resp.json()