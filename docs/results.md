# Results

The plan's tests, run once on 12 October 2026 on the [frozen dataset](dataset.md): 120 events on 79 companies, from 138 Kalshi ladders. The full output is in `data/study.json`. Returns are in percentage points, net of SPY. Research prototype, not investment advice.

## In brief

- The market's forecast is accurate. It missed the reported figure by a median of 1.2%: by 0.3% or less for a quarter of the figures, and by 4.4% or less for 3 quarters of them. Its middle half, from the 25th to the 75th percentile, contained the reported figure 71 times in 125, or 57%. A well-calibrated market would be near 50%, so its spread runs slightly wide.
- It is far ahead of a simple forecast. Outside the plan, it came closer than the same quarter a year earlier on 124 of 137 figures, and closer than the quarter before on 118 of 135. Its lead is narrower on growth rates such as comparable sales.
- Whether a beat or a miss moves the share is unresolved. Results day went 3.8 points better after a beat than after a miss, but the 95% interval runs from −0.4 to +8.0 points, so by the plan's rule the difference is not measurable. This sample could reliably detect only a gap of 6.1 points or more.
- Beats were followed by a rise less than half the time: 31 of 68. Misses were followed by a fall 30 times in 52.
- The largest moves against the surprise came from the rest of the report. For each of the 10, the news named guidance, profit or another figure.
- Nothing else showed. A wider spread of expectations did not come with bigger moves (a rank correlation of −0.09), and shares did not keep drifting in the surprise's direction over the next 20 or 60 sessions.

## The tests

| Test | Events | Result | 95% interval | Smallest detectable |
|---|---|---|---|---|
| Primary: results day, beats minus misses | 120 on 69 results days | +3.8 points | −0.4 to +8.0 | 6.1 points |
| 2 sessions, beats minus misses | 120 | +4.2 points | −0.5 to +8.9 | 6.8 points |
| Accuracy: median gap as a share of the figure | 138 ladders | 1.2% | | |
| Reported figure inside the middle half | 125 ladders | 57% | | |
| Beats followed by a rise | 68 | 31, or 46% | | |
| Misses followed by a fall | 52 | 30, or 58% | | |
| Spread against move size, rank correlation | 107 | −0.09 | | |
| Exploratory: drift over 20 sessions | 117 | −0.9 points | −5.8 to +4.7 | 7.5 points |
| Exploratory: drift over 60 sessions | 50 | +7.0 points | −4.3 to +20.3 | 17.6 points |
| Exploratory: slope on the standardised surprise | 107 | +1.6 points per spread | −1.1 to +5.2 | |

All returns are the share's minus SPY's over the same sessions. Each interval comes from 10,000 resamples of results dates, with the seed fixed.

## Against a simple forecast

Outside the plan, added after the study ran ([how](benchmark.md)). Codex cited each figure for the same quarter a year earlier and for the quarter before from the companies' own publications, and Python checked every citation. The output is in `data/benchmark.json`.

| Simple forecast | Figures | Market's median gap | Forecast's median gap | Market closer |
|---|---|---|---|---|
| The same quarter a year earlier | 137 | 1.2% | 13.4% | 124 |
| The quarter before | 135 | 1.2% | 6.7% | 118 |
| Growth rates only, against the year before | 23 | 0.74 points | 3.30 points | 18 |
| Growth rates only, against the quarter before | 23 | 0.74 points | 1.10 points | 16 |

Gaps are shares of the reported figure, as in the accuracy test, except for growth rates and margins, which are in points: a share of a small rate inflates every gap.

So the market's accuracy is not what anyone gets by repeating the last figure. Its median gap was 11 times smaller than the year-earlier figure's and 6 times smaller than the quarter before's. On growth rates, where the quarter before is already a fair guess, its lead is narrower.

## Moves against the surprise

The plan has Codex explain the 10 largest results-day moves against the surprise: a beat followed by a fall, or a miss followed by a rise. For each, Codex cited the company's release and news published by the end of results day, and `mef explanations` checked every passage at its locator and refused anything published later. The citations are in `data/explanations.json`.

| Company | Results day | The figure | Move, net of SPY | What the cited news named |
|---|---|---|---|---|
| Palantir | 4 August 2026 | Missed on customers | +27.7 points | A higher annual revenue forecast |
| Klarna | 14 May 2026 | Missed on active consumers | +19.5 points | Revenue and operating profit ahead of expectations |
| Snowflake | 3 September 2026 | Missed on $1m customers | +15.5 points | A higher annual product revenue forecast |
| Coinbase | 1 August 2025 | Beat on volume | −15.1 points | Lower adjusted profit; transaction revenue below estimates |
| Victoria's Secret | 3 September 2026 | Beat on comparable sales | −14.2 points | Quarterly profit guidance below estimates |
| CAVA | 12 August 2026 | Missed on restaurants | +14.0 points | Same-restaurant sales of 9.0%, against about 7.1% expected |
| Hims & Hers | 12 May 2026 | Beat on subscribers | −14.0 points | Gross margin down to 65% from 73%, and a surprise loss |
| Norwegian Cruise Line | 30 July 2026 | Beat on passengers | −11.5 points | A lower annual profit forecast and weak bookings |
| Altria | 30 July 2026 | Beat on cigarette shipments | −11.0 points | Earnings per share below forecasts |
| Chewy | 9 September 2026 | Beat on active customers | −10.4 points | Free cash flow short of expectations |

Each time, the news named something other than the contract's figure: guidance 4 times, profit, margin or cash 5 times, and another figure once. This fits the wide interval in the primary test: on results day, the figure is a small part of the report.

## Outside the plan

These are descriptive, not tests the plan set, so they may be chance.

- Misses fell and beats did not rise. Misses averaged −3.7 points and beats +0.1, so the whole of the gap came from the misses.
- Moves were large next to the gap. The median results-day move, up or down, was 5.0 points, so a gap of a few points between beats and misses explains little of them.

## What it means

For an individual investor, Kalshi's ladders are a good, free read of what a company is expected to report: far closer than a simple forecast, updated live, and expressed as a distribution. How they compare with the analysts' consensus, which is paid for, was not tested.

The figure is only part of what moves a share on results day, though. Guidance, margins and the market's reading of the whole report carry the rest, and in this sample a beat was followed by a fall more often than by a rise. The market's forecast tells an investor what is expected, not which way the share will go. Whether a miss costs more than a beat gains, as this sample hints, needs the larger sample that the third-quarter reports add.

## What comes next

- The third-quarter reports, from mid-October to early December 2026, will be put through the same tests once, after the last report, on about 100 events that did not exist when the plan was filed. The primary test will also be run on both samples together ([plan](plan.md), addendum 6).
- Before those reports, Codex filed forecasts for 11 figures that public data measures during the quarter ([replication](../replication/README.md)). They will be scored against the market's.

## Limits

- **The sample.** 120 events on 79 companies, 105 of them in 2026. The names are popular with individual traders, and Tesla alone has 8 events.
- **The cause.** Results days carry the whole report, so the tests measure association, not a figure's own effect.
- **The benchmark.** Returns are net of SPY, not of each share's sector or sensitivity to the market.
- **The comparison.** The simple forecasts are a low bar. The market was not compared with the analysts' consensus.
- **The timing.** Had a figure come out before the release Codex cited, the market's prices would already show it. None did: at the cutoff, each of the 138 ladders still had a threshold priced between 5% and 95%.
