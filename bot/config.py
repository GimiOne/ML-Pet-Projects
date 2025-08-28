from dataclasses import dataclass
from typing import Optional


@dataclass
class StrategyConfig:
	"""Конфиг стратегии детекта падения BTC и открытия шорта по альте."""

	btc_symbol: str = "BTCUSDT"
	alt_symbol: str = "ETHUSDT"

	# Процент падения BTC от локального максимума в окне наблюдения, чтобы триггернуть вход
	drop_pct_threshold: float = 1.0  # например 1%

	# Размер окна (секунд), в котором ищем локальный максимум BTC для оценки падения
	lookback_seconds: int = 300  # 5 минут

	# Максимальное время (секунд) после первого триггера входа
	# В рамках которого считаем, что падение «актуально» (например, первые 10 минут сильнее)
	entry_window_seconds: int = 600  # 10 минут

	# Минимальный интервал между входами (секунд), чтобы не перезаходить слишком часто
	cooldown_seconds: int = 900  # 15 минут

	# Размер ордера по альте (контракты/монеты). Упростим до количества монет.
	alt_order_qty: float = 1.0

	# Плечо. Здесь логика проста, чтобы легко валидировать в dry-run
	leverage: float = 3.0

	# Период опроса цен (секунд)
	poll_interval_seconds: float = 2.0

	# Стоп-лосс и тейк-профит (в процентах), применяются к цене входа позиции.
	# Для шорта: SL срабатывает при росте цены на sl_pct, TP — при падении цены на tp_pct.
	stop_loss_pct: float = 2.0
	take_profit_pct: float = 2.0

	# Включить подробный вывод (для отладки)
	verbose: bool = True


@dataclass
class HLConfig:
	"""Конфиг клиента Hyperliquid (здесь dry_run по умолчанию)."""

	api_key: Optional[str] = None
	api_secret: Optional[str] = None
	base_url: str = "https://api.hyperliquid.com"
	dry_run: bool = True