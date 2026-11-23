"""Add one Notion database page per sync, summarizing new upstream commits.
Usage: python3 -I notify_notion.py <repo_dir> <old_sha> <new_sha> <report.md>
Env: NOTION_TOKEN (required), NOTION_DATABASE_ID (optional, defaults to heo's DB). Set DRY_RUN=1 to print the payload instead.
"""
import json, os, re, subprocess, sys, urllib.request

repo, old, new, report_path = sys.argv[1:5]
report = open(report_path, encoding='utf-8').read()

def git(*a):
    return subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True).stdout.strip()

commits = git('log', '--format=%H%x09%cI%x09%s', f'{old}..{new}').splitlines()
latest_sha, latest_date, latest_msg = commits[0].split('\t', 2)
count = len(commits)

per_file = re.findall(r'^## (\S+): (\d+) param changes', report, re.M)
param_changes = sum(int(n) for _, n in per_file)
changed_files = [f"{f.split('/')[0]} {n}개" for f, n in per_file if int(n)]
weight_lines = [l for l in report.splitlines() if l.endswith('[WEIGHT]')]

title = f"커밋 {count}건 · 파라미터 {param_changes}개 변경 · {latest_msg[:60]}"
summary = f"새 커밋 {count}건, 파라미터 변경 {param_changes}개"
if changed_files:
    summary += " (" + ", ".join(changed_files) + ")"
if weight_lines:
    summary += " | " + "; ".join(l[2:].replace(' [WEIGHT]', '') for l in weight_lines[:8])
url = (f"https://github.com/xai-org/x-algorithm/commit/{latest_sha}" if count == 1
       else f"https://github.com/xai-org/x-algorithm/compare/{old[:12]}...{new[:12]}")

chunks = [report[i:i + 1900] for i in range(0, len(report), 1900)][:90]
children = [{"object": "block", "type": "code", "code": {"language": "markdown",
             "rich_text": [{"type": "text", "text": {"content": c}}]}} for c in chunks]

payload = {
    "parent": {"database_id": os.environ.get('NOTION_DATABASE_ID') or '42178036ac8381c9b96bdba058a3d5ee'},
    "properties": {
        "커밋": {"title": [{"text": {"content": title}}]},
        "날짜": {"date": {"start": latest_date}},
        "링크": {"url": url},
        "SHA": {"rich_text": [{"text": {"content": latest_sha[:12]}}]},
        "가중치 변경": {"checkbox": param_changes > 0},
        "변경 요약": {"rich_text": [{"text": {"content": summary[:1900]}}]},
        "상태": {"select": {"name": "새 커밋"}},
    },
    "children": children,
}

if os.environ.get('DRY_RUN'):
    print(json.dumps(payload, ensure_ascii=False, indent=1)[:3000]); sys.exit(0)

req = urllib.request.Request('https://api.notion.com/v1/pages', data=json.dumps(payload).encode(),
    headers={'Authorization': f"Bearer {os.environ['NOTION_TOKEN']}",
             'Notion-Version': '2022-06-28', 'Content-Type': 'application/json'}, method='POST')
try:
    with urllib.request.urlopen(req) as r:
        print('Notion page created:', json.load(r).get('url'))
except urllib.error.HTTPError as e:
    print('Notion error', e.code, e.read().decode()); sys.exit(1)
