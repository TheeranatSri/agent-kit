"""Offline sequential benchmark. Run each backend in a fresh Python process."""
from __future__ import annotations

import argparse
import csv
import hashlib
from dataclasses import asdict
import importlib
import json
import math
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import time

from runners.base import Prediction


def backend_for(name):
    module_name = 'baseline' if name == 'baseline' else f'runners.{name}'
    class_name = {'baseline': 'BaselineBackend', 'openthai': 'OpenThaiBackend', 'laya': 'LayaBackend'}[name]
    try:
        module = importlib.import_module(module_name)
        return getattr(module, class_name)()
    except (ImportError, AttributeError) as exc:
        raise RuntimeError(f"Backend {name!r} unavailable: need {module_name}.{class_name} and its local dependencies ({exc})") from exc


def percentile(values, percent):
    """Linear interpolation at (n-1)*percent/100, including singleton samples."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def gold_overrides(path):
    if path is None:
        return {}
    result = {}
    with Path(path).open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        if not {'case_id', 'user_label'} <= set(reader.fieldnames or []):
            raise ValueError('gold CSV requires case_id and user_label columns')
        for row in reader:
            label = row['user_label'].strip()
            if label:
                key = row['case_id'].strip()
                if key in result:
                    raise ValueError(f'duplicate filled gold label: {key}')
                result[key] = label
    return result


def score(cases, predictions, overrides=None):
    """The only function that reads expected; refusals remain in accuracy denominators."""
    overrides = overrides or {}
    by_id = {p.case_id: p for p in predictions}
    if len(by_id) != len(predictions) or set(by_id) != {c['case_id'] for c in cases}:
        raise ValueError('predictions must match unique case IDs exactly')
    if set(overrides) - set(by_id):
        raise ValueError('gold CSV contains unknown case IDs')
    groups, difficulties, tasks = {}, {}, {}
    refusals = critical_retention = critical_network = correct = 0
    for case in cases:
        q = case['questions'][0]
        gold = overrides.get(case['case_id'], q['expected']['label'])
        if gold not in q['request']['criteria']:
            raise ValueError(f"invalid gold label for {case['case_id']}: {gold}")
        pred = by_id[case['case_id']].label
        if pred is not None and pred not in q['request']['criteria']:
            raise ValueError(f"invalid prediction label for {case['case_id']}: {pred}")
        hit = pred == gold
        correct += hit
        refusals += pred is None
        for collection, key in ((groups, (case['task'], case['language'])), (difficulties, case.get('difficulty', 'unknown'))):
            entry = collection.setdefault(key, {'n': 0, 'correct': 0, 'refusals': 0})
            entry['n'] += 1
            entry['correct'] += hit
            entry['refusals'] += pred is None
        entry = tasks.setdefault(case['task'], {'labels': set(), 'pairs': []})
        entry['labels'].update(q['request']['criteria'])
        entry['pairs'].append((gold, pred))
        critical_retention += case['task'] == 'context_retention' and gold == 'must_keep' and pred == 'may_drop'
        rank = {'none': 0, 'request': 1, 'direct-read': 2}
        critical_network += case['task'] == 'network_level' and pred is not None and rank[pred] < rank[gold]
    def rows(collection):
        return [dict(key=list(key) if isinstance(key, tuple) else key, **value,
                     accuracy=value['correct'] / value['n']) for key, value in sorted(collection.items())]
    f1 = {}
    for task, entry in tasks.items():
        scores = []
        for label in sorted(entry['labels']):
            tp = sum(g == label and p == label for g, p in entry['pairs'])
            fp = sum(g != label and p == label for g, p in entry['pairs'])
            fn = sum(g == label and p != label for g, p in entry['pairs'])
            scores.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0)
        f1[task] = statistics.mean(scores)
    return {'n': len(cases), 'accuracy': correct / len(cases) if cases else None,
            'task_language': rows(groups), 'difficulty': rows(difficulties), 'macro_f1': f1,
            'refusals': refusals, 'critical_retention': critical_retention, 'critical_network': critical_network,
            'gold_overrides': len(overrides)}


def peak_rss_mib():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024 ** 2 if sys.platform == 'darwin' else 1024)


def ollama_rss():
    """Snapshot all Ollama server/runner PIDs; ps reports RSS in KiB on macOS."""
    try:
        output = subprocess.run(['ps', '-axo', 'pid=,rss=,comm='], check=True, capture_output=True, text=True).stdout
        rows = []
        for line in output.splitlines():
            parts = line.split(None, 2)
            if len(parts) == 3 and 'ollama' in parts[2].lower():
                rows.append({'pid': int(parts[0]), 'rss_mib': int(parts[1]) / 1024, 'command': parts[2]})
        return {'processes': rows, 'error': None if rows else 'no Ollama PIDs found'}
    except (OSError, subprocess.SubprocessError) as exc:
        return {'processes': [], 'error': str(exc)}


def public_case(case):
    # Explicit allowlist prevents proposed labels, rationales and sources reaching adapters.
    return {key: case[key] for key in ('case_id', 'task', 'language', 'state')} | {
        'questions': [{'id': q['id'], 'request': q['request']} for q in case['questions']]}


def benchmark(backend, cases, minimum_samples=100):
    if not cases or len({c['case_id'] for c in cases}) != len(cases):
        raise ValueError('cases must be nonempty and have unique case IDs')
    if any(len(c['questions']) != 1 for c in cases):
        raise ValueError('exactly one question per case is required')
    inputs = [public_case(c) for c in cases]
    memory = {'baseline_peak_rss_mib': peak_rss_mib()}
    if backend.name == 'openthai':
        memory['ollama_before_load'] = ollama_rss()
    start = time.perf_counter()
    try:
        backend.load()
    except ImportError as exc:
        raise RuntimeError(f"Backend {backend.name!r} load failed: install its documented dependencies locally before benchmarking ({exc})") from exc
    cold = (time.perf_counter() - start) * 1000
    memory['post_load_peak_rss_mib'] = peak_rss_mib()
    if backend.name == 'openthai':
        memory['ollama_after_load'] = ollama_rss()
    def call(case):
        start = time.perf_counter()
        try:
            pred = backend.predict(case)
        except Exception as exc:
            pred = Prediction(case['case_id'], None, error=f'{type(exc).__name__}: {exc}')
        elapsed = (time.perf_counter() - start) * 1000
        if pred.case_id != case['case_id']:
            raise ValueError('backend returned mismatched case_id')
        return pred, elapsed
    first_prediction, first = call(inputs[0])
    for i in range(5):
        call(inputs[i % len(inputs)])
    samples, timings, predictions = [], {c['case_id']: [] for c in cases}, {}
    server_snapshots = []
    workloads = {}
    for c in cases:
        key = (c['task'], c['language'])
        workloads[key] = workloads.get(key, 0) + 1
    repeats = max(1, math.ceil(minimum_samples / min(workloads.values())))
    for _ in range(repeats):
        for case in inputs:
            pred, ms = call(case)
            predictions.setdefault(case['case_id'], pred)
            timings[case['case_id']].append(ms)
            samples.append(ms)
        if backend.name == 'openthai':
            server_snapshots.append(ollama_rss())
    memory['peak_rss_mib'] = peak_rss_mib()
    memory['note'] = 'getrusage is lifetime Python peak RSS, not current idle RSS or GPU allocation; it excludes Ollama. No memory-pressure/swap measurement.'
    if backend.name == 'openthai':
        memory['ollama_after_each_pass'] = server_snapshots
        memory['ollama_sampling'] = 'ps snapshots before load and after each full case pass; transient peaks may be missed'
    records = [dict(asdict(predictions[c['case_id']]), ms=statistics.mean(timings[c['case_id']]),
                    warm_samples_ms=timings[c['case_id']]) for c in cases]
    workload_timing = []
    for (task, language), count in sorted(workloads.items()):
        values = [ms for c in cases if (c['task'], c['language']) == (task, language)
                  for ms in timings[c['case_id']]]
        workload_timing.append({'task': task, 'language': language, 'samples': count * repeats,
                                'p50_ms': percentile(values, 50), 'p95_ms': percentile(values, 95)})
    timing = {'cold_load_ms': cold, 'first_prediction_ms': first,
              'first_prediction_error': first_prediction.error,
              'cold_to_first_answer_ms': cold if backend.name == 'openthai' else None,
              'warmups': 5, 'warm_samples': len(samples), 'repeats': repeats,
              'workloads': workload_timing, 'warm_p50_ms': percentile(samples, 50), 'warm_p95_ms': percentile(samples, 95),
              'protocol': 'Fresh CLI process required; adapter load/connect then first inference. Five untimed warmups; full case passes >=100 samples per task/language workload. Backend must synchronize before returning. One request = one question.',
              'memory': memory}
    return records, timing


def report(name, scores, timing):
    lines = [f'# {name} evaluation', '',
             f"Accuracy: {scores['accuracy']:.1%} over {scores['n']} cases; {scores['refusals']} refusals (included as incorrect).",
             f"Critical errors: retention {scores['critical_retention']}; network {scores['critical_network']}.",
             f"Gold overrides: {scores['gold_overrides']}; remaining labels are proposed, awaiting human review.", '',
             f"Warm p50/p95: {timing['warm_p50_ms']:.3f}/{timing['warm_p95_ms']:.3f} ms/request and ms/question ({timing['warm_samples']} samples).",
             f"Load/connect: {timing['cold_load_ms']:.3f} ms; first prediction: {timing['first_prediction_ms']:.3f} ms."]
    if name == 'openthai':
        lines.append(f"Ollama cold-to-first-answer: {timing['cold_to_first_answer_ms']:.3f} ms (adapter load sends a readiness inference); not load-only. Server must be unloaded by the operator before this run.")
    lines += ['', timing['protocol'], '', 'Overall timing pools the mixed suite; each task/language workload also has >=100 samples. The 200 ms p95 target is provisional. Matched language adaptations are correlated, not independent observations.', '',
              '## Accuracy by task and language', '', '| Task | Language | Cases | Accuracy | Refusals |', '|---|---|---:|---:|---:|']
    for row in scores['task_language']:
        lines.append(f"| {row['key'][0]} | {row['key'][1]} | {row['n']} | {row['accuracy']:.1%} | {row['refusals']} |")
    lines += ['', '## Difficulty', '', '| Difficulty | Cases | Accuracy | Refusals |', '|---|---:|---:|---:|']
    for row in scores['difficulty']:
        lines.append(f"| {row['key']} | {row['n']} | {row['accuracy']:.1%} | {row['refusals']} |")
    lines += ['', '## Macro F1', '', '| Task | Macro F1 |', '|---|---:|']
    for task, value in sorted(scores['macro_f1'].items()):
        lines.append(f'| {task} | {value:.4f} |')
    lines += ['', 'Macro F1 averages every offered label, with zero for a zero denominator. Refusals create false negatives; they are not ranked network predictions.', '',
              'Each JSONL row stores the first warm Prediction, mean ms and every warm timing. Repeated timings do not multiply scoring cases. Exceptions are recorded as refusals. Warm latency includes refused requests.', '',
              '## Warm timings by workload', '', '| Task | Language | Samples | p50 ms | p95 ms |', '|---|---|---:|---:|---:|']
    for row in timing['workloads']:
        lines.append(f"| {row['task']} | {row['language']} | {row['samples']} | {row['p50_ms']:.3f} | {row['p95_ms']:.3f} |")
    lines += ['', '## Run provenance', '', json.dumps({key: timing[key] for key in ('environment', 'backend_settings', 'case_sha256', 'gold_sha256', 'adapter_import_and_construct_ms', 'runtime_note') if key in timing}, ensure_ascii=False), '', '## Memory', '', timing['memory']['note'], '', '```json', json.dumps(timing['memory'], indent=2), '```', '',
              '<!-- benchmark-summary ' + json.dumps({'backend': name, 'scores': scores, 'timing': timing}) + ' -->']
    return '\n'.join(lines) + '\n'


def write_results(out, name, records, scores, timing):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f'{name}.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records), encoding='utf-8')
    (out / f'{name}.md').write_text(report(name, scores, timing), encoding='utf-8')
    summaries = []
    for candidate in ('baseline', 'openthai', 'laya'):
        path = out / f'{candidate}.md'
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                if line.startswith('<!-- benchmark-summary '):
                    summaries.append(json.loads(line[len('<!-- benchmark-summary '):-4]))
    if len(summaries) > 1:
        lines = ['# Backend comparison', '', 'Compare only runs with identical cases, human labels and machine/runtime settings. These stored results may come from different runs; verify provenance before ranking.', '',
                 '| Backend | Accuracy | Refusals | Retention critical | Network critical | p50 ms | p95 ms |', '|---|---:|---:|---:|---:|---:|---:|']
        for row in summaries:
            s, t = row['scores'], row['timing']
            lines.append(f"| {row['backend']} | {s['accuracy']:.1%} | {s['refusals']} | {s['critical_retention']} | {s['critical_network']} | {t['warm_p50_ms']:.3f} | {t['warm_p95_ms']:.3f} |")
        (out / 'compare.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', required=True, choices=['openthai', 'laya', 'baseline'])
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--gold', type=Path)
    args = parser.parse_args(argv)
    try:
        cases = [json.loads(line) for line in args.cases.read_text(encoding='utf-8').splitlines() if line.strip()]
        overrides = gold_overrides(args.gold)
        import_start = time.perf_counter()
        backend = backend_for(args.backend)
        import_ms = (time.perf_counter() - import_start) * 1000
        records, timing = benchmark(backend, cases)
        timing['adapter_import_and_construct_ms'] = import_ms
        predictions = [Prediction(**{k: r[k] for k in ('case_id', 'label', 'probabilities', 'usage', 'raw', 'error')}) for r in records]
        scores = score(cases, predictions, overrides)
        timing['case_sha256'] = hashlib.sha256(args.cases.read_bytes()).hexdigest()
        timing['gold_sha256'] = hashlib.sha256(args.gold.read_bytes()).hexdigest() if args.gold else None
        timing['backend_settings'] = {k: getattr(backend, k) for k in ('model', 'dtype', 'num_ctx', 'timeout') if hasattr(backend, k)}
        timing['runtime_note'] = 'Checkpoint digest/revision, backend runtime version and optimization settings must be pinned by operator; not inferred by runner.'
        timing['environment'] = {'python': platform.python_version(), 'platform': platform.platform(), 'backend': backend.name,
                                 'cases_path': str(args.cases), 'gold_path': str(args.gold) if args.gold else None}
        write_results(args.out, args.backend, records, scores, timing)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        parser.exit(2, f'error: {exc}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
