"""Source-level smoke tests for the non-invasive Start redesign."""
import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_start_18_3_10 import StartBuildError, patch_start


def sample():
    return """class Dashboard:
    def __init__(self, launcher, action, hero, hero_layout):
        hero.setMaximumHeight(670)
        hero_layout.setContentsMargins(32,16,32,25)
        release=title('MINEVORA  •  LAUNCHER 18.3.7',12,True)
        self.version_button=action('Wersja',launcher.instances,False)
        self.loader_button=action('Loader',launcher.install_mod_loader,False)
        choices=QHBoxLayout()
        for b in (self.version_button,self.loader_button):
            b.setObjectName('heroSelect')
            b.setMinimumHeight(73)
        self.hero_play=action('▶  PLAY\\nMinecraft Java',launcher.play,True)
        self.hero_play.setObjectName('heroPlay')
        self.hero_play.setMinimumHeight(84)
        hero_layout.addWidget(self.hero_play)
"""


class StartGlowTests(unittest.TestCase):
    def test_layout_and_play_callback(self):
        baseline = sample()
        patched = patch_start(baseline)
        ast.parse(patched)
        self.assertEqual(baseline.count("launcher.play"), patched.count("launcher.play"))
        self.assertIn("launcher.play,True", patched)
        self.assertIn("launcher.instances", patched)
        self.assertIn("launcher.install_mod_loader", patched)
        self.assertIn("self.hero_play.setMinimumHeight(104)", patched)
        self.assertIn("self._play_pulse.start()", patched)
        self.assertIn("self.version_button", patched)
        self.assertIn("self.loader_button", patched)
        self.assertIn("MINEVORA  •  LAUNCHER 18.3.10", patched)

    def test_rejects_unknown_source(self):
        with self.assertRaises(StartBuildError):
            patch_start(sample().replace("launcher.play,True", "lambda:None,True"))

    def test_never_double_patches(self):
        with self.assertRaises(StartBuildError):
            patch_start(patch_start(sample()))


if __name__ == "__main__":
    unittest.main()
