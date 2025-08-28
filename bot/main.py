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
	qty: float = typer.Option(1.0, help="Размер ордера по альте (монеты), если не используется --usd-notional"),
	usd_notional: Optional[float] = typer.Option(None, help="Размер позиции в USD (перекрывает --qty)"),
	leverage: float = typer.Option(3.0, help="Плечо"),
	isolated: bool = typer.Option(False, help="Изоляция маржи (по умолчанию cross)"),
	poll: float = typer.Option(2.0, help="Период опроса (сек)"),
	sl: float = typer.Option(2.0, help="Стоп-лосс (%) от цены входа"),
	tp: float = typer.Option(2.0, help="Тейк-профит (%) от цены входа"),
	log_file: Optional[str] = typer.Option("/workspace/bot/logs/bot.log", help="Файл логов"),
	trade_log: Optional[str] = typer.Option("/workspace/bot/logs/trades.csv", help="CSV лог сделок"),
	dry_run: bool = typer.Option(True, help="Сухой режим клиента HL"),
	hl_api_secret: Optional[str] = typer.Option(None, help="HL Private Key (hex) для реальных ордеров"),
	use_testnet: bool = typer.Option(False, help="Использовать тестнет HL"),
	verbose: bool = typer.Option(True, help="Подробный вывод"),
):
	"""Работа с онлайн-ценами; при падении BTC открывает шорт по альте с SL/TP.

	Поддерживает USD-сайзинг (--usd-notional) и режим маржи (--isolated, --leverage).
	Для реальных ордеров укажите --dry-run False и --hl-api-secret (и при необходимости --use-testnet False для мейннета).
	"""
	cfg = StrategyConfig(
		btc_symbol="BTCUSDT",
		alt_symbol=alt,
		drop_pct_threshold=threshold,
		lookback_seconds=lookback,
		alt_order_qty=qty,
		usd_notional=usd_notional,
		leverage=leverage,
		use_isolated=isolated,
		stop_loss_pct=sl,
		take_profit_pct=tp,
		verbose=verbose,
	)
	logger = setup_logging(log_file, level=20)
	pp = BinancePriceProvider()
	hl = HyperliquidClient(HLConfig(api_secret=hl_api_secret, dry_run=dry_run), use_testnet=use_testnet)
	trade_logger = TradeCsvLogger(trade_log) if trade_log else None
	strategy = DropShortStrategy(cfg, pp, hl, trade_logger=trade_logger, logger=logger)
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
	"""Мгновенно открыть шорт с опциональными SL/TP, без детекта падения BTC.

	Опции:
	- --usd-notional N    Размер позиции в USD (перекрывает --qty)
	- --isolated          Изолированная маржа (по умолчанию cross)
	- --leverage L        Плечо (устанавливается в режиме маржи на HL)
	- --sl/--tp %         Стоп-лосс/тейк-профит от цены входа
	- --sl-price/--tp-price Абсолютные уровни вместо процентов
	- --use-testnet       Тестнет (True) или мейннет (False)
	- --hl-api-secret     Приватный ключ кошелька (hex) для реальных ордеров

	Примеры:
	- Dry-run (без реальных ордеров):
	  python3 -m bot.main short --alt-symbol ETHUSDT \
	    --usd-notional 50 --leverage 3 --isolated \
	    --sl 1.5 --tp 2.0 --dry-run

	- Тестнет (реальные ордера в тестовой сети HL):
	  python3 -m bot.main short --alt-symbol ETHUSDT \
	    --usd-notional 50 --leverage 3 --isolated \
	    --sl 1.5 --tp 2.0 --use-testnet \
	    --hl-api-secret 0xYOUR_TESTNET_PRIVATE_KEY_HEX \
	    --dry-run False
	"""
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


