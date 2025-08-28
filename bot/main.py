import os
import sys
import time
from typing import Optional, List
import typer
from rich import print

# Allow running as a script: python /workspace/bot/main.py
if __package__ is None or __package__ == "":
	sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import StrategyConfig, HLConfig
from bot.prices import BinancePriceProvider, ManualPriceProvider
from bot.exchanges import HyperliquidClient
from bot.strategy import DropShortStrategy
from bot.logging_utils import setup_logging, TradeCsvLogger

app = typer.Typer(help="Бот: шорт альткоина при падении BTC (учебный пример)")


def build_strategy_live(
	alt: str,
	threshold: float,
	lookback: int,
	qty: float,
	leverage: float,
	dry_run: bool,
	verbose: bool,
	sl: float,
	tp: float,
	log_file: Optional[str],
	trade_log: Optional[str],
) -> DropShortStrategy:
	cfg = StrategyConfig(
		btc_symbol="BTCUSDT",
		alt_symbol=alt,
		drop_pct_threshold=threshold,
		lookback_seconds=lookback,
		alt_order_qty=qty,
		leverage=leverage,
		stop_loss_pct=sl,
		take_profit_pct=tp,
		verbose=verbose,
	)
	logger = setup_logging(log_file, level=20)
	pp = BinancePriceProvider()
	hl = HyperliquidClient(HLConfig(dry_run=dry_run))
	trade_logger = TradeCsvLogger(trade_log) if trade_log else None
	return DropShortStrategy(cfg, pp, hl, trade_logger=trade_logger, logger=logger)


def build_strategy_manual(
	alt: str,
	threshold: float,
	lookback: int,
	qty: float,
	leverage: float,
	dry_run: bool,
	verbose: bool,
	sl: float,
	tp: float,
	log_file: Optional[str],
	trade_log: Optional[str],
	btc_price: Optional[float] = None,
	alt_price: Optional[float] = None,
) -> DropShortStrategy:
	cfg = StrategyConfig(
		btc_symbol="BTCUSDT",
		alt_symbol=alt,
		drop_pct_threshold=threshold,
		lookback_seconds=lookback,
		alt_order_qty=qty,
		leverage=leverage,
		stop_loss_pct=sl,
		take_profit_pct=tp,
		verbose=verbose,
	)
	logger = setup_logging(log_file, level=20)
	manual = ManualPriceProvider()
	if btc_price is not None:
		manual.set_price(cfg.btc_symbol, btc_price)
	if alt_price is not None:
		manual.set_price(cfg.alt_symbol, alt_price)
	hl = HyperliquidClient(HLConfig(dry_run=dry_run))
	trade_logger = TradeCsvLogger(trade_log) if trade_log else None
	return DropShortStrategy(cfg, manual, hl, trade_logger=trade_logger, logger=logger)


@app.command()
def run_live(
	alt: str = typer.Option("ETHUSDT", help="Символ альты (например ETHUSDT)"),
	threshold: float = typer.Option(1.0, help="Порог падения BTC от локального максимума (%)"),
	lookback: int = typer.Option(300, help="Окно поиска локального максимума BTC (сек)"),
	qty: float = typer.Option(1.0, help="Размер ордера по альте (монеты)"),
	leverage: float = typer.Option(3.0, help="Плечо"),
	poll: float = typer.Option(2.0, help="Период опроса (сек)"),
	sl: float = typer.Option(2.0, help="Стоп-лосс (%) от цены входа"),
	tp: float = typer.Option(2.0, help="Тейк-профит (%) от цены входа"),
	log_file: Optional[str] = typer.Option("/workspace/bot/logs/bot.log", help="Файл логов"),
	trade_log: Optional[str] = typer.Option("/workspace/bot/logs/trades.csv", help="CSV лог сделок"),
	dry_run: bool = typer.Option(True, help="Сухой режим клиента HL"),
	verbose: bool = typer.Option(True, help="Подробный вывод"),
):
	"""Работа с онлайн-ценами (Binance)."""
	strategy = build_strategy_live(alt, threshold, lookback, qty, leverage, dry_run, verbose, sl, tp, log_file, trade_log)
	print("[bold green]Start live mode. Press Ctrl+C to stop.[/bold green]")
	try:
		while True:
			res = strategy.on_tick()
			if res is not None:
				print(f"Order result: {res}")
			time.sleep(poll)
	except KeyboardInterrupt:
		print("[yellow]Stopped by user[/yellow]")


