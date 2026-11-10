"""Exercise the production timing function without importing the HTTP listener."""
import ast
from pathlib import Path
import re
import unittest


class MarineTimingTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(Path(__file__).resolve().parents[1].joinpath('cloud_server.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'get_timing_window')
        namespace = {'re': re, 'normalize_text': lambda text: ' '.join(text.split()),
                     'parse_descriptor': lambda text, issue: text.strip()}
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<marine-timing>', 'exec'), namespace)
        self.window = namespace['get_timing_window']

    def test_each_island_uses_its_own_expiry(self):
        text = 'Timing: Until 5 PM today for Antigua; until 8 PM today for Barbuda. Synopsis: Seas rough.'
        self.assertEqual(self.window(text, 'issued', True, target_island='Antigua'), ('issued', '5 PM today'))
        self.assertEqual(self.window(text, 'issued', True, target_island='Barbuda'), ('issued', '8 PM today'))

    def test_barbuda_start_does_not_borrow_antigua_start(self):
        text = 'Timing: From 2 PM until 5 PM for Antigua; from 3 PM until 8 PM for Barbuda. Synopsis: Rough.'
        self.assertEqual(self.window(text, 'issued', True, target_island='Barbuda'), ('3 PM', '8 PM'))

    def test_unknown_foreign_island_window_stays_unreadable(self):
        text = 'Timing: Until 8 PM for the BVI. Synopsis: Rough.'
        self.assertEqual(self.window(text, 'issued', True, target_island='Barbuda'), (None, None))

    def test_unqualified_local_window_still_works(self):
        self.assertEqual(self.window('Timing: Until 8 PM. Synopsis: Rough.', 'issued', True), ('issued', '8 PM'))


class MarineCheckTests(unittest.TestCase):
    def setUp(self):
        from datetime import datetime, timedelta, timezone
        from types import SimpleNamespace
        from official_alerts import parse_marine_locations, parse_marine_cancellations
        tree = ast.parse(Path(__file__).resolve().parents[1].joinpath('cloud_server.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'check_alert')
        now = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
        class Clock:
            @staticmethod
            def now(tz): return now
        self.namespace = {'re': re, 'datetime': Clock, 'ANTIGUA_TIME': timezone.utc,
            'normalize_text': lambda text: ' '.join(text.split()),
            'fetch': lambda url: self.text, 'pdf_to_text': lambda text: text,
            'parse_issue_datetime': lambda text: (now - timedelta(hours=1), SimpleNamespace(end=lambda: 0)),
            'parse_marine_locations': parse_marine_locations,
            'parse_marine_cancellations': parse_marine_cancellations,
            'get_timing_window': lambda *args, **kwargs: (now - timedelta(hours=1), now + timedelta(hours=3))}
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<marine-check>', 'exec'), self.namespace)
        self.check = self.namespace['check_alert']

    def test_one_island_cancellation_preserves_other_island(self):
        self.text = ('Small Craft Advisory for Antigua and Barbuda. '
                     'The Small Craft Advisory for Antigua has been cancelled. '
                     'Timing: Until5PM. Synopsis: Rough.')
        _, result = self.check(('Small Craft Advisory', 'https://www.antiguamet.com/test.pdf'))
        self.assertEqual(result['area_checks']['Antigua']['reason'], 'cancelled')
        self.assertTrue(result['area_checks']['Barbuda']['active'])

    def test_negated_and_future_cancellations_keep_current_alert(self):
        for qualifier in ['has not been cancelled', 'will be cancelled at 6 PM']:
            self.text = ('Small Craft Warning for Antigua. '
                         f'The Small Craft Warning for Antigua {qualifier}. Timing: Until6PM. Synopsis: Rough.')
            _, result = self.check(('Small Craft Warning', 'https://www.antiguamet.com/test.pdf'))
            self.assertTrue(result['area_checks']['Antigua']['active'])

    def test_ambiguous_cancelled_heading_cannot_show_current_alert(self):
        self.text = 'Small Craft Advisory for Antigua DISCONTINUED. Timing: Until5PM. Synopsis: Rough.'
        _, result = self.check(('Small Craft Advisory', 'https://www.antiguamet.com/test.pdf'))
        self.assertFalse(result['active'])
        self.assertEqual(result['area_checks']['Antigua']['reason'], 'cancellation_status_unverified')


if __name__ == '__main__':
    unittest.main()
