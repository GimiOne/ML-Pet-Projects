import csv
import logging
import os
from typing import Optional


def setup_logging(log_file_path: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
	logger = logging.getLogger("bot")
	logger.setLevel(level)
	logger.handlers = []

	console_handler = logging.StreamHandler()
	console_handler.setLevel(level)
	console_formatter = logging.Formatter(
		"%(asctime)s | %(levelname)s | %(message)s",
		datefmt="%Y-%m-%d %H:%M:%S",
	)
	console_handler.setFormatter(console_formatter)
	logger.addHandler(console_handler)

	if log_file_path:
		os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
		file_handler = logging.FileHandler(log_file_path)
		file_handler.setLevel(level)
		file_handler.setFormatter(console_formatter)
		logger.addHandler(file_handler)

	return logger


class TradeCsvLogger:
	"""Логгер сделок в CSV: фиксирует открытие/закрытие, цены и PnL."""

	def __init__(self, csv_path: str) -> None:
		self.csv_path = csv_path
		dirname = os.path.dirname(csv_path)
		if dirname:
			os.makedirs(dirname, exist_ok=True)
		self._ensure_header()

	def _ensure_header(self) -> None:
		if not os.path.exists(self.csv_path) or os.path.getsize(self.csv_path) == 0:
			with open(self.csv_path, mode="w", newline="") as f:
				writer = csv.writer(f)
				writer.writerow([
					"ts_open",
					"ts_close",
					"symbol",
					"side",
					"quantity",
					"entry_price",
					"exit_price",
					"pnl",
					"pnl_pct",
					"reason",  # tp | sl | manual
				])

	def log_trade(
		self,
		ts_open: float,
		ts_close: float,
		symbol: str,
		side: str,
		quantity: float,
		entry_price: float,
		exit_price: float,
		pnl: float,
		pnl_pct: float,
		reason: str,
	) -> None:
		with open(self.csv_path, mode="a", newline="") as f:
			writer = csv.writer(f)
			writer.writerow([
				ts_open,
				ts_close,
				symbol,
				side,
				quantity,
				entry_price,
				exit_price,
				pnl,
				pnl_pct,
				reason,
			])