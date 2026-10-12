# Analysis plan

Filed on 12 October 2026, before any share return was computed. A change after that date goes in a dated addendum at the end, with its reason, never into the text above it. Research prototype, not investment advice.

## Questions

When a company reports a figure that Kalshi priced beforehand, such as deliveries, users or same-store sales:

1. How close was the market's expected figure to the reported one?
2. How did the share move on results day when the company beat the market's expected figure, against when it missed? This is the primary test.
3. Did a wider spread of market expectations come with a bigger results-day move?
4. Did the share keep moving in the surprise's direction over the next 20 and 60 trading days? This is exploratory.

Question 2 measures the gap between a share's value after a beat and after a miss. The first iteration of this work could not cite that gap for any single case.

## Sample

**Contracts.** A company-figure ladder is a set of Kalshi contracts on 1 reported figure: "Will <company> report above <X> <figure> in <period>?" at several thresholds X. The population is every such ladder that resolved between 12 October 2024 and 12 October 2026, the span that 2 years of share prices can cover.

**Companies.** US common stocks listed on NYSE, Nasdaq or NYSE American, trading at least $20m a day over the 20 sessions before the report. Funds, ETFs and ADRs are out.

**Events.** 1 per company and results day. Where a company reports several priced figures on 1 day, the ladder with the most contracts traded in the 30 days before the report counts; the others serve question 1 only.

**Expected size.** The first iteration priced 157 reported figures. 144 fall inside the price window, on 129 results days. The rebuilt sample prices every threshold and may be larger.

## Definitions

**Report time.** The publication time of the company's release, which Codex cites from the release itself. A release before 09:30 New York time makes that day results day; one at or after 16:00, or on a day without a session, makes the next session results day.

**The market's expected figure.** Each threshold is priced at the venue's last daily close before the report's date, which ends at midnight New York time, so no price can follow the report.
- The price is the mid of the bid and ask where both exist, else the last trade.
- The probabilities of "above X", made to fall as X rises, give a distribution.
- Its median is the market's expected figure, interpolated between the 2 thresholds that bracket 50%.
- Its 25th and 75th percentiles give the spread.
- A median outside the priced thresholds is not computable.

**The reported figure.** The figure the ladder settled on. Codex cites the figure as the company published it and says whether it matches the contract's rules: definition, units, rounding, segment and period.

**Beat and miss.** A beat is a reported figure above the market's expected figure, and a miss is one below it; equal figures are dropped. The standardised surprise is the difference divided by the spread.

**Returns.** Daily closes adjusted for splits. A return is the share's minus SPY's over the same sessions.
- **Results-day return:** from the close before results day to the close of results day.
- **2-session return,** a secondary measure: to the close of the next session.
- **Drift:** from the close of results day to the close 20 and 60 sessions later.

## Tests

**Primary.** The mean results-day return of beats minus that of misses. Its 95% interval comes from 10,000 bootstrap resamples that draw results dates rather than events, so events on 1 day move together. With about 130 events and a results-day spread of about 10 points, the smallest gap this test can reliably detect is about 5 points. The report states the detectable gap computed from the sample itself.

**Secondary.**
- **Accuracy:** the median absolute gap between expected and reported figures, as a share of the reported figure. Also the share of reported figures inside the market's 25th to 75th percentiles, which a well-calibrated market puts near 50%.
- **Direction:** the share of beats followed by a positive results-day return, and of misses followed by a negative one.
- **Spread and move size:** the rank correlation between the spread, as a share of the expected figure, and the absolute results-day return.

**Exploratory.**
- **Drift over 20 and 60 sessions,** beats minus misses, reported with its detectable gap. With about 65 events that have 60 sessions of history, only a drift above about 11 points could be detected.
- **The slope** of results-day returns on the standardised surprise.

## Exclusions

An event is excluded, with the reason recorded, when:
- its stock falls outside the universe on the report date;
- Codex cannot cite the report's time from the company's release;
- the market's expected figure is not computable, or no threshold traded in the 10 days before the report;
- Codex finds that the contract's figure differs from the company's published figure in a way that would change the beat or miss.

The last group is also reported on its own: it is where reading the market's price at face value misleads.

## What Codex does

- **For each event,** Codex cites the release's date and time, and the reported figure, and says whether that figure matches the contract's rules.
- **For the 10 largest results-day returns against the surprise,** it cites the news that explains them, such as guidance or a deal.
- **Python checks** that every citation exists at its locator, in a document published by the time it describes.

## Replication on the third quarter of 2026

The third-quarter reports, from mid-October to early December 2026, are a replication fixed in advance. It uses the same definitions and tests, run once after the last of them is reported, on events that did not exist when this plan was filed.

Some third-quarter figures are measured during the quarter by public data, such as monthly operating reports or government statistics.
- **Before each report,** Codex files an estimated distribution for such a figure, with cited inputs.
- **After the report,** Codex's estimate and the market's are scored with the continuous ranked probability score.

These are case studies, perhaps 10 to 20 a season.

## When to stop

- **Fewer than 100 events after exclusions:** report accuracy only, with no claim about returns.
- **A primary interval that includes 0:** report no measurable difference, with the detectable gap.

Either is a finding, not a failure.

## Addenda

**1. 12 October 2026, before any share return was computed.** The plan sets results day for a release before 09:30 and for one at or after 16:00 New York time, but not for one during the session. A release from 09:30 to 16:00 makes that day results day, so its return runs from the close before the release to the close after it, which contains the reaction.

**2. 12 October 2026, before any share return was computed.** The plan picks the ladder with the most contracts traded when a company reports several figures on 1 day, but does not say what happens when that ladder is excluded. Exclusions apply to each ladder, and the event takes the most-traded ladder that is not excluded.

**3. 12 October 2026, before any share return was computed.** Where the venue states the settled figure only as a bound, such as "above 3.6 billion", the reported figure is the one Codex cites from the company's release, provided it agrees with every threshold's settlement. Where the venue states it in other units than its thresholds, such as "5.1 million" against thresholds counted in millions, it is converted to the thresholds' units, provided it then agrees with every settlement; only a figure more than 30 times larger or smaller than the thresholds is converted.

**4. 12 October 2026, before any share return was computed.** The plan's "US common stocks" is read as the ticker reference's common-stock type, listed on NYSE, Nasdaq or NYSE American, whatever the company's home country. Shares of foreign companies listed directly, such as Ferrari's or Spotify's, count; ADRs, funds and ETFs do not.

**5. 12 October 2026, before any third-quarter figure was published.** The report time is the company's release, but some figures come out before the results: Boeing's deliveries in a release of their own, for example, or a quarter's last month in a monthly operating report. For the replication, the report is the company's first release of the figure. An estimate counts only if it was filed before midnight New York time of that release's date, and the market's prices are read at the same cutoff, so both are scored on the same information.

**6. 12 October 2026, after the study ran and before any third-quarter report.** The study's primary interval, −0.4 to +8.0 points, included 0, and this sample could reliably detect only a gap of 6.1 points. The replication alone, with about 100 events, will detect no smaller one. So beside the replication's own test, which stays as the plan sets it, the primary test will also be run once on both samples together, with the same bootstrap over results dates. This addendum was written after the first result was seen, and the pooled estimate should be read with that in mind.
