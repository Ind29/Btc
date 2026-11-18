"""Deterministic, long-only cbBTC/USDC bot for agent-fun/bars-replay/v1.

Strategy: enter a confirmed rebound after a deep 12-bar pullback; exit on a
fee-inclusive profit/loss threshold or a maximum holding period. No network,
clock, external packages, leverage, or short selling.
SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import os
import sys
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
MAX_SLIPPAGE_BPS = 100

# Parameters selected by a deterministic sweep on the published 1,440-bar dev
# window. All signal comparisons use integer arithmetic to avoid float drift.
PULLBACK_BPS = 100       # close at least 1.00% below the rolling 12-bar high
REBOUND_BARS = 3
REBOUND_MIN_BPS = 5      # last 3-bar return must be at least +0.05%
LOOKBACK_BARS = 8
LOOKBACK_FLOOR_BPS = -200  # 8-bar return must be no worse than -2.00%
TAKE_PROFIT_BPS = 100    # measured against fee-inclusive position cost
STOP_LOSS_BPS = 150
MAX_HOLD_BARS = 45


class Strategy:
    def __init__(self) -> None:
        self.closes: deque[int] = deque(maxlen=12)
        self.entry_fill_seq: int | None = None

    def on_batch(self, state, batch):
        bar = next((item for item in batch["bars"] if item["symbol"] == SYMBOL), None)
        if bar is None:
            return []

        close = int(bar["c"])
        self.closes.append(close)
        if state.warming_up:
            return []

        held = state.positions.get(SYMBOL)
        if held is not None:
            # Position first appears in the batch after its order filled.
            if self.entry_fill_seq is None:
                self.entry_fill_seq = state.seq

            marked_value = state.value(SYMBOL, held.qty)
            take_profit = marked_value * 10_000 >= held.cost * (10_000 + TAKE_PROFIT_BPS)
            stop_loss = marked_value * 10_000 <= held.cost * (10_000 - STOP_LOSS_BPS)
            time_exit = (
                self.entry_fill_seq is not None
                and state.seq - self.entry_fill_seq >= MAX_HOLD_BARS
            )
            if take_profit or stop_loss or time_exit:
                self.entry_fill_seq = None
                return [{
                    "side": "sell",
                    "symbol": SYMBOL,
                    "qty": held.qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]
            return []

        self.entry_fill_seq = None
        # Need 12 closes for the pullback high, plus 8 bars for the floor test.
        if len(self.closes) < 12:
            return []

        closes = list(self.closes)
        high_12 = max(closes)
        close_3_ago = closes[-(REBOUND_BARS + 1)]
        close_8_ago = closes[-(LOOKBACK_BARS + 1)] if len(closes) > LOOKBACK_BARS else None
        if close_8_ago is None:
            return []

        deep_pullback = close * 10_000 <= high_12 * (10_000 - PULLBACK_BPS)
        rebound_confirmed = close * 10_000 >= close_3_ago * (10_000 + REBOUND_MIN_BPS)
        not_collapsing = close * 10_000 >= close_8_ago * (10_000 + LOOKBACK_FLOOR_BPS)

        if deep_pullback and rebound_confirmed and not_collapsing:
            max_weight_bps = state.hello["caps"]["max_weight_bps"]
            spend = min(state.cash, state.equity * max_weight_bps // 10_000)
            minimum = int(state.hello["fees"]["min_notional_quote_units"])
            if spend >= minimum:
                return [{
                    "side": "buy",
                    "symbol": SYMBOL,
                    "notional_quote_units": spend,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]

        return []


if __name__ == "__main__":
    strategy = Strategy()
    makefun_bars.run(strategy.on_batch)
