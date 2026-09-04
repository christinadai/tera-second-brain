# Operations

Setup, running, debugging, and limits. Written for someone who does not write
code, because after the internship that is who owns this.

---

## 1. Setup

### Get Reddit credentials

1. Sign in to Reddit, go to <https://www.reddit.com/prefs/apps>.
2. "Create another app". Choose type **script**.
3. Name: `tera-second-brain`. Redirect URI: `http://localhost:8080` (unused, but required).
4. After creating it: the **client ID** is the short string under the app name.
   The **client secret** is the longer one labelled `secret`.

### Put them where the code can find them

```bash
cp .env.example .env
```

Edit `.env` and fill in the three values. `REDDIT_USER_AGENT` should name the
app and your Reddit username, which is Reddit's stated requirement.

**`.env` is gitignored and must never be committed.** Keys live in the
environment, never in code.

### Install and build the database

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python scripts/init_db.py
```

`init_db.py` is safe to run repeatedly. It creates anything missing and leaves
existing data alone.

---

## 2. Running

| Command | What it does |
|---|---|
| `scripts/init_db.py` | Creates the database file and tables from `src/second_brain/schema.sql` |
| `scripts/verify_reddit.py` | Fetches one real post to prove the credentials work |
| `scripts/pull_once.py --limit 10` | One small collection pass into `raw`, logged in `job_logs` |

Always run `verify_reddit.py` first when something breaks. If credentials are
the problem, nothing downstream can work and the error will be clearer here.

### Changing what gets collected

Edit `config/sources.yaml`. It is plain text and meant to be edited by hand:
which subreddits, how many posts, what gets dropped. No code change needed.

---

## 3. Reading `job_logs`

Every run writes one row with a **typed outcome**. This is the most important
table for trusting the output.

| Outcome | Means | What to do |
|---|---|---|
| `ok` | Ran, stored what we expected | Nothing |
| `no-results` | Ran fine, genuinely nothing new | Nothing. A real quiet period |
| `partial` | Some subreddits worked, some failed | Read `detail`. Often one sub renamed or went private |
| `rate-limited` | Reddit asked us to slow down | Wait and re-run. Not a bug |
| `auth-failed` | Credentials rejected | **A person must fix this.** Never retried automatically |
| `unreachable` | Network or Reddit is down | Re-run later |
| `schema-drift` | The response did not look how we expected | **Investigate.** Reddit changed something |
| `degraded` | Ran, but returned far less than usual | Early warning. Compare against recent runs |

**Why this matters more than it looks:** five of these produce zero stored
records, and only `no-results` means nobody was talking. A briefing that says
"no discussion this week" is only true if the outcome was `no-results`. Without
this column, a broken pull and a quiet week look identical.

```sql
SELECT started_at, outcome, records_fetched, records_stored, detail
FROM job_logs ORDER BY started_at DESC LIMIT 10;
```

---

## 4. Troubleshooting

**"Missing credentials"** — `.env` does not exist or a value is blank. Copy
`.env.example` and fill it in.

**`auth-failed`** — the client ID or secret is wrong, or the app was deleted on
Reddit. Re-check <https://www.reddit.com/prefs/apps>. Deliberately never
retried: retrying bad credentials just gets you blocked.

**`rate-limited`** — Reddit throttles by user agent and account. Wait, then
re-run. Note that Reddit's search and RSS endpoints answer an anonymous 429
with `x-ratelimit-reset` and no `Retry-After`, so naive short backoff re-fails.
PRAW handles this internally, which is a reason we use it.

**A run stored 0 records but says `ok`** — everything fetched was already in
`raw`. Check `records_duplicate`. This is expected on a re-run and is the
upsert behaviour working correctly.

**Everything looks right but the numbers seem low** — check `records_skipped`.
The drop rules in `config/sources.yaml` remove deleted, removed, stickied and
bot posts before storing.

---

## 5. Known limits

State these in any report built on this data. They are not defects to hide.

- **Audience mismatch.** tera targets Gen Z women. Reddit skews male, and the
  Gen Z beauty conversation is heavier on TikTok. Reddit gives depth of
  reasoning, not a representative sample.
- **Age is not knowable.** Reddit exposes no age field. The `stated_age` column
  is only populated when an author states an age in their own words. It is
  never inferred from slang or from which subreddit someone posts in. Any Gen Z
  analysis must report what percentage of posts it actually covers.
- **Selection bias.** Ranking by engagement over-represents controversial and
  older content.
- **Single platform.** One source cannot tell you what is absent from another.
- **Vocabulary rot.** A term missing from the matching vocabulary produces
  silence, not an error. Review the most frequent unmatched terms weekly.

---

## 6. Deliberately out of scope

Campaign launching, TikTok, PubMed, any interface beyond the briefing,
**sentiment scores** (a number between minus one and one looks precise and
tells you nothing actionable, whereas named objections with quotes are messier
and more useful), historical backfill, and **automated recommendations** (the
system ranks evidence, a person decides).