@app.command()
def manual_once(
	btc: float = typer.Option(..., help="BTC цена"),
	alt: float = typer.Option(..., help="ALT цена"),
	alt_symbol: str = typer.Option("ETHUSDT", help="Символ альты"),
	threshold: float = typer.Option(1.0, help="Порог падения BTC (%)"),
	lookback: int = typer.Option(300, help="Окно lookback для локального максимума BTC (сек)"),
	qty: float = typer.Option(1.0, help="Размер ордера по альте"),
	leverage: float = typer.Option(3.0, help="Плечо"),
	sl: float = typer.Option(2.0, help="Стоп-лосс (%)"),
	tp: float = typer.Option(2.0, help="Тейк-профит (%)"),
	log_file: Optional[str] = typer.Option("/workspace/bot/logs/bot.log", help="Файл логов"),
	trade_log: Optional[str] = typer.Option("/workspace/bot/logs/trades.csv", help="CSV лог сделок"),
	dry_run: bool = typer.Option(True, help="Сухой режим HL"),
	verbose: bool = typer.Option(True, help="Подробный вывод"),
):
	"""Одноразовый шаг стратегии с ручными ценами (без опроса API)."""
	strategy = build_strategy_manual(alt_symbol, threshold, lookback, qty, leverage, dry_run, verbose, sl, tp, log_file, trade_log, btc_price=btc, alt_price=alt)
	res = strategy.on_tick()
	print(f"on_tick result: {res}")


@app.command()
def manual_replay(
	btc_seq: str = typer.Option(..., help="Список цен BTC через запятую"),
	alt_seq: str = typer.Option(..., help="Список цен ALT через запятую"),
	alt_symbol: str = typer.Option("ETHUSDT", help="Символ альты"),
	threshold: float = typer.Option(1.0, help="Порог падения BTC (%)"),
	lookback: int = typer.Option(300, help="Окно lookback (сек)"),
	qty: float = typer.Option(1.0, help="Размер ордера по альте"),
	leverage: float = typer.Option(3.0, help="Плечо"),
	sl: float = typer.Option(2.0, help="Стоп-лосс (%)"),
	tp: float = typer.Option(2.0, help="Тейк-профит (%)"),
	log_file: Optional[str] = typer.Option("/workspace/bot/logs/bot.log", help="Файл логов"),
	trade_log: Optional[str] = typer.Option("/workspace/bot/logs/trades.csv", help="CSV лог сделок"),
	dry_run: bool = typer.Option(True, help="Сухой режим HL"),
	verbose: bool = typer.Option(True, help="Подробный вывод"),
	step_delay: float = typer.Option(0.0, help="Пауза между тиками (сек)"),
):
	"""Пошаговая симуляция стратегии списками ручных цен."""
	strategy = build_strategy_manual(alt_symbol, threshold, lookback, qty, leverage, dry_run, verbose, sl, tp, log_file, trade_log)
	btc_prices = [float(x) for x in btc_seq.split(",") if x.strip()]
	alt_prices = [float(x) for x in alt_seq.split(",") if x.strip()]
	if len(btc_prices) != len(alt_prices):
		raise typer.BadParameter("btc_seq and alt_seq must have the same length")

	for i, (bp, ap) in enumerate(zip(btc_prices, alt_prices)):
		strategy.price_provider.set_price("BTCUSDT", bp)
		strategy.price_provider.set_price(alt_symbol, ap)
		res = strategy.on_tick()
		print(f"step={i} bp={bp} ap={ap} -> {res}")
		if step_delay > 0:
			time.sleep(step_delay)


if __name__ == "__main__":
	app()