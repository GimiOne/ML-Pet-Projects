from dataclasses import dataclass
from typing import Optional, Any
import time

from eth_account import Account
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL

from bot.config import HLConfig


@dataclass
class OrderRequest:
	"""Запрос на размещение ордера."""

	symbol: str  # e.g. "ETH" (coin name) per SDK naming
	side: str  # "SELL" для шорта, "BUY" для лонга
	quantity: float  # кол-во монет
	leverage: float = 1.0
	price: Optional[float] = None  # лимитная цена; если None — используем market_open


@dataclass
class OrderResult:
	"""Результат размещения ордера (dry-run или реальный)."""

	success: bool
	order_id: Optional[str]
	message: str
	ts: float


class HyperliquidClient:
	"""Клиент Hyperliquid на базе официального hyperliquid-python-sdk.

	- Для реальной работы требуется приватный ключ (EVM) для LocalAccount.
	- В этом примере используем упрощение: HLConfig.api_key хранит адрес, api_secret — приватный ключ (hex).
	- По умолчанию dry_run=True: действия не отправляются, а имитируются.
	"""

	def __init__(self, config: Optional[HLConfig] = None, use_testnet: bool = False) -> None:
		self._cfg = config or HLConfig()
		self._base_url = TESTNET_API_URL if use_testnet else MAINNET_API_URL
		self._info: Optional[Info] = None
		self._ex: Optional[Exchange] = None

		if not self._cfg.dry_run and self._cfg.api_secret:
			wallet: LocalAccount = Account.from_key(self._cfg.api_secret)
			self._ex = Exchange(wallet=wallet, base_url=self._base_url)
			self._info = self._ex.info
		else:
			# Для dry-run достаточно Info для получения mid и user_state (если адрес задан)
			self._info = Info(base_url=self._base_url, skip_ws=True)

	def _coin_from_symbol(self, symbol: str) -> str:
		# SDK использует coin name, например "ETH" вместо "ETHUSDT".
		# Простейшее преобразование: обрезать суффикс USDT/USDC при наличии.
		if symbol.endswith("USDT"):
			return symbol[:-4]
		if symbol.endswith("USDC"):
			return symbol[:-4]
		return symbol

	def place_order(self, req: OrderRequest) -> OrderResult:
		if self._cfg.dry_run or not self._ex:
			order_id = f"dry-{int(time.time()*1000)}"
			msg = f"DRY_RUN: {req.side} {req.quantity} {req.symbol} price={req.price}"
			return OrderResult(True, order_id, msg, time.time())

		coin = self._coin_from_symbol(req.symbol)
		is_buy = True if req.side.upper() == "BUY" else False
		try:
			if req.price is None:
				# Рыночная через market_open (агрессивный лимит Ioc)
				resp: Any = self._ex.market_open(name=coin, is_buy=is_buy, sz=req.quantity)
			else:
				# Лимитный GTC
				resp: Any = self._ex.order(name=coin, is_buy=is_buy, sz=req.quantity, limit_px=req.price, order_type={"limit": {"tif": "Gtc"}})
			repr_id = str(resp)
			return OrderResult(True, repr_id, str(resp), time.time())
		except Exception as e:
			return OrderResult(False, None, f"error: {e}", time.time())

	def place_trigger_exit(self, symbol: str, quantity: float, trigger_px: float, tpsl: str) -> OrderResult:
		"""Установить стоп/профит-триггер (reduce-only) для закрытия позиции по рынку.

		- Для шорта используйте tpsl='sl' (рост цены) и tpsl='tp' (падение цены), is_buy=True.
		"""
		if tpsl not in ("sl", "tp"):
			return OrderResult(False, None, "tpsl must be 'sl' or 'tp'", time.time())
		if self._cfg.dry_run or not self._ex:
			order_id = f"dry-{int(time.time()*1000)}"
			msg = f"DRY_RUN: trigger {tpsl} {symbol} qty={quantity} triggerPx={trigger_px}"
			return OrderResult(True, order_id, msg, time.time())
		coin = self._coin_from_symbol(symbol)
		try:
			resp: Any = self._ex.order(
				name=coin,
				is_buy=True,  # закрываем шорт
				sz=quantity,
				limit_px=trigger_px,  # для isMarket=True safe fallback
				order_type={
					"trigger": {
						"isMarket": True,
						"triggerPx": trigger_px,
						"tpsl": tpsl,
					}
				},
				reduce_only=True,
			)
			return OrderResult(True, str(resp), str(resp), time.time())
		except Exception as e:
			return OrderResult(False, None, f"error: {e}", time.time())

	def close_position(self, symbol: str, quantity: float, side: str) -> OrderResult:
		if self._cfg.dry_run or not self._ex:
			order_id = f"dry-{int(time.time()*1000)}"
			msg = f"DRY_RUN: close {symbol} qty={quantity} from side={side}"
			return OrderResult(True, order_id, msg, time.time())
		coin = self._coin_from_symbol(symbol)
		try:
			resp = self._ex.market_close(coin=coin, sz=quantity)
			return OrderResult(True, str(resp), str(resp), time.time())
		except Exception as e:
			return OrderResult(False, None, f"error: {e}", time.time())

	def get_balance(self) -> Optional[dict]:
		try:
			if self._cfg.dry_run or not self._ex:
				return {"note": "dry_run", "equity": None, "available": None}
			address = self._ex.wallet.address if self._ex else None
			if not address:
				return None
			state = self._ex.info.user_state(address)
			ms = state.get("marginSummary") or {}
			return {
				"accountValue": float(ms.get("accountValue")) if ms.get("accountValue") is not None else None,
				"totalNtlPos": float(ms.get("totalNtlPos")) if ms.get("totalNtlPos") is not None else None,
				"withdrawable": float(state.get("withdrawable")) if state.get("withdrawable") is not None else None,
			}
		except Exception:
			return None