# Against a simple forecast

Outside the plan, added on 12 October 2026 after the study ran. The study found that the market's expected figure missed the reported one by a median of 1.2%. This compares that gap with 2 simple forecasts any investor could make, on the same ladders:

- **The year before:** the figure for the same quarter a year earlier.
- **The quarter before:** the figure for the previous quarter.

Research prototype, not investment advice.

## What Codex cites

For each ladder the accuracy test kept, Codex cites from the company's own publications the same figure for the same fiscal quarter a year earlier, and for the fiscal quarter before. It must be the quantity the contract settles on, in the contract's units, as the reported figure is in `data/events.json`. The release Codex cited for the reported figure often states the year-earlier figure in the same table.

Write a JSON file under `runs/comparatives/` with a list under `comparatives`, 1 entry per ladder:

```json
{
  "comparatives": [
    {
      "ladder": "KXCAVA-26AUGCOMP",
      "year_ago": {
        "period": "Q2 2025",
        "as_published": "14.4%",
        "value": 14.4,
        "citation": {"url": "https://...", "locator": "paragraph-0012", "excerpt": "..."}
      },
      "previous_quarter": {
        "period": "Q1 2026",
        "as_published": "10.8%",
        "value": 10.8,
        "citation": {"url": "https://...", "locator": "table-0003/row-0004", "excerpt": "..."}
      }
    }
  ]
}
```

- Give `null` for a figure the company's publications do not state, and give the entry `unverifiable` with the reason when neither can be cited.
- Read every source with `mef read` and quote only the passages it lists, word for word, with their locators, as [verification](verification.md) describes. Never look up share prices or how shares moved.
- Run `mef comparatives runs/comparatives/<file>.json --sources runs/sources` until every entry passes.

## How it is compared

`mef benchmark` takes each forecast's ladders and compares the market's median gap with the forecast's, using the accuracy test's measure: the gap as a share of the reported figure. It also counts how often each came closer, and compares growth rates and margins again in points, since a share of a small rate inflates every gap. They are told apart by their titles. It needs only `data/events.json` and `data/comparatives.json`, the citations `mef comparatives` checked, so it reruns from a clean copy of the repository. The results are in [results](results.md).
