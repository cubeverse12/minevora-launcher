"""Offline contract tests for the experimental 18.3.9 PLAY UI."""
import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_play_18_3_9 import LABEL_NEW, LABEL_OLD, OBJECT_NAME, PlayBuildError, patch_dashboard


def dummy_dashboard(label=LABEL_OLD):
    return (
        "self.version_button=action('Wersja',launcher.instances,False)\n"
        "self.loader_button=action('Loader',launcher.install_mod_loader,False)\n"
        + label + "\n"
        + OBJECT_NAME + "\n"
    )


class TestPlayButtonContract(unittest.TestCase):
    def test_keeps_actual_launcher_play_callback(self):
        updated = patch_dashboard(dummy_dashboard())
        ast.parse(updated)
        self.assertIn(LABEL_NEW, updated)
        self.assertIn("launcher.play,True", updated)
        self.assertIn("self.version_button=action(", updated)
        self.assertIn("self.loader_button=action(", updated)
        self.assertIn("setAccessibleName", updated)
        self.assertIn("setAutoRepeat(False)", updated)
        self.assertNotIn(LABEL_OLD, updated)

    def test_refuses_an_unsupported_dashboard(self):
        with self.assertRaises(PlayBuildError):
            patch_dashboard(dummy_dashboard("self.hero_play=action('Demo',lambda:None,True)"))

    def test_refuses_duplicate_patch(self):
        with self.assertRaises(PlayBuildError):
            patch_dashboard(patch_dashboard(dummy_dashboard()))


if __name__ == "__main__":
    unittest.main()
