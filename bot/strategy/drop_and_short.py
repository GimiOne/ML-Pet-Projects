from collections import deque
from dataclasses import dataclass
from typing import Deque, Tuple, Optional
import time

from ..config import StrategyConfig
from ..prices.base import PriceProvider, PriceTick
from ..exchanges.hl import HyperliquidClient, OrderRequest, OrderResult


@dataclass
class StrategyState:
	"""Состояние стратегии: история цен, последний вход, флаг активного окна входа."""

	last_entry_ts: Optional[float] = None
	first_trigger_ts: Optional[float] = None


class DropShortStrategy:
	"""Стратегия: когда BTC падает от локального максимума более заданного процента,
	входим в шорт по выбранной альте в окне входа (обычно первые ~10 минут сильнее).
	"""

	def __init__(
		self,
		cfg: StrategyConfig,
		price_provider: PriceProvider,
		exchange: HyperliquidClient,
		max_history_seconds: Optional[int] = None,
	) -> None:
		self.cfg = cfg
		self.price_provider = price_provider
		self.exchange = exchange
		self.state = StrategyState()
		self._btc_history: Deque[Tuple[float, float]] = deque()  # (ts, price)
		self._alt_history: Deque[Tuple[float, float]] = deque()
		self._max_hist = max_history_seconds or max(cfg.lookback_seconds * 2, 1200)

	def _append_history(self, symbol: str, price: float, ts: float) -> None:
		target = self._btc_history if symbol == self.cfg.btc_symbol else self._alt_history
		target.append((ts, price))
		cutoff = ts - self._max_hist
		while target and target[0][0] < cutoff:
			target.popleft()

	def _calc_btc_drawdown_pct(self, now_ts: float) -> Optional[float]:
		# Находим локальный максимум за lookback_seconds, затем считаем падение относительно цены сейчас
		lookback_cutoff = now_ts - self.cfg.lookback_seconds
		relevant = [p for (ts, p) in self._btc_history if ts >= lookback_cutoff]
		if not relevant:
			return None
		local_max = max(relevant)
		current = self._btc_history[-1][1] if self._btc_history else None
		if current is None or local_max <= 0:
			return None
		drawdown_pct = (local_max - current) / local_max * 100.0
		return drawdown_pct

	def _cooldown_active(self, now_ts: float) -> bool:
		if self.state.last_entry_ts is None:
			return False
		return (now_ts - self.state.last_entry_ts) < self.cfg.cooldown_seconds

	def _entry_window_active(self, now_ts: float) -> bool:
		if self.state.first_trigger_ts is None:
			return False
		return (now_ts - self.state.first_trigger_ts) <= self.cfg.entry_window_seconds

	def _maybe_mark_first_trigger(self, now_ts: float) -> None:
		if self.state.first_trigger_ts is None:
			self.state.first_trigger_ts = now_ts

	def _reset_trigger_if_window_passed(self, now_ts: float) -> None:
		if self.state.first_trigger_ts is not None and not self._entry_window_active(now_ts):
			self.state.first_trigger_ts = None

	def on_tick(self) -> Optional[OrderResult]:
		"""Основной шаг стратегии. Возвращает результат ордера, если был вход."""
		now_ts = time.time()

		# Считываем цены
		btc = self.price_provider.get_price(self.cfg.btc_symbol)
		alt = self.price_provider.get_price(self.cfg.alt_symbol)

		# Проверка типов и значений
		if not isinstance(btc, PriceTick) or not isinstance(alt, PriceTick):
			raise TypeError("Price provider must return PriceTick instances")
		if btc.price <= 0 or alt.price <= 0:
			raise ValueError("Received non-positive price from provider")

		# Обновляем историю
		self._append_history(btc.symbol, btc.price, btc.ts)
		self._append_history(alt.symbol, alt.price, alt.ts)

		# Обслуживаем окно входа
		self._reset_trigger_if_window_passed(now_ts)

		# Детект падения BTC
		drawdown_pct = self._calc_btc_drawdown_pct(now_ts)
		if self.cfg.verbose:
			print(f"BTC drawdown: {drawdown_pct:.4f}% (threshold {self.cfg.drop_pct_threshold}%)") if drawdown_pct is not None else print("BTC drawdown: n/a")

		if drawdown_pct is None:
			return None

		if drawdown_pct >= self.cfg.drop_pct_threshold:
			# Первый триггер — пометить окно входа
			self._maybe_mark_first_trigger(now_ts)
		else:
			# Если падение меньше порога, не входим. Но окно может ещё быть активно.
			return None

		# Проверка cooldown
		if self._cooldown_active(now_ts):
			if self.cfg.verbose:
				print("Cooldown active, skip entry")
			return None

		# Разрешён вход только в окне entry_window_seconds
		if not self._entry_window_active(now_ts):
			if self.cfg.verbose:
				print("Entry window not active, skip")
			return None

		# Формируем запрос на шорт по альте
		order = OrderRequest(
			symbol=self.cfg.alt_symbol,
			side="SELL",
			quantity=self.cfg.alt_order_qty,
			leverage=self.cfg.leverage,
		)
		res = self.exchange.place_order(order)
		if res.success:
			self.state.last_entry_ts = now_ts
			if self.cfg.verbose:
				print(f"Entered short: {res}")
		return res