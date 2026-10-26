"""Replay real Nikki choice screenshots through the installed template matcher."""

import unittest
from pathlib import Path
from unittest.mock import Mock

import cv2
from ok.feature.FeatureSet import FeatureSet

from scripts.verify_templates import validate
from src.config import config
from src.tasks.AutoSkipDialogTask import AutoSkipDialogTask
from src.tasks.dialogue_choices import ChoiceMemory, text_band_lengths


class FrameTask(AutoSkipDialogTask):
    @property
    def frame(self):
        """Return a fixture without creating a game executor."""
        return self.test_frame


ROOT = Path(__file__).resolve().parents[1]


class TestProjectTemplates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Decode both source screenshots once for the resolution matrix."""
        cls.frames = {}
        for suffix in ("184802", "184825"):
            path = ROOT / "ok_templates" / f"screenshot_20261026_{suffix}.png"
            frame = cv2.imread(str(path))
            if frame is None:
                raise AssertionError(f"Missing source screenshot: {path}")
            cls.frames[suffix] = frame

    def make_matcher(self):
        """Use the exact matcher defaults configured for the application."""
        settings = config["template_matching"]
        return FeatureSet(
            False, str(ROOT / settings["coco_feature_json"]),
            settings["default_horizontal_variance"], settings["default_vertical_variance"],
            settings["default_threshold"],
        )

    def test_published_templates_equal_source(self):
        """Fail for stale publishing, invalid IDs, or altered source crops."""
        validate(ROOT)

    def test_choice_screenshots_at_supported_sizes(self):
        """Dialogue and chat-option icons must match at every configured size."""
        matcher = self.make_matcher()
        for size in config["supported_resolution"]["resize_to"]:
            for suffix, original in self.frames.items():
                frame = cv2.resize(original, size)
                for name in ("dialog_icon", "chat_icon"):
                    with self.subTest(size=size, screenshot=suffix, feature=name):
                        self.assertTrue(matcher.find_one_feature(frame, name, threshold=0.9, limit=1))
                for name in ("skip_f",):
                    with self.subTest(size=size, screenshot=suffix, absent_feature=name):
                        self.assertFalse(matcher.find_one_feature(frame, name, threshold=0.9, limit=1))

    def test_local_ws_annotation_at_native_size(self):
        """Preserve the user's W/S crop and validate it at its captured resolution."""
        matcher = self.make_matcher()
        for suffix, frame in self.frames.items():
            with self.subTest(screenshot=suffix):
                self.assertTrue(matcher.find_one_feature(frame, "skip_choose", threshold=0.9, limit=1))

    def test_task_recognizes_choices_and_requires_dialogue(self):
        """Replay a choice and a frame with its history icon removed, without game I/O."""
        for suffix, original in self.frames.items():
            for has_dialogue in (True, False):
                with self.subTest(screenshot=suffix, has_dialogue=has_dialogue):
                    frame = original.copy()
                    if not has_dialogue:
                        frame[:180, :200] = 0
                    matcher = self.make_matcher()
                    task = FrameTask.__new__(FrameTask)
                    task.test_frame = frame
                    task._choice_memory = ChoiceMemory()
                    task.find_one = lambda name, **kwargs: next(
                        iter(matcher.find_one_feature(kwargs.pop("frame", frame), name, limit=1, **kwargs)), None
                    )
                    task.find_feature = lambda name, **kwargs: matcher.find_one_feature(
                        kwargs.pop("frame", frame), name, **kwargs
                    )
                    task.send_key = Mock()
                    task.click = Mock(return_value=True)
                    self.assertIs(task.run(), False)
                    if has_dialogue:
                        task.click.assert_called_once()
                        self.assertAlmostEqual(task.click.call_args.args[0].x, 2285, delta=2)
                        self.assertEqual(len(task._choice_memory.records), 1)
                    else:
                        task.click.assert_not_called()
                    task.send_key.assert_not_called()

    def test_measured_band_is_background_and_scale_stable(self):
        """The same visible text yields a matching fingerprint at each size."""
        memory = ChoiceMemory()
        for size in config["supported_resolution"]["resize_to"]:
            for suffix, original in self.frames.items():
                with self.subTest(size=size, screenshot=suffix):
                    frame = cv2.resize(original, size)
                    matcher = self.make_matcher()
                    icons = matcher.find_one_feature(frame, "chat_icon", threshold=0.9, limit=1)
                    lengths = text_band_lengths(frame, icons)
                    self.assertIsNotNone(lengths)
                    self.assertEqual(len(lengths), 1)
                    memory.hide()
                    memory.commit(memory.prepare(lengths))
        self.assertEqual(len(memory.records), 1)

    def test_task_item_popup_is_ignored(self):
        """The user's new F prompt must not dismiss a task-item popup."""
        path = ROOT / "ok_templates" / "screenshot_20261026_200542.png"
        frame = cv2.imread(str(path))
        self.assertIsNotNone(frame)
        matcher = self.make_matcher()
        self.assertTrue(matcher.find_one_feature(frame, "skip_f", threshold=0.9, limit=1))
        task = FrameTask.__new__(FrameTask)
        task.test_frame = frame
        task._choice_memory = ChoiceMemory()
        task.find_one = lambda name, **kwargs: next(iter(matcher.find_one_feature(
            kwargs.pop("frame", frame), name, limit=1, **kwargs
        )), None)
        task.send_key = Mock()
        task.click = Mock()
        self.assertIs(task.run(), False)
        task.send_key.assert_not_called()
        task.click.assert_not_called()

    def test_two_chat_rows_are_detected_sorted_and_measured(self):
        """Replay a second chat row while excluding the original exit icon."""
        frame = self.frames["184825"].copy()
        # Reuse the real icon and text pixels at the next row, leaving the menu background intact.
        frame[1572:1636, 2270:2570] = frame[1460:1524, 2270:2570].copy()
        matcher = self.make_matcher()
        from ok import Box
        icons = sorted(matcher.find_one_feature(
            frame, "chat_icon", threshold=0.9, box=Box(1696, 600, 1628, 1440)
        ), key=lambda box: box.y)
        self.assertEqual(len(icons), 2)
        lengths = text_band_lengths(frame, icons)
        self.assertIsNotNone(lengths)
        self.assertAlmostEqual(lengths[0], lengths[1], delta=0.3)
