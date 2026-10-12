# Forecasts for the third quarter of 2026

Before the third-quarter 2026 reports, Codex filed forecasts for figures that public data measures during the quarter. The plan and the `mef` tool call them estimates. After the last report, each forecast and the market's are scored against the reported figure with the continuous ranked probability score. The [plan](../docs/plan.md) fixed this in advance, and [docs/estimates.md](../docs/estimates.md) sets the format and the deadlines. Research prototype, not investment advice.

## What was filed

- On 12 October 2026, Kalshi listed 121 open ladders on third-quarter company figures (`open-q3.json`).
- For each one, Codex looked for public data that measures the figure during the quarter, with citations (`triage.json`). It found such data for 16.
- Codex filed forecasts for 11 of the 16 (`estimates/`), each with the script that computes it (`scripts/`). All 11 pass `mef estimate-check`, and all were filed on 12 October 2026, before any of the figures was released.
- For the other 5, the public data Codex could read does not measure the contract's figure, and Codex declined to fill the gap with assumptions:
  - American's and Alaska's load factors: the government's monthly airline data that Codex could read gave seats and passengers, but a load factor needs passenger miles and seat miles for the whole group.
  - Rocket Lab's vehicles launched: its Electron launches are public, but not all of the HASTE launches the figure may also count.
  - Talen's generation: the government's monthly generation by plant comes as spreadsheets in an archive, which `mef read` cannot open, and the daily reactor reports cover only its nuclear plant, about half its output.
  - Nu's customers: the public counts are rounded milestones, such as over 140 million in Latin America, not the global count at the end of September.

## Codex and the market on 12 October

Both medians are read the same way: Codex's from its forecast, and the market's from its prices on 12 October 2026 at 15:15 UTC. The scoring uses the market's prices at each deadline, not these.

| Figure | Codex's median | Market's median | Results date |
|---|---|---|---|
| United passengers | 51.35m | 50.15m | 20 October |
| Southwest seats flown | 57.10m | 57.37m | 21 October |
| Boeing commercial deliveries | 159.5 | 160.2 | 27 October, deliveries earlier |
| Robinhood funded customers | 28.67m | 28.66m | 27 October |
| Robinhood event contracts traded | 15.1bn | 17.0bn | 27 October |
| Schwab active brokerage accounts | 40.21m | 40.26m | no date cited |
| eToro funded accounts | 4.36m | 4.37m | no date cited |
| CAVA restaurants | 501.2 | 500.5 | no date cited |
| CAVA same-restaurant sales growth | 4.3% | 4.4% | no date cited |
| Petrobras production, thousand boe a day | 3,497 | 3,446 | no date cited |
| Venture Global LNG sold, TBtu | 446 | 471 | no date cited |

Boeing releases its deliveries before its results, and that earlier release sets the deadline. So does any monthly report that carries September.

## Where they differ most

- Robinhood's event contracts. 6.1bn were traded in July and 4.7bn in August. The market's median needs about 6.2bn in September; Codex's needs about 4.3bn. The market became confident on 9 October, when its chance of more than 18bn fell from about 20% to 2%. No Robinhood release that day was found, and the monthly releases found cover only the first 2 months of a quarter, so September comes with the results.
- United's passengers. The government's July count of passengers on United's flights rose 6.1% on a year earlier. Codex carries that growth to the quarter, 6.1% above last year's 48.38m; the market's median implies 3.7%.
- Venture Global's LNG. The government's July exports from its 2 plants were 148.1 Bcf, below the second quarter's monthly average of 153.2 Bcf, when it sold 466.4 TBtu. Codex's median is 446 TBtu, the market's 471.
- Petrobras's production. The regulator's data for its share of Brazil's fields rose from 3.45m boe a day in July to 3.60m in August. Codex's median is 3,497 thousand boe a day, the market's 3,446.

## Files

- `open-q3.json`: the 121 open ladders, with their contract rules and thresholds, as listed on 12 October 2026.
- `triage.json`: Codex's triage of each ladder, with its citations.
- `estimates/`: Codex's 11 forecasts, in the format [docs/estimates.md](../docs/estimates.md) sets.
- `scripts/`: the script behind each forecast. Each ran in Codex's working folder, next to the 2 files above and the saved copies of the cited sources, and uses no network access and no market prices.

## After the reports

After the last third-quarter report, Codex cites when each figure was first released, as it did for the dataset, and that release sets the deadline. Each forecast, and the market's prices at the same cutoff, are then scored with the continuous ranked probability score.
