#!/usr/bin/env python3
"""Offline fixed-seed sampling and human-curated case/CSV export; stdlib only.

No company text belongs in this file. Curation lives exclusively in ignored local/.
Sampling is reproducible for an unchanged, sorted log snapshot. It is not a labeler.
"""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import random
import re

SEED = 20261008
ROOT = Path(__file__).resolve().parent
LOGS = Path.home() / 'agent-io-logs'
SECRET = re.compile(r'sk-[A-Za-z0-9]{16,}|api[_-]?key\s*[:=]|BEGIN [A-Z ]*PRIVATE KEY', re.I)
CRITERIA = {
    'context_retention': {'must_keep': 'Needed verbatim for next step', 'may_drop': 'Not needed in active context'},
    'agent_routing': {'cheap': 'Bounded search/read/summary', 'current': 'Clear implementation in current scope', 'escalate': 'User decision, method choice or ambiguity'},
    'network_level': {'none': 'Local inputs suffice', 'request': 'Fetch via approved orchestrator request', 'direct-read': 'Public-only research; no private data/credentials'},
}
INSTRUCTIONS = {
    'context_retention': 'Keep this result verbatim for the stated next step?',
    'agent_routing': 'Choose the appropriate worker route.',
    'skill_selection': 'Choose the best skill for this request, or none.',
    'network_level': 'Propose job access under design 5.1; this grants no permission.',
}
LEAK = ('must_keep', 'may_drop', 'must keep', 'may drop', 'direct-read', 'escalate',
        'ควรเก็บ', 'ไม่ต้องเก็บ', 'จำเป็นต้องเก็บ', 'ทิ้งได้', 'ควรส่งต่อ',
        'ไม่ต้องใช้เน็ต', 'ต้องใช้เน็ต', 'label:', 'answer:', 'คำตอบ')
FIELDS = ['case_id', 'task', 'language', 'difficulty', 'state', 'question', 'options', 'proposed_label', 'rationale', 'user_label', 'user_note']


def events(logs):
    for path in sorted(logs.glob('*/*.jsonl')):
        for line, raw in enumerate(path.open(encoding='utf-8'), 1):
            try:
                event = json.loads(raw)
            except ValueError as exc:
                raise ValueError(f'Malformed JSON at {path.name}:{line}') from exc
            yield {'file': str(path.relative_to(logs)), 'line': line}, event


def sample(logs, limit, kind):
    pool = []
    skipped = 0
    for source, event in events(logs):
        if kind == 'user':
            texts = [(None, event.get('text', ''))] if event.get('event') == 'user_input' else []
        else:
            texts = [(i, tool.get('result', '')) for i, tool in enumerate(event.get('tools', []))]
        for index, text in texts:
            text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
            if not text.strip():
                continue
            if SECRET.search(text):
                skipped += 1
                continue
            pool.append((source, index, text))
    random.Random(SEED).shuffle(pool)
    print(json.dumps({'seed': SEED, 'kind': kind, 'eligible': len(pool), 'secret_pattern_excluded': skipped}))
    for source, index, text in pool[:limit]:
        print(json.dumps({'source': source, 'tool_index': index, 'excerpt': text[:300]}, ensure_ascii=False))


def skill_names():
    bases = [Path.home()/'.claude/skills', Path.home()/'agent-kit/skills', Path.home()/'Documents/projects_cj/npd-comparables/.claude/skills']
    return {p.parent.name for base in bases for p in base.rglob('SKILL.md')}


