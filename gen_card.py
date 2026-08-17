import json, os, sys, urllib.request
from datetime import datetime

LOGIN = sys.argv[1]
TOKEN = os.environ.get("GITHUB_TOKEN", "")

def get(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {TOKEN}" if TOKEN else "",
        "User-Agent": "ascii-card"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}",
                 "Content-Type": "application/json",
                 "User-Agent": "ascii-card"},
        method="POST")
    with urllib.request.urlopen(req) as r:
        return json.load(r)

user = get(f"https://api.github.com/users/{LOGIN}")

stars, langs = 0, {}
for r in get(f"https://api.github.com/users/{LOGIN}/repos?per_page=100"):
    stars += r["stargazers_count"]
    if r.get("language"):
        langs[r["language"]] = langs.get(r["language"], 0) + 1
shell = max(langs, key=langs.get) if langs else "bash"

contribs = streak = 0
try:
    data = gql("""query($login:String!){user(login:$login){
        contributionsCollection{contributionCalendar{
        totalContributions weeks{contributionDays{contributionCount}}}}}""",
        {"login": LOGIN})
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    contribs = cal["totalContributions"]
    days = [d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]]
    if days and days[-1] == 0:
        days.pop() 
    for c in days:
        streak = streak + 1 if c > 0 else 0
except Exception:
    pass

created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
years = max((datetime.now(created.tzinfo) - created).days // 365, 1)

info = [
    f"{LOGIN}@github", "-" * 30,
    f"{'OS':<14} GitHub {created.year}",
    f"{'Uptime':<14} {years} year{'s' if years > 1 else ''}",
    f"{'Packages':<14} {user['public_repos']} repos",
    f"{'Shell':<14} {shell}",
    f"{'Stars':<14} {stars}",
    f"{'Followers':<14} {user['followers']}",
    f"{'Contributions':<14} {contribs}",
    f"{'Streak':<14} {streak}d",
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
card = "\n".join(card)

text = open("README.md", encoding="utf-8").read()
s, e = "<!-- card:start -->", "<!-- card:end -->"
block = f"{s}\n```\n{card}\n```\n{e}"
open("README.md", "w", encoding="utf-8").write(
    text[:text.index(s)] + block + text[text.index(e) + len(e):])