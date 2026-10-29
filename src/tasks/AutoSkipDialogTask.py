"""剧情跳过：选项菜单按默认首项选中，用 S 导航、F 确认。"""

from dataclasses import dataclass

from ok import Box, TriggerTask

from src.data.FeatureList import FeatureList as fL
from src.tasks.BaseINTask import BaseINTask
from src.tasks.dialogue_choices import ChoiceDecision, ChoiceMemory, text_band_lengths


@dataclass
class ChoiceAttempt:
    """Track one visible menu across trigger ticks; never retry a failed attempt."""

    decision: ChoiceDecision
    sent_s: int = 0
    phase: str = "navigate"
    checks: int = 0
    absent_frames: int = 0


class AutoSkipDialogTask(BaseINTask, TriggerTask):
    CONFIRM_CHECKS = 5
    ABSENT_FRAMES = 2

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

    def _menu_lengths(self, frame):
        height, width = frame.shape[:2]
        icons = sorted(self.find_feature(
            fL.chat_icon, threshold=0.9, frame=frame,
            box=Box(width * 0.5, height * 0.25, width * 0.48, height * 0.6),
        ), key=lambda box: (box.y, box.x))
        return text_band_lengths(frame, icons) if icons else None

    @staticmethod
    def _same_lengths(expected, actual):
        return (actual is not None and len(expected) == len(actual)
                and all(abs(a - b) <= max(0.3, 0.05 * max(a, b))
                        for a, b in zip(expected, actual)))

    def _stop_choice(self, reason, frame=None):
        """Fail closed until the current menu has really disappeared."""
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

    def _run_choice(self, frame):
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

        if not self._menu_visible(frame) or not self._same_lengths(
                attempt.decision.lengths, self._menu_lengths(frame)):
            self._stop_choice("导航过程中菜单消失或选项内容变化", frame)
            return

        if attempt.sent_s < attempt.decision.index:
            key = "s"
            step = attempt.sent_s + 1
        else:
            key = "f"
            step = attempt.sent_s
        self.screenshot(name=f"dialog_ws_before_{key}_{step}", frame=frame)
        if self.send_key(key, down_time=0.08, after_sleep=0.12) is False:
            self._stop_choice(f"发送 {key.upper()} 失败", frame)
            return

        # Capture after *every* key, and validate again on the next trigger tick.
        updated = self.next_frame()
        if updated is None:
            self._stop_choice(f"发送 {key.upper()} 后未获取到新截图")
            return
        self.screenshot(name=f"dialog_ws_after_{key}_{step}", frame=updated)
        if key == "s":
            if not self._menu_visible(updated) or not self._same_lengths(
                    attempt.decision.lengths, self._menu_lengths(updated)):
                self._stop_choice("按下 S 后菜单消失或选项内容变化", updated)
                return
            attempt.sent_s += 1
        else:
            attempt.phase = "confirm"
            self._observe_confirmation(updated)

    def run(self):
        """Send at most one W/S/F input per trigger tick; never click choice icons."""
        frame = self.frame
        if frame is None:
            if self._choice_attempt is not None and self._choice_attempt.phase != "blocked":
                self._stop_choice("无法获取当前截图")
            return False

        if self._choice_attempt is not None:
            self._run_choice(frame)
            return False

        if self._menu_visible(frame):
            lengths = self._menu_lengths(frame)
            if lengths is not None:
                decision = self._choice_memory.prepare(lengths)
                if decision is not None:
                    # On *each fresh menu*, assume keyboard focus starts on option 0.
                    self._choice_attempt = ChoiceAttempt(decision)
                    self._run_choice(frame)
            return False

        self._choice_memory.hide()
        if self.find_one(fL.dialog_icon, threshold=0.9, frame=frame):
            if self.find_one(fL.skip_f, threshold=0.9, frame=frame):
                self.send_key("f", after_sleep=0.1)
        return False
