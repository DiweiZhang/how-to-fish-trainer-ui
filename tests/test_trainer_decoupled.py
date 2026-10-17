"""Tests for decoupled trainer engine, callbacks, and background execution."""

import unittest
from unittest.mock import MagicMock, patch
import time

from howtofish_cheat.trainer import HowToFishTrainer
from howtofish_cheat.features import CheatFeature, LockHealthCheat


class TestTrainerDecoupled(unittest.TestCase):
    """Test callback subscriptions and headless/background execution."""

    @patch("howtofish_cheat.trainer.keyboard")
    def test_status_callbacks(self, mock_keyboard):
        trainer = HowToFishTrainer(language="zh")
        received = []

        def on_status(msg):
            received.append(msg)

        trainer.add_status_callback(on_status)
        trainer.set_status("Test Message 1")
        trainer.set_status("Test Message 2")

        self.assertEqual(received, ["Test Message 1", "Test Message 2"])

        # Test remove callback
        trainer.remove_status_callback(on_status)
        trainer.set_status("Test Message 3")
        self.assertEqual(len(received), 2)

    @patch("howtofish_cheat.trainer.keyboard")
    def test_language_callbacks(self, mock_keyboard):
        trainer = HowToFishTrainer(language="zh")
        lang_history = []

        trainer.add_language_callback(lambda lang: lang_history.append(lang))
        trainer.toggle_language()
        self.assertEqual(trainer.language, "en")
        self.assertEqual(lang_history, ["en"])

        trainer.set_language("zh")
        self.assertEqual(trainer.language, "zh")
        self.assertEqual(lang_history, ["en", "zh"])

    @patch("howtofish_cheat.trainer.keyboard")
    def test_attach_callbacks(self, mock_keyboard):
        trainer = HowToFishTrainer(language="zh")
        attach_events = []

        trainer.add_attach_callback(lambda attached, pid, domain: attach_events.append((attached, pid, domain)))
        trainer._notify_attach(True, 1234, 0x1000)
        trainer._notify_attach(False, 0, 0)

        self.assertEqual(attach_events, [(True, 1234, 0x1000), (False, 0, 0)])

    @patch("howtofish_cheat.trainer.keyboard")
    def test_feature_callbacks_and_lookup(self, mock_keyboard):
        trainer = HowToFishTrainer(language="zh")
        feature_events = []

        trainer.add_feature_callback(lambda f: feature_events.append(f.hotkey))

        # Look up feature by hotkey
        f1 = trainer.get_feature("F1")
        self.assertIsNotNone(f1)
        self.assertEqual(f1.hotkey, "F1")

        # Fake PM and Mono to test feature enabling
        trainer.pm = MagicMock()
        trainer.mono = MagicMock()

        # Mock feature enable/disable
        f1.enable = MagicMock(side_effect=lambda: setattr(f1, "is_enabled", True))
        f1.disable = MagicMock(side_effect=lambda: setattr(f1, "is_enabled", False))

        trainer.set_feature_enabled("F1", True)
        self.assertTrue(f1.is_enabled)
        self.assertIn("F1", feature_events)

        trainer.set_feature_enabled("F1", False)
        self.assertFalse(f1.is_enabled)

    @patch("howtofish_cheat.trainer.keyboard")
    def test_background_thread_start_and_stop(self, mock_keyboard):
        trainer = HowToFishTrainer(language="zh")

        # Mock poll_step so it doesn't actually try to attach
        trainer.poll_step = MagicMock()

        bg_thread = trainer.start_background(poll_interval=0.02)
        self.assertTrue(trainer.is_running)
        self.assertTrue(bg_thread.is_alive())

        # Allow loop to execute a few ticks
        time.sleep(0.06)
        self.assertTrue(trainer.poll_step.call_count >= 1)

        trainer.stop()
        trainer.join(timeout=1.0)
        self.assertFalse(trainer.is_running)
        self.assertFalse(bg_thread.is_alive())

    @patch("howtofish_cheat.trainer.keyboard")
    def test_f10_safety_debounce(self, mock_keyboard):
        trainer = HowToFishTrainer(language="zh")
        trainer.stop = MagicMock()

        # First press: should NOT stop, but warn
        trainer._handle_f10_press()
        trainer.stop.assert_not_called()
        self.assertIn("防误触", trainer.status_message)

        # Immediate second press: should stop
        trainer._handle_f10_press()
        trainer.stop.assert_called_once()

    @patch("howtofish_cheat.trainer.keyboard")
    def test_state_deduplication(self, mock_keyboard):
        trainer = HowToFishTrainer(language="zh")
        status_calls = []
        attach_calls = []

        trainer.add_status_callback(lambda msg: status_calls.append(msg))
        trainer.add_attach_callback(lambda att, pid, dom: attach_calls.append((att, pid, dom)))

        # Calling set_status with same message should only trigger once
        trainer.set_status("Same Status")
        trainer.set_status("Same Status")
        trainer.set_status("Same Status")
        self.assertEqual(len(status_calls), 1)

        # Calling _notify_attach with same state should only trigger once
        trainer._notify_attach(False, 0, 0)
        trainer._notify_attach(False, 0, 0)
        trainer._notify_attach(False, 0, 0)
        self.assertEqual(len(attach_calls), 1)

    def test_is_admin_check(self):
        res = HowToFishTrainer.is_admin()
        self.assertIsInstance(res, bool)


if __name__ == "__main__":
    unittest.main()
