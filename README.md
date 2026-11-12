# Maybe: daily post

Posts one Maybe card a day to Instagram and to the Maybe Project LinkedIn page, at 8 am Pacific.

## The week
| Day | Post |
|---|---|
| Mon, Wed, Thu, Sat, Sun | A line from *Maybe: Turn What‑Ifs into Brave Next Steps* (a few are from *The Maybe Pages*) |
| Tue | **Tuesday experiment**: one small, right‑sized step (Týr's day, the bravest day of the week) |
| Fri | **Spot the maybe**: one reflection question |

- `posts.json`: three queues. `quote` (247 lines, every one checked word for word against the March 2026 manuscript), `tuesday` (52) and `friday` (52). Each entry has the card text, the Instagram caption and the LinkedIn text.
- `cards/`: one 1080×1350 card per entry. Quotes alternate cream and navy; Tuesday cards are red, Friday cards navy.
- `config.json`: start date, posting hour, the week pattern, a pause switch, and an on/off switch for each platform.
- Each queue moves forward one card each time its day comes round, counted from `start_date`, and starts again from the top when it runs out (quotes last about 49 weeks, the prompts a year).

Run `python3 scripts/schedule.py --week` to see the next two weeks.

## Everyday controls
- **Pause:** set `"paused": true` in `config.json`.
- **Turn one platform off:** set `"on": false` under `instagram` or `linkedin`.
- **Change or swap a line:** edit it in `posts.json`. The **Build cards** workflow redraws the cards by itself when `posts.json` changes.
- **Change the week:** edit `"week"` in `config.json` (each day is `quote`, `tuesday` or `friday`).
- **Test without posting:** Actions → Daily post → Run workflow, with "Test only" ticked. Instagram prepares the post without publishing it; LinkedIn uploads the image without posting it.
- If a post fails, an issue opens in this repository and GitHub emails you. One platform failing doesn't stop the other.

## Fonts
The cards are designed in the brand fonts, Zodiak and Satoshi. To stay on the right side of Fontshare's licence, the font files aren't kept in this public repository: the **Build cards** workflow downloads them from Fontshare each time it runs and doesn't save them here. If Fontshare can't be reached, it falls back to Fraunces and Manrope (both open licence, in `fonts/`). Run **Build cards** once after setup so every card is drawn in Zodiak and Satoshi.

## Setup
### Instagram
The Maybe Instagram account must be a Business or Creator account, connected to a Facebook Page, in a Meta business portfolio. Then, as for West Coast Hearts:
1. In the Meta app (Instagram API with Unified login), add the Maybe Instagram account and generate a system‑user token with `instagram_basic`, `instagram_content_publish`, `pages_show_list` and `business_management`.
2. Add it as the repository secret `IG_TOKEN`.
3. Add the account's Instagram user id as the secret `IG_USER_ID` (or put it in `config.json` under `instagram.user_id`).

### LinkedIn (the Maybe Project page)
Posting as a company page needs LinkedIn's **Community Management API**, which LinkedIn reviews before granting. Until it's approved, leave `linkedin.on` set to `false`; Instagram runs without it.
1. At developer.linkedin.com, create an app linked to the Maybe Project page, and have a page admin verify it.
2. Under Products, request **Community Management API** (Development tier is enough for one post a day). LinkedIn asks for the business's legal name, address, website and privacy policy.
3. Once it's approved, open Docs and tools → OAuth Token Tools, and create a token for the app with the scopes `w_organization_social` and `r_organization_social`, signed in as a page admin.
4. Add the token as the secret `LI_TOKEN`, and set `linkedin.token_set_on` in `config.json` to today's date.
5. Put the page's number in `linkedin.organization_id` (it's in the admin URL: linkedin.com/company/**12345678**/admin), then set `linkedin.on` to `true`.

LinkedIn tokens last 60 days. Ten days before this one runs out, an issue opens here as a reminder; repeat step 3 and 4. If LinkedIn ever gives the app refresh tokens, add `LI_REFRESH_TOKEN`, `LI_CLIENT_ID` and `LI_CLIENT_SECRET` as secrets and set `linkedin.auto_refresh` to `true`; the script then gets a fresh token on every run.

`linkedin.api_version` is the LinkedIn API version the posts use (`YYYYMM`). LinkedIn retires each version after about a year; if posts start failing with a version error, set it to a recent month.

## Secrets (Settings → Secrets and variables → Actions)
- `IG_TOKEN`, `IG_USER_ID`: Instagram.
- `LI_TOKEN`: LinkedIn. Optional: `LI_REFRESH_TOKEN`, `LI_CLIENT_ID`, `LI_CLIENT_SECRET`.

## How it runs
`.github/workflows/daily-post.yml` runs every hour from 7 am to 2 pm Pacific. The first run at or after 8 am posts; later runs see the day's marker on the `state` branch and skip. Instagram fetches the card from this repository's public URL, so the repository has to stay public.
