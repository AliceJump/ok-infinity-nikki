"""Replay real Nikki choice screenshots through the installed template matcher."""

import unittest
from pathlib import Path
from unittest.mock import Mock

import cv2
from ok import Box
from ok.feature.FeatureSet import FeatureSet

from scripts.verify_templates import validate
from src.config import config
from src.tasks.AutoSkipDialogTask import AutoSkipDialogTask

ROOT = Path(__file__).resolve().parents[1]


class EndFrame(Exception):
    """Stop the one-time task after a single iteration without sending real input."""


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
                for name in ("skip_f", "skip_b", "task_icon"):
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
                    task = AutoSkipDialogTask.__new__(AutoSkipDialogTask)
                    task._scroll_on_next_choice = True
                    task.find_one = lambda name, **kwargs: next(
                        iter(matcher.find_one_feature(frame, name, limit=1, **kwargs)), None
                    )
                    task.box_of_screen = lambda x, y, to_x, to_y: Box(
                        x * frame.shape[1], y * frame.shape[0],
                        (to_x - x) * frame.shape[1], (to_y - y) * frame.shape[0],
                    )
                    task.send_key = Mock()
                    task.scroll_relative = Mock()
                    task.sleep = Mock()
                    task.next_frame = Mock(side_effect=EndFrame)
                    try:
                        task.run()
                    except EndFrame:
                        pass
                    if has_dialogue:
                        task.send_key.assert_called_once_with("f", after_sleep=0.2)
                        task.scroll_relative.assert_called_once_with(0.5, 0.5, -1)
                    else:
                        task.send_key.assert_not_called()
                        task.scroll_relative.assert_not_called()
