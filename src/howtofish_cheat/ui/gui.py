"""Modern CustomTkinter GUI Dashboard for How to Fish Trainer."""

import logging
import threading
from typing import TYPE_CHECKING, Dict, Optional, Union
import customtkinter as ctk

from ..features import (
    CheatFeature,
    DamageMultiplierCheat,
    AddMoneyCheat,
)
from ..i18n import tr

if TYPE_CHECKING:
    from ..trainer import HowToFishTrainer

logger = logging.getLogger(__name__)

# Appearance configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class BooleanFeatureCard(ctk.CTkFrame):
    """Card widget for boolean cheats (F1~F4) with a modern toggle switch."""

    def __init__(
        self,
        master,
        feature: CheatFeature,
        language: str = "zh",
        on_toggle=None,
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=10,
            fg_color=("#F0F2F5", "#1c1f2b"),
            border_width=1,
            border_color=("#E0E0E0", "#2b3042"),
            **kwargs,
        )
        self.feature = feature
        self.language = language
        self.on_toggle = on_toggle
        self._updating_from_event = False

        # Left: Hotkey Badge
        self.badge = ctk.CTkLabel(
            self,
            text=f"[{feature.hotkey}]",
            width=54,
            height=32,
            corner_radius=6,
            fg_color=("#E2E7F0", "#252b3d"),
            text_color="#00D26A",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.badge.pack(side="left", padx=(14, 12), pady=12)

        # Center: Title & Description
        self.info_box = ctk.CTkFrame(self, fg_color="transparent")
        self.info_box.pack(side="left", fill="both", expand=True, pady=8)

        fname = feature.get_name(self.language) if hasattr(feature, "get_name") else feature.name
        fdesc = feature.get_description(self.language) if hasattr(feature, "get_description") else feature.description

        self.title_lbl = ctk.CTkLabel(
            self.info_box,
            text=fname,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1A1A1A", "#FFFFFF"),
        )
        self.title_lbl.pack(fill="x")

        self.desc_lbl = ctk.CTkLabel(
            self.info_box,
            text=fdesc,
            anchor="w",
            text_color=("#666666", "#8F96A0"),
            font=ctk.CTkFont(size=11),
        )
        self.desc_lbl.pack(fill="x", pady=(2, 0))

        # Right: Toggle Switch
        self.switch_var = ctk.BooleanVar(value=feature.is_enabled)
        self.switch = ctk.CTkSwitch(
            self,
            text="",
            width=46,
            switch_width=44,
            switch_height=22,
            variable=self.switch_var,
            progress_color="#00D26A",
            button_color="#FFFFFF",
            button_hover_color="#E0E0E0",
            command=self._on_switch_clicked,
        )
        self.switch.pack(side="right", padx=(8, 16), pady=12)

    def _on_switch_clicked(self) -> None:
        if self._updating_from_event:
            return
        if self.on_toggle:
            self.on_toggle(self.feature.hotkey, self.switch_var.get())

    def set_active(self, is_active: bool) -> None:
        """Synchronizes switch state when triggered via external hotkey without recursive loop."""
        self._updating_from_event = True
        try:
            self.switch_var.set(is_active)
        finally:
            self._updating_from_event = False

    def update_language(self, language: str) -> None:
        """Updates text labels to new language."""
        self.language = language
        fname = self.feature.get_name(self.language) if hasattr(self.feature, "get_name") else self.feature.name
        fdesc = (
            self.feature.get_description(self.language)
            if hasattr(self.feature, "get_description")
            else self.feature.description
        )
        self.title_lbl.configure(text=fname)
        self.desc_lbl.configure(text=fdesc)


class DamageMultiplierCard(ctk.CTkFrame):
    """Card widget for damage multiplier (F5) with segmented button mode selector."""

    MODE_LABELS = {
        "zh": ["1x 默认", "2x", "5x", "10x", "秒杀"],
        "en": ["1x Normal", "2x", "5x", "10x", "One-Shot"],
    }

    def __init__(
        self,
        master,
        feature: DamageMultiplierCheat,
        language: str = "zh",
        on_mode_change=None,
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=10,
            fg_color=("#F0F2F5", "#1c1f2b"),
            border_width=1,
            border_color=("#E0E0E0", "#2b3042"),
            **kwargs,
        )
        self.feature = feature
        self.language = language
        self.on_mode_change = on_mode_change
        self._updating_from_event = False

        # Left: Hotkey Badge
        self.badge = ctk.CTkLabel(
            self,
            text=f"[{feature.hotkey}]",
            width=54,
            height=32,
            corner_radius=6,
            fg_color=("#E2E7F0", "#252b3d"),
            text_color="#FFB300",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.badge.pack(side="left", padx=(14, 12), pady=12)

        # Center: Title & Description
        self.info_box = ctk.CTkFrame(self, fg_color="transparent")
        self.info_box.pack(side="left", fill="both", expand=True, pady=8)

        fname = feature.get_name(self.language) if hasattr(feature, "get_name") else feature.name
        fdesc = feature.get_description(self.language) if hasattr(feature, "get_description") else feature.description

        self.title_lbl = ctk.CTkLabel(
            self.info_box,
            text=fname,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1A1A1A", "#FFFFFF"),
        )
        self.title_lbl.pack(fill="x")

        self.desc_lbl = ctk.CTkLabel(
            self.info_box,
            text=fdesc,
            anchor="w",
            text_color=("#666666", "#8F96A0"),
            font=ctk.CTkFont(size=11),
        )
        self.desc_lbl.pack(fill="x", pady=(2, 0))

        # Right: Segmented Button
        current_labels = self.MODE_LABELS.get(self.language, self.MODE_LABELS["en"])
        cur_idx = getattr(feature, "current_mode_index", 0)
        init_val = current_labels[cur_idx] if cur_idx < len(current_labels) else current_labels[0]

        self.seg_button = ctk.CTkSegmentedButton(
            self,
            values=current_labels,
            selected_color="#FFB300",
            selected_hover_color="#FFA000",
            unselected_color=("#DFE2E8", "#242938"),
            unselected_hover_color=("#CFD3DC", "#2D3446"),
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_segment_selected,
        )
        self.seg_button.set(init_val)
        self.seg_button.pack(side="right", padx=(8, 16), pady=12)

    def _on_segment_selected(self, value: str) -> None:
        if self._updating_from_event:
            return
        labels = self.MODE_LABELS.get(self.language, self.MODE_LABELS["en"])
        if value in labels:
            idx = labels.index(value)
            if self.on_mode_change:
                self.on_mode_change(idx)

    def set_mode_index(self, index: int) -> None:
        """Updates segmented button to target mode index from background event."""
        self._updating_from_event = True
        try:
            labels = self.MODE_LABELS.get(self.language, self.MODE_LABELS["en"])
            if 0 <= index < len(labels):
                self.seg_button.set(labels[index])
        finally:
            self._updating_from_event = False

    def update_language(self, language: str) -> None:
        """Updates labels and reconfigures segmented button values."""
        self.language = language
        fname = self.feature.get_name(self.language) if hasattr(self.feature, "get_name") else self.feature.name
        fdesc = (
            self.feature.get_description(self.language)
            if hasattr(self.feature, "get_description")
            else self.feature.description
        )
        self.title_lbl.configure(text=fname)
        self.desc_lbl.configure(text=fdesc)

        labels = self.MODE_LABELS.get(self.language, self.MODE_LABELS["en"])
        cur_idx = getattr(self.feature, "current_mode_index", 0)
        self.seg_button.configure(values=labels)
        if 0 <= cur_idx < len(labels):
            self.seg_button.set(labels[cur_idx])


class AddMoneyCard(ctk.CTkFrame):
    """Card widget for Add Money cheat (F6) with amount entry and action button."""

    def __init__(
        self,
        master,
        feature: AddMoneyCheat,
        language: str = "zh",
        on_add_money=None,
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=10,
            fg_color=("#F0F2F5", "#1c1f2b"),
            border_width=1,
            border_color=("#E0E0E0", "#2b3042"),
            **kwargs,
        )
        self.feature = feature
        self.language = language
        self.on_add_money = on_add_money

        # Left: Hotkey Badge
        self.badge = ctk.CTkLabel(
            self,
            text=f"[{feature.hotkey}]",
            width=54,
            height=32,
            corner_radius=6,
            fg_color=("#E2E7F0", "#252b3d"),
            text_color="#00ADB5",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.badge.pack(side="left", padx=(14, 12), pady=12)

        # Center: Title & Description
        self.info_box = ctk.CTkFrame(self, fg_color="transparent")
        self.info_box.pack(side="left", fill="both", expand=True, pady=8)

        fname = feature.get_name(self.language) if hasattr(feature, "get_name") else feature.name
        fdesc = feature.get_description(self.language) if hasattr(feature, "get_description") else feature.description

        self.title_lbl = ctk.CTkLabel(
            self.info_box,
            text=fname,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1A1A1A", "#FFFFFF"),
        )
        self.title_lbl.pack(fill="x")

        self.desc_lbl = ctk.CTkLabel(
            self.info_box,
            text=fdesc,
            anchor="w",
            text_color=("#666666", "#8F96A0"),
            font=ctk.CTkFont(size=11),
        )
        self.desc_lbl.pack(fill="x", pady=(2, 0))

        # Right Action Area: Entry + Button + Total Label
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.pack(side="right", padx=(8, 16), pady=8)

        # Top row: Entry + Add Button
        self.top_row = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        self.top_row.pack(fill="x")

        self.amount_entry = ctk.CTkEntry(
            self.top_row,
            width=76,
            height=28,
            font=ctk.CTkFont(size=12),
            placeholder_text="10000",
        )
        self.amount_entry.insert(0, str(getattr(feature, "add_amount", 10000)))
        self.amount_entry.pack(side="left", padx=(0, 6))

        self.add_btn = ctk.CTkButton(
            self.top_row,
            text=tr("btn_add_money", self.language),
            width=72,
            height=28,
            corner_radius=6,
            fg_color="#00ADB5",
            hover_color="#00888F",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_add_clicked,
        )
        self.add_btn.pack(side="left")

        # Bottom row: Total added counter
        self.total_lbl = ctk.CTkLabel(
            self.action_frame,
            text=tr("total_added_label", self.language, total=getattr(feature, "total_added", 0)),
            font=ctk.CTkFont(size=10),
            text_color="#00ADB5",
            anchor="e",
        )
        self.total_lbl.pack(fill="x", pady=(2, 0))

    def _on_add_clicked(self) -> None:
        raw = self.amount_entry.get().strip()
        try:
            val = int(raw)
            if val <= 0:
                val = 10000
        except ValueError:
            val = 10000
        if self.on_add_money:
            self.on_add_money(val)

    def update_total_added(self, total: int) -> None:
        """Updates total added count."""
        self.total_lbl.configure(text=tr("total_added_label", self.language, total=total))

    def update_language(self, language: str) -> None:
        """Updates labels to new language."""
        self.language = language
        fname = self.feature.get_name(self.language) if hasattr(self.feature, "get_name") else self.feature.name
        fdesc = (
            self.feature.get_description(self.language)
            if hasattr(self.feature, "get_description")
            else self.feature.description
        )
        self.title_lbl.configure(text=fname)
        self.desc_lbl.configure(text=fdesc)
        self.add_btn.configure(text=tr("btn_add_money", self.language))
        self.total_lbl.configure(
            text=tr("total_added_label", self.language, total=getattr(self.feature, "total_added", 0))
        )


class TrainerApp(ctk.CTk):
    """Main window application for How to Fish Trainer GUI."""

    def __init__(self, trainer: Optional[object] = None):
        super().__init__()
        if trainer is None:
            from ..trainer import HowToFishTrainer
            self.trainer = HowToFishTrainer(language="zh")
        else:
            self.trainer = trainer
        self.language = self.trainer.language
        self.cards: Dict[str, Union[BooleanFeatureCard, DamageMultiplierCard, AddMoneyCard]] = {}
        self._ui_is_attached = False

        # Window configurations
        self.title(tr("gui_title", self.language))
        self.geometry("680x740")
        self.minsize(620, 680)

        # Center on screen
        self._center_window(680, 740)

        # Intercept window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Setup Layout
        self._setup_ui()

        # Connect Trainer Callbacks
        self._bind_trainer_events()

        # Start trainer loop in background
        self.trainer.start_background(poll_interval=0.25)

    def _center_window(self, width: int, height: int) -> None:
        """Centers window on the primary monitor."""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_ui(self) -> None:
        """Builds all visual frames and component hierarchies."""
        # Main container with padding
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=16)

        # -----------------------------------------------------
        # 1. Header Frame
        # -----------------------------------------------------
        self.header_frame = ctk.CTkFrame(
            self.container,
            corner_radius=12,
            fg_color=("#F0F2F5", "#161922"),
            border_width=1,
            border_color=("#E0E0E0", "#242938"),
        )
        self.header_frame.pack(fill="x", pady=(0, 14))

        # Title bar row
        self.title_row = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.title_row.pack(fill="x", padx=16, pady=(14, 8))

        self.title_label = ctk.CTkLabel(
            self.title_row,
            text="HOW TO FISH",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("#1A1A1A", "#FFFFFF"),
        )
        self.title_label.pack(side="left")

        self.version_badge = ctk.CTkLabel(
            self.title_row,
            text="TRAINER v0.1.1",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#E2E7F0", "#242938"),
            text_color="#00ADB5",
            corner_radius=6,
            width=90,
            height=24,
        )
        self.version_badge.pack(side="left", padx=(10, 0))

        # Language Toggle on Right
        self.lang_btn = ctk.CTkSegmentedButton(
            self.title_row,
            values=["中文", "English"],
            font=ctk.CTkFont(size=11, weight="bold"),
            selected_color="#00ADB5",
            selected_hover_color="#00888F",
            command=self._on_lang_changed,
        )
        self.lang_btn.set("中文" if self.language == "zh" else "English")
        self.lang_btn.pack(side="right")

        # Subtitle & Admin privilege badge
        is_admin = getattr(self.trainer, "is_admin", lambda: True)()
        admin_hint = "" if is_admin else ("  |  ⚠️ " + ("未以管理员身份运行" if self.language == "zh" else "Non-Admin Mode"))
        self.sub_label = ctk.CTkLabel(
            self.header_frame,
            text=f"Unity Mono JIT Engine  |  External Trainer{admin_hint}",
            font=ctk.CTkFont(size=11),
            text_color="#FFA000" if not is_admin else ("#666666", "#8F96A0"),
        )
        self.sub_label.pack(anchor="w", padx=16, pady=(0, 10))

        # Connection Status Banner
        self.status_banner = ctk.CTkFrame(
            self.header_frame,
            corner_radius=8,
            fg_color=("#EAEAEA", "#1e2230"),
            border_width=1,
            border_color=("#D0D0D0", "#2b3144"),
        )
        self.status_banner.pack(fill="x", padx=16, pady=(0, 14))

        self.status_dot = ctk.CTkLabel(
            self.status_banner,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color="#FFA000",
            width=24,
        )
        self.status_dot.pack(side="left", padx=(10, 4), pady=6)

        self.conn_text_lbl = ctk.CTkLabel(
            self.status_banner,
            text=tr("status_waiting", self.language, process_name=self.trainer.process_name),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#333333", "#CCCCCC"),
            anchor="w",
        )
        self.conn_text_lbl.pack(side="left", fill="x", expand=True, padx=4, pady=6)

        # -----------------------------------------------------
        # 2. Features Scrollable List
        # -----------------------------------------------------
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.container,
            fg_color="transparent",
            corner_radius=0,
        )
        self.scroll_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Populate Cards from trainer.features
        for feature in self.trainer.features:
            if isinstance(feature, DamageMultiplierCheat):
                card = DamageMultiplierCard(
                    self.scroll_frame,
                    feature=feature,
                    language=self.language,
                    on_mode_change=self._on_gui_damage_mode_change,
                )
            elif isinstance(feature, AddMoneyCheat):
                card = AddMoneyCard(
                    self.scroll_frame,
                    feature=feature,
                    language=self.language,
                    on_add_money=self._on_gui_add_money,
                )
            else:
                card = BooleanFeatureCard(
                    self.scroll_frame,
                    feature=feature,
                    language=self.language,
                    on_toggle=self._on_gui_feature_toggle,
                )
            card.pack(fill="x", pady=5)
            self.cards[feature.hotkey] = card

        # -----------------------------------------------------
        # 3. Footer Frame (Status Bar & Hotkey Hints)
        # -----------------------------------------------------
        self.footer_frame = ctk.CTkFrame(
            self.container,
            corner_radius=10,
            fg_color=("#F0F2F5", "#161922"),
            border_width=1,
            border_color=("#E0E0E0", "#242938"),
        )
        self.footer_frame.pack(fill="x", pady=(4, 0))

        self.status_msg_lbl = ctk.CTkLabel(
            self.footer_frame,
            text=f"• {self.trainer.status_message}",
            font=ctk.CTkFont(size=12),
            text_color="#00D26A",
            anchor="w",
        )
        self.status_msg_lbl.pack(fill="x", padx=14, pady=(8, 2))

        self.shortcut_hint_lbl = ctk.CTkLabel(
            self.footer_frame,
            text=tr("footer_shortcuts", self.language),
            font=ctk.CTkFont(size=11),
            text_color=("#888888", "#707684"),
            anchor="w",
        )
        self.shortcut_hint_lbl.pack(fill="x", padx=14, pady=(0, 8))

    # ---------------------------------------------------------
    # Trainer Event Callbacks (Dispatched to Tk Main Thread)
    # ---------------------------------------------------------

    def _safe_after(self, func, *args) -> None:
        """Dispatches callback safely to Tk main thread if the window is alive."""
        try:
            if not getattr(self, "_is_closing", False) and self.winfo_exists():
                self.after(0, func, *args)
        except Exception:
            pass

    def _bind_trainer_events(self) -> None:
        """Subscribes GUI listeners to engine event notifications."""
        self.trainer.add_status_callback(lambda msg: self._safe_after(self._handle_status_update, msg))
        self.trainer.add_attach_callback(
            lambda att, pid, dom: self._safe_after(self._handle_attach_update, att, pid, dom)
        )
        self.trainer.add_feature_callback(lambda f: self._safe_after(self._handle_feature_update, f))
        self.trainer.add_language_callback(lambda lang: self._safe_after(self._handle_language_update, lang))
        self.trainer.add_exit_callback(lambda: self._safe_after(self.on_closing))

    def _handle_status_update(self, msg: str) -> None:
        """Updates footer status message."""
        try:
            if self.winfo_exists():
                self.status_msg_lbl.configure(text=f"• {msg}")
        except Exception:
            pass

    def _handle_attach_update(self, is_attached: bool, pid: int, mono_domain: int) -> None:
        """Updates header connection banner and status indicators."""
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        was_attached = getattr(self, "_ui_is_attached", False)
        self._ui_is_attached = is_attached

        if is_attached:
            self.status_dot.configure(text_color="#00D26A")
            msg = tr("status_connected", self.language, process_name=self.trainer.process_name, pid=pid)
            if mono_domain:
                msg += f" | Mono: 0x{mono_domain:X}"
            self.conn_text_lbl.configure(text=msg, text_color="#00D26A")
            self.status_banner.configure(border_color="#00965E")
        else:
            self.status_dot.configure(text_color="#FFA000")
            msg = tr("status_waiting", self.language, process_name=self.trainer.process_name)
            self.conn_text_lbl.configure(text=msg, text_color="#FFA000")
            self.status_banner.configure(border_color=("#D0D0D0", "#2b3144"))

            # When game disconnects, reset UI visual switches to OFF
            for card in self.cards.values():
                if isinstance(card, BooleanFeatureCard):
                    card.set_active(False)
                elif isinstance(card, DamageMultiplierCard):
                    card.set_mode_index(0)

    def _handle_feature_update(self, feature: CheatFeature) -> None:
        """Updates feature card state in GUI when modified externally (e.g. via keyboard hotkey)."""
        card = self.cards.get(feature.hotkey)
        if not card:
            return

        if isinstance(feature, DamageMultiplierCheat) and isinstance(card, DamageMultiplierCard):
            card.set_mode_index(feature.current_mode_index)
        elif isinstance(feature, AddMoneyCheat) and isinstance(card, AddMoneyCard):
            card.update_total_added(feature.total_added)
        elif isinstance(card, BooleanFeatureCard):
            card.set_active(feature.is_enabled)

    def _handle_language_update(self, lang: str) -> None:
        """Synchronizes GUI text labels when language is changed (e.g. via F12 or dropdown)."""
        self.language = lang
        self.title(tr("gui_title", self.language))
        self.lang_btn.set("中文" if self.language == "zh" else "English")
        self.shortcut_hint_lbl.configure(text=tr("footer_shortcuts", self.language))

        # Re-update banner text with current attachment state
        is_attached = self.trainer.pm is not None and self.trainer.mono is not None
        pid = self.trainer.pm.process_id if self.trainer.pm else 0
        domain = self.trainer.mono.root_domain if (self.trainer.mono and self.trainer.mono.root_domain) else 0
        self._handle_attach_update(is_attached, pid, domain)

        # Update all feature cards
        for card in self.cards.values():
            card.update_language(self.language)

    # ---------------------------------------------------------
    # GUI User Interaction Handlers
    # ---------------------------------------------------------

    def _on_gui_feature_toggle(self, hotkey: str, is_active: bool) -> None:
        """User toggled a Boolean card switch in the GUI."""
        success = self.trainer.set_feature_enabled(hotkey, is_active)
        if not success:
            card = self.cards.get(hotkey)
            if card and isinstance(card, BooleanFeatureCard):
                card.set_active(False)

    def _on_gui_damage_mode_change(self, mode_idx: int) -> None:
        """User clicked a damage multiplier mode in the segmented button."""
        res = self.trainer.set_damage_multiplier_mode(mode_idx)
        if res is None:
            card = self.cards.get("F5")
            if card and isinstance(card, DamageMultiplierCard):
                card.set_mode_index(0)

    def _on_gui_add_money(self, amount: int) -> None:
        """User clicked Add Money button."""
        self.trainer.trigger_add_money(amount)

    def _on_lang_changed(self, choice: str) -> None:
        """User clicked language toggle in header."""
        target_lang = "zh" if choice == "中文" else "en"
        if target_lang != self.language:
            self.trainer.set_language(target_lang)

    def on_closing(self) -> None:
        """Ensures safe teardown of trainer thread and memory hooks when window is closed."""
        if getattr(self, "_is_closing", False):
            return
        self._is_closing = True
        try:
            self.trainer.stop()
            self.trainer.join(timeout=1.0)
        except Exception as e:
            logger.debug(f"Error during trainer stop on closing: {e}")
        try:
            self.destroy()
        except Exception:
            pass


def run_gui(process_name: str = "How to Fish.exe", language: str = "zh") -> None:
    """Launches the CustomTkinter GUI."""
    from ..trainer import HowToFishTrainer

    trainer = HowToFishTrainer(process_name=process_name, language=language)
    app = TrainerApp(trainer)
    app.mainloop()

