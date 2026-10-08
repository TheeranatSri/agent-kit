import unittest
from baseline import BaselineBackend


def case(task, state, labels, gold='unused', language='en', difficulty='easy', case_id='synthetic'):
    return {'case_id': case_id, 'task': task, 'language': language, 'difficulty': difficulty,
            'state': state, 'questions': [{'id': 'q', 'request': {'type': 'choice', 'instructions': 'Select',
            'criteria': labels}, 'expected': {'label': gold}}]}


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.backend = BaselineBackend()
        self.backend.load()

    def test_retention_languages(self):
        labels = {'must_keep': 'keep', 'may_drop': 'drop'}
        for text in ('failed', 'ไม่ผ่าน', 'error ที่ /tmp/file', 'count 42'):
            with self.subTest(text=text):
                self.assertEqual(self.backend.predict(case('context_retention', text, labels)).label, 'must_keep')
        self.assertEqual(self.backend.predict(case('context_retention', 'hello', labels)).label, 'may_drop')

    def test_network_priority(self):
        labels = dict.fromkeys(('none', 'request', 'direct-read'), '')
        for text, wanted in [('web search', 'direct-read'), ('ค้นเว็บ', 'direct-read'),
                             ('BigQuery web', 'request'), ('ดึงข้อมูล', 'request'), ('local file', 'none')]:
            self.assertEqual(self.backend.predict(case('network_level', text, labels)).label, wanted)

    def test_routing(self):
        labels = dict.fromkeys(('cheap', 'current', 'escalate'), '')
        for text, wanted in [('summarize', 'cheap'), ('แก้โค้ด', 'current'), ('choose method', 'escalate'),
                             ('ตัดสินใจ', 'escalate')]:
            self.assertEqual(self.backend.predict(case('agent_routing', text, labels)).label, wanted)

    def test_skill_overlap_and_none(self):
        labels = {'handoff': 'Prepare next-session handoff', 'wiki': 'Maintain knowledge wiki',
                  'skill-creator': 'Create reusable skills', 'none': 'No skill'}
        for text, wanted in [('prepare handoff', 'handoff'), ('ส่งต่อเซสชัน', 'handoff'),
                             ('knowledge wiki', 'wiki'), ('สร้างสกิล', 'skill-creator'), ('hello', 'none')]:
            self.assertEqual(self.backend.predict(case('skill_selection', text, labels)).label, wanted)

    def test_gold_not_read(self):
        class Poison(dict):
            def __getitem__(self, key):
                if key == 'expected':
                    raise AssertionError('gold accessed')
                return super().__getitem__(key)
        value = case('context_retention', 'error', {'must_keep': '', 'may_drop': ''})
        value['questions'][0] = Poison(value['questions'][0])
        self.assertEqual(self.backend.predict(value).label, 'must_keep')

    def test_refuses_unsupported(self):
        value = case('other', 'text', {'a': '', 'b': ''})
        self.assertIsNone(self.backend.predict(value).label)
        value['questions'][0]['request']['type'] = 'noul'
        self.assertIsNone(self.backend.predict(value).label)
