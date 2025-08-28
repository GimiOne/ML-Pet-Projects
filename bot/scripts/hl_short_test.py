#!/usr/bin/env python3
"""
Standalone test script: place a market SHORT on Hyperliquid with optional SL/TP triggers.

What you need to run this file:
- Python 3.10+
- pip install hyperliquid-python-sdk
- A private key (hex) of an EVM wallet authorized on Hyperliquid
- Choose network: testnet or mainnet (recommended testnet first)

How it works:
- Creates Exchange with LocalAccount from your private key
- Places a market short (market_open with is_buy=False via aggressive limit IoC)
- Optionally places trigger exits (reduce-only, isMarket=True):
  - TP: triggers on price drop (for short)
  - SL: triggers on price rise (for short)

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
# Replace with your testnet wallet key. Keep this file out of version control if you put real keys.
PRIVATE_KEY_HEX: str = "0xYOUR_PRIVATE_KEY_HEX"

# Symbol selection
# For SDK, use coin name like "ETH", not "ETHUSDT". We'll map below if needed.
SYMBOL: str = "ETHUSDT"  # You can put "ETH", script will map ETHUSDT->ETH

# Order params
QTY: float = 0.01  # position size (coins)
TAKE_PROFIT_PCT: Optional[float] = 1.0  # % below entry (short). None to skip
STOP_LOSS_PCT: Optional[float] = 1.0    # % above entry (short). None to skip

# Slippage for market_open pricing (SDK uses aggressive limit IoC)
SLIPPAGE: float = 0.02  # 2%


# ============================
# IMPLEMENTATION
# ============================

@dataclass
class OrderResult:
	ok: bool
	msg: str


def coin_from_symbol(symbol: str) -> str:
	if symbol.endswith("USDT"):
		return symbol[:-4]
	if symbol.endswith("USDC"):
		return symbol[:-4]
	return symbol


def main() -> None:
	if not PRIVATE_KEY_HEX or PRIVATE_KEY_HEX.endswith("YOUR_PRIVATE_KEY_HEX"):
		raise SystemExit("Please set PRIVATE_KEY_HEX to your testnet key before running.")

	wallet: LocalAccount = Account.from_key(PRIVATE_KEY_HEX)
	base_url = TESTNET_API_URL if USE_TESTNET else MAINNET_API_URL
	ex = Exchange(wallet=wallet, base_url=base_url)
	info = ex.info

	coin = coin_from_symbol(SYMBOL)

	# Get mid as reference entry price
	mids = info.all_mids()
	if coin not in mids:
		raise SystemExit(f"Coin {coin} not found in mids: keys={list(mids.keys())[:10]} ...")
	mid = float(mids[coin])
	print(f"Placing SHORT on {coin}, mid ~ {mid}")

	# Market short (is_buy=False)
	# SDK market_open computes aggressive limit with slippage and uses IoC.
	resp = ex.market_open(name=coin, is_buy=False, sz=QTY, px=mid, slippage=SLIPPAGE)
	print("Market short response:", resp)

	# Compute TP/SL absolute levels relative to mid (approx entry)
	tp_px: Optional[float] = None
	sl_px: Optional[float] = None
	if TAKE_PROFIT_PCT is not None:
		tp_px = mid * (1.0 - TAKE_PROFIT_PCT / 100.0)
		print(f"TP set at {tp_px}")
	if STOP_LOSS_PCT is not None:
		sl_px = mid * (1.0 + STOP_LOSS_PCT / 100.0)
		print(f"SL set at {sl_px}")

	# Place triggers (reduce-only, isMarket=True)
	if tp_px is not None:
		resp_tp = ex.order(
			name=coin,
			is_buy=True,  # close short
			sz=QTY,
			limit_px=tp_px,
			order_type={"trigger": {"isMarket": True, "triggerPx": tp_px, "tpsl": "tp"}},
			reduce_only=True,
		)
		print("TP trigger response:", resp_tp)

	if sl_px is not None:
		resp_sl = ex.order(
			name=coin,
			is_buy=True,  # close short
			sz=QTY,
			limit_px=sl_px,
			order_type={"trigger": {"isMarket": True, "triggerPx": sl_px, "tpsl": "sl"}},
			reduce_only=True,
		)
		print("SL trigger response:", resp_sl)

	print("Done. Monitor orders on Hyperliquid UI.")


if __name__ == "__main__":
	main()