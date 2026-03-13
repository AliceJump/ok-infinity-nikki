from enum import Enum


class FeatureList(str, Enum):
    dialog_icon = 'dialog_icon'
    skip_b = 'skip_b'
    skip_choose = 'skip_choose'
    skip_f = 'skip_f'
    task_icon = 'task_icon'
