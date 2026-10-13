"""Unit tests for CustomTkinter GUI components and TrainerApp."""

import unittest
from unittest.mock import MagicMock, patch

import customtkinter as ctk
from howtofish_cheat.features import (
    LockHealthCheat,
    DamageMultiplierCheat,
    AddMoneyCheat,
    get_default_features,
)
from howtofish_cheat.trainer import HowToFishTrainer
from howtofish_cheat.ui.gui import (
    BooleanFeatureCard,
    DamageMultiplierCard,
    AddMoneyCard,
    TrainerApp,
)


class TestGUIComponents(unittest.TestCase):
    """Test GUI widgets and state updates."""

    @classmethod
    def setUpClass(cls):
        # Create a hidden dummy root if needed
        cls.root = ctk.CTk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_boolean_feature_card(self):
        feat = LockHealthCheat(hotkey="F1")
        card = BooleanFeatureCard(self.root, feature=feat, language="zh")

        # Test initial state
        self.assertFalse(card.switch_var.get())
        self.assertEqual(card.badge.cget("text"), "[F1]")

        # Test external state sync
        card.set_active(True)
        self.assertTrue(card.switch_var.get())

        card.set_active(False)
        self.assertFalse(card.switch_var.get())

        # Test language update
        card.update_language("en")
        self.assertEqual(card.title_lbl.cget("text"), "Lock Health")
        card.destroy()

    def test_damage_multiplier_card(self):
        feat = DamageMultiplierCheat(hotkey="F5")
        card = DamageMultiplierCard(self.root, feature=feat, language="zh")

        self.assertEqual(card.badge.cget("text"), "[F5]")
        # Test mode index sync
        card.set_mode_index(2)  # 5x
        self.assertEqual(card.seg_button.get(), "5x")

        # Test language update
        card.update_language("en")
        self.assertEqual(card.title_lbl.cget("text"), "Damage Multiplier")
        card.destroy()

    def test_add_money_card(self):
        feat = AddMoneyCheat(hotkey="F6")
        card = AddMoneyCard(self.root, feature=feat, language="zh")

        self.assertEqual(card.badge.cget("text"), "[F6]")
        card.update_total_added(50000)
        self.assertIn("50,000", card.total_lbl.cget("text"))

        card.update_language("en")
        self.assertEqual(card.title_lbl.cget("text"), "Add Money (+1w)")
        card.destroy()

    @patch("howtofish_cheat.trainer.keyboard")
    def test_trainer_app_lifecycle(self, mock_keyboard):
        trainer = HowToFishTrainer(language="zh")
        trainer.start_background = MagicMock()
        trainer.stop = MagicMock()
        trainer.join = MagicMock()

        app = TrainerApp(trainer)
        app.withdraw()

        # Check all 6 cards are mapped
        self.assertEqual(len(app.cards), 6)
        self.assertIn("F1", app.cards)
        self.assertIn("F5", app.cards)
        self.assertIn("F6", app.cards)

        # Test status update
        app._handle_status_update("Test Status")
        self.assertIn("Test Status", app.status_msg_lbl.cget("text"))

        # Test attachment update
        app._handle_attach_update(True, 1234, 0x1000)
        self.assertIn("1234", app.conn_text_lbl.cget("text"))

        # Test clean shutdown
        app.on_closing()
        trainer.stop.assert_called_once()
        trainer.join.assert_called_once()

    @patch("howtofish_cheat.trainer.keyboard")
    def test_unattached_gui_toggle_reverts(self, mock_keyboard):
        trainer = HowToFishTrainer(language="zh")
        trainer.start_background = MagicMock()
        trainer.pm = None  # Unattached

        app = TrainerApp(trainer)
        app.withdraw()

        f1_card = app.cards["F1"]
        # Simulate user clicking switch to ON when unattached
        app._on_gui_feature_toggle("F1", True)
        self.assertFalse(f1_card.switch_var.get())

        f5_card = app.cards["F5"]
        # Simulate user selecting 5x damage when unattached
        app._on_gui_damage_mode_change(2)
        self.assertEqual(f5_card.seg_button.get(), "1x 默认")

        app.on_closing()

    @patch("howtofish_cheat.trainer.keyboard")
    def test_disconnection_resets_ui_cards(self, mock_keyboard):
        trainer = HowToFishTrainer(language="zh")
        trainer.start_background = MagicMock()

        app = TrainerApp(trainer)
        app.withdraw()

        f1_card = app.cards["F1"]
        f1_card.set_active(True)
        self.assertTrue(f1_card.switch_var.get())

        f5_card = app.cards["F5"]
        f5_card.set_mode_index(3)  # 10x
        self.assertEqual(f5_card.seg_button.get(), "10x")

        # Game disconnects
        app._handle_attach_update(False, 0, 0)
        self.assertFalse(f1_card.switch_var.get())
        self.assertEqual(f5_card.seg_button.get(), "1x 默认")

        app.on_closing()

    @patch("howtofish_cheat.trainer.keyboard")
    def test_f10_exit_triggers_gui_close(self, mock_keyboard):
        trainer = HowToFishTrainer(language="zh")
        trainer.start_background = MagicMock()

        app = TrainerApp(trainer)
        app.withdraw()

        app.on_closing = MagicMock()
        # Trigger stop() as would happen on F10
        trainer.stop()
        app.update()  # Process pending events scheduled via after(0, ...)
        app.on_closing.assert_called_once()


if __name__ == "__main__":
    unittest.main()

