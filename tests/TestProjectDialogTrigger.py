"""No-game dialogue decisions and independent option fingerprints."""

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
        """Return a fixture without creating a game executor."""
        return self.test_frame



class TestProjectDialogTrigger(unittest.TestCase):
    def setUp(self):
        """Isolate the task from capture and input."""
        self.task = FrameTask.__new__(FrameTask)
        self.task.test_frame = np.zeros((240, 339, 3), dtype=np.uint8)
        self.task._choice_memory = ChoiceMemory()
        self.task.send_key = Mock()
        self.task.click = Mock(return_value=True)
        self.found = set()
        self.task.find_one = Mock(side_effect=lambda name, **kwargs: name in self.found)
        self.options = [Box(220, 130, 6, 4), Box(220, 145, 6, 4)]
        self.task.find_feature = Mock(side_effect=lambda *args, **kwargs: self.options)

    def test_registry(self):
        """Dialogue skipping is opt-in trigger work."""
        entry = ["src.tasks.AutoSkipDialogTask", "AutoSkipDialogTask"]
        self.assertTrue(issubclass(AutoSkipDialogTask, TriggerTask))
        self.assertIn(entry, config["trigger_tasks"])
        self.assertNotIn(entry, config["onetime_tasks"])

    def test_idle_and_removed_task_item_fallback(self):
        """Neither orphan hints nor removed task-item handling may send input."""
        for found in (set(), {Feature.skip_f}, {Feature.skip_choose}):
            self.found = found
            self.assertIs(self.task.run(), False)
        self.task.send_key.assert_not_called()
        self.task.click.assert_not_called()
        self.task.find_feature.assert_not_called()

    def test_continuation_requires_dialogue(self):
        """A verified dialogue and F prompt can advance once."""
        self.found = {Feature.dialog_icon, Feature.skip_f}
        self.assertIs(self.task.run(), False)
        self.task.send_key.assert_called_once_with("f", after_sleep=0.1)
        self.task.click.assert_not_called()

    def test_ws_gate_and_choice_priority(self):
        """W/S gates option detection and takes priority over F."""
        self.found = {Feature.dialog_icon}
        self.task.run()
        self.task.find_feature.assert_not_called()
        self.found |= {Feature.skip_choose, Feature.skip_f}
        self.task.find_feature.return_value = []
        self.task.find_feature.side_effect = None
        self.task.run()
        self.task.send_key.assert_not_called()
        self.task.click.assert_not_called()

    def test_repeated_fingerprint_advances_after_menu_disappears(self):
        """Debounce a visible menu; returning menus advance and wrap."""
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        with patch("src.tasks.AutoSkipDialogTask.text_band_lengths", return_value=(4.0, 6.0)):
            self.task.run()
            self.task.run()
            self.task.click.assert_called_once_with(self.options[0], after_sleep=0.2)
            self.found = set()
            self.task.run()
            self.found = {Feature.dialog_icon, Feature.skip_choose}
            self.task.run()
            self.assertEqual(self.task.click.call_args.args[0], self.options[1])
            self.task._choice_memory.hide()
            self.task.run()
            self.assertEqual(self.task.click.call_args.args[0], self.options[0])
        self.task.send_key.assert_not_called()

    def test_failed_click_and_unreadable_text_do_not_advance(self):
        """Save progress only after a measured option was successfully clicked."""
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        with patch("src.tasks.AutoSkipDialogTask.text_band_lengths", return_value=None):
            self.task.run()
        self.task.click.assert_not_called()
        self.task.click.return_value = False
        with patch("src.tasks.AutoSkipDialogTask.text_band_lengths", return_value=(4.0, 6.0)):
            self.task.run()
            self.assertFalse(self.task._choice_memory.records)
            self.task.click.return_value = True
            self.task.run()
        self.task.click.assert_called_with(self.options[0], after_sleep=0.2)


class TestProjectChoiceMemory(unittest.TestCase):
    def test_joint_fingerprints_keep_independent_progress(self):
        """Count and every row width distinguish interleaved menus."""
        memory = ChoiceMemory()

        def select(lengths):
            """Simulate another appearance of a menu."""
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
