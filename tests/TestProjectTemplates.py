"""Replay 16:9 Nikki choice screenshots with the installed template matcher."""

import unittest
import json
from pathlib import Path
from unittest.mock import Mock

import cv2
import numpy as np
from ok import Box
from ok.feature.FeatureSet import FeatureSet

from scripts.verify_templates import validate
from src.config import config
from src.tasks.AutoSkipDialogTask import AutoSkipDialogTask
from src.tasks.dialogue_choices import (
    ChoiceMemory, dimmed_text_rows, highlighted_choice_index, text_band_lengths,
)


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

    def test_gray_visited_text_keeps_measurable_fingerprint(self):
        """Dim the first real label: only that choice should become visited."""
        matcher = self.make_matcher()
        icons = sorted(matcher.find_one_feature(
            self.frame, "chat_icon", threshold=0.9, box=Box(960, 270, 921, 648),
        ), key=lambda box: box.y)
        self.assertEqual(len(icons), 4)
        self.assertEqual(dimmed_text_rows(self.frame, icons), (False,) * 4)
        self.assertEqual(highlighted_choice_index(self.frame, icons), 0)
        before = text_band_lengths(self.frame, icons)
        changed = self.frame.copy()
        first = icons[0]
        left = round(first.x + first.width + first.height * 0.12)
        top = round(first.y - first.height * 0.2)
        band = changed[top:top + round(first.height * 1.4), left:left + first.height * 7]
        hsv = cv2.cvtColor(band, cv2.COLOR_BGR2HSV)
        bright = (hsv[:, :, 1] < 85) & (hsv[:, :, 2] > 170)
        band[bright] = np.clip(band[bright].astype(np.float32) * 0.68, 0, 255).astype(np.uint8)
        self.assertEqual(dimmed_text_rows(changed, icons), (True, False, False, False))
        after = text_band_lengths(changed, icons)
        self.assertIsNotNone(after)
        for old, new in zip(before, after):
            self.assertAlmostEqual(old, new, delta=0.3)
        self.assertEqual(highlighted_choice_index(changed, icons), 0)

    def test_existing_skip_f_template_ranks_focused_row(self):
        """Test the actual published skip_f pixels against each option's left-hand F."""
        metadata = json.loads((ROOT / "assets" / "coco_annotations.json").read_text("utf-8"))
        category = next(cat["id"] for cat in metadata["categories"] if cat["name"] == "skip_f")
        annotation = next(a for a in metadata["annotations"] if a["category_id"] == category)
        image = next(i for i in metadata["images"] if i["id"] == annotation["image_id"])
        source = cv2.imread(str(ROOT / "assets" / image["file_name"]))
        self.assertIsNotNone(source)
        x, y, w, h = annotation["bbox"]
        template = source[y:y + h, x:x + w]

        matcher = self.make_matcher()
        icons = sorted(matcher.find_one_feature(
            self.frame, "chat_icon", threshold=0.9, box=Box(960, 270, 921, 648)
        ), key=lambda box: box.y)
        self.assertEqual(len(icons), 4)
        scores = []
        for icon in icons:
            unit = icon.height
            x0 = max(0, round(icon.x - unit * 6.1))
            x1 = min(self.frame.shape[1], round(icon.x - unit * 2.3))
            y0 = max(0, round(icon.y - unit * 0.65))
            y1 = min(self.frame.shape[0], round(icon.y + unit * 1.6))
            correlation = cv2.matchTemplate(
                self.frame[y0:y1, x0:x1], template, cv2.TM_CCOEFF_NORMED
            )
            scores.append(float(correlation.max()))
        print("Actual runtime skip_f template, per-row confidence:", scores, flush=True)
        # The existing bottom-right skip_f crop only reaches ~0.64 on this
        # option keycap, so it is unsuitable for the normal 0.9 threshold.
        # Retain the comparison but do not confuse it with a passing match.
        self.assertGreater(scores[0], max(scores[1:]))
