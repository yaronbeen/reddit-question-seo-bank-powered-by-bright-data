# Reddit Live Check | Powered by Bright Data

Checked 2026-11-09 with Bright Data MCP.

## Direct-page result

`scrape_as_markdown` on a public subreddit and a direct thread URL returned `Reddit - Prove your humanity`, not thread evidence. A public JSON endpoint also timed out. The skill therefore forbids substituting direct Reddit page content or search snippets for structured post records.

## Structured MCP result

The maintained Reddit Posts scraper was called through MCP with:

- Dataset `gd_lvz8ah06191smkebj4`
- Method `discover_by_keyword`
- Keyword `SEO migration`
- Date `Past year`
- A five-record cap

The asynchronous run completed with **5 records and 0 collection errors**. It required progress/results polling. Returned fields included `post_id`, `url`, `title`, `community_name`, and other fields not needed by this skill.

Two question titles were sanitized into the live fixture. Usernames, bodies, engagement, profile data, and community metadata were discarded. One real title is a case-study-style question, illustrating why the helper keeps exact titles but does not treat every question as a content gap.

## Limits

- Five records are a smoke test, not a trend sample.
- Keyword selection and Reddit's own discovery results bias the sample.
- Structured collection does not grant permission to copy answers or target users.
- Review Reddit's current terms and confirm current dataset pricing before a run. No comments, posts, votes, DMs, or thread-page challenge bypasses are used.
