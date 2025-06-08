import sys
from pathlib import Path
import unittest

# Ensure the services package can be imported when tests are run from repo root
sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.spotify import _select_tempo

class TestSelectTempo(unittest.TestCase):
    def test_weighted_average_when_close(self):
        s1 = {'tempo': 100, 'energy': 0.8}
        s2 = {'tempo': 105, 'energy': 0.2}
        self.assertEqual(_select_tempo(s1, s2), 101)

    def test_reference_choice_large_gap(self):
        s1 = {'tempo': 95, 'energy': 0.4}
        s2 = {'tempo': 160, 'energy': 0.6}
        # 95 is closer to reference 120 than 160
        self.assertEqual(_select_tempo(s1, s2), 95)

    def test_energy_tiebreak_on_reference(self):
        s1 = {'tempo': 80, 'energy': 0.4}
        s2 = {'tempo': 160, 'energy': 0.6}
        # both distances to reference (120) are 40 -> choose higher energy 160
        self.assertEqual(_select_tempo(s1, s2), 160)

if __name__ == '__main__':
    unittest.main()
