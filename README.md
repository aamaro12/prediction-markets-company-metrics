# Prediction markets on company metrics

Kalshi, a US prediction market, lists contracts on the numbers companies report each quarter: Tesla's deliveries, Uber's trips, CAVA's same-restaurant sales and many more. Before a report, the prices on those contracts together give a forecast of the number. This project looks at how good those forecasts are, and whether a company beating or missing them says anything about its share price.

It covers 120 company reports from late 2024 to 2026. The analysis plan was written before any share return was computed, and every reported figure was checked against the company's own release. Codex, OpenAI's coding agent, found and quoted the sources. Python checked each quote against a saved copy of its source and did all the calculations.

This is a research prototype, not investment advice.

## Findings

- The forecasts are accurate. The median gap between the market's forecast and the reported figure was 1.2%, across 138 metrics.
- They are far better than a naive guess. The market was closer than the figure for the same quarter a year earlier in 124 of 137 cases, and closer than the previous quarter's figure in 118 of 135.
- A beat is no guide to the share price. Only 31 of 68 beats were followed by a rise on results day, relative to the S&P 500 (SPY).
- Whether beats do better than misses is still open. On average, shares did 3.8 percentage points better after a beat than after a miss, but the 95% confidence interval runs from −0.4 to +8.0, so this sample cannot tell whether the difference is genuine.
- The biggest surprises came from elsewhere in the report. For the 10 largest moves against the surprise, such as a beat followed by a fall, the news pointed to guidance, profit or another metric each time.

So these markets are a good, free guide to what a company is expected to report, but not to how its shares will react. The full results are in [docs/results.md](docs/results.md).

## How the study works

Kalshi's contracts on a company metric come as a ladder: "will the company report more than X?" for several values of X. The prices across a ladder give a probability for each threshold, and the median of that distribution is the market's forecast. The study takes it from the last daily close before the day of the report.

The data covers every such ladder that settled between October 2024 and October 2026: 197 ladders on 95 companies. For each one, Codex cited when the company's report came out and the figure it published, and flagged any difference from the contract's definition. 138 ladders passed every check, giving 120 events on 79 companies. The dataset was frozen before the tests ran, and each test was run once.

Share prices come from Massive. Returns are measured against SPY on results day, the first trading session that can react to the report, and the confidence intervals come from resampling the results dates 10,000 times. [docs/plan.md](docs/plan.md) has the plan and its 6 dated addenda, and [docs/dataset.md](docs/dataset.md) explains what was left out and why. The working history that timestamps these steps is kept private.

## Forecasts for the third quarter of 2026

Before the third-quarter reports, Codex also filed its own forecasts for 11 metrics that public data tracks during the quarter, such as airline passenger numbers from US government statistics. Once the last of those companies has reported, in early December, each forecast will be scored against the market's, and the main tests will be run again on the new reports. See [replication/README.md](replication/README.md).

## Repository layout

| Folder | Contents |
|---|---|
| `docs/` | The plan, how the dataset was built, the results, and the instructions Codex worked from |
| `data/` | The frozen dataset, Codex's cited work and the test outputs |
| `replication/` | The third-quarter forecasts |
| `src/mef/` | The `mef` command-line tool |
| `tests/` | Offline tests |

## Reproducing the results

With Python 3.12:

```sh
python3.12 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests
.venv/bin/mef study --events data/events.json --output runs/study.json
.venv/bin/mef benchmark --events data/events.json --comparatives data/comparatives.json --output runs/benchmark.json
```

The last 2 commands regenerate `data/study.json` and `data/benchmark.json` exactly.

Rebuilding the dataset from scratch also needs curl, network access, a contact address in `MEF_USER_AGENT` and a `MASSIVE_API_KEY` for share prices. The steps are `mef ladders`, `mef candles`, `mef prices`, the verification checked by `mef verify` (see [docs/verification.md](docs/verification.md)), then `mef events`.

## Licence

MIT. This is version 1.0.0; see the [changelog](CHANGELOG.md).
