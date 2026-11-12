"""Post today's Maybe card to Instagram and to the Maybe Project LinkedIn page.

Runs from GitHub Actions every hour through the morning and posts once a day,
at or after the posting hour (Pacific). It records what went out in the folder
given as STATE_DIR (the workflow keeps that on the "state" branch), so a later
run the same day skips anything already posted. Each platform is tried on its
own: if one fails, the other still goes out, and the run is marked failed.
"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error, re
from datetime import datetime, date
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schedule import plan, ROOT

REPO = os.environ.get("GITHUB_REPOSITORY", "")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
DRY = os.environ.get("DRY_RUN") == "true"
FORCE = os.environ.get("FORCE") == "true"
STATE = os.environ.get("STATE_DIR", os.path.join(ROOT, ".state"))
os.makedirs(STATE, exist_ok=True)

cfg = json.load(open(os.path.join(ROOT, "config.json")))
now = datetime.now(ZoneInfo("America/Los_Angeles"))
today = now.date()

if cfg.get("paused"):
    print("Paused in config.json; nothing to do."); sys.exit(0)
if today < date.fromisoformat(cfg["start_date"]) and not FORCE:
    print(f"Daily posts start on {cfg['start_date']}; nothing to do yet."); sys.exit(0)
if now.hour < cfg["post_hour_pacific"] and not FORCE:
    print(f"It's {now:%H:%M} Pacific; waiting for {cfg['post_hour_pacific']}:00."); sys.exit(0)

p = plan(today)
post = p["post"]
print(f"Today ({p['date']}, {p['kind']}): {post['id']}: {post['text']}")
image_path = os.path.join(ROOT, post["image"])
image_url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{post['image']}"


def http(method, url, data=None, headers=None, secret=""):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = r.read()
            return r.status, dict(r.headers), (json.loads(body) if body.strip().startswith(b"{") else body)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if secret: body = body.replace(secret, "***")
        raise RuntimeError(f"{method} {url.split('?')[0]} -> {e.code} {body[:600]}")


def marker(platform):
    return os.path.join(STATE, f"posted-{p['date']}-{platform}")


# ---------------------------------------------------------------- Instagram
def instagram():
    token = os.environ.get("IG_TOKEN", "")
    user = os.environ.get("IG_USER_ID") or cfg["instagram"].get("user_id")
    if not token or not user:
        raise RuntimeError("Instagram isn't connected yet: add the IG_TOKEN secret and the account id.")
    api = "https://graph.facebook.com/v23.0"

    def call(method, path, **params):
        params["access_token"] = token
        q = urllib.parse.urlencode(params)
        if method == "GET":
            return http("GET", f"{api}/{path}?{q}", secret=token)[2]
        return http("POST", f"{api}/{path}", data=q.encode(), secret=token)[2]

    try:
        container = call("POST", f"{user}/media", image_url=image_url, caption=post["caption"])["id"]
    except RuntimeError:
        # Tokens made with Instagram login use graph.instagram.com instead. Try that,
        # and say which account the token belongs to, to make setup problems obvious.
        for host, fields in (("https://graph.facebook.com/v23.0", "id,name"),
                             ("https://graph.instagram.com/v23.0", "user_id,username")):
            try:
                who = http("GET", f"{host}/me?fields={fields}&access_token={token}", secret=token)[2]
                print(f"  token works on {host.split('/')[2]} as {who}")
            except RuntimeError as e:
                print(f"  token doesn't work on {host.split('/')[2]}: {str(e)[:160]}")
        api = "https://graph.instagram.com/v23.0"
        container = call("POST", f"{user}/media", image_url=image_url, caption=post["caption"])["id"]
    for _ in range(30):
        status = call("GET", container, fields="status_code").get("status_code")
        if status == "FINISHED": break
        if status == "ERROR": raise RuntimeError("Instagram could not process the image.")
        time.sleep(2)
    else:
        raise RuntimeError("Instagram took too long to process the image.")
    if DRY:
        return "dry run: prepared, not published"
    media = call("POST", f"{user}/media_publish", creation_id=container)
    return f"media id {media.get('id')}"


# ---------------------------------------------------------------- LinkedIn
LI_RESERVED = re.compile(r"([\\|{}@\[\]()<>#*_~])")


def li_text(s):
    """LinkedIn's 'little text' format: escape reserved characters, keep hashtags as hashtags."""
    out = []
    for part in re.split(r"(#[A-Za-z][A-Za-z0-9]*)", s):
        if re.fullmatch(r"#[A-Za-z][A-Za-z0-9]*", part):
            out.append("{hashtag|\\#|" + part[1:] + "}")
        else:
            out.append(LI_RESERVED.sub(r"\\\1", part))
    return "".join(out)


def linkedin_token():
    rt, cid, cs = (os.environ.get(k, "") for k in ("LI_REFRESH_TOKEN", "LI_CLIENT_ID", "LI_CLIENT_SECRET"))
    if rt and cid and cs:
        data = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": rt,
                                       "client_id": cid, "client_secret": cs}).encode()
        res = http("POST", "https://www.linkedin.com/oauth/v2/accessToken", data=data,
                   headers={"Content-Type": "application/x-www-form-urlencoded"}, secret=cs)[2]
        return res["access_token"]
    tok = os.environ.get("LI_TOKEN", "")
    if not tok:
        raise RuntimeError("LinkedIn isn't connected yet: add the LI_TOKEN secret (see README).")
    return tok


def linkedin():
    org = cfg["linkedin"].get("organization_id")
    if not org:
        raise RuntimeError("Set linkedin.organization_id in config.json.")
    token = linkedin_token()
    owner = f"urn:li:organization:{org}"
    H = {"Authorization": f"Bearer {token}", "LinkedIn-Version": cfg["linkedin"]["api_version"],
         "X-Restli-Protocol-Version": "2.0.0", "Content-Type": "application/json"}
    init = http("POST", "https://api.linkedin.com/rest/images?action=initializeUpload",
                data=json.dumps({"initializeUploadRequest": {"owner": owner}}).encode(), headers=H, secret=token)[2]
    upload_url, image_urn = init["value"]["uploadUrl"], init["value"]["image"]
    http("PUT", upload_url, data=open(image_path, "rb").read(),
         headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"}, secret=token)
    if DRY:
        return f"dry run: image uploaded as {image_urn}, nothing posted"
    body = {"author": owner, "commentary": li_text(post["linkedin"]), "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                             "thirdPartyDistributionChannels": []},
            "content": {"media": {"id": image_urn, "altText": post["text"][:4000]}},
            "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
    status, headers, _ = http("POST", "https://api.linkedin.com/rest/posts",
                              data=json.dumps(body).encode(), headers=H, secret=token)
    return f"post {headers.get('x-restli-id') or headers.get('X-RestLi-Id') or status}"


failed = []
for name, on, fn in (("instagram", cfg["instagram"].get("on"), instagram),
                     ("linkedin", cfg["linkedin"].get("on"), linkedin)):
    if not on:
        print(f"{name}: off in config.json"); continue
    if os.path.exists(marker(name)) and not DRY:
        print(f"{name}: already posted today"); continue
    try:
        result = fn()
        print(f"{name}: {result}")
        if not DRY:
            open(marker(name), "w").write(f"{post['id']}\n{result}\n")
    except Exception as e:
        print(f"{name}: FAILED: {e}"); failed.append(name)

if failed:
    sys.exit(f"Didn't post to: {', '.join(failed)}")
