# Dataset

Frozen on 12 October 2026, before the study ran. `data/events.json` has SHA-256 `87f59c3b153375b0f29ec5c642512087239e4fcbfc699173ebfab2b95517a38c`. Research prototype, not investment advice.

## How it was built

1. **Ladders.** Kalshi listed 197 company-figure ladders on 95 companies that resolved between 12 October 2024 and 12 October 2026. They come from the series whose contract terms settle on a figure a company reports.
   - 148 state the settled figure as a number. 22 of those were converted from other units to the thresholds' units, as addendum 3 sets out, and all 148 agree with every threshold's settlement.
   - 49 state only a bound, such as "above 3.6 billion". For these, the figure Codex cited from the company is used.
2. **The market's expected figure.** Kalshi's daily candles give each of the 1,602 thresholds its price at the last daily close before the report's date. The price is the mid of the bid and ask, or the last trade where one side was missing.
3. **Codex's verification.** 5 Codex sessions, 4 batches and 1 retry, cited for each ladder the report's date and time and the figure the company published. Python checked every citation at its locator in the saved copy of its source.
   - **Verified with a time of day:** 178 ladders.
   - **Unverifiable:** 15. The reasons were investor sites that refused automated reading, figures published only where no passage could be cited, and rules without units.
   - **No citable time of day:** 4.
   - **Definition differences:** Codex flagged 7, and none changed a beat or a miss.
4. **Share prices.** Massive supplied split-adjusted daily closes for 94 of the companies and for SPY, and each company's identity from its ticker reference.

## What was excluded

| Reason | Ladders |
|---|---|
| Report time not cited | 19 |
| No cited figure agrees with the settlements | 9 |
| Expected figure not computable: the priced thresholds sit on 1 side of 50%, or fewer than 2 are priced | 22 |
| No threshold traded in the 10 days before the report | 1 |
| Outside the universe: below $20m a day | 3 |
| Outside the universe: an ADR | 2 |
| Outside the universe: an ETF | 1 |
| Outside the universe: no ticker reference | 2 |
| Kept | 138 |

## Events

The 138 kept ladders give 120 events, 1 per company and results day.
- **Spread:** 79 companies and 69 results days.
- **Outcomes:** 68 beats and 52 misses of the market's expected figure.
- **Dates:** 15 events fall in 2025 and 105 in 2026.
- **Drift:** 50 events have 60 sessions of prices after results day.
- **Concentration:** Tesla has 8 events, Coinbase 6 and Meta 5.

## Corrections before the study

**A pricing rule stricter than the plan.** The first assembly dropped a ladder whenever any of its thresholds had no price before the report. That is stricter than the plan, which reads the median from the priced thresholds and calls it not computable only when it falls outside them. The first assembly left 75 events. The count of exclusions, not any return, showed the problem: 62 of the 84 ladders dropped as not computable did bracket 50% among their priced thresholds. The code and its test were corrected to the plan's rule, and the dataset was rebuilt. The first assembly had computed returns, but none was examined, and the study had not run.

**Verification instructions narrower than the plan.** They first asked for the figure from the company's release, where the plan says "as the company published it". They were corrected to any document the company published. A citation of a release page's recorded publication time was also allowed. A retry pass then ran on the 43 unresolved ladders and verified 28 of them.

## Files

- **`data/events.json`:** every ladder, with its expected and reported figure and any exclusion, and the 120 events with their returns net of SPY.
- **`data/verifications.json`:** Codex's verification of each ladder, with its citations.
