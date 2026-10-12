# Estimating a third-quarter figure

The plan's replication asks Codex to estimate the third-quarter figures that public data measures during the quarter, before each company reports, and scores Codex's estimate against the market's. Research prototype, not investment advice.

## What to file

1 file per ladder, `runs/replication/estimates/<ladder>.json`, written before the company's report. Each file is then copied to `replication/estimates/` and pushed, so the repository's history dates it. A later estimate may replace an earlier one; the one scored is the last filed before the deadline.

The deadline is midnight New York time at the start of the day the company first releases the figure. For some figures that release comes before the results: Boeing's deliveries have a release of their own, and a monthly operating report can carry a quarter's last month ([plan](plan.md), addendum 5). The `report_date` an estimate gives is Codex's reading; the verified release sets the deadline.

```json
{
  "ladder": "KXSCHW-26OCTACCTS",
  "report_date": "2026-10-15",
  "filed_at": "2026-10-13T15:00:00+00:00",
  "chances": [{"strike": 40000000, "above": 0.62}, {"strike": 40300000, "above": 0.48}],
  "inputs": [{"url": "https://...", "locator": "table-0002", "excerpt": "...", "claim": "July's new brokerage accounts"}],
  "method": "How the cited inputs give each chance, in 2 to 4 sentences."
}
```

- `chances` gives, for every threshold of the ladder, the chance that the reported figure is above it. The chances must fall as the threshold rises.
- `inputs` cite the data that measures the quarter, read with `mef read` and quoted word for word.
- `method` says how those inputs give the chances. An analysis script may sit beside the file.

You may read the market's prices. The test is whether public data adds anything to them, so copying them is allowed, but it scores no better than the market.

Run `mef estimate-check runs/replication/estimates/<ladder>.json --open runs/replication/open-q3.json --sources runs/sources` until it passes.

## How it is scored

After the report, each estimate and the market's prices are scored on the same ladder with the continuous ranked probability score. Over a ladder's thresholds, this is the sum of each squared gap between a chance and the outcome, weighted by the distance to the next threshold. Lower is better. The market's prices are read as the plan defines them: at the last daily close before the report's date.
