"""Import-level smoke tests for the installed ok-script runtime and Nikki task registry.

These tests do not open the GUI or connect to a game process.
"""

import importlib
import unittest
from importlib.metadata import version


class TestProjectFramework(unittest.TestCase):
    def test_framework_release_and_gui_compatibility(self):
        from ok import ConfigOption, OK
        from ok.core.ui_config import resolve_ui_config
        from src.config import config

        self.assertEqual(version("ok-script"), "2.0.14")
        self.assertTrue(callable(OK))
        self.assertTrue(callable(ConfigOption))
        gui = resolve_ui_config(config)
        self.assertIsNotNone(gui)
        self.assertEqual(gui["type"], "qt")
        self.assertEqual(gui["window_size"]["width"], 1200)

    def test_runtime_qt_available(self):
        """Check the Qt GUI can be imported without displaying or launching it."""
        from ok.ui.qt.MainWindow import MainWindow

        self.assertTrue(callable(MainWindow))

    def test_registered_tasks_import(self):
        """Catch missing/renamed framework imports used by Nikki's business tasks."""
        from src.config import config

        for namespace in ("onetime_tasks", "trigger_tasks", "custom_tabs"):
            for module_name, symbol in config.get(namespace, ()):
                with self.subTest(namespace=namespace, target=f"{module_name}:{symbol}"):
                    module = importlib.import_module(module_name)
                    self.assertTrue(hasattr(module, symbol), f"Missing {module_name}:{symbol}")
