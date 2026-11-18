# cbBTC/USDC Trading Bot — make.fun BTC Race 24H

A deterministic, long-only Python bot for the `agent-fun/bars-replay/v1` protocol.
It trades the competition's `CBBTC` symbol against USDC using only the Python
standard library and the competition's vendored Python SDK shim.

## Strategy

The bot looks for a confirmed rebound after a deep short-term pullback:

- Pullback: close is at least 1.00% below the highest close in the latest 12 bars.
- Rebound confirmation: the 3-bar return is at least +0.05%.
- Downtrend guard: the 8-bar return is no worse than -2.00%.
- Entry: uses available cash up to the harness `max_weight_bps` cap.
- Exit: +1.00% take-profit, -1.50% stop-loss, or 45 bars after the fill.
- Slippage ceiling: 100 bps; no shorts, leverage, external services, or real funds.

Signal checks use integer arithmetic. Orders are decided at a bar close and,
per the competition protocol, fill at the next bar's open.

## Files

```text
main.py
README.md
LICENSE
vendor/
  makefun_bars.py
```

`vendor/makefun_bars.py` is the unmodified Python SDK shim supplied in the
competition kit. It is included because the sandbox has no package-install step.

## Local development

The competition runtime is Python 3.13. From this directory:

```bash
python -m py_compile main.py vendor/makefun_bars.py
python -m unittest discover -s vendor -p 'test_*.py'
```

For the official local grade, use the competition kit's exact command from the
unpacked kit directory:

```bash
node cli/makefun.mjs grade-local --kit . --bot /path/to/this/repository --driver docker
```

The official grader verifies the kit and dataset, executes the bot twice, and
checks that both action logs match byte for byte. A successful dev gate requires
net PnL strictly above 0 USDC after fees, slippage, and price impact.

## Validation status

A separate deterministic local replay was used to tune the entry/exit
thresholds against the published 1,440-bar dev dataset and the market equations
in the kit. That advisory replay estimated **+9.797551 USDC net PnL**, one
completed round trip (one buy and one sell), and approximately **0.1221%**
maximum drawdown. This is not an official `grade-local` result. The official
Docker grader has not been run in this environment; do not claim `dev_profitable`
until the official grader reports it.

## License

MIT. See `LICENSE`.
