"""剧情跳过：由 TriggerTask 调度，每次只检测一帧、最多执行一个动作。"""

from ok import Box, TriggerTask

from src.data.FeatureList import FeatureList as fL
from src.tasks.BaseINTask import BaseINTask
from src.tasks.dialogue_choices import ChoiceMemory, text_band_lengths


class AutoSkipDialogTask(BaseINTask, TriggerTask):
    def __init__(self, *args, **kwargs):
        """Configure periodic detection and independent choice fingerprints."""
        super().__init__(*args, **kwargs)
        self.name = "自动跳过对话任务"
        self.description = "启用后自动检测并跳过剧情对话"
        self.trigger_interval = 0.3
        self._choice_memory = ChoiceMemory()

    def run(self):
        """Inspect dialogue hints once and return after at most one input action."""
        frame = self.frame
        if frame is None:
            return False

        if self.find_one(fL.dialog_icon, threshold=0.9, frame=frame):
            height, width = frame.shape[:2]
            if self.find_one(fL.skip_choose, threshold=0.9, frame=frame):
                options = sorted(self.find_feature(
                    fL.chat_icon, threshold=0.9, frame=frame,
                    box=Box(width * 0.5, height * 0.25, width * 0.48, height * 0.6),
                ), key=lambda box: (box.y, box.x))
                if options:
                    lengths = text_band_lengths(frame, options)
                    if lengths is not None:
                        decision = self._choice_memory.prepare(lengths)
                        if decision is not None:
                            if self.click(options[decision.index], after_sleep=0.2) is not False:
                                self._choice_memory.commit(decision)
                return False

            self._choice_memory.hide()
            if self.find_one(fL.skip_f, threshold=0.9, frame=frame):
                self.send_key("f", after_sleep=0.1)
                return False

        self._choice_memory.hide()

        # ok-script 用 run() == True 作为特殊重启信号，
        # 返回 False 使执行器正常清理本轮状态并继续轮询。
        return False
