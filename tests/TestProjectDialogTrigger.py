"""No-game verification of W/S/F choices and fail-closed menu progression."""

import unittest
from unittest.mock import Mock, patch

import numpy as np
from ok import Box, TriggerTask

from src.config import config
from src.data.FeatureList import FeatureList as Feature
from src.tasks.AutoSkipDialogTask import AutoSkipDialogTask
from src.tasks.dialogue_choices import ChoiceMemory


class FrameTask(AutoSkipDialogTask):
    @property
    def frame(self):
        return self.test_frame


class TestProjectDialogTrigger(unittest.TestCase):
    def setUp(self):
        self.task = FrameTask.__new__(FrameTask)
        self.task.test_frame = np.zeros((240, 339, 3), dtype=np.uint8)
        self.task._choice_memory = ChoiceMemory()
        self.task._choice_attempt = None
        self.task.send_key = Mock(return_value=True)
        self.task.next_frame = Mock(side_effect=lambda: self.task.test_frame)
        self.task.screenshot = Mock()
        self.task.log_warning = Mock()
        self.task.click = Mock()
        self.found = set()
        self.task.find_one = Mock(side_effect=lambda name, **kwargs: name in self.found)
        self.options = [Box(220, 130, 6, 4), Box(220, 145, 6, 4)]
        self.task.find_feature = Mock(return_value=self.options)

    def run_with_lengths(self, lengths):
        with patch("src.tasks.AutoSkipDialogTask.text_band_lengths", return_value=lengths):
            return self.task.run()

    def confirm_menu_gone(self):
        self.found = set()
        self.task.run()
        self.task.run()

    def test_registry(self):
        entry = ["src.tasks.AutoSkipDialogTask", "AutoSkipDialogTask"]
        self.assertTrue(issubclass(AutoSkipDialogTask, TriggerTask))
        self.assertIn(entry, config["trigger_tasks"])
        self.assertNotIn(entry, config["onetime_tasks"])

    def test_orphan_prompts_are_ignored(self):
        for found in (set(), {Feature.skip_f}, {Feature.skip_choose}):
            self.found = found
            self.assertIs(self.task.run(), False)
        self.task.send_key.assert_not_called()
        self.task.click.assert_not_called()
        self.task.find_feature.assert_not_called()

    def test_continuation_f_still_requires_dialogue(self):
        self.found = {Feature.dialog_icon, Feature.skip_f}
        self.assertIs(self.task.run(), False)
        self.task.send_key.assert_called_once_with("f", after_sleep=0.1)
        self.task.click.assert_not_called()

    def test_first_option_only_f_after_screenshot(self):
        self.found = {Feature.dialog_icon, Feature.skip_choose, Feature.skip_f}
        self.run_with_lengths((4.0, 6.0))
        self.task.send_key.assert_called_once_with("f", down_time=0.08, after_sleep=0.12)
        self.assertEqual(self.task._choice_attempt.phase, "confirm")
        self.assertEqual(self.task._choice_memory.records, [])
        self.assertEqual(self.task.screenshot.call_count, 2)
        self.task.click.assert_not_called()
        self.confirm_menu_gone()
        self.assertEqual(len(self.task._choice_memory.records), 1)
        self.assertEqual(self.task._choice_memory.records[0].next_index, 1)

    def test_second_option_s_then_f_on_separate_fresh_frames(self):
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        with patch("src.tasks.AutoSkipDialogTask.text_band_lengths", return_value=(4.0, 6.0)):
            self.task.run()  # First menu: F only.
            self.confirm_menu_gone()
            self.found = {Feature.dialog_icon, Feature.skip_choose}
            self.task.send_key.reset_mock()
            self.task.run()  # Returning menu: one S, no F yet.
            self.task.send_key.assert_called_once_with("s", down_time=0.08, after_sleep=0.12)
            self.assertEqual(self.task._choice_attempt.sent_s, 1)
            self.task.run()  # New trigger frame: F.
        self.assertEqual([c.args[0] for c in self.task.send_key.call_args_list], ["s", "f"])
        self.assertEqual(self.task.next_frame.call_count, 3)
        self.assertEqual(len(self.task._choice_memory.records), 1)
        self.confirm_menu_gone()
        self.assertEqual(self.task._choice_memory.records[0].next_index, 0)
        self.task.click.assert_not_called()

    def test_four_options_require_three_s_then_f(self):
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.options = [Box(220, 110 + i * 15, 6, 4) for i in range(4)]
        self.task.find_feature.return_value = self.options
        self.task._choice_memory.records = []
        with patch("src.tasks.AutoSkipDialogTask.text_band_lengths", return_value=(3.0, 4.0, 5.0, 6.0)):
            for target_index in range(3):
                for _ in range(target_index + 1):  # S * index, then F
                    self.task.run()
                self.confirm_menu_gone()
                self.found = {Feature.dialog_icon, Feature.skip_choose}
            self.task.send_key.reset_mock()
            for _ in range(4):
                self.task.run()
        self.assertEqual([c.args[0] for c in self.task.send_key.call_args_list], ["s", "s", "s", "f"])
        self.assertEqual(self.task._choice_attempt.phase, "confirm")
        self.task.click.assert_not_called()

    def test_no_f_after_missing_screen_or_changed_menu(self):
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        with patch("src.tasks.AutoSkipDialogTask.text_band_lengths", return_value=(4.0, 6.0)):
            self.task.run()
        self.confirm_menu_gone()
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        with patch("src.tasks.AutoSkipDialogTask.text_band_lengths", return_value=(4.0, 6.0)):
            self.task.run()  # S on the second visit.
        self.task.test_frame = None
        self.assertIs(self.task.run(), False)
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.assertEqual(self.task.send_key.call_args_list[-1].args[0], "s")
        self.task.test_frame = np.zeros((240, 339, 3), dtype=np.uint8)
        with patch("src.tasks.AutoSkipDialogTask.text_band_lengths", return_value=(4.0, 7.0)):
            self.task.run()  # Blocked: never issue F.
        self.assertEqual(self.task.send_key.call_args_list[-1].args[0], "s")
        self.assertTrue(self.task.log_warning.called)

    def test_failed_send_blocks_retries_until_menu_disappears(self):
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.task.send_key.return_value = False
        self.run_with_lengths((4.0, 6.0))
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.assertFalse(self.task._choice_memory.records)
        with patch("src.tasks.AutoSkipDialogTask.text_band_lengths", return_value=(4.0, 6.0)):
            for _ in range(5):
                self.task.run()
        self.assertEqual(self.task.send_key.call_count, 1)
        self.confirm_menu_gone()
        self.assertIsNone(self.task._choice_attempt)
        self.assertFalse(self.task._choice_memory.records)

    def test_f_without_visual_transition_stops_and_does_not_advance(self):
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.run_with_lengths((4.0, 6.0))
        for _ in range(self.task.CONFIRM_CHECKS):
            self.run_with_lengths((4.0, 6.0))
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.assertFalse(self.task._choice_memory.records)
        self.assertEqual(self.task.send_key.call_count, 1)
        self.assertTrue(self.task.log_warning.called)

    def test_unreadable_text_never_sends_input(self):
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.run_with_lengths(None)
        self.assertIsNone(self.task._choice_attempt)
        self.task.send_key.assert_not_called()
        self.task.click.assert_not_called()


class TestProjectChoiceMemory(unittest.TestCase):
    def test_joint_fingerprints_keep_independent_progress(self):
        memory = ChoiceMemory()

        def select(lengths):
            memory.hide()
            decision = memory.prepare(lengths)
            memory.commit(decision)
            return decision.index

        self.assertEqual(select((4.0, 6.0)), 0)
        self.assertEqual(select((4.0, 9.0)), 0)
        self.assertEqual(select((4.0,)), 0)
        self.assertEqual(select((4.1, 6.1)), 1)
        self.assertEqual(select((4.0, 9.1)), 1)
        self.assertEqual(select((4.0,)), 0)
        self.assertEqual(select((4.0, 6.0)), 0)
        self.assertEqual(len(memory.records), 3)
