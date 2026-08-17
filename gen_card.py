import json, os, sys, urllib.request
from datetime import datetime, timezone

LOGIN = sys.argv[1]
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HDR = {"User-Agent": "ascii-card", **({"Authorization": f"token {TOKEN}"} if TOKEN else {})}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HDR)) as r:
        return json.load(r)

def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={**HDR, "Authorization": f"bearer {TOKEN}",
                 "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def ago(iso):
    d = (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    return f"{d}d" if d > 0 else "today"

try:
    user  = get(f"https://api.github.com/users/{LOGIN}")
    repos = get(f"https://api.github.com/users/{LOGIN}/repos?per_page=100&sort=updated")
except Exception as e:
    print("API unavailable, keeping old card:", e); sys.exit(0)

stars = sum(r["stargazers_count"] for r in repos)
langs = {}
for r in repos:
    if r.get("language"):
        langs[r["language"]] = langs.get(r["language"], 0) + 1
top = sorted(langs.items(), key=lambda kv: -kv[1])[:3]
shell = top[0][0] if top else "bash"

contribs = cur = best = 0
weeks = []
try:
    data = gql("""query($l:String!){user(login:$l){contributionsCollection{
        contributionCalendar{totalContributions
        weeks{contributionDays{contributionCount}}}}}}""", {"l": LOGIN})
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    contribs = cal["totalContributions"]
    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
    days = [d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]]
    if days and days[-1] == 0: days.pop()
    for c in days:
        cur = cur + 1 if c > 0 else 0
        best = max(best, cur)
except Exception as e:
    print("no graphql:", e)

try:
    events = [e for e in get(f"https://api.github.com/users/{LOGIN}/events/public")
              if e["type"] == "PushEvent"][:3]
except Exception:
    events = []

def spark(vals):
    chars = " ▁▂▃▄▅▆▇█"
    hi = max(vals, default=0) or 1
    return "".join(chars[min(v * 8 // hi, 8)] for v in vals)

mx = top[0][1] if top else 1
langline = "  ".join(f"{n} {'█' * max(1, round(c * 8 / mx))} {c}" for n, c in top)

pushlines = []
for e in events:
    cs = e["payload"].get("commits") or [{}]
    msg = (cs[-1].get("message") or "").split("\n")[0][:48]
    pushlines.append(f"   * {e['repo']['name'].split('/')[-1]}: {msg} ({ago(e['created_at'])})")

created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
years = max((datetime.now(timezone.utc) - created).days // 365, 1)

info = [
    f"{LOGIN}@github", "-" * 30,
    f"{'OS':<14} GitHub {created.year}",
    f"{'Uptime':<14} {years} year{'s' if years > 1 else ''}",
    f"{'Packages':<14} {user['public_repos']} repos",
    f"{'Shell':<14} {shell}",
    f"{'Stars':<14} {stars}",
    f"{'Followers':<14} {user['followers']}",
    f"{'Contributions':<14} {contribs}",
    f"{'Streak':<14} {cur}d (best {best}d)",
]

tree = [
    "    *-----*-----*-----*-----*-----*-----*-----*-----*   [main]",
    "           \\                       \\",
    "            \\                       *-----*-----*   [release]",
    "             \\                             \\",
    "              \\                             *-----*   [v1.0]",
    "               *-----*-----*-----*-----*-----*   [dev]",
    "                          \\           \\",
    "                           \\           *-----*   [feat]",
    "                            \\",
    "                             *-----*   [fix]",
    "                                    \\",
    "                                      *   [hotfix]",
]

W = 66
def line(left, right=""):
    return left + " " * (W - len(left)) + right if right else left

card = [f" * {LOGIN}@github", ""]
for i, t in enumerate(tree):
    card.append(line(t, info[i - 1] if 0 <= i - 1 < len(info) else ""))
card += ["", f" Activity   {spark(weeks[-16:])}"]
if top:        card.append(f" Languages  {langline}")
if pushlines:  card += [" Pushes"] + pushlines
card = "\n".join(card)

text = open("README.md", encoding="utf-8").read()
s, e = "<!-- card:start -->", "<!-- card:end -->"
block = f"{s}\n```\n{card}\n```\n{e}"
open("README.md", "w", encoding="utf-8").write(
    text[:text.index(s)] + block + text[text.index(e) + len(e):])