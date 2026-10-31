"""Regression tests for menu re-entry and fresh F-confirmation captures."""

import unittest
from unittest.mock import Mock

from src.tasks.AutoSkipDialogTask import AutoSkipDialogTask, ChoiceAttempt
from src.tasks.dialogue_choices import ChoiceMemory


class FrameTask(AutoSkipDialogTask):
    @property
    def frame(self):
        return self.test_frame


class TestProjectDialogRecovery(unittest.TestCase):
    def setUp(self):
        self.task = FrameTask.__new__(FrameTask)
        self.task.test_frame = object()
        self.task._choice_memory = ChoiceMemory()
        self.task._choice_attempt = None
        self.lengths = (3.0, 5.0)
        self.positions = (0.4, 0.5)
        self.task._menu_visible = Mock(return_value=True)
        self.task._menu_state = Mock(return_value=(
            self.lengths, (False, False), 0, self.positions,
        ))
        self.task.next_frame = Mock(side_effect=lambda: object())
        self.task.send_key = Mock(return_value=True)
        self.task.screenshot = Mock()
        self.task.log_warning = Mock()
        self.task.log_info = Mock()

    def hide_blocked_menu(self):
        self.task._menu_visible.return_value = False
        for _ in range(self.task.ABSENT_FRAMES):
            self.task._run_cycle()
        self.assertIsNone(self.task._choice_attempt)
        self.task._menu_visible.return_value = True

    def test_navigation_memory_survives_hide_without_committing_choice(self):
        memory = self.task._choice_memory
        decision = memory.prepare(self.lengths)
        memory.mark_navigated(decision)
        memory.hide()
        retry = memory.prepare((3.1, 5.1))
        self.assertTrue(memory.has_navigated(retry.lengths))
        self.assertEqual(retry.index, 0)
        self.assertFalse(memory.records)
        self.assertFalse(memory.has_navigated((8.0, 12.0)))
        self.assertFalse(memory.has_navigated((3.0, 5.0, 7.0)))

    def test_failed_navigation_cannot_restore_first_row_assumption(self):
        self.task._menu_state.return_value = (
            self.lengths, (True, False), 0, self.positions,
        )
        self.task.send_key.return_value = False
        self.task._run_cycle()
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.hide_blocked_menu()
        self.task.send_key.reset_mock()
        self.task._menu_state.return_value = (
            self.lengths, (True, False), None, self.positions,
        )
        self.task._run_cycle()
        self.task.send_key.assert_not_called()
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.assertFalse(self.task._choice_memory.records)

    def test_missing_post_input_capture_still_remembers_navigation(self):
        self.task._menu_state.return_value = (
            self.lengths, (True, False), 0, self.positions,
        )
        self.task.next_frame.side_effect = None
        self.task.next_frame.return_value = None
        self.task._run_cycle()
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.assertTrue(self.task._choice_memory.has_navigated(self.lengths))
        self.assertFalse(self.task._choice_memory.records)

    def test_known_focus_is_allowed_after_previous_navigation(self):
        self.task._choice_memory.mark_navigated(
            self.task._choice_memory.prepare(self.lengths))
        self.task._menu_state.return_value = (
            self.lengths, (True, False), 1, self.positions,
        )
        self.task._run_cycle()
        self.task.send_key.assert_called_once_with("f", down_time=0.08, after_sleep=0.12)

    def test_new_menu_keeps_initial_first_row_assumption(self):
        memory = self.task._choice_memory
        memory.mark_navigated(memory.prepare(self.lengths))
        self.task._menu_state.return_value = (
            (8.0, 12.0), (False, False), None, self.positions,
        )
        self.task._run_cycle()
        self.task.send_key.assert_called_once_with("f", down_time=0.08, after_sleep=0.12)

    def test_cached_absence_cannot_hide_a_reappearing_menu(self):
        decision = self.task._choice_memory.prepare(self.lengths)
        self.task._choice_attempt = ChoiceAttempt(decision, phase="confirm", absent_frames=1)
        fresh = object()
        self.task.next_frame.side_effect = None
        self.task.next_frame.return_value = fresh
        self.task._menu_visible.side_effect = lambda frame: frame is fresh
        self.task._run_choice(self.task.test_frame)
        self.task.next_frame.assert_called_once_with()
        self.assertIsNotNone(self.task._choice_attempt)
        self.assertEqual(self.task._choice_attempt.absent_frames, 0)
        self.assertFalse(self.task._choice_memory.records)
        self.task.send_key.assert_not_called()

    def test_confirmation_requires_two_new_captures(self):
        decision = self.task._choice_memory.prepare(self.lengths)
        self.task._choice_attempt = ChoiceAttempt(decision, phase="confirm")
        self.task._menu_visible.return_value = False
        self.task.next_frame.side_effect = [object(), object()]
        self.task._run_choice(self.task.test_frame)
        self.assertFalse(self.task._choice_memory.records)
        self.task._run_choice(self.task.test_frame)
        self.assertEqual(self.task.next_frame.call_count, 2)
        self.assertIsNone(self.task._choice_attempt)
        self.assertEqual(self.task._choice_memory.records[0].next_index, 1)
        self.task.send_key.assert_not_called()

    def test_missing_confirmation_capture_never_counts_as_absence(self):
        decision = self.task._choice_memory.prepare(self.lengths)
        self.task._choice_attempt = ChoiceAttempt(decision, phase="confirm", absent_frames=1)
        self.task._menu_visible.return_value = False
        self.task.next_frame.side_effect = None
        self.task.next_frame.return_value = None
        self.task._run_choice(self.task.test_frame)
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.assertFalse(self.task._choice_memory.records)
        self.task.send_key.assert_not_called()

    def test_f_directly_opens_next_menu_without_waiting_for_absence(self):
        initial = (self.lengths, (True, False), 1, self.positions)
        replacement = ((7.0,), (False,), 0, (0.6,))
        self.task._menu_state.side_effect = [initial, initial, replacement, replacement]
        self.task._run_cycle()
        self.assertFalse(self.task._choice_memory.records)
        self.assertEqual(self.task.send_key.call_count, 1)
        self.task._run_cycle()
        self.assertIsNone(self.task._choice_attempt)
        self.assertEqual(self.task.next_frame.call_count, 2)
        self.assertEqual(self.task.send_key.call_count, 1)
        self.assertEqual(self.task._choice_memory.records[0].lengths, self.lengths)
        self.assertEqual(self.task._choice_memory.records[0].next_index, 0)

        self.task._menu_state.side_effect = None
        self.task._menu_state.return_value = replacement
        self.task._run_cycle()
        self.assertEqual(self.task.send_key.call_count, 2)
        self.assertEqual(self.task._choice_attempt.decision.lengths, (7.0,))

    def test_selected_bright_row_becomes_dim_in_two_new_captures(self):
        initial = (self.lengths, (True, False), 1, self.positions)
        completed = (self.lengths, (True, True), 0, self.positions)
        self.task._menu_state.side_effect = [initial, initial, completed, completed]
        self.task._run_cycle()
        self.assertFalse(self.task._choice_memory.records)
        self.task._run_cycle()
        self.assertIsNone(self.task._choice_attempt)
        self.assertEqual(self.task._choice_memory.records[0].next_index, 0)
        self.assertEqual(self.task.next_frame.call_count, 2)
        self.task.send_key.assert_called_once_with("f", down_time=0.08, after_sleep=0.12)

    def test_transient_or_unreadable_replacement_does_not_commit(self):
        self.task._run_cycle()
        unchanged = (self.lengths, (False, False), 0, self.positions)
        replacement = ((7.0,), (False,), 0, (0.6,))
        for state in (replacement, unchanged, replacement, None, replacement):
            self.task._menu_state.return_value = state
            self.task._run_cycle()
            self.assertFalse(self.task._choice_memory.records)
        self.task._run_cycle()
        self.assertIsNone(self.task._choice_attempt)
        self.assertEqual(len(self.task._choice_memory.records), 1)
        self.assertEqual(self.task.send_key.call_count, 1)

    def test_different_visible_completion_evidence_is_not_combined(self):
        self.task._run_cycle()
        for state in (
            ((7.0,), (False,), 0, (0.6,)),
            ((7.0,), (False,), 0, (0.7,)),
            (self.lengths, (True, False), 1, self.positions),
        ):
            self.task._menu_state.return_value = state
            self.task._run_cycle()
            self.assertFalse(self.task._choice_memory.records)
        self.task._run_cycle()
        self.assertIsNone(self.task._choice_attempt)
        self.assertEqual(len(self.task._choice_memory.records), 1)
        self.assertEqual(self.task.send_key.call_count, 1)

    def test_absence_and_visible_replacement_need_separate_confirmation(self):
        self.task._run_cycle()
        self.task._menu_state.return_value = ((7.0,), (False,), 0, (0.6,))
        for visible in (False, True, False, True):
            self.task._menu_visible.return_value = visible
            self.task._run_cycle()
            self.assertFalse(self.task._choice_memory.records)
        self.task._run_cycle()
        self.assertIsNone(self.task._choice_attempt)
        self.assertEqual(len(self.task._choice_memory.records), 1)
        self.assertEqual(self.task.send_key.call_count, 1)

    def test_missing_capture_after_replacement_does_not_commit(self):
        self.task._run_cycle()
        self.task._menu_state.return_value = ((7.0,), (False,), 0, (0.6,))
        self.task._run_cycle()
        self.task.next_frame.side_effect = None
        self.task.next_frame.return_value = None
        self.task._run_cycle()
        self.assertEqual(self.task._choice_attempt.phase, "blocked")
        self.assertFalse(self.task._choice_memory.records)
        self.assertEqual(self.task.send_key.call_count, 1)
