import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from runners.base import Prediction
from run_eval import benchmark, backend_for, gold_overrides, percentile, score, write_results, main
from tests.test_baseline import case


class FakeBackend:
    name = 'fake'

    def __init__(self):
        self.calls = 0
        self.loads = 0

    def load(self):
        self.loads += 1

    def predict(self, value):
        self.calls += 1
        assert 'source' not in value and 'rationale' not in value
        assert 'expected' not in value['questions'][0]
        return Prediction(value['case_id'], 'must_keep', usage={'tokens': 2})


class RunnerTests(unittest.TestCase):
    def test_percentiles(self):
        self.assertEqual(percentile([1, 2, 3, 4], 50), 2.5)
        self.assertAlmostEqual(percentile([1, 2, 3, 4], 95), 3.85)
        self.assertEqual(percentile([7], 95), 7)
        self.assertIsNone(percentile([], 50))

    def test_scoring_and_critical_errors(self):
        retention = {'must_keep': '', 'may_drop': ''}
        network = dict.fromkeys(('none', 'request', 'direct-read'), '')
        cases = [case('context_retention', '', retention, g, case_id=str(i), difficulty='hard' if i == 1 else 'easy')
                 for i, g in enumerate(['must_keep', 'must_keep', 'may_drop', 'may_drop'])]
        cases += [case('network_level', '', network, g, case_id=str(i + 4))
                  for i, g in enumerate(['direct-read', 'request', 'none', 'direct-read'])]
        preds = [Prediction(str(i), p) for i, p in enumerate(['must_keep', 'may_drop', 'may_drop', None,
                                                            'request', 'none', 'none', None])]
        result = score(cases, preds)
        self.assertEqual(result['accuracy'], 3 / 8)
        self.assertEqual(result['refusals'], 2)
        self.assertEqual(result['critical_retention'], 1)
        self.assertEqual(result['critical_network'], 2)
        # Retention F1: keep=2/3; drop=1/2; macro=7/12.
        self.assertAlmostEqual(result['macro_f1']['context_retention'], 7 / 12)
        # Network F1: none=2/3, request=0, direct-read=0.
        self.assertAlmostEqual(result['macro_f1']['network_level'], 2 / 9)
        self.assertEqual(result['difficulty'][1]['accuracy'], 0)
        self.assertEqual(result['task_language'][0]['accuracy'], .5)

    def test_gold_csv_override(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temp:
            path = Path(temp) / 'gold.csv'
            path.write_text('case_id,user_label,user_note\nx,may_drop,reviewed\ny, ,pending\n')
            overrides = gold_overrides(path)
            self.assertEqual(overrides, {'x': 'may_drop'})
            cases = [case('context_retention', '', {'must_keep': '', 'may_drop': ''}, 'must_keep', case_id='x')]
            self.assertEqual(score(cases, [Prediction('x', 'may_drop')], overrides)['accuracy'], 1)
            with self.assertRaises(ValueError):
                score(cases, [Prediction('x', 'may_drop')], {'x': 'invalid'})
            path.write_text('case_id,user_label\nx,may_drop\nx,must_keep\n')
            with self.assertRaises(ValueError):
                gold_overrides(path)

    def test_timing_protocol_and_sanitization(self):
        cases = [case('context_retention', 'error', {'must_keep': '', 'may_drop': ''}, 'must_keep', case_id=str(i)) for i in range(3)]
        backend = FakeBackend()
        # Advancing clock makes each timed operation exactly 1 ms.
        with patch('run_eval.time.perf_counter', side_effect=(i / 1000 for i in range(10000))):
            records, timing = benchmark(backend, cases)
        self.assertEqual(backend.loads, 1)
        self.assertEqual(timing['warm_samples'], 102)
        self.assertEqual(backend.calls, 1 + 5 + 102)
        self.assertAlmostEqual(timing['cold_load_ms'], 1)
        self.assertAlmostEqual(timing['first_prediction_ms'], 1)
        self.assertAlmostEqual(timing['warm_p95_ms'], 1)
        self.assertEqual(len(records), 3)
        self.assertEqual(len(records[0]['warm_samples_ms']), 34)
        self.assertEqual(records[0]['usage'], {'tokens': 2})

    def test_prediction_exception_is_refusal(self):
        backend = FakeBackend()
        backend.predict = lambda value: (_ for _ in ()).throw(ValueError('too_long'))
        cases = [case('context_retention', '', {'must_keep': '', 'may_drop': ''}, 'must_keep')]
        records, _ = benchmark(backend, cases)
        self.assertIsNone(records[0]['label'])
        self.assertIn('too_long', records[0]['error'])

    def test_output_and_comparison(self):
        cases = [case('context_retention', '', {'must_keep': '', 'may_drop': ''}, 'must_keep')]
        records, timing = benchmark(FakeBackend(), cases)
        scores = score(cases, [Prediction('synthetic', 'must_keep')])
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temp:
            write_results(temp, 'baseline', records, scores, timing)
            self.assertFalse((Path(temp) / 'compare.md').exists())
            write_results(temp, 'laya', records, scores, timing)
            self.assertIn('| baseline |', (Path(temp) / 'compare.md').read_text())
            rows = [json.loads(line) for line in (Path(temp) / 'baseline.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertIn('ms', rows[0])

    def test_missing_runner_clear_error_and_lazy_import(self):
        with patch('run_eval.importlib.import_module', side_effect=ImportError('synthetic missing dependency')):
            with self.assertRaisesRegex(RuntimeError, 'runners.laya.LayaBackend'):
                backend_for('laya')
        self.assertEqual(backend_for('baseline').name, 'baseline')

    def test_each_workload_reaches_100_samples(self):
        cases = [case('context_retention', '', {'must_keep': '', 'may_drop': ''}, 'must_keep',
                      language='th' if i == 0 else 'en', case_id=str(i)) for i in range(3)]
        records, timing = benchmark(FakeBackend(), cases)
        self.assertEqual(timing['warm_samples'], 300)
        self.assertEqual(sorted(w['samples'] for w in timing['workloads']), [100, 200])

    def test_ollama_memory_and_cold_semantics(self):
        backend = FakeBackend()
        backend.name = 'openthai'
        cases = [case('context_retention', '', {'must_keep': '', 'may_drop': ''}, 'must_keep')]
        with patch('run_eval.ollama_rss', return_value={'processes': [{'pid': 123, 'rss_mib': 4}], 'error': None}) as ps:
            _, timing = benchmark(backend, cases)
        self.assertEqual(timing['cold_to_first_answer_ms'], timing['cold_load_ms'])
        self.assertEqual(ps.call_count, 102)  # Before load, after load, after each pass.
        self.assertEqual(timing['memory']['ollama_after_load']['processes'][0]['pid'], 123)

    def test_ps_failure_recorded(self):
        from run_eval import ollama_rss
        with patch('run_eval.subprocess.run', side_effect=PermissionError('sandbox')):
            result = ollama_rss()
        self.assertEqual(result['processes'], [])
        self.assertIn('sandbox', result['error'])

    def test_load_import_error_is_clear(self):
        backend = FakeBackend()
        backend.load = lambda: (_ for _ in ()).throw(ImportError('missing fake runtime'))
        cases = [case('context_retention', '', {'must_keep': '', 'may_drop': ''}, 'must_keep')]
        with self.assertRaisesRegex(RuntimeError, 'install its documented dependencies locally'):
            benchmark(backend, cases)

    def test_cli_synthetic(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temp:
            path = Path(temp) / 'cases.jsonl'
            path.write_text(json.dumps(case('context_retention', 'error', {'must_keep': '', 'may_drop': ''}, 'must_keep')) + '\n')
            self.assertEqual(main(['--backend', 'baseline', '--cases', str(path), '--out', str(Path(temp) / 'results')]), 0)
            self.assertTrue((Path(temp) / 'results' / 'baseline.md').exists())
