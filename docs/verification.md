# Verifying an event

Codex's task for each ladder in the study: cite when the company's report came out and what figure it published, and say whether that figure is the quantity the contract settles on. Python checks every citation and decides everything else. Research prototype, not investment advice.

## What to cite

1. **When the report came out.** Cite the release's date and its time of day, and give both as `report_time` with its New York offset, such as `2026-08-11T16:05:00-04:00`. The time can come from:
   - the release itself;
   - the company's earlier announcement of the report, such as "will report results after the market close on August 11";
   - the time a wire service shows on the release's page;
   - the publication time the release's page records, which `mef read` lists as `published_at`. Cite it with the locator `published_at` and that time, exactly, as the excerpt.

   Without a citable time of day, the event is excluded.
2. **The figure as the company published it,** in its release, shareholder letter, presentation or filing. Give it as text in `figure_as_published`, and as a number in the contract's units in `figure_value`. For example, 9.0% same-restaurant sales growth is `9.0`, and 358,023 deliveries is `358023`.
3. **Whether it is the contract's figure.** Read the contract's rules and compare its definition, units, rounding, segment and period with the published figure. Set `matches_contract` to true or false, and describe any difference in `mismatch`.

A wire service's copy of the release, or a syndicated one, counts as the release. Several ladders on 1 report share its time and can cite the same passage.

## How to read and quote

- Read every source with `mef read <url> --sources runs/sources --find <words>`.
- Quote only the passages it lists, word for word, with their locators.
- Never use what you remember about the company or about how its shares moved, and never look up share prices: the study must not see returns through you.

## File format

Write a JSON file under `runs/verify/` with a list under `verifications`, 1 entry per ladder:

```json
{
  "verifications": [
    {
      "ladder": "KXCAVA-26AUGCOMP",
      "report_time": "2026-08-11T16:05:00-04:00",
      "report_citations": [
        {"url": "https://...", "locator": "paragraph-0001", "excerpt": "Aug. 11, 2026 -- CAVA Group, Inc. today reported"},
        {"url": "https://...", "locator": "paragraph-0003", "excerpt": "will report results after the market close"}
      ],
      "figure_as_published": "9.0%",
      "figure_value": 9.0,
      "figure_citation": {"url": "https://...", "locator": "paragraph-0007", "excerpt": "Same restaurant sales growth of 9.0%"},
      "matches_contract": true
    },
    {"ladder": "KXEXAMPLE-26AUG", "unverifiable": "The company's releases and every copy refused automated reading"}
  ]
}
```

Run `mef verify runs/verify/<file>.json --sources runs/sources` until every entry passes. Give an entry you cannot verify `unverifiable` with its reason, rather than leaving it out.
