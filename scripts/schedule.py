"""What goes out on a given day.

The week pattern in config.json decides the kind of post (a book quote, a
Tuesday experiment or a Friday "Spot the maybe" question). Each kind has its
own queue in posts.json and moves forward one card each time that kind comes
up, counted from start_date, so nothing needs to remember what was posted.
When a queue runs out it starts again from the top.

    python3 scripts/schedule.py          # today
    python3 scripts/schedule.py --week   # the next 14 days
"""
import json, os
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def load():
    return (json.load(open(os.path.join(ROOT, "config.json"))),
            json.load(open(os.path.join(ROOT, "posts.json"))))


def plan(day=None, cfg=None, posts=None):
    if cfg is None or posts is None:
        cfg, posts = load()
    day = day or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    start = date.fromisoformat(cfg["start_date"])
    kind = cfg["week"][DAYS[day.weekday()]]
    # how many earlier days since start_date had this same kind
    n = sum(1 for k in range((day - start).days)
            if cfg["week"][DAYS[(start + timedelta(k)).weekday()]] == kind)
    queue = posts[kind]
    return {"date": day.isoformat(), "kind": kind, "post": queue[n % len(queue)]}


if __name__ == "__main__":
    import sys
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    days = 14 if "--week" in sys.argv else 1
    cfg, posts = load()
    for k in range(days):
        d = max(today, date.fromisoformat(cfg["start_date"])) + timedelta(k)
        p = plan(d, cfg, posts)
        print(f"{p['date']} {DAYS[d.weekday()]}  {p['post']['id']}  {p['post']['text'][:80]}")
