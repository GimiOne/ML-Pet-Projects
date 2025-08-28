import time
from typing import Optional, List
import typer
from rich import print

from .config import StrategyConfig, HLConfig
from .prices import BinancePriceProvider, ManualPriceProvider
from .exchanges import HyperliquidClient
from .strategy import DropShortStrategy

app = typer.Typer(help="Бот: шорт альткоина при падении BTC (учебный пример)")


def build_strategy_live(alt: str, threshold: float, lookback: int, qty: float, leverage: float, dry_run: bool, verbose: bool) -> DropShortStrategy:
	cfg = StrategyConfig(
		btc_symbol="BTCUSDT",
		alt_symbol=alt,
		drop_pct_threshold=threshold,
		lookback_seconds=lookback,
		alt_order_qty=qty,
		leverage=leverage,
		verbose=verbose,
	)
	pp = BinancePriceProvider()
	hl = HyperliquidClient(HLConfig(dry_run=dry_run))
	return DropShortStrategy(cfg, pp, hl)


def build_strategy_manual(alt: str, threshold: float, lookback: int, qty: float, leverage: float, dry_run: bool, verbose: bool,
							btc_price: Optional[float] = None, alt_price: Optional[float] = None) -> DropShortStrategy:
	cfg = StrategyConfig(
		btc_symbol="BTCUSDT",
		alt_symbol=alt,
		drop_pct_threshold=threshold,
		lookback_seconds=lookback,
		alt_order_qty=qty,
		leverage=leverage,
		verbose=verbose,
	)
	manual = ManualPriceProvider()
	if btc_price is not None:
		manual.set_price(cfg.btc_symbol, btc_price)
	if alt_price is not None:
		manual.set_price(cfg.alt_symbol, alt_price)
	hl = HyperliquidClient(HLConfig(dry_run=dry_run))
	return DropShortStrategy(cfg, manual, hl)


@app.command()
def run_live(
	alt: str = typer.Option("ETHUSDT", help="Символ альты (например ETHUSDT)"),
	threshold: float = typer.Option(1.0, help="Порог падения BTC от локального максимума (%)"),
	lookback: int = typer.Option(300, help="Окно поиска локального максимума BTC (сек)"),
	qty: float = typer.Option(1.0, help="Размер ордера по альте (монеты)"),
	leverage: float = typer.Option(3.0, help="Плечо"),
	poll: float = typer.Option(2.0, help="Период опроса (сек)"),
	dry_run: bool = typer.Option(True, help="Сухой режим клиента HL"),
	verbose: bool = typer.Option(True, help="Подробный вывод"),
):
	"""Работа с онлайн-ценами (Binance)."""
	strategy = build_strategy_live(alt, threshold, lookback, qty, leverage, dry_run, verbose)
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
	dry_run: bool = typer.Option(True, help="Сухой режим HL"),
	verbose: bool = typer.Option(True, help="Подробный вывод"),
):
	"""Одноразовый шаг стратегии с ручными ценами (без опроса API)."""
	strategy = build_strategy_manual(alt_symbol, threshold, lookback, qty, leverage, dry_run, verbose, btc_price=btc, alt_price=alt)
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
	dry_run: bool = typer.Option(True, help="Сухой режим HL"),
	verbose: bool = typer.Option(True, help="Подробный вывод"),
	step_delay: float = typer.Option(0.0, help="Пауза между тиками (сек)"),
):
	"""Пошаговая симуляция стратегии списками ручных цен."""
	btc_prices = [float(x) for x in btc_seq.split(",") if x.strip()]
	alt_prices = [float(x) for x in alt_seq.split(",") if x.strip()]
	if len(btc_prices) != len(alt_prices):
		raise typer.BadParameter("btc_seq and alt_seq must have the same length")

	strategy = build_strategy_manual(alt_symbol, threshold, lookback, qty, leverage, dry_run, verbose)
	for i, (bp, ap) in enumerate(zip(btc_prices, alt_prices)):
		strategy.price_provider.set_price("BTCUSDT", bp)
		strategy.price_provider.set_price(alt_symbol, ap)
		res = strategy.on_tick()
		print(f"step={i} bp={bp} ap={ap} -> {res}")
		if step_delay > 0:
			time.sleep(step_delay)


if __name__ == "__main__":
	app()