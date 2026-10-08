import copy
import sys
import types
import unittest
from unittest.mock import patch

from runners.laya import LayaBackend


class Tokenizer:
    mask_token = '<mask>'
    mask_token_id = -1
    cls_token_id = -2
    sep_token_id = -3

    def __call__(self, text, add_special_tokens=False):
        assert add_special_tokens is False
        return {'input_ids': [ord(c) for c in text]}


class Agent:
    tok = Tokenizer()
    cfg = {'max_len': 1024, 'head_max_len': 256}

    def __init__(self, answer=None, usage=None):
        self.calls = []
        self.raw = {'answers': {'q': answer or {'choice': 'keep', 'probabilities': {'keep': .8, 'drop': .2}}},
                    'usage': usage or {'input_tokens': 80, 'truncated': False, 'state_tokens_dropped': 0,
                                       'truncated_questions': []}}

    def predict(self, state, questions):
        self.calls.append((state, questions))
        return self.raw


def case(state='สถานะงาน: keep this fact'):
    return {'case_id': 'synthetic', 'state': state, 'questions': [
        {'id': 'q', 'request': {'type': 'choice', 'instructions': 'Choose',
                              'criteria': {'keep': None, 'drop': None}},
         'expected': {'label': 'drop'}}]}


class LayaTests(unittest.TestCase):
    def test_success_thai_gold_not_passed(self):
        c = case()
        before = copy.deepcopy(c)
        agent = Agent()
        result = LayaBackend(agent=agent).predict(c)
        self.assertEqual(result.label, 'keep')
        self.assertEqual(result.probabilities, {'keep': .8, 'drop': .2})
        self.assertIs(result.raw, agent.raw)
        self.assertEqual(result.usage['state_tokens_dropped'], 0)
        self.assertEqual(agent.calls, [(c['state'], {'q': c['questions'][0]['request']})])
        self.assertEqual(c, before)
        self.assertIn('สถานะ', agent.calls[0][0])

    def refuse(self, c, agent=None):
        agent = agent or Agent()
        result = LayaBackend(agent=agent).predict(c)
        self.assertIsNone(result.label)
        self.assertTrue(result.error.startswith('too_long:'), result.error)
        self.assertEqual(agent.calls, [])
        return result

    def test_sequence_overflow(self):
        result = self.refuse(case('x' * 1024))
        self.assertGreater(result.usage['preflight']['prepared_tokens'], 1024)

    def test_state_contract_limit(self):
        self.refuse(case('x' * 701))

    def test_option_initial_cap(self):
        c = case()
        c['questions'][0]['request']['criteria']['keep'] = 'x' * 49
        self.refuse(c)

    def test_instruction_shortening(self):
        c = case()
        c['questions'][0]['request']['instructions'] = 'x' * 300
        self.refuse(c)

    def test_crowded_options(self):
        c = case()
        c['questions'][0]['request']['criteria'] = {str(i): 'x' * 35 for i in range(10)}
        self.refuse(c)

    def test_marker_collision(self):
        self.refuse(case('literal <mask>'))

    def test_runtime_preparation_shortening(self):
        agent = Agent()
        agent.prepare = lambda state, questions: ([{'ids': [1], 'state_stats': {'truncated': True}}], [])
        self.refuse(case(), agent)

    def test_runtime_diagnostics_preserved(self):
        usage = {'truncated': True, 'state_tokens_dropped': 3, 'truncated_questions': ['q']}
        agent = Agent(usage=usage)
        result = LayaBackend(agent=agent).predict(case())
        self.assertIsNone(result.label)
        for key, value in usage.items():
            self.assertEqual(result.usage[key], value)
        self.assertIs(result.raw, agent.raw)

    def test_unknown_choice(self):
        result = LayaBackend(agent=Agent({'choice': 'other'})).predict(case())
        self.assertEqual(result.error, 'invalid_response: unknown choice label')

    def test_noul_mapping(self):
        c = case()
        c['questions'][0]['request'] = {'type': 'noul', 'instructions': 'Is it true?'}
        result = LayaBackend(agent=Agent({'noul': .75})).predict(c)
        self.assertEqual(result.label, 'true')
        self.assertEqual(result.probabilities, {'false': .25, 'true': .75})

    def test_score_mapping(self):
        c = case()
        c['questions'][0]['request'] = {'type': 'score', 'instructions': 'Rate', 'criteria': ['low', 'high']}
        result = LayaBackend(agent=Agent({'score': .8, 'probabilities': {'0': .2, '1': .8}})).predict(c)
        self.assertEqual(result.label, '1')
        self.assertEqual(result.raw['answers']['q']['score'], .8)

    def test_no_tokenizer_fails_closed(self):
        agent = Agent()
        agent.tok = None
        result = LayaBackend(agent=agent).predict(case())
        self.assertTrue(result.error.startswith('preflight_unavailable:'))
        self.assertEqual(agent.calls, [])

    def test_lazy_load(self):
        calls = []
        fake = types.SimpleNamespace(load=lambda *a, **kw: calls.append((a, kw)) or Agent())
        with patch.dict(sys.modules, {'laya_mlx': fake}):
            backend = LayaBackend()
            backend.load()
        self.assertEqual(calls, [(('aac6fef/laya-multilingual-mlx',),
                                 {'dtype': 'float16', 'device': 'gpu', 'batch_size': 1})])
        self.assertEqual(backend.predict(case()).label, 'keep')

    def test_contract_validation(self):
        self.assertTrue(LayaBackend().predict(case()).error.startswith('not_loaded:'))
        c = case()
        c['questions'] *= 2
        self.assertTrue(LayaBackend(agent=Agent()).predict(c).error.startswith('invalid_case:'))


if __name__ == '__main__':
    unittest.main()
