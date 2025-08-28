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
from bot.exchanges import HyperliquidClient, OrderRequest
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


@app.command()
def short(
	alt_symbol: str = typer.Option("ETHUSDT", help="Символ альты для шорта (например ETHUSDT)"),
	qty: float = typer.Option(1.0, help="Размер позиции (монеты), если не используется --usd-notional"),
	usd_notional: Optional[float] = typer.Option(None, help="Размер позиции в USD (если указан, перекрывает --qty)"),
	leverage: int = typer.Option(3, help="Плечо (используется при обновлении режима маржи)"),
	isolated: bool = typer.Option(False, help="Включить изолированную маржу (по умолчанию cross)"),
	sl: Optional[float] = typer.Option(None, help="Стоп-лосс (%) от цены входа"),
	tp: Optional[float] = typer.Option(None, help="Тейк-профит (%) от цены входа"),
	sl_price: Optional[float] = typer.Option(None, help="Стоп-лосс абсолютной ценой (для шорта: BUY закрытие)"),
	tp_price: Optional[float] = typer.Option(None, help="Тейк-профит абсолютной ценой (для шорта: BUY закрытие)"),
	poll: float = typer.Option(2.0, help="Период опроса цен для брекетов (сек)"),
	log_file: Optional[str] = typer.Option("/workspace/bot/logs/bot.log", help="Файл логов"),
	trade_log: Optional[str] = typer.Option("/workspace/bot/logs/trades.csv", help="CSV лог сделок"),
	dry_run: bool = typer.Option(True, help="Сухой режим HL"),
	hl_api_key: Optional[str] = typer.Option(None, help="HL Address (опционально)"),
	hl_api_secret: Optional[str] = typer.Option(None, help="HL Private Key (hex) для реальных ордеров"),
	use_testnet: bool = typer.Option(False, help="Использовать тестнет HL"),
	verbose: bool = typer.Option(True, help="Подробный вывод"),
):
	"""Мгновенно открыть шорт с опциональными SL/TP, без детекта падения BTC."""
	logger = setup_logging(log_file, level=20)
	pp = BinancePriceProvider()
	hl = HyperliquidClient(HLConfig(api_key=hl_api_key, api_secret=hl_api_secret, dry_run=dry_run), use_testnet=use_testnet)
	trade_logger = TradeCsvLogger(trade_log) if trade_log else None

	entry_tick = pp.get_price(alt_symbol)
	entry_price = entry_tick.price
	logger.info(f"Entry (market SELL) planned at ~{entry_price:.6f} {alt_symbol}")

	# Установка маржи: cross/isolated
	lev_res = hl.set_leverage_mode(alt_symbol, leverage=leverage, is_cross=not isolated)
	if lev_res:
		logger.info(f"Leverage mode set: {lev_res}")

	# USD sizing -> convert to coin qty
	qty_final = qty
	if usd_notional is not None:
		qty_final = usd_notional / entry_price
		logger.info(f"Sizing by USD: {usd_notional} -> qty {qty_final}")

	res = hl.place_order(OrderRequest(symbol=alt_symbol, side="SELL", quantity=qty_final, leverage=float(leverage), price=None))
	if not res.success:
		logger.error(f"Short open failed: {res.message}")
		raise typer.Exit(code=1)
	logger.info(f"Short opened: order_id={res.order_id} qty={qty_final} entry~{entry_price}")

	entry_ts = time.time()

	computed_sl = None
	computed_tp = None
	if sl_price is not None:
		computed_sl = float(sl_price)
	elif sl is not None:
		computed_sl = entry_price * (1.0 + sl / 100.0)

	if tp_price is not None:
		computed_tp = float(tp_price)
	elif tp is not None:
		computed_tp = entry_price * (1.0 - tp / 100.0)

	if computed_sl:
		logger.info(f"SL at {computed_sl:.6f}")
	if computed_tp:
		logger.info(f"TP at {computed_tp:.6f}")

	if not dry_run and (computed_sl or computed_tp):
		if computed_tp:
			resp_tp = hl.place_trigger_exit(alt_symbol, qty_final, computed_tp, tpsl="tp")
			logger.info(f"Place TP trigger: {resp_tp}")
		if computed_sl:
			resp_sl = hl.place_trigger_exit(alt_symbol, qty_final, computed_sl, tpsl="sl")
			logger.info(f"Place SL trigger: {resp_sl}")

	try:
		while dry_run:
			btc = pp.get_price("BTCUSDT")
			alt = pp.get_price(alt_symbol)
			balance = hl.get_balance()
			logger.info(f"BTC={btc.price:.4f} ALT({alt_symbol})={alt.price:.4f} Balance={balance}")

			should_close = False
			reason = None
			if computed_tp is not None and alt.price <= computed_tp:
				should_close = True
				reason = "tp"
			if computed_sl is not None and alt.price >= computed_sl:
				should_close = True
				reason = "sl"

			if should_close:
				close_res = hl.close_position(alt_symbol, qty_final, side="SELL")
				if not close_res.success:
					logger.error(f"Close failed: {close_res.message}")
					raise typer.Exit(code=2)
				pnl = -(alt.price - entry_price) * qty_final
				pnl_pct = -(alt.price - entry_price) / entry_price * 100.0
				logger.info(f"Position closed: reason={reason} exit={alt.price:.6f} pnl={pnl:.4f} pnl%={pnl_pct:.4f}")
				if trade_logger:
					trade_logger.log_trade(
						ts_open=entry_ts,
						ts_close=time.time(),
						symbol=alt_symbol,
						side="SELL",
						quantity=qty_final,
						entry_price=entry_price,
						exit_price=alt.price,
						pnl=pnl,
						pnl_pct=pnl_pct,
						reason=reason or "manual",
					)
				break

			time.sleep(poll)
	except KeyboardInterrupt:
		logger.info("Stopped by user")


if __name__ == "__main__":
	app()