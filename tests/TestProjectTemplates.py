"""Replay 16:9 Nikki choice screenshots with the installed template matcher."""

import unittest
from pathlib import Path
from unittest.mock import Mock

import cv2
from ok import Box
from ok.feature.FeatureSet import FeatureSet

from scripts.verify_templates import validate
from src.config import config
from src.tasks.AutoSkipDialogTask import AutoSkipDialogTask
from src.tasks.dialogue_choices import ChoiceMemory, text_band_lengths


class FrameTask(AutoSkipDialogTask):
    @property
    def frame(self):
        return self.test_frame


ROOT = Path(__file__).resolve().parents[1]
CHOICE_SCREENSHOT = "screenshot_20261030_001845.png"


class TestProjectTemplates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = cv2.imread(str(ROOT / "ok_templates" / CHOICE_SCREENSHOT))
        if cls.frame is None:
            raise AssertionError(f"Missing 16:9 choice fixture: {CHOICE_SCREENSHOT}")
        assert cls.frame.shape[:2] == (1080, 1920)

    def make_matcher(self):
        settings = config["template_matching"]
        return FeatureSet(
            False, str(ROOT / settings["coco_feature_json"]),
            settings["default_horizontal_variance"], settings["default_vertical_variance"],
            settings["default_threshold"],
        )

    def make_task(self, frame, matcher):
        task = FrameTask.__new__(FrameTask)
        task.test_frame = frame
        task._choice_memory = ChoiceMemory()
        task._choice_attempt = None
        task.find_one = lambda name, **kwargs: next(iter(matcher.find_one_feature(
            kwargs.pop("frame", frame), name, limit=1, **kwargs
        )), None)
        task.find_feature = lambda name, **kwargs: matcher.find_one_feature(
            kwargs.pop("frame", frame), name, **kwargs
        )
        task.send_key = Mock(return_value=True)
        task.next_frame = Mock(return_value=frame)
        task.screenshot = Mock()
        task.log_warning = Mock()
        task.click = Mock()
        return task

    def test_published_templates_equal_source(self):
        validate(ROOT)

    def test_choice_icons_match_at_native_size(self):
        matcher = self.make_matcher()
        for name in ("dialog_icon", "chat_icon", "skip_choose"):
            with self.subTest(feature=name):
                self.assertTrue(matcher.find_one_feature(self.frame, name, threshold=0.9, limit=1))

    def test_task_uses_f_instead_of_click_on_first_option(self):
        matcher = self.make_matcher()
        task = self.make_task(self.frame, matcher)
        self.assertIs(task.run(), False)
        task.send_key.assert_called_once_with("f", down_time=0.08, after_sleep=0.12)
        task.click.assert_not_called()
        self.assertEqual(task._choice_attempt.phase, "confirm")
        self.assertFalse(task._choice_memory.records)
        # A still-visible menu must not cause a second F or premature commit.
        self.assertIs(task.run(), False)
        self.assertEqual(task.send_key.call_count, 1)
        self.assertFalse(task._choice_memory.records)

    def test_without_dialogue_icon_no_input(self):
        frame = self.frame.copy()
        frame[:180, :200] = 0
        matcher = self.make_matcher()
        task = self.make_task(frame, matcher)
        self.assertIs(task.run(), False)
        task.send_key.assert_not_called()
        task.click.assert_not_called()

    def test_four_chat_rows_are_found_and_measurable(self):
        matcher = self.make_matcher()
        icons = sorted(matcher.find_one_feature(
            self.frame, "chat_icon", threshold=0.9, box=Box(960, 270, 921, 648)
        ), key=lambda box: box.y)
        self.assertEqual(len(icons), 4)
        lengths = text_band_lengths(self.frame, icons)
        self.assertIsNotNone(lengths)
        self.assertEqual(len(lengths), 4)
        self.assertTrue(all(value > 0 for value in lengths))