def validate(rows, logs):
    assert len(rows) == 96, 'Need exactly 96 rows'
    assert len({r['case_id'] for r in rows}) == 96
    cells = collections.Counter((r['task'], r['language']) for r in rows)
    assert all(cells[(t, lang)] == 8 for t in INSTRUCTIONS for lang in ('th', 'en', 'mixed'))
    names = skill_names()
    for row in rows:
        state = row['state']; task = row['task']; lang = row['language']
        assert 0 < len(state) <= 600, row['case_id']
        assert not any(phrase in state.lower() for phrase in LEAK), row['case_id']
        th = sum('\u0e00' <= c <= '\u0e7f' for c in state)
        en = sum(c.isascii() and c.isalpha() for c in state)
        total = max(th + en, 1)
        assert (lang == 'th' and th/total >= .5) or (lang == 'en' and th == 0) or (lang == 'mixed' and min(th, en)/total >= .15), row['case_id']
        q = row['questions'][0]; options = q['request']['criteria']
        assert len(row['questions']) == 1 and q['request']['type'] == 'choice'
        assert q['expected']['label'] in options
        if task == 'skill_selection':
            assert 'none' in options and 4 <= len(options) <= 7
            assert set(options)-{'none'} <= names
        else:
            assert options == CRITERIA[task]
        assert row['difficulty'] in ('easy', 'hard') and row['rationale']
        source = row['source']; path = logs/source['file']
        assert path.is_file() and source['line'] >= 1
        record = next((r for n, r in enumerate(path.open(encoding='utf-8'), 1) if n == source['line']), None)
        assert record is not None
        event = json.loads(record)
        if 'tool_index' in source:
            assert 0 <= source['tool_index'] < len(event.get('tools', []))
        if task == 'context_retention':
            task_line, separator, excerpt = state.partition('\nTool output: ')
            assert separator and '\n' not in task_line and excerpt.strip(), row['case_id']
            assert not any('\u0e00' <= c <= '\u0e7f' for c in excerpt), row['case_id']
            raw = event['tools'][source['tool_index']]['result']
            assert isinstance(raw, str) and excerpt in raw, row['case_id']
        assert not SECRET.search(json.dumps(row, ensure_ascii=False))
    groups = collections.defaultdict(list)
    for row in rows:
        groups[(row['task'], row['case_id'].rsplit('_', 1)[1])].append(row)
    assert len(groups) == 32
    for group in groups.values():
        assert {r['language'] for r in group} == {'th', 'en', 'mixed'}
        first = group[0]
        for row in group[1:]:
            assert row['source'] == first['source']
            assert row['difficulty'] == first['difficulty']
            assert row['questions'] == first['questions']
            if row['task'] == 'context_retention':
                assert row['state'].split('\nTool output: ', 1)[1] == first['state'].split('\nTool output: ', 1)[1]
    for task in INSTRUCTIONS:
        assert len({r['questions'][0]['expected']['label'] for r in rows if r['task'] == task}) >= 2


def build(selection, logs):
    groups = json.loads(selection.read_text(encoding='utf-8'))
    rows = []
    for group in groups:
        task = group['task']
        for lang in ('th', 'en', 'mixed'):
            variant = group['variants'][lang]
            criteria = group.get('criteria', CRITERIA.get(task))
            rows.append({'case_id': f"{task}_{lang}_{group['number']:03d}", 'task': task,
                         'language': lang, 'state': variant['state'],
                         'questions': [{'id': task, 'request': {'type': 'choice', 'instructions': INSTRUCTIONS[task], 'criteria': criteria},
                                        'expected': {'label': group['label']}}],
                         'source': group['source'], 'rationale': variant['rationale'], 'difficulty': group['difficulty']})
    validate(rows, logs)
    local = ROOT/'local'; local.mkdir(exist_ok=True)
    review = local/'review.csv'
    if review.exists():
        with review.open(encoding='utf-8-sig', newline='') as stream:
            if any(r.get('user_label') or r.get('user_note') for r in csv.DictReader(stream)):
                raise ValueError('Refusing to overwrite human review; archive the reviewed CSV first')
    (local/'cases.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows), encoding='utf-8')
    with (local/'review.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS); writer.writeheader()
        for row in rows:
            q = row['questions'][0]
            writer.writerow({**{k: row[k] for k in ('case_id','task','language','difficulty','state','rationale')},
                             'question': q['request']['instructions'],
                             'options': json.dumps(q['request']['criteria'], ensure_ascii=False),
                             'proposed_label': q['expected']['label'], 'user_label': '', 'user_note': ''})
    print(json.dumps({'cases': len(rows), 'labels': {task: dict(collections.Counter(r['questions'][0]['expected']['label'] for r in rows if r['task'] == task)) for task in INSTRUCTIONS}, 'sha256': hashlib.sha256((local/'cases.jsonl').read_bytes()).hexdigest()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logs', type=Path, default=LOGS)
    sub = parser.add_subparsers(dest='command', required=True)
    sampling = sub.add_parser('sample'); sampling.add_argument('--kind', choices=['user', 'tool'], default='user'); sampling.add_argument('--limit', type=int, default=40)
    building = sub.add_parser('build'); building.add_argument('--selection', type=Path, default=ROOT/'local/selections.json')
    args = parser.parse_args()
    if args.command == 'sample':
        sample(args.logs, args.limit, args.kind)
    else:
        build(args.selection, args.logs)

if __name__ == '__main__':
    main()
