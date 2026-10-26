from src.tasks.BaseINTask import BaseINTask
from src.data.FeatureList import FeatureList as fL
class AutoSkipDialogTask(BaseINTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "自动跳过对话任务"
        self.description = "这是一个自动跳过对话的任务"

    def run(self):
        scroll_bool=False
        while True:
            if self.find_one(fL.dialog_icon, threshold=0.9):
                # 使用各模板自己的缩放坐标；固定 16:9 搜索框会漏掉 3392×2400 的选项提示。
                if self.find_one(fL.skip_f,threshold=0.9):
                    self.send_key("f", after_sleep=0.1)
                if self.find_one(fL.skip_choose, threshold=0.9):
                    if not scroll_bool:
                        self.scroll_relative(0.5,0.5,-1)
                        scroll_bool=True
                    else:
                        scroll_bool=False
                    self.send_key("f", after_sleep=0.2)
            if self.find_one(fL.skip_b, threshold=0.9):
                self.send_key("f", after_sleep=0.1)
            if self.find_one(fL.task_icon, threshold=0.9):
                self.send_key("f", after_sleep=0.1)
            self.sleep(0.1)
            self.next_frame()
