from __future__ import annotations

import unittest

from star_ring_codex_trpg.errors import IntentError
from star_ring_codex_trpg.playable_loop import play_choice


class PlayableLoopTests(unittest.TestCase):
    def test_play_choice_is_reproducible(self) -> None:
        left = play_choice(choice_id="observe", seed=1729, seasons=10)
        right = play_choice(choice_id="observe", seed=1729, seasons=10)
        self.assertEqual(left["intent"], right["intent"])
        self.assertEqual(left["resolution"], right["resolution"])
        self.assertEqual(left["after"]["active_node"], right["after"]["active_node"])
        self.assertEqual(left["after"]["world_pulse"], right["after"]["world_pulse"])

    def test_play_choice_appends_resolution_history(self) -> None:
        result = play_choice(choice_id="observe", seed=1729, seasons=10)
        before_len = len(result["before"]["bundle"]["world_state"]["resolved_world"]["resolution_history"])
        after_len = len(result["after"]["bundle"]["world_state"]["resolved_world"]["resolution_history"])
        self.assertEqual(after_len, before_len + 1)

    def test_play_choice_mutation_is_observable(self) -> None:
        result = play_choice(choice_id="observe", seed=1729, seasons=10)
        before_node = result["before"]["active_node"]
        after_node = result["after"]["active_node"]
        before_institution = result["before"]["institution_alert"]
        after_institution = result["after"]["institution_alert"]
        before_pulse = result["before"]["world_pulse"]
        after_pulse = result["after"]["world_pulse"]
        self.assertTrue(before_node != after_node or before_institution != after_institution or before_pulse != after_pulse)

    def test_failure_still_has_meaning(self) -> None:
        result = play_choice(choice_id="trace_pressure", seed=1729, seasons=10)
        self.assertEqual(result["resolution"]["outcome"], "failure")
        self.assertNotEqual(result["before"]["world_pulse"], result["after"]["world_pulse"])
        self.assertGreater(
            result["after"]["bundle"]["world_state"]["resolved_world"]["resolution_history"][-1]["vessel_gain"],
            0.0,
        )

    def test_unknown_choice_is_rejected(self) -> None:
        with self.assertRaises(IntentError):
            play_choice(choice_id="unknown-choice", seed=1729, seasons=10)


if __name__ == "__main__":
    unittest.main()
