"""Offline tests for dimmed visited rows and screenshot-verified W/S/F input."""

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
        """Simulate menus and keyboard focus; do not send Windows input."""
        self.task = FrameTask.__new__(FrameTask)
        self.task.test_frame = np.zeros((240, 339, 3), dtype=np.uint8)
        self.task._choice_memory = ChoiceMemory()
        self.task._choice_attempt = None
        self.found = set()
        self.options = [Box(220, 130 + i * 15, 6, 4) for i in range(4)]
        self.lengths = (3.0, 4.0, 5.0, 6.0)
        self.dimmed = (False,) * 4
        self.focus = 0
        self.deliver_keys = True
        self.send_result = True
        self.task.find_one = Mock(side_effect=lambda name, **kwargs: name in self.found)
        self.task.find_feature = Mock(return_value=self.options)
        self.task.next_frame = Mock(side_effect=lambda: self.task.test_frame)
        self.task.screenshot = Mock()
        self.task.log_warning = Mock()
        self.task.click = Mock()

        def key_press(key, **kwargs):
            if self.deliver_keys:
                self.focus += (1 if key == "s" else -1 if key == "w" else 0)
            return self.send_result

        self.task.send_key = Mock(side_effect=key_press)
        for name, callback in (
            ("text_band_lengths", lambda frame, icons: self.lengths),
            ("dimmed_text_rows", lambda frame, icons: self.dimmed),
            ("highlighted_choice_index", lambda frame, icons: self.focus),
        ):
            patcher = patch("src.tasks.AutoSkipDialogTask." + name, side_effect=callback)
            patcher.start()
            self.addCleanup(patcher.stop)

    def tick(self, count=1):
        """Advance a requested number of trigger ticks."""
        for _ in range(count):
            self.assertIs(self.task.run(), False)

    def menu_closed(self):
        """Commit a confirmed selection after two frames without W/S."""
        self.found = set()
        self.tick(2)
        self.focus = 0

    def test_registry(self):
        """Keep the task registered only as an opt-in trigger."""
        entry = ["src.tasks.AutoSkipDialogTask", "AutoSkipDialogTask"]
        self.assertTrue(issubclass(AutoSkipDialogTask, TriggerTask))
        self.assertIn(entry, config["trigger_tasks"])
        self.assertNotIn(entry, config["onetime_tasks"])

    def test_orphan_prompts_and_normal_continuation(self):
        """Ignore unrelated hints, but keep ordinary F continuation."""
        for found in (set(), {Feature.skip_f}, {Feature.skip_choose}):
            self.found = found
            self.tick()
        self.task.send_key.assert_not_called()
        self.found = {Feature.dialog_icon, Feature.skip_f}
        self.tick()
        self.task.send_key.assert_called_once_with("f", after_sleep=0.1)
        self.task.click.assert_not_called()

    def test_first_bright_option_f_and_commit(self):
        """Do not commit a selection before the menu actually disappears."""
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.tick()
        self.task.send_key.assert_called_once_with("f", down_time=0.08, after_sleep=0.12)
        self.assertFalse(self.task._choice_memory.records)
        self.tick()
        self.assertEqual(self.task.send_key.call_count, 1)
        self.menu_closed()
        self.assertEqual(self.task._choice_memory.records[0].next_index, 1)
        self.assertTrue(self.task.screenshot.called)
        self.task.click.assert_not_called()

    def test_visited_first_choice_skipped(self):
        """Gray visited rows are not candidates, even if memory starts at zero."""
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.dimmed = (True, False, False, False)
        self.tick(2)
        self.assertEqual([c.args[0] for c in self.task.send_key.call_args_list], ["s", "f"])
        self.assertEqual(self.task._choice_attempt.decision.index, 1)
        self.menu_closed()
        self.assertEqual(self.task._choice_memory.records[0].next_index, 2)

    def test_second_row_already_highlighted_sends_f(self):
        """Match the supplied night screenshot: row 1 dim and row 2 focused."""
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.dimmed = (True, False, False, False)
        self.focus = 1
        self.tick()
        self.task.send_key.assert_called_once_with("f", down_time=0.08, after_sleep=0.12)
        self.assertEqual(self.task._choice_attempt.decision.index, 1)

    def test_w_navigation_from_lower_focus(self):
        """Use W when the actual focus is below the next bright candidate."""
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.dimmed = (True, False, True, True)
        self.focus = 3
        self.tick(3)
        self.assertEqual([c.args[0] for c in self.task.send_key.call_args_list], ["w", "w", "f"])
        self.assertEqual(self.focus, 1)

    def test_four_rows_navigate_three_s_before_f(self):
        """Preserve menu fingerprint rotation among available choices."""
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        for index in range(3):
            self.tick(index + 1)
            self.menu_closed()
            self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.task.send_key.reset_mock()
        self.tick(4)
        self.assertEqual([c.args[0] for c in self.task.send_key.call_args_list], ["s", "s", "s", "f"])
        self.task.click.assert_not_called()

    def test_all_rows_dark_stops(self):
        """If everything has been selected, do not default to any row."""
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.dimmed = (True, True, True, True)
        self.tick(5)
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.task.send_key.assert_not_called()
        self.assertFalse(self.task._choice_memory.records)

    def test_missing_s_effect_blocks_before_f(self):
        """No observed keyboard focus movement means stop, not blind confirm."""
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.dimmed = (True, False, False, False)
        self.deliver_keys = False
        self.tick(4)
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.assertEqual([c.args[0] for c in self.task.send_key.call_args_list], ["s"])
        self.assertFalse(self.task._choice_memory.records)

    def test_unresponsive_w_chooses_the_still_bright_focused_row(self):
        """Reproduce user log: W unchanged, then use focused bright row, not lock."""
        from src.tasks.dialogue_choices import ChoiceRecord

        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.task._choice_memory.records.append(ChoiceRecord(self.lengths, next_index=0))
        self.focus = 1
        self.deliver_keys = False
        self.tick()
        self.assertEqual(self.task._choice_attempt.phase, "verify_move")
        self.tick(2)
        self.assertEqual(self.task._choice_attempt.phase, "navigate")
        self.assertEqual(self.task._choice_attempt.decision.index, 1)
        self.tick()
        self.assertEqual([c.args[0] for c in self.task.send_key.call_args_list], ["w", "f"])
        self.assertFalse(self.task._choice_memory.active)
        self.menu_closed()
        self.assertEqual(self.task._choice_memory.records[0].next_index, 2)

    def test_delayed_w_focus_update_is_accepted(self):
        """The first screenshot after key delivery can precede a rendered focus."""
        from src.tasks.dialogue_choices import ChoiceRecord

        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.task._choice_memory.records.append(ChoiceRecord(self.lengths, next_index=0))
        self.focus = 1
        self.deliver_keys = False
        self.tick()
        self.assertEqual(self.task._choice_attempt.phase, "verify_move")
        self.focus = 0
        self.tick()
        self.assertEqual(self.task._choice_attempt.phase, "navigate")
        self.tick()
        self.assertEqual([c.args[0] for c in self.task.send_key.call_args_list], ["w", "f"])
        self.assertEqual(self.task._choice_attempt.decision.index, 0)

    def test_missing_focus_never_blindly_confirms_after_s(self):
        """If focus cannot be observed, no bright fallback is safe."""
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.dimmed = (True, False, False, False)
        self.deliver_keys = False
        self.tick()
        self.focus = None
        self.tick(3)
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.assertEqual([c.args[0] for c in self.task.send_key.call_args_list], ["s"])

    def test_real_screenshots_focus_moves_despite_noisy_text_width(self):
        """W succeeds even when clothing glints corrupt all text-width bands.

        Reproduces screenshots at 01:51:51: F moves row 2 -> row 1.
        The old 5% width check wrongly reported that navigation failed.
        """
        from src.tasks.dialogue_choices import ChoiceRecord

        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.task._choice_memory.records.append(ChoiceRecord(self.lengths, next_index=0))
        self.focus = 1

        def render_key(key, **kwargs):
            if key == "w":
                self.focus = 0
                self.lengths = (13.3125, 8.875, 28.75, 7.5)
            return True

        self.task.send_key.side_effect = render_key
        self.tick()
        self.assertEqual(self.task._choice_attempt.phase, "navigate")
        self.assertEqual(self.focus, 0)
        self.tick()
        self.assertEqual([c.args[0] for c in self.task.send_key.call_args_list], ["w", "f"])
        self.assertEqual(self.task._choice_attempt.phase, "confirm")
        self.assertFalse(self.task.log_warning.called)

    def test_menu_row_positions_change_during_w_blocks_confirmation(self):
        """A different menu layout after W cannot be mistaken for this one."""
        from src.tasks.dialogue_choices import ChoiceRecord

        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.task._choice_memory.records.append(ChoiceRecord(self.lengths, next_index=0))
        self.focus = 1

        def replace_menu(key, **kwargs):
            if key == "w":
                self.focus = 0
                self.options[0].y += 20
            return True

        self.task.send_key.side_effect = replace_menu
        self.tick(3)
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.assertEqual([c.args[0] for c in self.task.send_key.call_args_list], ["w"])
        self.assertFalse(self.task._choice_memory.active)

    def test_f_still_visible_never_commits(self):
        """An unresponsive F key must not advance choice memory."""
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.tick(self.task.CONFIRM_CHECKS + 1)
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.assertEqual(self.task.send_key.call_count, 1)
        self.assertFalse(self.task._choice_memory.records)

    def test_unreadable_or_failed_input(self):
        """Unknown text and failed send return do not advance or retry."""
        self.found = {Feature.dialog_icon, Feature.skip_choose}
        self.lengths = None
        self.tick()
        self.task.send_key.assert_not_called()
        self.lengths = (3.0, 4.0, 5.0, 6.0)
        self.send_result = False
        self.tick(4)
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.assertEqual(self.task.send_key.call_count, 1)
        self.assertFalse(self.task._choice_memory.records)


class TestProjectChoiceMemory(unittest.TestCase):
    def test_joint_fingerprints_keep_independent_progress(self):
        """Interleaved choices retain separate approximate width fingerprints."""
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
