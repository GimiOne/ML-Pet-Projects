import time
from typing import Optional
from hyperliquid.info import Info
from bot.prices.base import PriceProvider, PriceTick


def coin_from_symbol(symbol: str) -> str:
	if symbol.endswith("USDT"):
		return symbol[:-4]
	if symbol.endswith("USDC"):
		return symbol[:-4]
	return symbol


class HLInfoPriceProvider(PriceProvider):
	"""Провайдер цен от Info.all_mids() SDK Hyperliquid."""

	def __init__(self, info: Info) -> None:
		self.info = info

	def get_price(self, symbol: str) -> PriceTick:
		mids = self.info.all_mids()
		coin = coin_from_symbol(symbol)
		if coin not in mids:
			raise KeyError(f"Coin {coin} not found in Hyperliquid mids")
		price = float(mids[coin])
		return PriceTick(symbol=symbol, price=price, ts=time.time())