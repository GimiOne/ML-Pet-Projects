#!/usr/bin/env python3
"""
Standalone test script: place a market SHORT on Hyperliquid with optional SL/TP triggers.

What you need to run this file:
- Python 3.10+
- pip install hyperliquid-python-sdk
- A private key (hex) of an EVM wallet authorized on Hyperliquid
- Choose network: testnet or mainnet (recommended testnet first)

Features:
- Cross/Isolated leverage mode update
- USD sizing (convert USD -> coin size by mid)
- Place market short and trigger exits (reduce-only, isMarket=True) with proper price rounding

Safety:
- Test first on testnet
- Use small size
- Double check symbol/coin mapping: 'ETHUSDT' -> 'ETH'
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from eth_account import Account
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL


# ============================
# HARD-CODED CONFIG (EDIT ME)
# ============================

# Use TESTNET first for safety
USE_TESTNET: bool = True

# Private key (hex string, with or without 0x). DO NOT COMMIT REAL KEYS!
PRIVATE_KEY_HEX: str = "0xYOUR_PRIVATE_KEY_HEX"

# Symbol selection (SDK uses coin name like "ETH")
SYMBOL: str = "ETHUSDT"  # script maps to coin 'ETH'

# Position sizing: choose one
USE_USD_SIZING: bool = True
USD_NOTIONAL: float = 20.0  # if USE_USD_SIZING=True
COIN_SIZE: float = 0.003    # if USE_USD_SIZING=False

# Leverage settings
SET_LEVERAGE: bool = True
LEVERAGE_VALUE: int = 3
IS_CROSS: bool = False  # False -> isolated

# Brackets as percentages from entry mid (approx)
TAKE_PROFIT_PCT: Optional[float] = 1.0  # % below entry (short). None to skip
STOP_LOSS_PCT: Optional[float] = 1.0    # % above entry (short). None to skip

# Market slippage for aggressive limit IoC
SLIPPAGE: float = 0.02  # 2%


# ============================
# HELPERS
# ============================

def coin_from_symbol(symbol: str) -> str:
	if symbol.endswith("USDT"):
		return symbol[:-4]
	if symbol.endswith("USDC"):
		return symbol[:-4]
	return symbol


def round_trigger_price(info: Info, coin: str, px: float) -> float:
	asset = info.name_to_asset(coin)
	is_spot = asset >= 10_000
	decimals = (6 if not is_spot else 8) - info.asset_to_sz_decimals[asset]
	return round(float(f"{px:.5g}"), decimals)


# ============================
# MAIN
# ============================

def main() -> None:
	if not PRIVATE_KEY_HEX or PRIVATE_KEY_HEX.endswith("YOUR_PRIVATE_KEY_HEX"):
		raise SystemExit("Please set PRIVATE_KEY_HEX to your testnet key before running.")

	wallet: LocalAccount = Account.from_key(PRIVATE_KEY_HEX)
	base_url = TESTNET_API_URL if USE_TESTNET else MAINNET_API_URL
	ex = Exchange(wallet=wallet, base_url=base_url)
	info = ex.info

	coin = coin_from_symbol(SYMBOL)

	# Mid for sizing & reference
	mids = info.all_mids()
	if coin not in mids:
		raise SystemExit(f"Coin {coin} not found in mids: keys={list(mids.keys())[:10]} ...")
	mid = float(mids[coin])
	print(f"Placing SHORT on {coin}, mid ~ {mid}")

	# Optional: leverage mode update
	if SET_LEVERAGE:
		resp_lev = ex.update_leverage(leverage=LEVERAGE_VALUE, name=coin, is_cross=IS_CROSS)
		print("Update leverage mode:", resp_lev)

	# Sizing
	if USE_USD_SIZING:
		sz = USD_NOTIONAL / mid
	else:
		sz = COIN_SIZE

	# Market short
	resp = ex.market_open(name=coin, is_buy=False, sz=sz, px=mid, slippage=SLIPPAGE)
	print("Market short response:", resp)

	# Compute TP/SL absolute levels, then round to valid precision
	tp_px: Optional[float] = None
	sl_px: Optional[float] = None
	if TAKE_PROFIT_PCT is not None:
		tp_px = round_trigger_price(info, coin, mid * (1.0 - TAKE_PROFIT_PCT / 100.0))
		print(f"TP set at {tp_px}")
	if STOP_LOSS_PCT is not None:
		sl_px = round_trigger_price(info, coin, mid * (1.0 + STOP_LOSS_PCT / 100.0))
		print(f"SL set at {sl_px}")

	# Place triggers (reduce-only, isMarket=True)
	if tp_px is not None:
		resp_tp = ex.order(
			name=coin,
			is_buy=True,  # close short
			sz=sz,
			limit_px=tp_px,
			order_type={"trigger": {"isMarket": True, "triggerPx": tp_px, "tpsl": "tp"}},
			reduce_only=True,
		)
		print("TP trigger response:", resp_tp)

	if sl_px is not None:
		resp_sl = ex.order(
			name=coin,
			is_buy=True,  # close short
			sz=sz,
			limit_px=sl_px,
			order_type={"trigger": {"isMarket": True, "triggerPx": sl_px, "tpsl": "sl"}},
			reduce_only=True,
		)
		print("SL trigger response:", resp_sl)

	print("Done. Monitor orders on Hyperliquid UI.")


if __name__ == "__main__":
	main()