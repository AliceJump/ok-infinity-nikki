"""剧情跳过：由 TriggerTask 调度，每次只检测一帧、最多执行一个动作。"""

from ok import TriggerTask

from src.data.FeatureList import FeatureList as fL
from src.tasks.BaseINTask import BaseINTask


class AutoSkipDialogTask(BaseINTask, TriggerTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "自动跳过对话任务"
        self.description = "启用后自动检测并跳过剧情对话"
        self.trigger_interval = 0.3
        self._scroll_on_next_choice = True

    def run(self):
        # 每次触发只检测当前帧。不要使用 while True，以免阻塞其他任务。
        if self.find_one(fL.dialog_icon, threshold=0.9):
            dialog_box = self.box_of_screen(
                1460 / 1920, 1000 / 1080, 1810 / 1920, 1040 / 1080
            )
            if self.find_one(fL.skip_f, threshold=0.9, box=dialog_box):
                self._scroll_on_next_choice = True
                self.send_key("f", after_sleep=0.1)
                return False

            if self.find_one(fL.skip_choose, threshold=0.9, box=dialog_box):
                if self._scroll_on_next_choice:
                    self.scroll_relative(0.5, 0.5, -1)
                self._scroll_on_next_choice = not self._scroll_on_next_choice
                self.send_key("f", after_sleep=0.2)
                return False

        # 对话选择消失后，下次出现时重新从滚动开始。
        self._scroll_on_next_choice = True
        if self.find_one(fL.skip_b, threshold=0.9):
            self.send_key("f", after_sleep=0.1)
            return False

        if self.find_one(fL.task_icon, threshold=0.9):
            self.send_key("f", after_sleep=0.1)

        # ok-script 用 run() == True 作为特殊重启信号，
        # 返回 False 使执行器正常清理本轮状态并继续轮询。
        return False
