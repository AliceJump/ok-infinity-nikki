import time

import win32gui

from src.interaction.Mouse import user32


def move_keys(hwnd, keys, duration):
    """
    Simulates pressing and holding specified keys for a duration, then releases them.
    模拟按下并保持指定键位(w,a,s,d)组合一段时间，然后释放按键。

    Parameters 参数:
    keys – str or list[str]. Keys to press. 需要按下的键位，例如 "w" 或 ["w", "a"]。
    duration – float. Duration to hold the keys in seconds. 按键持续的时间（秒）。
    """

    try:
        current_hwnd = win32gui.GetForegroundWindow()
        # 只有不在前台才激活
        if current_hwnd != hwnd:
            win32gui.ShowWindow(hwnd, 5)  # 5表示SW_SHOW，显示并激活窗口
            win32gui.SetForegroundWindow(hwnd)  # 将窗口设置为前台窗口
            time.sleep(0.5)  # 等待窗口激活

    except Exception as e:
        print("窗口激活失败:", e)  # 捕获并打印窗口激活过程中的异常
    key_map = {
        "w": 0x57,
        "a": 0x41,
        "s": 0x53,
        "d": 0x44,
    }

    KEYEVENTF_KEYUP = 0x0002

    # 全部按下
    for k in keys:
        user32.keybd_event(key_map[k.lower()], 0, 0, 0)

    time.sleep(duration)

    # 全部抬起
    for k in keys:
        user32.keybd_event(key_map[k.lower()], 0, KEYEVENTF_KEYUP, 0)
