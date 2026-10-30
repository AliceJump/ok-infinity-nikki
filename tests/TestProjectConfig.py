"""Lightweight repository migration checks (do not launch the game)."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestProjectConfig(unittest.TestCase):
    def test_entrypoints_and_assets_exist(self):
        for path in (
            "main.py",
            "main_debug.py",
            "src/config.py",
            "assets/coco_detection.json",
            "pyappify.yml",
        ):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())

    def test_project_configuration(self):
        from src.config import config

        self.assertIn("X6Game-Win64-Shipping.exe", config["windows"]["exe"])
        self.assertEqual(config["gui_title"], "ok-in")
        self.assertTrue(config["onetime_tasks"])

    def test_supported_resolution_ratio_and_priority(self):
        from src.config import config

        resolution = config["supported_resolution"]
        expected = [
            (3840, 2160),
            (2560, 1440),
            (1920, 1080),
            (1600, 900),
            (1366, 768),
            (1280, 720),
        ]
        self.assertEqual(resolution["ratio"], "16:9")
        self.assertEqual(resolution["min_size"], (1280, 720))
        self.assertEqual(resolution["resize_to"], expected)

        numerator, denominator = map(int, resolution["ratio"].split(":"))
        target_ratio = numerator / denominator
        previous_width = float("inf")
        for width, height in resolution["resize_to"]:
            with self.subTest(width=width, height=height):
                self.assertLess(width, previous_width)
                self.assertGreaterEqual(width, resolution["min_size"][0])
                self.assertGreaterEqual(height, resolution["min_size"][1])
                self.assertEqual(height % 2, 0)
                self.assertLessEqual(abs(width / height - target_ratio), 0.01 * target_ratio)
                previous_width = width
