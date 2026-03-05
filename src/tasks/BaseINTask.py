import random
import re
import time
import cv2
import imagehash
import numpy as np
import pyautogui

from functools import partial
from typing import List
from PIL import Image
from ok import BaseTask, Box
from skimage.metrics import structural_similarity as ssim

from src.data.FeatureList import FeatureList
from src.image.frame_processs import isolate_by_hsv_ranges
from src.interaction.Key import move_keys
from src.interaction.Mouse import active_and_send_mouse_delta, move_to_target_once, run_at_window_pos
from src.interaction.ScreenPosition import ScreenPosition

TOLERANCE = 50

class BaseINTask(BaseTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.box=ScreenPosition(self)
    def move_keys(self, keys, duration):
        """向当前窗口发送按键移动指令
        
        Args:
            keys: 按键或按键列表，例如 "w" 或 ["w", "a"]
            duration: 按键持续时间（秒），例如 0.5
        """
        move_keys(self.hwnd.hwnd, keys, duration)

    def move_to_target_once(self, ocr_obj, max_step=100, min_step=20, slow_radius=200):
        """根据目标位置执行一次视角/鼠标对准
        
        Args:
            ocr_obj: OCR识别到的目标对象
            max_step: 最大移动步长
            min_step: 最小移动步长
            slow_radius: 减速半径
        """
        return move_to_target_once(self.hwnd.hwnd, ocr_obj, self.screen_center, max_step=max_step, min_step=min_step, slow_radius=slow_radius)

    def active_and_send_mouse_delta(self, dx=1, dy=1, activate=True, only_activate=False, delay=0.02, steps=3):
        """激活窗口并发送鼠标位移
        
        Args:
            dx: 水平位移
            dy: 垂直位移
            activate: 是否先激活窗口
            only_activate: 是否仅激活不移动
            delay: 每步延迟
            steps: 分步次数
        """
        return active_and_send_mouse_delta(self.hwnd.hwnd, dx, dy, activate, only_activate, delay, steps)

    def isolate_by_hsv_ranges(self, frame, ranges, invert=True, kernel_size=2):
        """按HSV范围提取颜色区域
        
        Args:
            frame: 输入图像（BGR）
            ranges: HSV区间列表
            invert: 是否反转结果
            kernel_size: 形态学核大小
        """
        return isolate_by_hsv_ranges(frame, ranges, invert, kernel_size)

    def make_hsv_isolator(self, ranges):
        """生成固定HSV范围的图像处理函数
        
        Args:
            ranges: HSV区间列表
        """
        return partial(self.isolate_by_hsv_ranges, ranges=ranges)

    def click_with_alt(self, x: int| float | Box | List[Box] = -1, y: int|float = -1, move_back: bool = False,
                       name: str | None = None, interval: int = -1, move: bool = True, down_time: float = 0.01,
                       after_sleep: float = 0, key: str = 'left'):
        """按住Alt并点击指定位置
        
        Args:
            x: 点击X坐标（0-1为比例，或像素值）
            y: 点击Y坐标
            move_back: 点击后是否移回原位
            name: 点击目标名称
            interval: 多次点击间隔
            move: 是否移动鼠标到目标
            down_time: 鼠标按下时间
            after_sleep: 点击后等待时间
            key: 鼠标按键('left'/'right'/'middle')
        """
        self.send_key_down("alt")
        self.sleep(0.5)
        self.click(x=x, y=y, move_back=move_back, name=name, interval=interval, move=move, down_time=down_time,
                   after_sleep=after_sleep, key=key)
        self.send_key_up("alt")

    def scroll(self, x: int, y: int, count: int) -> None:
        """在指定像素坐标滚动鼠标滚轮
        
        Args:
            x: 滚动位置X坐标（像素）
            y: 滚动位置Y坐标（像素）
            count: 滚动次数（正数向上，负数向下）
        """
        run_at_window_pos(self.hwnd.hwnd, super().scroll, x, y, 0.5, x, y, count)

    def scroll_relative(self, x: float, y: float, count: int) -> None:
        """在指定比例坐标滚动鼠标滚轮
        
        Args:
            x: 滚动位置X坐标（0-1的比例）
            y: 滚动位置Y坐标（0-1的比例）
            count: 滚动次数
        """
        run_at_window_pos(self.hwnd.hwnd, super().scroll_relative, int(x * self.width), int(y * self.height), 0.5, x, y,
                          count)

    def screen_center(self):
        """获取屏幕中心坐标
        
        Returns:
            tuple: (中心X, 中心Y)
        """
        return int(self.width / 2), int(self.height / 2)

    def wait_ui_stable(
            self,
            method="phash",
            threshold=5,
            stable_time=0.5,
            max_wait=5,
            refresh_interval=0.2,
    ):
        """等待界面稳定（UI停止变化）再执行操作
        
        Args:
            method: 比较两帧相似度方法("phash"/"dhash"/"pixel"/"ssim")
            threshold: 方法对应的阈值
                - phash/dhash: 汉明距离，默认5
                - pixel: 平均像素差，默认5
                - ssim: 相似度(0~1)，默认0.98
            stable_time: 连续稳定时间（秒），默认0.5秒
            max_wait: 最大等待时间（秒），默认5秒
            refresh_interval: 每次获取新帧的间隔（秒），默认0.2秒
        
        Returns:
            bool: True表示UI已稳定，False表示超时仍未稳定
        """
        start_time = time.time()
        last_frame = self.next_frame()  # 获取初始帧
        stable_start = None

        while True:
            current_frame = self.next_frame()  # 获取最新帧

            # 1️⃣ phash / dhash 相似度
            if method in ("phash", "dhash"):
                img1 = Image.fromarray(last_frame)
                img2 = Image.fromarray(current_frame)
                h1 = (
                    imagehash.phash(img1)
                    if method == "phash"
                    else imagehash.dhash(img1)
                )
                h2 = (
                    imagehash.phash(img2)
                    if method == "phash"
                    else imagehash.dhash(img2)
                )
                distance = h1 - h2
                is_stable = distance <= threshold

            # 2️⃣ 像素差法
            elif method == "pixel":
                if last_frame.shape != current_frame.shape:
                    is_stable = False
                else:
                    diff = cv2.absdiff(last_frame, current_frame)
                    is_stable = np.mean(diff) <= threshold

            # 3️⃣ 结构相似度 SSIM
            elif method == "ssim":
                last_gray = cv2.cvtColor(last_frame, cv2.COLOR_BGR2GRAY)
                current_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
                if last_gray.shape != current_gray.shape:
                    is_stable = False
                else:
                    score, _ = ssim(last_gray, current_gray, full=True)
                    is_stable = score >= threshold

            else:
                raise ValueError(f"Unknown method {method}")

            # 处理连续稳定时间
            if is_stable:
                if stable_start is None:
                    stable_start = time.time()
                elif time.time() - stable_start >= stable_time:
                    return True  # 连续稳定达到要求
            else:
                stable_start = None  # 重置计时

            # 超时退出
            if time.time() - start_time > max_wait:
                return False

            last_frame = current_frame
            time.sleep(refresh_interval)

    def align_ocr_or_find_target_to_center(
            self,
            ocr_match_or_feature_name_list,
            only_x=False,
            only_y=False,
            box=None,
            threshold=0.8,
            max_time=50,
            ocr=True,
            raise_if_fail=True,
            is_num=False,
            need_scroll=False,
            max_step=100,
            min_step=20,
            slow_radius=200,
            once_time=0.5,
            tolerance=TOLERANCE,
            ocr_frame_processor_list=None
    ):
        """将OCR识别或图像特征检测的目标对准屏幕中心（自动移动视角/鼠标）
        
        Args:
            ocr_match_or_feature_name_list: OCR匹配模式(str/List)或特征名称(str/List)
            only_x: True时仅对齐X轴（左右），Y轴保持不变
            only_y: True时仅对齐Y轴（上下），X轴保持不变
            box: 搜索区域框(Box)，None表示全屏。用于限制OCR/特征检测范围
            threshold: 图像特征匹配阈值(0-1)，默认0.8，仅在ocr=False时使用
            max_time: 最大尝试循环次数，默认50次
            ocr: True使用OCR模式识别，False使用图像特征匹配模式
            raise_if_fail: True时对中失败抛出异常，False时返回False
            is_num: 数字型目标Y坐标微调（用于识别数字时的位置校正）
            need_scroll: True时在对中过程中自动滚动（通常用于列表)
            max_step: 单次移动最大步长(像素)
            min_step: 单次移动最小步长(像素)
            slow_radius: 接近目标时减速的半径范围(像素)
            once_time: 每次循环最小耗时(秒)，保证操作频率
            tolerance: 目标中心与屏幕中心的容忍偏差(像素)，默认50，偏差在范围内判定成功
            ocr_frame_processor_list: OCR帧处理函数列表(可用于色彩隔离等预处理)
        
        Returns:
            bool: 成功对中返回True，失败返回False(当raise_if_fail=False时)
        
        Raises:
            Exception: 对中失败且raise_if_fail=True时抛出异常
        """
        if box:
            feature_box = box
        else:
            feature_box = self.box_of_screen(
                (1920 - 1550) / 1920,
                150 / 1080,
                1550 / 1920,
                (1080 - 150) / 1080,
            )
        last_target = None
        last_target_fail_count = 0
        success = False
        random_move_count = 0
        move_count = 0
        scroll_bool = False
        sum_dx = 0
        sum_dy = 0
        for i in range(max_time):
            start_action_time = time.time()
            if ocr:
                # 使用OCR模式识别目标，设置超时时间为2秒，并启用日志记录
                start_time = time.time()
                result = None
                while time.time() - start_time < 1:
                    frame = self.next_frame()
                    if not isinstance(ocr_frame_processor_list, list):
                        ocr_frame_processor_list = [ocr_frame_processor_list]
                    for ocr_frame_processor in ocr_frame_processor_list:
                        result = self.ocr(
                            match=ocr_match_or_feature_name_list,
                            box=box,
                            frame=frame,
                            log=True,
                            frame_processor=ocr_frame_processor,
                        )
                        if result:
                            break
                    if result:
                        break
                    time.sleep(0.1)
            else:
                if isinstance(ocr_match_or_feature_name_list, str):
                    ocr_match_or_feature_name_list = [ocr_match_or_feature_name_list]
                start_time = time.time()
                result = None
                while True:
                    if time.time() - start_time >= 1:
                        break
                    self.next_frame()
                    for feature_name in ocr_match_or_feature_name_list:
                        if time.time() - start_time >= 1:
                            break

                        result = self.find_feature(
                            feature_name=feature_name,
                            threshold=threshold,
                            box=feature_box,
                        )
                        if result:
                            break
                    if result:
                        break
                    self.sleep(0.1)
            if result:
                success = True
                random_move_count = 0
                move_count = 0
                # OCR 成功
                if isinstance(result, list):
                    result = result[0]
                if is_num:
                    result.y = result.y - int(self.height * ((525 - 486) / 1080))
                if only_y:
                    result.x = self.width // 2 - result.width // 2
                if only_x:
                    result.y = self.height // 2 - result.height // 2
                target_center = (
                    result.x + result.width // 2,
                    result.y + result.height // 2,
                )
                screen_center_pos = self.screen_center()
                last_target = result
                last_target_fail_count = 0
                # 计算偏移量

                dx = target_center[0] - screen_center_pos[0]

                dy = target_center[1] - screen_center_pos[1]

                # 如果目标在容忍范围内
                if abs(dx) <= tolerance and abs(dy) <= tolerance:
                    return True
                else:
                    dx, dy = self.move_to_target_once(result, max_step=max_step, min_step=min_step,
                                                      slow_radius=slow_radius)
                    sum_dx += dx
                    sum_dy += dy

            else:
                # 每次 OCR 失败，直接随机移动
                max_offset = 60  # 最大随机偏移
                if last_target:
                    decay = 0.9 ** last_target_fail_count
                    # 计算目标中心到屏幕中心的偏移

                    screen_center_x, screen_center_y = self.screen_center()
                    offset_x = int((screen_center_x - last_target.x) * decay)
                    offset_y = int((screen_center_y - last_target.y) * decay)
                    offset_width = int(last_target.width / 2 * decay)
                    offset_height = int(last_target.height / 2 * decay)
                    # 直接修改 last_target 坐标
                    last_target.x = screen_center_x - offset_x
                    last_target.y = screen_center_y - offset_y
                    last_target.width = offset_width
                    last_target.height = offset_height
                    dx, dy = self.move_to_target_once(last_target)
                    sum_dx += dx
                    sum_dy += dy
                    last_target_fail_count += 1
                    random_move_count = 0
                    move_count += 1
                    if move_count >= 10:
                        last_target = None
                        move_count = 0
                else:
                    if not success:
                        max_offset = self.width // 4
                    last_target = None
                    last_target_fail_count = 0
                    dx = random.randint(-max_offset, max_offset)
                    if not success:
                        dy = 0
                    else:
                        dy = random.randint(-max_offset, max_offset)

                    # 移动鼠标
                    active_and_send_mouse_delta(
                        self.hwnd.hwnd,
                        dx,
                        dy,
                        activate=True,
                        delay=0.1,
                    )
                    sum_dx += dx
                    sum_dy += dy
                    move_count = 0
                    random_move_count += 1
                    if random_move_count >= 10:
                        success = False
                        random_move_count = 0

            if time.time() - start_action_time < once_time:
                self.sleep(once_time - (time.time() - start_action_time))  # OCR 成功后不需要处理，下一次失败仍然随机
            if not scroll_bool and need_scroll:
                scroll_bool = True
                # cx = int(self.width * 0.5)
                # cy = int(self.height * 0.5)
                for _ in range(6):
                    # self.scroll(cx, cy, 8)
                    pyautogui.scroll(80)
                    self.sleep(1)
        if raise_if_fail:
            raise Exception("对中失败")
        else:
            return False
    def operate(self, func):
        self.executor.interaction.operate(func, block=True)

    def do_mouse_down(self, key):
        self.executor.interaction.do_mouse_down(key=key)

    def do_mouse_up(self, key):
        self.executor.interaction.do_mouse_up(key=key)

    def do_send_key_down(self, key):
        self.executor.interaction.do_send_key_down(key)

    def do_send_key_up(self, key):
        self.executor.interaction.do_send_key_up(key)
