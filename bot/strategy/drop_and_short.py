from collections import deque
from dataclasses import dataclass
from typing import Deque, Tuple, Optional
import time
import logging

from bot.config import StrategyConfig
from bot.prices.base import PriceProvider, PriceTick
from bot.exchanges.hl import HyperliquidClient, OrderRequest, OrderResult
from bot.logging_utils import TradeCsvLogger


@dataclass
class StrategyState:
	"""Состояние стратегии: история цен, последний вход, окно входа и позиция."""

	last_entry_ts: Optional[float] = None
	first_trigger_ts: Optional[float] = None

	# Текущая позиция (упрощённо: одна позиция по альте)
	position_side: Optional[str] = None  # "SELL" (шорт) или "BUY"
	position_qty: float = 0.0
	entry_price: Optional[float] = None
	entry_ts: Optional[float] = None


class DropShortStrategy:
	"""Стратегия: при падении BTC входим в шорт по альте, сопровождаем SL/TP, ведём логи."""

	def __init__(
		self,
		cfg: StrategyConfig,
		price_provider: PriceProvider,
		exchange: HyperliquidClient,
		trade_logger: Optional[TradeCsvLogger] = None,
		logger: Optional[logging.Logger] = None,
		max_history_seconds: Optional[int] = None,
	) -> None:
		self.cfg = cfg
		self.price_provider = price_provider
		self.exchange = exchange
		self.trade_logger = trade_logger
		self.log = logger or logging.getLogger("bot")
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

	def _try_close_with_reason(self, reason: str, alt_price: float) -> Optional[OrderResult]:
		if not self.state.position_side or self.state.position_qty <= 0 or self.state.entry_price is None:
			return None
		qty = self.state.position_qty
		side = self.state.position_side
		res = self.exchange.close_position(self.cfg.alt_symbol, qty, side)
		if res.success:
			pnlsign = -1.0 if side == "SELL" else 1.0
			pnl = pnlsign * (alt_price - self.state.entry_price) * qty
			pnl_pct = pnlsign * (alt_price - self.state.entry_price) / self.state.entry_price * 100.0
			if self.trade_logger and self.state.entry_ts is not None:
				self.trade_logger.log_trade(
					ts_open=self.state.entry_ts,
					ts_close=time.time(),
					symbol=self.cfg.alt_symbol,
					side=side,
					quantity=qty,
					entry_price=self.state.entry_price,
					exit_price=alt_price,
					pnl=pnl,
					pnl_pct=pnl_pct,
					reason=reason,
				)
			self.log.info(f"Closed position: reason={reason} pnl={pnl:.4f} pnl%={pnl_pct:.4f}")
			self.state.position_side = None
			self.state.position_qty = 0.0
			self.state.entry_price = None
			self.state.entry_ts = None
		return res

	def _check_sl_tp(self, alt_price: float) -> Optional[OrderResult]:
		if not self.state.position_side or self.state.entry_price is None:
			return None
		entry = self.state.entry_price
		if self.state.position_side == "SELL":
			# Для шорта: TP при падении цены на take_profit_pct, SL при росте на stop_loss_pct
			tp_price = entry * (1.0 - self.cfg.take_profit_pct / 100.0)
			sl_price = entry * (1.0 + self.cfg.stop_loss_pct / 100.0)
			if alt_price <= tp_price:
				return self._try_close_with_reason("tp", alt_price)
			if alt_price >= sl_price:
				return self._try_close_with_reason("sl", alt_price)
		else:
			# Для полноты: лонг (не используется в текущей стратегии)
			tp_price = entry * (1.0 + self.cfg.take_profit_pct / 100.0)
			sl_price = entry * (1.0 - self.cfg.stop_loss_pct / 100.0)
			if alt_price >= tp_price:
				return self._try_close_with_reason("tp", alt_price)
			if alt_price <= sl_price:
				return self._try_close_with_reason("sl", alt_price)
		return None

	def on_tick(self) -> Optional[OrderResult]:
		"""Основной шаг стратегии. Возвращает результат ордера, если был вход/выход."""
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

		# Логи текущих метрик
		balance = self.exchange.get_balance()
		self.log.info(f"BTC={btc.price:.4f} ALT({self.cfg.alt_symbol})={alt.price:.4f} Balance={balance}")

		# Если есть позиция — проверить SL/TP
		exit_res = self._check_sl_tp(alt.price)
		if exit_res is not None:
			return exit_res

		# Обслуживаем окно входа
		self._reset_trigger_if_window_passed(now_ts)

		# Детект падения BTC
		drawdown_pct = self._calc_btc_drawdown_pct(now_ts)
		if self.cfg.verbose:
			if drawdown_pct is None:
				self.log.info("BTC drawdown: n/a")
			else:
				self.log.info(f"BTC drawdown: {drawdown_pct:.4f}% (threshold {self.cfg.drop_pct_threshold}%)")

		if drawdown_pct is None:
			return None

		if drawdown_pct >= self.cfg.drop_pct_threshold:
			self._maybe_mark_first_trigger(now_ts)
		else:
			return None

		# Проверка cooldown
		if self._cooldown_active(now_ts):
			self.log.info("Cooldown active, skip entry")
			return None

		# Разрешён вход только в окне entry_window_seconds
		if not self._entry_window_active(now_ts):
			self.log.info("Entry window not active, skip")
			return None

		# Если уже есть позиция — не открываем новую
		if self.state.position_side is not None and self.state.position_qty > 0:
			return None

		# Формируем запрос на шорт по альте (рыночный)
		order = OrderRequest(
			symbol=self.cfg.alt_symbol,
			side="SELL",
			quantity=self.cfg.alt_order_qty,
			leverage=self.cfg.leverage,
			price=None,
		)
		res = self.exchange.place_order(order)
		if res.success:
			self.state.last_entry_ts = now_ts
			self.state.position_side = "SELL"
			self.state.position_qty = self.cfg.alt_order_qty
			self.state.entry_price = alt.price
			self.state.entry_ts = now_ts
			self.log.info(f"Entered short: order_id={res.order_id} qty={self.state.position_qty} entry={self.state.entry_price}")
		return res