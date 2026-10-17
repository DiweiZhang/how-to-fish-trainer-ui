"""Trainer engine orchestrating process attachment, Mono runtime, and cheat hotkeys."""

import atexit
import logging
import signal
import sys
import threading
import time
from typing import Callable, List, Optional, Union
import keyboard
import pymem
import pymem.process
from rich.console import Console
from rich.live import Live

from .features import (
    CheatFeature,
    LockHealthCheat,
    LockHungerCheat,
    InfiniteJumpCheat,
    UnlimitedAmmoCheat,
    DamageMultiplierCheat,
    AddMoneyCheat,
    get_default_features,
)
from .mono.bridge import MonoBridge
from .mono.patcher import MethodPatcher
from .ui.console import TrainerUI
from .i18n import tr

logger = logging.getLogger(__name__)


class HowToFishTrainer:
    """Main trainer orchestrator for How to Fish with decoupled event hooks."""

    def __init__(self, process_name: str = "How to Fish.exe", language: str = "zh"):
        self.process_name = process_name
        self.language = language
        self.pm: Optional[pymem.Pymem] = None
        self.mono: Optional[MonoBridge] = None
        self.patcher: Optional[MethodPatcher] = None
        self.features: List[CheatFeature] = get_default_features()
        self.is_running = False
        self.status_message = tr("starting", self.language)
        self.console = Console()
        self.ui = TrainerUI(self.console)
        self._feature_hotkey_hooks = []
        self._control_hotkey_hooks = []

        # Decoupled event listeners
        self._status_callbacks: List[Callable[[str], None]] = []
        self._attach_callbacks: List[Callable[[bool, int, int], None]] = []
        self._feature_callbacks: List[Callable[[CheatFeature], None]] = []
        self._language_callbacks: List[Callable[[str], None]] = []
        self._exit_callbacks: List[Callable[[], None]] = []

        # Background thread reference
        self._bg_thread: Optional[threading.Thread] = None

        # State de-duplication caches
        self._last_status_message: Optional[str] = None
        self._last_attach_state: Optional[tuple] = None
        self._last_f10_time: float = 0.0

        # Register global control hotkeys (F10 exit, F12 toggle language) immediately
        self._setup_control_hotkeys()

        # Ensure cleanup is called on process termination
        atexit.register(self._cleanup)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except Exception:
            pass

    # ---------------------------------------------------------
    # Event Callback Management
    # ---------------------------------------------------------

    def add_exit_callback(self, cb: Callable[[], None]) -> None:
        """Subscribes a listener to stop/exit events."""
        if cb not in self._exit_callbacks:
            self._exit_callbacks.append(cb)

    def remove_exit_callback(self, cb: Callable[[], None]) -> None:
        """Unsubscribes an exit listener."""
        if cb in self._exit_callbacks:
            self._exit_callbacks.remove(cb)

    def add_status_callback(self, cb: Callable[[str], None]) -> None:
        """Subscribes a listener to status message changes."""
        if cb not in self._status_callbacks:
            self._status_callbacks.append(cb)

    def remove_status_callback(self, cb: Callable[[str], None]) -> None:
        """Unsubscribes a status listener."""
        if cb in self._status_callbacks:
            self._status_callbacks.remove(cb)

    def add_attach_callback(self, cb: Callable[[bool, int, int], None]) -> None:
        """Subscribes a listener to process attachment state (is_attached, pid, mono_domain)."""
        if cb not in self._attach_callbacks:
            self._attach_callbacks.append(cb)

    def remove_attach_callback(self, cb: Callable[[bool, int, int], None]) -> None:
        """Unsubscribes an attach listener."""
        if cb in self._attach_callbacks:
            self._attach_callbacks.remove(cb)

    def add_feature_callback(self, cb: Callable[[CheatFeature], None]) -> None:
        """Subscribes a listener to cheat feature toggles/updates."""
        if cb not in self._feature_callbacks:
            self._feature_callbacks.append(cb)

    def remove_feature_callback(self, cb: Callable[[CheatFeature], None]) -> None:
        """Unsubscribes a feature listener."""
        if cb in self._feature_callbacks:
            self._feature_callbacks.remove(cb)

    def add_language_callback(self, cb: Callable[[str], None]) -> None:
        """Subscribes a listener to interface language switches."""
        if cb not in self._language_callbacks:
            self._language_callbacks.append(cb)

    def remove_language_callback(self, cb: Callable[[str], None]) -> None:
        """Unsubscribes a language listener."""
        if cb in self._language_callbacks:
            self._language_callbacks.remove(cb)

    def set_status(self, msg: str, force: bool = False) -> None:
        """Sets status message and notifies all registered listeners with de-duplication."""
        if not force and self.status_message == msg and self._last_status_message == msg:
            return
        self._last_status_message = msg
        self.status_message = msg
        for cb in list(self._status_callbacks):
            try:
                cb(msg)
            except Exception as e:
                logger.debug(f"Error in status callback: {e}")

    def _notify_attach(self, is_attached: bool, pid: int, mono_domain: int, force: bool = False) -> None:
        """Notifies attach listeners only when attachment state actually changes."""
        current_state = (is_attached, pid, mono_domain)
        if not force and self._last_attach_state == current_state:
            return
        self._last_attach_state = current_state
        for cb in list(self._attach_callbacks):
            try:
                cb(is_attached, pid, mono_domain)
            except Exception as e:
                logger.debug(f"Error in attach callback: {e}")

    def _notify_feature_change(self, feature: CheatFeature) -> None:
        for cb in list(self._feature_callbacks):
            try:
                cb(feature)
            except Exception as e:
                logger.debug(f"Error in feature callback: {e}")

    def _notify_language_change(self, lang: str) -> None:
        for cb in list(self._language_callbacks):
            try:
                cb(lang)
            except Exception as e:
                logger.debug(f"Error in language callback: {e}")

    # ---------------------------------------------------------
    # Control Hotkeys & Language Management
    # ---------------------------------------------------------

    def _setup_control_hotkeys(self) -> None:
        """Registers persistent control hotkeys (F10 with safety debounce, Ctrl+F10, F12) that work at any time."""
        self._remove_control_hotkeys()
        try:
            exit_hook = keyboard.add_hotkey("F10", self._handle_f10_press, suppress=False)
            self._control_hotkey_hooks.append(exit_hook)
        except Exception as e:
            logger.debug(f"Failed to register F10 exit hotkey: {e}")

        try:
            ctrl_exit_hook = keyboard.add_hotkey("Ctrl+F10", self.stop, suppress=False)
            self._control_hotkey_hooks.append(ctrl_exit_hook)
        except Exception as e:
            logger.debug(f"Failed to register Ctrl+F10 exit hotkey: {e}")

        try:
            lang_hook = keyboard.add_hotkey("F12", self.toggle_language, suppress=False)
            self._control_hotkey_hooks.append(lang_hook)
        except Exception as e:
            logger.debug(f"Failed to register F12 language hotkey: {e}")

    def _handle_f10_press(self) -> None:
        """Handles F10 press with double-tap safety to prevent accidental exits on laptop function keys."""
        now = time.time()
        if now - self._last_f10_time < 2.0:
            self.stop()
        else:
            self._last_f10_time = now
            warn_msg = (
                "【防误触】2 秒内再次按下 [F10] 确认退出，或按 [Ctrl+F10] 立即退出"
                if self.language == "zh"
                else "[Safety] Press [F10] again within 2s to exit, or [Ctrl+F10] to exit now"
            )
            self.set_status(warn_msg, force=True)

    def _remove_control_hotkeys(self) -> None:
        """Unregisters persistent control hotkeys."""
        for hook in self._control_hotkey_hooks:
            try:
                keyboard.remove_hotkey(hook)
            except Exception:
                pass
            self._control_hotkey_hooks.clear()

    def toggle_language(self) -> None:
        """Toggles interface language between Chinese ('zh') and English ('en')."""
        new_lang = "en" if self.language == "zh" else "zh"
        self.set_language(new_lang)

    def set_language(self, lang: str) -> None:
        """Sets interface language ('zh' or 'en') and notifies listeners."""
        self.language = lang
        self.set_status(tr("lang_switched", self.language))
        self._notify_language_change(self.language)

    def _signal_handler(self, signum, frame):
        """Catches exit signals and triggers clean shutdown."""
        self.stop()

    # ---------------------------------------------------------
    # Process Attachment & Feature Setup
    # ---------------------------------------------------------

    def attach(self) -> bool:
        """Attempts to find and attach to the game process and Mono runtime."""
        try:
            self.pm = pymem.Pymem(self.process_name)
            self.set_status(tr("found_process", self.language, process_name=self.process_name))
            self.patcher = MethodPatcher(self.pm)
            self.mono = MonoBridge(self.pm)
            self._setup_features()
            self._setup_feature_hotkeys()
            self.set_status(tr("attached_ready", self.language))
            pid = self.pm.process_id if self.pm else 0
            domain = self.mono.root_domain if (self.mono and self.mono.root_domain) else 0
            self._notify_attach(True, pid, domain)
            return True
        except pymem.exception.ProcessNotFound:
            self.pm = None
            self.set_status(tr("waiting_process", self.language, process_name=self.process_name))
            self._notify_attach(False, 0, 0)
            return False
        except Exception as e:
            self.set_status(f"Attachment error: {e}")
            self._cleanup_game_resources()
            self._notify_attach(False, 0, 0)
            return False

    def _setup_features(self) -> None:
        """Initializes all available cheat features and pre-compiles JIT methods."""
        health_cheat = LockHealthCheat(self.pm, self.mono, self.patcher, hotkey="F1")
        hunger_cheat = LockHungerCheat(self.pm, self.mono, self.patcher, hotkey="F2")
        jump_cheat = InfiniteJumpCheat(self.pm, self.mono, self.patcher, hotkey="F3")
        ammo_cheat = UnlimitedAmmoCheat(self.pm, self.mono, self.patcher, hotkey="F4")
        damage_cheat = DamageMultiplierCheat(self.pm, self.mono, self.patcher, hotkey="F5")
        money_cheat = AddMoneyCheat(self.pm, self.mono, self.patcher, hotkey="F6")

        health_cheat.prepare()
        hunger_cheat.prepare()
        jump_cheat.prepare()
        ammo_cheat.prepare()
        damage_cheat.prepare()
        money_cheat.prepare()

        self.features = [health_cheat, hunger_cheat, jump_cheat, ammo_cheat, damage_cheat, money_cheat]
        for f in self.features:
            self._notify_feature_change(f)

    def _setup_feature_hotkeys(self) -> None:
        """Registers feature hotkeys (F1..F6)."""
        self._remove_feature_hotkeys()
        for feature in self.features:
            def make_handler(f):
                return lambda: self._on_hotkey_pressed(f)
            try:
                hook = keyboard.add_hotkey(feature.hotkey, make_handler(feature), suppress=False)
                self._feature_hotkey_hooks.append(hook)
            except Exception as e:
                logger.debug(f"Failed to register hotkey {feature.hotkey}: {e}")

    def _remove_feature_hotkeys(self) -> None:
        """Unregisters all active feature hotkey hooks."""
        for hook in self._feature_hotkey_hooks:
            try:
                keyboard.remove_hotkey(hook)
            except Exception:
                pass
        self._feature_hotkey_hooks.clear()

    # ---------------------------------------------------------
    # Programmatic & Hotkey Feature Control
    # ---------------------------------------------------------

    def get_feature(self, feature_or_hotkey: Union[CheatFeature, str]) -> Optional[CheatFeature]:
        """Finds feature by instance or hotkey string (e.g. 'F1')."""
        if isinstance(feature_or_hotkey, CheatFeature):
            return feature_or_hotkey
        for f in self.features:
            if f.hotkey.upper() == str(feature_or_hotkey).upper():
                return f
        return None

    def _on_hotkey_pressed(self, feature: CheatFeature) -> None:
        """Handles hotkey trigger and toggles feature."""
        if not self.pm or not self.mono:
            return
        feature.toggle()
        self._notify_feature_change(feature)
        fname = feature.get_name(self.language) if hasattr(feature, "get_name") else feature.name
        if isinstance(feature, DamageMultiplierCheat):
            if self.language == "zh":
                mode_name = feature.MODES_ZH[feature.current_mode_index]
                self.set_status(f"{fname} 已设置为 [{mode_name}]")
            else:
                mode_name = feature.MODES[feature.current_mode_index]
                self.set_status(f"{fname} set to [{mode_name}]")
        elif isinstance(feature, AddMoneyCheat):
            if self.language == "zh":
                self.set_status(f"成功增加 +${feature.add_amount:,} 金币！(累计增加: +${feature.total_added:,})")
            else:
                self.set_status(f"+${feature.add_amount:,} money added! (Total added: +${feature.total_added:,})")
        elif hasattr(feature, "last_action_message") and feature.last_action_message:
            self.set_status(feature.last_action_message)
        else:
            if self.language == "zh":
                state = "已开启" if feature.is_enabled else "已关闭"
                self.set_status(f"{fname} 当前状态: [{state}]")
            else:
                state = "ENABLED" if feature.is_enabled else "DISABLED"
                self.set_status(f"{fname} is now [{state}]")

    def toggle_feature_by_hotkey(self, hotkey: str) -> Optional[CheatFeature]:
        """Toggles a feature programmatically by hotkey identifier."""
        feature = self.get_feature(hotkey)
        if feature:
            self._on_hotkey_pressed(feature)
        return feature

    def set_feature_enabled(self, feature_or_hotkey: Union[CheatFeature, str], enabled: bool) -> bool:
        """Explicitly sets a feature's enabled state (e.g. from UI Switch)."""
        feature = self.get_feature(feature_or_hotkey)
        if not feature:
            return False

        if not self.pm or not self.mono:
            self.set_status(tr("waiting_process", self.language, process_name=self.process_name))
            return False

        if feature.is_enabled != enabled:
            if enabled:
                feature.enable()
            else:
                feature.disable()
            self._notify_feature_change(feature)
            fname = feature.get_name(self.language) if hasattr(feature, "get_name") else feature.name
            state = ("已开启" if enabled else "已关闭") if self.language == "zh" else ("ENABLED" if enabled else "DISABLED")
            self.set_status(f"{fname} 当前状态: [{state}]" if self.language == "zh" else f"{fname} is now [{state}]")
        return True

    def cycle_damage_multiplier(self) -> Optional[str]:
        """Cycles damage multiplier to the next mode."""
        feature = self.get_feature("F5")
        if isinstance(feature, DamageMultiplierCheat) and self.pm and self.mono:
            feature.toggle()
            self._notify_feature_change(feature)
            fname = feature.get_name(self.language) if hasattr(feature, "get_name") else feature.name
            mode_name = (
                feature.MODES_ZH[feature.current_mode_index]
                if self.language == "zh"
                else feature.MODES[feature.current_mode_index]
            )
            self.set_status(f"{fname} 已设置为 [{mode_name}]" if self.language == "zh" else f"{fname} set to [{mode_name}]")
            return mode_name
        return None

    def set_damage_multiplier_mode(self, mode_index: int) -> Optional[str]:
        """Sets damage multiplier directly to a specific mode index (0=1x, 1=2x, 2=5x, 3=10x, 4=Kill)."""
        feature = self.get_feature("F5")
        if isinstance(feature, DamageMultiplierCheat):
            if not self.pm or not self.mono:
                self.set_status(tr("waiting_process", self.language, process_name=self.process_name))
                return None
            feature.apply_mode(mode_index)
            self._notify_feature_change(feature)
            fname = feature.get_name(self.language) if hasattr(feature, "get_name") else feature.name
            mode_name = (
                feature.MODES_ZH[feature.current_mode_index]
                if self.language == "zh"
                else feature.MODES[feature.current_mode_index]
            )
            self.set_status(f"{fname} 已设置为 [{mode_name}]" if self.language == "zh" else f"{fname} set to [{mode_name}]")
            return mode_name
        return None

    def trigger_add_money(self, amount: Optional[int] = None) -> bool:
        """Triggers the add money action."""
        feature = self.get_feature("F6")
        if isinstance(feature, AddMoneyCheat):
            if not self.pm or not self.mono:
                self.set_status(tr("waiting_process", self.language, process_name=self.process_name))
                return False
            if amount is not None:
                feature.add_amount = amount
            feature.toggle()
            self._notify_feature_change(feature)
            if self.language == "zh":
                self.set_status(f"成功增加 +${feature.add_amount:,} 金币！(累计增加: +${feature.total_added:,})")
            else:
                self.set_status(f"+${feature.add_amount:,} money added! (Total added: +${feature.total_added:,})")
            return True
        return False

    # ---------------------------------------------------------
    # Resource Teardown & Lifecycle
    # ---------------------------------------------------------

    def _cleanup_game_resources(self) -> None:
        """Restores memory patches and frees game handles without unhooking global hotkeys."""
        self._remove_feature_hotkeys()

        for f in self.features:
            try:
                f.disable()
            except Exception:
                pass

        if self.patcher:
            try:
                self.patcher.restore_all()
            except Exception:
                pass
            self.patcher = None

        if self.mono:
            try:
                self.mono.close()
            except Exception:
                pass
            self.mono = None

        if self.pm:
            try:
                self.pm.close_process()
            except Exception:
                pass
            self.pm = None

        self.features = get_default_features()
        for f in self.features:
            self._notify_feature_change(f)
        self._notify_attach(False, 0, 0)

    def _cleanup(self) -> None:
        """Restores all memory patches, frees handles, and unhooks all hotkeys."""
        self._cleanup_game_resources()
        self._remove_control_hotkeys()

    def stop(self) -> None:
        """Stops the trainer loop and notifies exit callbacks."""
        self.is_running = False
        self.set_status(tr("shutting_down", self.language))
        for cb in list(self._exit_callbacks):
            try:
                cb()
            except Exception as e:
                logger.debug(f"Error in exit callback: {e}")

    # ---------------------------------------------------------
    # Polling Step & Multi-Thread Execution
    # ---------------------------------------------------------

    @staticmethod
    def is_admin() -> bool:
        """Checks if the current process is running with Administrator privileges on Windows."""
        if sys.platform == "win32":
            try:
                import ctypes
                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            except Exception:
                return False
        return True

    def poll_step(self) -> None:
        """Single tick of process connection checking and feature memory updates."""
        if self.pm:
            try:
                if self.mono and getattr(self.mono, "module_base", None):
                    _ = self.pm.read_int(self.mono.module_base)
                else:
                    self.set_status(tr("game_closed", self.language))
                    self._cleanup_game_resources()
            except Exception:
                self.set_status(tr("game_closed", self.language))
                self._cleanup_game_resources()

        if not self.pm:
            self.attach()

        if self.pm and self.features:
            for f in self.features:
                if f.is_enabled:
                    try:
                        f.update()
                    except Exception:
                        pass

    def start_background(self, poll_interval: float = 0.25) -> threading.Thread:
        """Starts the monitoring loop in a background daemon thread."""
        if self.is_running and self._bg_thread and self._bg_thread.is_alive():
            return self._bg_thread

        self.is_running = True
        self._bg_thread = threading.Thread(
            target=self._background_loop,
            args=(poll_interval,),
            daemon=True,
            name="TrainerWorkerThread",
        )
        self._bg_thread.start()
        return self._bg_thread

    def _background_loop(self, poll_interval: float) -> None:
        try:
            while self.is_running:
                try:
                    self.poll_step()
                except Exception as e:
                    logger.debug(f"Unhandled error in poll_step: {e}")
                time.sleep(poll_interval)
        finally:
            self._cleanup()

    def join(self, timeout: Optional[float] = None) -> None:
        """Waits for background thread to exit."""
        if self._bg_thread:
            self._bg_thread.join(timeout=timeout)

    def run(self) -> None:
        """Runs the live terminal trainer loop with guaranteed cleanup."""
        self.is_running = True
        self.console.clear()

        try:
            with Live(console=self.console, refresh_per_second=4, screen=False) as live:
                while self.is_running:
                    self.poll_step()

                    is_attached = self.pm is not None and self.mono is not None
                    pid = self.pm.process_id if self.pm else 0
                    domain = self.mono.root_domain if (self.mono and self.mono.root_domain) else 0

                    dashboard = self.ui.generate_dashboard(
                        is_attached=is_attached,
                        process_name=self.process_name,
                        pid=pid,
                        mono_domain=domain,
                        features=self.features,
                        status_message=self.status_message,
                        language=self.language,
                    )
                    live.update(dashboard)
                    time.sleep(0.25)
        finally:
            self._cleanup()
            exit_text = tr("stopped_clean", self.language)
            self.console.print(f"\n[bold green]{exit_text}[/bold green]")

