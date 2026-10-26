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
