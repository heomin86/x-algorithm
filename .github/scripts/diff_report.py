"""Summarize x-algorithm repo changes between two commits.
Usage: python3 -I diff_report.py <repo_dir> <from_commit> <to_commit>
"""
import re, subprocess, sys

repo, a, b = sys.argv[1:4]
def git(*args):
    return subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True).stdout

PARAM_RE = re.compile(r'param!\(\s*(\w+)\s*,\s*[\w:<>]+\s*,\s*"[^"]+"\s*,\s*([^)]*?)\s*,?\s*\)\s*;', re.S)
def params(commit, path):
    return {m.group(1): m.group(2).strip() for m in PARAM_RE.finditer(git('show', f'{commit}:{path}'))}

print(f"# x-algorithm changes {a}..{b}")
print(git('log', '--format=- %h %ad %s', '--date=iso', f'{a}..{b}'))
for path in ['home-mixer/params/param.rs', 'vm-ranker/params.rs', 'visibility-filtering/params.rs']:
    old, new = params(a, path), params(b, path)
    ch = [(k, old.get(k, '∅'), new.get(k, '∅')) for k in sorted(set(old) | set(new)) if old.get(k) != new.get(k)]
    print(f"\n## {path}: {len(ch)} param changes")
    for k, o, n in ch:
        tag = ' [WEIGHT]' if re.search(r'Weight|Boost|Factor|Decay|Floor', k) else ''
        print(f"- {k}: {o} -> {n}{tag}")
print("\n## Added / deleted files (tests, fixtures excluded)")
for line in git('diff', '--name-status', a, b).splitlines():
    st, *p = line.split('\t')
    if st[0] in 'AD' and not re.search(r'test|fixture|golden', p[-1]):
        print(f"- {st[0]} {p[-1]}")
print("\n## README diff")
print(git('diff', a, b, '--', 'README.md')[:6000] or '(none)')
print("\n## Diffstat (top dirs)")
print(git('diff', '--dirstat=files,3', a, b))
