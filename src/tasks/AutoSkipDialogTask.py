"""剧情跳过：跳过暗色已选选项，用 W/S 调整焦点后 F 确认。"""

from dataclasses import dataclass

from ok import Box, TriggerTask

from src.data.FeatureList import FeatureList as fL
from src.tasks.BaseINTask import BaseINTask
from src.tasks.dialogue_choices import (
    ChoiceDecision, ChoiceMemory, dimmed_text_rows, highlighted_choice_index,
    text_band_lengths,
)


@dataclass
class ChoiceAttempt:
    """Track one visible menu across trigger ticks; never retry a failed attempt."""

    decision: ChoiceDecision
    moves: int = 0
    phase: str = "navigate"
    checks: int = 0
    absent_frames: int = 0
    pending_focus: int | None = None
    pending_origin: int | None = None
    move_checks: int = 0


class AutoSkipDialogTask(BaseINTask, TriggerTask):
    CONFIRM_CHECKS = 5
    ABSENT_FRAMES = 2
    MOVE_CONFIRM_CHECKS = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "自动跳过对话任务"
        self.description = "启用后自动检测并跳过剧情对话"
        self.trigger_interval = 0.3
        self._choice_memory = ChoiceMemory()
        self._choice_attempt = None

    def _menu_visible(self, frame):
        """Require both dialogue and navigation hints for a choice menu."""
        return (frame is not None
                and bool(self.find_one(fL.dialog_icon, threshold=0.9, frame=frame))
                and bool(self.find_one(fL.skip_choose, threshold=0.9, frame=frame)))

    def _menu_state(self, frame):
        """Read text fingerprint, visited status, and highlighted row."""
        height, width = frame.shape[:2]
        icons = sorted(self.find_feature(
            fL.chat_icon, threshold=0.9, frame=frame,
            box=Box(width * 0.5, height * 0.25, width * 0.48, height * 0.6),
        ), key=lambda box: (box.y, box.x))
        if not icons:
            return None
        lengths = text_band_lengths(frame, icons)
        dimmed = dimmed_text_rows(frame, icons)
        if lengths is None or dimmed is None or len(dimmed) != len(lengths):
            return None
        return lengths, dimmed, highlighted_choice_index(frame, icons)

    @staticmethod
    def _same_lengths(expected, actual):
        """Tolerate small antialiasing or highlighting differences."""
        return (actual is not None and len(expected) == len(actual)
                and all(abs(a - b) <= max(0.3, 0.05 * max(a, b))
                        for a, b in zip(expected, actual)))

    @staticmethod
    def _choose_unvisited(decision, dimmed):
        """Choose a bright row starting from the remembered menu index."""
        for offset in range(len(dimmed)):
            index = (decision.index + offset) % len(dimmed)
            if not dimmed[index]:
                decision.index = index
                return True
        return False

    def _stop_choice(self, reason, frame=None):
        """Block this menu when a key or its visual effect is uncertain."""
        self._choice_attempt.phase = "blocked"
        self._choice_attempt.absent_frames = 0
        self.log_warning(f"剧情选项输入已停止：{reason}；等待当前菜单消失后才可重试")
        if frame is not None:
            self.screenshot(name="dialog_ws_failed", frame=frame)

    def _observe_confirmation(self, frame):
        """Confirm a completed choice by two consecutive frames without W/S."""
        attempt = self._choice_attempt
        if self._menu_visible(frame):
            attempt.absent_frames = 0
            attempt.checks += 1
            if attempt.checks >= self.CONFIRM_CHECKS:
                self._stop_choice("按下 F 后选项菜单仍然存在", frame)
            return
        attempt.absent_frames += 1
        if attempt.absent_frames >= self.ABSENT_FRAMES:
            self.screenshot(name="dialog_ws_confirmed", frame=frame)
            self._choice_memory.commit(attempt.decision)
            self._choice_memory.hide()
            self._choice_attempt = None

    def _verify_navigation(self, frame):
        """Wait for a focus update before treating W/S as an input failure.

        Never send a second movement while one is pending. When focus never
        moved but the currently highlighted row is bright, confirming that row
        is safer than permanently locking a usable dialogue.
        """
        attempt = self._choice_attempt
        state = self._menu_state(frame) if self._menu_visible(frame) else None
        if state is not None and self._same_lengths(attempt.decision.lengths, state[0]):
            _, dimmed, focus = state
            if focus == attempt.pending_focus:
                attempt.pending_focus = None
                attempt.pending_origin = None
                attempt.phase = "navigate"
                return
        else:
            dimmed, focus = None, None

        attempt.move_checks += 1
        if attempt.move_checks < self.MOVE_CONFIRM_CHECKS:
            return
        if (dimmed is not None and focus == attempt.pending_origin
                and focus is not None and not dimmed[focus]):
            attempt.decision.index = focus
            attempt.phase = "navigate"
            attempt.pending_focus = None
            attempt.pending_origin = None
            self.log_warning("W/S 未见高亮移动，改为确认当前已高亮的亮色选项")
            return
        self._stop_choice(
            f"W/S 后高亮无法确认（原行={attempt.pending_origin}，"
            f"期望行={attempt.pending_focus}，观察行={focus}）", frame)

    def _run_choice(self, frame):
        """Validate each W/S movement against the actual highlighted row."""
        attempt = self._choice_attempt
        if attempt.phase == "blocked":
            if self._menu_visible(frame):
                attempt.absent_frames = 0
            else:
                attempt.absent_frames += 1
                if attempt.absent_frames >= self.ABSENT_FRAMES:
                    self._choice_attempt = None
                    self._choice_memory.hide()
            return
        if attempt.phase == "confirm":
            self._observe_confirmation(frame)
            return
        if attempt.phase == "verify_move":
            self._verify_navigation(frame)
            return
        if not self._menu_visible(frame):
            self._stop_choice("导航过程中菜单消失", frame)
            return
        state = self._menu_state(frame)
        if state is None or not self._same_lengths(attempt.decision.lengths, state[0]):
            self._stop_choice("导航过程中选项内容无法确认", frame)
            return
        lengths, dimmed, focus = state
        target = attempt.decision.index
        if dimmed[target]:
            self._stop_choice("目标选项已经变暗，禁止继续选择", frame)
            return
        if focus is None:
            # Fall back to first-item assumption only before moving focus.
            if attempt.moves:
                self._stop_choice("无法确认 W/S 后的当前高亮行", frame)
                return
            focus = 0
        key = "s" if focus < target else "w" if focus > target else "f"
        step = attempt.moves
        self.screenshot(name=f"dialog_ws_before_{key}_{step}", frame=frame)
        if self.send_key(key, down_time=0.08, after_sleep=0.12) is False:
            self._stop_choice(f"发送 {key.upper()} 失败", frame)
            return
        updated = self.next_frame()
        if updated is None:
            self._stop_choice(f"发送 {key.upper()} 后未获取到新截图")
            return
        self.screenshot(name=f"dialog_ws_after_{key}_{step}", frame=updated)
        if key == "f":
            attempt.phase = "confirm"
            self._observe_confirmation(updated)
            return
        attempt.moves += 1
        attempt.pending_origin = focus
        attempt.pending_focus = focus + (1 if key == "s" else -1)
        attempt.move_checks = 0
        attempt.phase = "verify_move"
        self._verify_navigation(updated)

    def run(self):
        """Choose bright unvisited options, at most one input per trigger."""
        frame = self.frame
        if frame is None:
            if self._choice_attempt is not None and self._choice_attempt.phase != "blocked":
                self._stop_choice("无法获取当前截图")
            return False
        if self._choice_attempt is not None:
            self._run_choice(frame)
            return False
        if self._menu_visible(frame):
            state = self._menu_state(frame)
            if state is not None:
                lengths, dimmed, focus = state
                decision = self._choice_memory.prepare(lengths)
                if decision is not None:
                    self._choice_attempt = ChoiceAttempt(decision)
                    if self._choose_unvisited(decision, dimmed):
                        self._run_choice(frame)
                    else:
                        self._stop_choice("所有对话选项文字都已变暗", frame)
            return False
        self._choice_memory.hide()
        if self.find_one(fL.dialog_icon, threshold=0.9, frame=frame):
            if self.find_one(fL.skip_f, threshold=0.9, frame=frame):
                self.send_key("f", after_sleep=0.1)
        return False
