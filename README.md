# Reddit Question SEO Bank | Powered by Bright Data

> **Your next useful FAQ is already being asked. Find it without inventing search volume.**

Collect structured Reddit posts through Bright Data MCP, cluster the actual questions, and check a small set of search-result pages before commissioning content. The prize is not another keyword list. It is a cited queue of original FAQs and article briefs rooted in real wording.

## The decision

**Which recurring question deserves an original answer, and what evidence is still missing?**

Use it to:

- Build a deduplicated question bank for SEO and content strategy.
- Find FAQ and H2 candidates in the audience’s own wording.
- Check whether a small set of collected pages leaves a specific information gap.

## Why Bright Data

Direct Reddit page retrieval can be unreliable for a simple research workflow. [Bright Data](https://docs.brightdata.com/products/mcp-server/overview) MCP provides a Reddit Posts scraper for structured discovery, plus search and public-page fetching for the follow-up evidence check. One MCP connection takes you from seed keyword to question rows to cited content decision. No custom Reddit parser. No snippet-only SEO verdicts.

## Start with 5,000 free credits

**New Bright Data accounts include 5,000 free credits per month. No credit card is required.** Credits share one account-level pool, reset monthly, and are subject to current eligibility and product terms.

A small default plan uses **20 Reddit records, 4 searches, and 4 result-page fetches**. Dataset records and page requests are planned separately. Bright Data's documented free tier explicitly covers search and public-page fetching; coverage and pricing for structured scraper records must be confirmed in your account before `run_scraper`. The 5,000-credit offer is not a promise that every scraper record is free. Your agent shows the exact caps and asks for that confirmation before collection.

## What you get

- `report.md`: ranked question clusters, subreddit spread, and coverage status.
- `questions.csv`: stable cluster keys, exact wording, thread evidence, and change status.
- `run.json`: the current snapshot for repeat research; vanished threads are not labeled as removed.
- `briefs.md`: up to four original-research brief scaffolds with question variants, an outline, acceptance checks, and citations—only for page-supported `gap_observed` clusters.
- Explicit warnings when coverage input matches zero or multiple clusters; unsupported clusters produce no brief.

## Give this to your agent

```text
Use reddit-question-seo-bank for [topic].
My seed keywords are [1-2 keywords]. My optional subreddits are [names].
My reader is [audience]. My target country is [two-letter country].

Use the Bright Data MCP Reddit Posts scraper, dataset gd_lvz8ah06191smkebj4,
discover_by_keyword. Cap collection at 20 total posts. Show the record budget and
ask me to confirm current pricing before run_scraper. Poll only until the bounded
job finishes or fails. Exclude usernames and do not scrape Reddit thread HTML.

Cluster question titles. For at most 4 clusters, use one search and one selected
public result page per cluster. Snippets cannot support a gap verdict. Label the
result gap_observed, covered, or not_assessed from collected passages only.
Run scripts/report.py and return the question bank plus the generated briefs.md.
Review every brief as a research scaffold; do not auto-publish it as an article.
Do not copy Reddit answers, estimate search volume, post, comment, or contact users.
```

## Install

Requires Python 3.10+ and an MCP-compatible agent. This is a public repo.

### 1. Connect Bright Data MCP

Follow [Install Bright Data MCP](docs/install-bright-data-mcp.md). Choose hosted or local setup with the `scrapers` tool group, then verify the base tools and structured scraper tools are connected as `brightdata`.

### 2. Clone the skill

```bash
git clone https://github.com/yaronbeen/reddit-question-seo-bank-powered-by-bright-data.git \
  ~/.claude/skills/reddit-question-seo-bank
```

For OpenCode, clone into `~/.config/opencode/skills/reddit-question-seo-bank`. See the [connection and schema guide](docs/technical-guide.md).

## Run the example

```bash
cd ~/.claude/skills/reddit-question-seo-bank
python3 scripts/report.py examples/input.json --output-dir examples/output
```

For a later run:

```bash
python3 scripts/report.py new-input.json \
  --previous examples/output/run.json --output-dir output
```

The example is synthetic. The [live-check note](docs/live-check.md) records both the structured-scraper check and the failed direct-page check.

## Example output

| Question cluster | Threads | Subreddits | Coverage | Status |
|---|---:|---:|---|---|
| how can i migrate safely | 2 | 2 | gap_observed | new |
| which cms is best for a small site | 1 | 1 | not_assessed | new |

`gap_observed` means the collected passages leave a documented question unanswered. It does **not** mean low keyword difficulty, high traffic, or guaranteed rankings.

## Tests

Test-first history starts with a red commit. The helper is deterministic and never calls the network.

```bash
python3 -m unittest discover -s tests -v
```

Tests cover question detection, Unicode normalization, deterministic clustering, subreddit spread, prior-cluster identity, snippet rejection, generated brief content, no-evidence/no-brief gates, MCP installation docs, CSV injection, and repeat-run diffs. See [the testing note](docs/testing.md).

## What this is not

- Not all Reddit questions. Keyword selection and Reddit’s own results shape the sample.
- Not a search-volume or ranking-difficulty tool.
- Not a license to copy answers or target Reddit users. Review Reddit's current terms and Bright Data's scraper terms before collection.
- Not an auto-publisher. A human approves every brief and every word that ships.

## Repo map

```text
SKILL.md                 Agent workflow and MCP limits
scripts/report.py        Stdlib-only deterministic helper
tests/                   Unit tests + sanitized live fixture
examples/                Synthetic input and generated output
docs/                    Setup, schema, testing, and live-check notes
```

## FAQ

**Why use the Reddit dataset instead of thread pages?**  The documented smoke check found that direct page retrieval did not yield thread content, while Bright Data's MCP scraper returned structured post records. That is a retrieval observation, not permission to ignore Reddit's terms or a guarantee of future access.

**What is the CSV key?**  `cluster_key`. On repeat runs, the helper matches similar prior clusters and carries the old key forward where possible. Thread IDs remain in the evidence JSON.

**What if no cluster earns a brief?**  That is a valid result. Collect better evidence or move to the next question.

---

Independent project by Yaron Been. MIT licensed. Powered by Bright Data; no affiliation or endorsement is implied.
