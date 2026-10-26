from enum import Enum


class FeatureList(str, Enum):
    chat_icon = 'chat_icon'
    dialog_icon = 'dialog_icon'
    skip_choose = 'skip_choose'
    skip_f = 'skip_f'
