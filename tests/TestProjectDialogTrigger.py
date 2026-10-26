"""No-game, per-tick regressions for Nikki's dialogue skip trigger task."""

import unittest
from unittest.mock import Mock

from ok import TriggerTask

from src.config import config
from src.data.FeatureList import FeatureList as Feature
from src.tasks.AutoSkipDialogTask import AutoSkipDialogTask


class TestProjectDialogTrigger(unittest.TestCase):
    def setUp(self):
        """Create an isolated task with mocked game input and controlled detections."""
        # Test the decision tree without a live game or initializing the executor.
        self.task = AutoSkipDialogTask.__new__(AutoSkipDialogTask)
        self.task._scroll_on_next_choice = True
        self.task.send_key = Mock()
        self.task.scroll_relative = Mock()
        self.found = set()

        def find_one(feature, *, threshold):
            """Return selected fixtures while enforcing the production threshold."""
            self.assertEqual(threshold, 0.9)
            return object() if feature in self.found else None

        self.task.find_one = Mock(side_effect=find_one)

    def test_registry_and_trigger_inheritance(self):
        """Keep dialogue skipping registered exclusively as a trigger task."""
        entry = ["src.tasks.AutoSkipDialogTask", "AutoSkipDialogTask"]
        self.assertTrue(issubclass(AutoSkipDialogTask, TriggerTask))
        self.assertIn(entry, config["trigger_tasks"])
        self.assertNotIn(entry, config["onetime_tasks"])
        self.assertEqual(AutoSkipDialogTask.__init__.__code__.co_name, "__init__")

    def test_idle_cycle_does_nothing(self):
        """An empty frame must never produce input or scrolling."""
        self.assertIs(self.task.run(), False)
        self.task.send_key.assert_not_called()
        self.task.scroll_relative.assert_not_called()

    def test_dialogue_skip_has_priority_and_only_one_keypress(self):
        """Ordinary continuation takes priority over all other visible hints."""
        self.found = {Feature.dialog_icon, Feature.skip_f, Feature.skip_choose,
                      Feature.skip_b, Feature.task_icon}
        self.assertIs(self.task.run(), False)
        self.task.send_key.assert_called_once_with("f", after_sleep=0.1)
        self.task.scroll_relative.assert_not_called()

    def test_dialogue_skip_icon_requires_dialogue(self):
        """Standalone continuation or choice hints must not send input."""
        self.found = {Feature.skip_f, Feature.skip_choose}
        self.assertIs(self.task.run(), False)
        self.task.send_key.assert_not_called()

    def test_choice_alternates_scrolling_then_resets_after_disappearing(self):
        """Continuous choices alternate scrolling and reset when choices disappear."""
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.assertIs(self.task.run(), False)
        self.assertIs(self.task.run(), False)
        self.assertEqual(self.task.scroll_relative.call_count, 1)
        self.assertEqual(self.task.send_key.call_count, 2)
        self.task.send_key.assert_any_call("f", after_sleep=0.2)

        self.found = set()
        self.assertIs(self.task.run(), False)
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.assertIs(self.task.run(), False)
        self.assertEqual(self.task.scroll_relative.call_count, 2)

    def test_fallback_icons_work_without_dialogue(self):
        """Preserve independent B and task-marker fallback behavior."""
        self.found = {Feature.skip_b, Feature.task_icon}
        self.assertIs(self.task.run(), False)
        self.task.send_key.assert_called_once_with("f", after_sleep=0.1)

        self.task.send_key.reset_mock()
        self.found = {Feature.task_icon}
        self.assertIs(self.task.run(), False)
        self.task.send_key.assert_called_once_with("f", after_sleep=0.1)
