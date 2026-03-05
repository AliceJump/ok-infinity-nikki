# ===== device layer =====
import ctypes
import time
import win32gui

user32 = ctypes.windll.user32
MOUSEEVENTF_MOVE = 0x0001


# ===== math layer =====
import math


def calc_direction_step(
    from_pos, to_pos, max_step=100, min_step=20, slow_radius=200, deadzone=4
):
    dx_raw = to_pos[0] - from_pos[0]
    dy_raw = to_pos[1] - from_pos[1]

    dist = math.hypot(dx_raw, dy_raw)

    if dist < deadzone:
        return 0, 0

    if dist > slow_radius:
        step = max_step
    else:
        step = max(min_step, int(max_step * (dist / slow_radius)))

    dx = round(dx_raw / dist * step)
    dy = round(dy_raw / dist * step)

    return dx, dy


# ===== device control =====
def active_and_send_mouse_delta(
    hwnd, dx=1, dy=1, activate=True, only_activate=False, delay=0.02, steps=3
):
    if only_activate:
        activate = True

    if activate:
        try:
            current_hwnd = win32gui.GetForegroundWindow()
            if current_hwnd != hwnd:
                win32gui.ShowWindow(hwnd, 5)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(delay)
        except Exception as e:
            print("窗口激活失败:", e)

    if not only_activate:
        for _ in range(steps):
            step_dx = round(dx / steps)
            step_dy = round(dy / steps)
            user32.mouse_event(MOUSEEVENTF_MOVE, step_dx, step_dy, 0, 0)
            time.sleep(delay)


# ===== control =====
def move_to_target_once(hwnd, ocr_obj, screen_center_func,max_step=100,min_step=20,slow_radius=200):
    if ocr_obj is None:
        return None

    target_center = (
        ocr_obj.x + ocr_obj.width // 2,
        ocr_obj.y + ocr_obj.height // 2,
    )

    center_pos = screen_center_func()

    dx, dy = calc_direction_step(center_pos, target_center,max_step= max_step,min_step= min_step,slow_radius= slow_radius)

    if dx != 0 or dy != 0:
        active_and_send_mouse_delta(hwnd, dx, dy)
    return dx, dy


def run_at_window_pos(hwnd, func, x, y, sleep_time=0.5, *args, **kwargs):
    """
    临时移动鼠标到窗口客户区 (x,y)，执行函数后恢复原位置
    """

    original_pos = user32.GetCursorPos
    pt = ctypes.wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    original = (pt.x, pt.y)

    try:
        screen_x, screen_y = win32gui.ClientToScreen(hwnd, (x, y))
        user32.SetCursorPos(screen_x, screen_y)
        time.sleep(sleep_time)
        func(*args, **kwargs)
        time.sleep(sleep_time)
    finally:
        user32.SetCursorPos(original[0], original[1])