@app.command()
def simulate_btc_fall(
	alt_symbol: str = typer.Option("ETHUSDT", help="Альта для входа (например ETHUSDT)"),
	threshold: float = typer.Option(2.0, help="Порог падения BTC (%) для входа"),
	qty: float = typer.Option(1.0, help="Размер позиции (монеты), если не используется --usd-notional"),
	usd_notional: Optional[float] = typer.Option(None, help="Размер позиции в USD (если указан, перекрывает --qty)"),
	sl: float = typer.Option(2.0, help="Стоп-лосс (%)"),
	tp: float = typer.Option(2.0, help="Тейк-профит (%)"),
	leverage: int = typer.Option(3, help="Плечо"),
	isolated: bool = typer.Option(False, help="Изоляция маржи (по умолчанию cross)"),
	interval: float = typer.Option(2.0, help="Интервал симуляции падения BTC (сек)"),
	fall_step_pct: float = typer.Option(0.1, help="Шаг падения BTC за интервал (%)"),
	# ALT simulation controls
	sim_alt: bool = typer.Option(False, help="Симулировать цену альты вместе с BTC"),
	alt_mode: str = typer.Option("follow", help="Режим симуляции альты: follow|drop|rise"),
	alt_beta: float = typer.Option(1.2, help="Чувствительность альты к шагу BTC при follow (alt_delta = beta * btc_delta)"),
	close_on_sim_hit: bool = typer.Option(False, help="При срабатывании SL/TP на симулированной цене закрывать позицию реально"),
	log_file: Optional[str] = typer.Option("/workspace/bot/logs/bot.log", help="Файл логов"),
	trade_log: Optional[str] = typer.Option("/workspace/bot/logs/trades.csv", help="CSV лог сделок"),
	hl_api_secret: Optional[str] = typer.Option(None, help="HL Private Key (hex) для реальных ордеров на мейннетe/тестнете"),
	use_testnet: bool = typer.Option(False, help="False для мейннета (реальные средства)"),
	verbose: bool = typer.Option(True, help="Подробный вывод"),
):
	"""Симуляция падения BTC каждые interval секунд; при падении >= threshold открывается шорт на альте с SL/TP.

	Расширения симуляции:
	- --sim-alt            Симулировать цену альты синхронно с BTC
	- --alt-mode MODE     follow|drop|rise: поведение альты
	- --alt-beta B        чувствительность альты при follow (alt_delta = B * btc_delta)
	- --close-on-sim-hit  Реально закрыть позицию маркетом при срабатывании на симулированной цене

	Размер и маржа:
	- --usd-notional USD  Размер позиции в USD (перекрывает --qty)
	- --isolated, --leverage  Установка режима маржи/плеча на HL перед входом

	Мейннет пример (реальные средства!):
	python3 -m bot.main simulate-btc-fall \
	  --alt-symbol ETHUSDT \
	  --threshold 2.0 \
	  --usd-notional 50 \
	  --sl 1.0 --tp 1.0 \
	  --leverage 3 --isolated \
	  --interval 2 --fall-step-pct 0.1 \
	  --sim-alt --alt-mode follow --alt-beta 1.2 \
	  --close-on-sim-hit \
	  --use-testnet False \
	  --hl-api-secret 0xYOUR_MAINNET_PRIVATE_KEY_HEX
	"""
	logger = setup_logging(log_file, level=20)

	from hyperliquid.info import Info
	from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
	from bot.prices import HLInfoPriceProvider
	from bot.exchanges import HyperliquidClient, OrderRequest

	base_url = TESTNET_API_URL if use_testnet else MAINNET_API_URL
	info = Info(base_url=base_url, skip_ws=True)
	pp = HLInfoPriceProvider(info)

	hl = HyperliquidClient(HLConfig(api_secret=hl_api_secret, dry_run=False), use_testnet=use_testnet)
	trade_logger = TradeCsvLogger(trade_log) if trade_log else None

	# Initialize BTC and ALT
	btc_tick = pp.get_price("BTCUSDT")
	btc_start = btc_tick.price
	btc_current = btc_start
	alt_real_tick = pp.get_price(alt_symbol)
	alt_real_start = alt_real_tick.price
	alt_sim = alt_real_start
	logger.info(f"Sim start on {'TESTNET' if use_testnet else 'MAINNET'}: BTC start={btc_start:.2f} ALT({alt_symbol}) start(real)={alt_real_start:.4f}")

	# Set leverage mode
	lev_res = hl.set_leverage_mode(alt_symbol, leverage=leverage, is_cross=not isolated)
	if lev_res:
		logger.info(f"Leverage mode set: {lev_res}")

	entered = False
	entry_ts = None
	entry_price_real = None
	entry_price_sim = None
	qty_final = None

	try:
		while True:
			# Simulate BTC drop step
			btc_current *= (1.0 - fall_step_pct / 100.0)
			drawdown_pct = (btc_start - btc_current) / btc_start * 100.0

			# Real ALT price (for logging)
			alt_real_tick = pp.get_price(alt_symbol)
			alt_real_px = alt_real_tick.price

			# Sim ALT path (optional)
			if sim_alt:
				btc_step_delta = -fall_step_pct
				if alt_mode.lower() == "follow":
					alt_step = btc_step_delta * alt_beta
				elif alt_mode.lower() == "drop":
					alt_step = -abs(fall_step_pct)
				elif alt_mode.lower() == "rise":
					alt_step = abs(fall_step_pct)
				else:
					alt_step = btc_step_delta * alt_beta
				alt_sim *= (1.0 + alt_step / 100.0)

			logger.info(
				f"Sim BTC={btc_current:.2f} (↓{drawdown_pct:.2f}%) ALT_real({alt_symbol})={alt_real_px:.4f}"
				+ (f" ALT_sim={alt_sim:.4f} mode={alt_mode} beta={alt_beta}" if sim_alt else "")
			)

			if (not entered) and drawdown_pct >= threshold:
				# sizing USD->qty
				qty_final = qty
				ref_px_for_sizing = alt_sim if sim_alt else alt_real_px
				if usd_notional is not None:
					qty_final = usd_notional / ref_px_for_sizing
					logger.info(f"Sizing by USD: {usd_notional} -> qty {qty_final}")
				res = hl.place_order(OrderRequest(symbol=alt_symbol, side="SELL", quantity=qty_final, leverage=float(leverage), price=None))
				if not res.success:
					logger.error(f"Short open failed: {res.message}")
					raise typer.Exit(code=1)
				entered = True
				entry_ts = time.time()
				entry_price_real = alt_real_px
				entry_price_sim = alt_sim
				logger.info(f"Real short OPENED: qty={qty_final} entry_real={entry_price_real:.6f} entry_sim={entry_price_sim:.6f}")
				# place on-chain triggers for real market behavior
				if tp:
					resp_tp = hl.place_trigger_exit(alt_symbol, qty_final, entry_price_real * (1.0 - tp / 100.0), tpsl="tp")
					logger.info(f"TP trigger place: {resp_tp}")
				if sl:
					resp_sl = hl.place_trigger_exit(alt_symbol, qty_final, entry_price_real * (1.0 + sl / 100.0), tpsl="sl")
					logger.info(f"SL trigger place: {resp_sl}")

			if entered:
				# Live PnL by real price
				pnl_real = -(alt_real_px - entry_price_real) * qty_final
				pnl_real_pct = -(alt_real_px - entry_price_real) / entry_price_real * 100.0
				# Sim PnL by simulated price (if enabled)
				pnl_sim = None
				pnl_sim_pct = None
				if sim_alt:
					pnl_sim = -(alt_sim - entry_price_sim) * qty_final
					pnl_sim_pct = -(alt_sim - entry_price_sim) / entry_price_sim * 100.0
				logger.info(
					f"PnL real: {pnl_real:.4f} ({pnl_real_pct:.2f}%)"
					+ (f" | PnL sim: {pnl_sim:.4f} ({pnl_sim_pct:.2f}%)" if sim_alt else "")
				)

				# Simulated SL/TP hit handling (optional)
				if sim_alt:
					hit_tp = alt_sim <= entry_price_sim * (1.0 - tp / 100.0) if tp else False
					hit_sl = alt_sim >= entry_price_sim * (1.0 + sl / 100.0) if sl else False
					if hit_tp or hit_sl:
						reason = "tp" if hit_tp else "sl"
						logger.info(f"SIM {reason.upper()} HIT at alt_sim={alt_sim:.6f}")
						if close_on_sim_hit:
							close_res = hl.close_position(alt_symbol, qty_final, side="SELL")
							logger.info(f"Real market close on SIM hit: {close_res}")
							break

			time.sleep(interval)
	except KeyboardInterrupt:
		logger.info("Stopped by user")


# Register alias so underscores also work
try:
	app.command(name="simulate_btc_fall")(simulate_btc_fall)  # alias for simulate-btc-fall
except Exception:
	pass

if __name__ == "__main__":
	app()