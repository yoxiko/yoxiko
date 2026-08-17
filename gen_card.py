import json, os, sys, time, urllib.request
from datetime import datetime, timezone

LOGIN = sys.argv[1]
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HDR = {"User-Agent": "ascii-card", **({"Authorization": f"token {TOKEN}"} if TOKEN else {})}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HDR)) as r:
        return json.load(r)

def get2(url, tries=2):
    for _ in range(tries):
        try:
            return get(url)
        except Exception:
            time.sleep(2)
    return None

def fmt(n):
    return f"{max(n, 0):,}".replace(",", " ")

try:
    user  = get(f"https://api.github.com/users/{LOGIN}")
    repos = get(f"https://api.github.com/users/{LOGIN}/repos?per_page=100")
except Exception as e:
    print("API unavailable, keeping old card:", e); sys.exit(0)

add = dele = 0
lang_bytes = {}
for r in repos:
    base = f"https://api.github.com/repos/{LOGIN}/{r['name']}"
    cf = get2(f"{base}/stats/code_frequency")
    if isinstance(cf, list):
        for _, a, d in cf:
            add += a; dele -= d
    for k, v in (get2(f"{base}/languages") or {}).items():
        lang_bytes[k] = lang_bytes.get(k, 0) + v

net = add - dele
stars = sum(r["stargazers_count"] for r in repos)
total_b = sum(lang_bytes.values()) or 1
top = sorted(lang_bytes.items(), key=lambda kv: -kv[1])[:3]
top_lang = top[0][0].lower() if top else "no code"
lang_str = " · ".join(f"{k.lower()} {round(v * 100 / total_b)}%" for k, v in top) or "no code yet"

contribs = cur = 0
try:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": """query($l:String!){user(login:$l){
            contributionsCollection{contributionCalendar{totalContributions
            weeks{contributionDays{contributionCount}}}}}}""",
            "variables": {"l": LOGIN}}).encode(),
        headers={**HDR, "Authorization": f"bearer {TOKEN}",
                 "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        cal = json.load(r)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    contribs = cal["totalContributions"]
    days = [d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]]
    if days and days[-1] == 0: days.pop()
    for c in days:
        cur = cur + 1 if c > 0 else 0
except Exception as e:
    print("no graphql:", e)

created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
years = max((datetime.now(timezone.utc) - created).days // 365, 1)

left = f"{LOGIN}@github"
s1 = " " * (len(left) + 1)   
s2 = " " * (len(left) + 7)  

card = "\n".join([
    s1 + f"@+{fmt(add)} all time / -{fmt(dele)}",
    s1 + "^",
    s1 + "|",
    left + " *---> " + f"{fmt(net)} lines of code ---> {top_lang}",
    s2 + "|",
    s2 + "*-----> " + lang_str,
    s1 + "|",
    s1 + f"*-----> {user['public_repos']} repos · {user['followers']} followers · {stars} stars",
    s1 + "|",
    s1 + f"`-----> {contribs} contributions · {cur}d streak · {years}y uptime",
])

text = open("README.md", encoding="utf-8").read()
s, e = "<!-- card:start -->", "<!-- card:end -->"
block = f"{s}\n```\n{card}\n```\n{e}"
open("README.md", "w", encoding="utf-8").write(
    text[:text.index(s)] + block + text[text.index(e) + len(e):])