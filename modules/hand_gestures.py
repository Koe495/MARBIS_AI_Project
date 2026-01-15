import cv2
import pyautogui
import numpy as np
import math
import time
import ctypes

# ======================================================
# CẤU HÌNH HỆ THỐNG
# ======================================================
is_dragging = False

# Lấy độ phân giải 1 lần duy nhất (Không gọi trong vòng lặp)
SCREEN_W, SCREEN_H = pyautogui.size()

# Cấu hình PyAutoGUI tối ưu
pyautogui.PAUSE = 0
pyautogui.MINIMUM_DURATION = 0
pyautogui.FAILSAFE = False

# Vùng biên điều khiển (Ảo)
MARGIN_LEFT = 250
MARGIN_RIGHT = 100
MARGIN_TOP = 150
MARGIN_BOTTOM = 150

# Biến lưu trạng thái chuột (Dùng float để tính toán chính xác hơn)
plocX, plocY = 0.0, 0.0
clocX, clocY = 0.0, 0.0

last_action_time = 0
zoom_counter = 0


# ======================================================
# CÁC HÀM ĐIỀU KHIỂN WINDOWS API (LOW LEVEL)
# ======================================================

def fast_move_mouse(x, y):
    """Di chuyển chuột dùng Ctypes (Nhanh nhất có thể)"""
    ctypes.windll.user32.SetCursorPos(int(x), int(y))


def fast_drag_move(x, y):
    """Kéo chuột mượt mà dùng toạ độ tuyệt đối"""
    # 65535 là toạ độ chuẩn hoá của màn hình trong Windows API
    abs_x = int(x * 65535 / SCREEN_W)
    abs_y = int(y * 65535 / SCREEN_H)
    ctypes.windll.user32.mouse_event(0x8001, abs_x, abs_y, 0, 0)


# ======================================================
# LOGIC LÀM MƯỢT THÔNG MINH (ADAPTIVE SMOOTHING)
# ======================================================
def get_adaptive_smoothing(dist):
    """
    Điều chỉnh độ mượt dựa trên tốc độ di chuyển tay.
    - Di chuyển chậm -> Smooth cao (Mouse đi đầm, chính xác)
    - Di chuyển nhanh -> Smooth thấp (Mouse bay nhanh, không delay)
    """
    if dist < 100:  # Di chuyển tinh chỉnh
        return 7.0  # Rất đầm
    elif dist < 300:  # Di chuyển bình thường
        return 3.0
    else:  # Vẩy tay nhanh
        return 1.5  # Phản hồi tức thì


# ======================================================
# LOGIC ZOOM (GIỮ NGUYÊN)
# ======================================================
def process_zoom_mode(frame, right_hand_lm, left_hand_lm):
    global zoom_counter
    h, w, _ = frame.shape

    # 1. Check tay trái (Trigger)
    l_fingers = []
    if left_hand_lm[4].x > left_hand_lm[3].x:
        l_fingers.append(1)
    else:
        l_fingers.append(0)

    tips = [8, 12, 16, 20];
    pips = [6, 10, 14, 18]
    for i in range(4):
        l_fingers.append(1 if left_hand_lm[tips[i]].y < left_hand_lm[pips[i]].y else 0)

    if sum(l_fingers) <= 1: return False

    # UI Trigger
    lx, ly = int(left_hand_lm[0].x * w), int(left_hand_lm[0].y * h)
    cv2.putText(frame, "ZOOM MODE ON", (lx, ly - 20), cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 0, 255), 2)
    cv2.circle(frame, (lx, ly), 10, (255, 0, 255), cv2.FILLED)

    # 2. Check tay phải (Action)
    dist_pinch = math.hypot(right_hand_lm[8].x - right_hand_lm[4].x, right_hand_lm[8].y - right_hand_lm[4].y)
    px, py = (right_hand_lm[8].x + right_hand_lm[4].x) / 2 * w, (right_hand_lm[8].y + right_hand_lm[4].y) / 2 * h

    if dist_pinch < 0.05:
        cv2.circle(frame, (int(px), int(py)), 15, (0, 255, 255), cv2.FILLED)
        left_threshold = 0.65 * w
        right_threshold = 0.85 * w

        # Vẽ line
        cv2.line(frame, (int(left_threshold), 0), (int(left_threshold), h), (200, 200, 200), 1)
        cv2.line(frame, (int(right_threshold), 0), (int(right_threshold), h), (200, 200, 200), 1)

        zoom_counter += 1
        if px < left_threshold:
            cv2.putText(frame, "<< ZOOM OUT", (int(px) - 120, int(py)), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
            if zoom_counter % 3 == 0: pyautogui.hotkey('ctrl', '-')
        elif px > right_threshold:
            text_x = int(px) - 150 if int(px) + 150 > w else int(px) + 20
            cv2.putText(frame, "ZOOM IN >>", (text_x, int(py)), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
            if zoom_counter % 3 == 0: pyautogui.hotkey('ctrl', '+')
        else:
            cv2.putText(frame, "|| HOLD ||", (int(px) - 40, int(py) - 30), cv2.FONT_HERSHEY_PLAIN, 1.5, (200, 200, 200),
                        2)
            zoom_counter = 0
        return True
    return True


# ======================================================
# XỬ LÝ GESTURE & MOUSE
# ======================================================
def process_gestures(frame, landmarks):
    global plocX, plocY, clocX, clocY, last_action_time, is_dragging

    h, w, _ = frame.shape
    lm = landmarks
    current_time = time.time()

    # --- ĐẾM NGÓN TAY ---
    fingers = []
    if lm[4].x < lm[3].x:
        fingers.append(1)
    else:
        fingers.append(0)

    tips = [8, 12, 16, 20];
    pips = [6, 10, 14, 18]
    for i in range(4):
        fingers.append(1 if lm[tips[i]].y < lm[pips[i]].y else 0)

    # Toạ độ gốc từ ngón trỏ
    target_x, target_y = lm[8].x * w, lm[8].y * h

    # 1. STOP (Nắm tay hoặc chỉ ngón cái)
    if sum(fingers) == 0 or (sum(fingers) == 1 and fingers[0] == 1):
        cv2.putText(frame, "!!! ABORT !!!", (20, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 3)
        return "STOP"

    # 2. SCROLL (Pinch ngón cái + trỏ)
    dist_pinch = math.hypot(lm[8].x - lm[4].x, lm[8].y - lm[4].y)
    # Loại trừ trường hợp Click
    is_clicking_gesture = (fingers[0] == 0 and fingers[1] == 1 and fingers[2] == 1)

    if dist_pinch < 0.05 and not is_clicking_gesture:
        pinch_cx, pinch_cy = (lm[4].x + lm[8].x) / 2 * w, (lm[4].y + lm[8].y) / 2 * h
        cv2.circle(frame, (int(pinch_cx), int(pinch_cy)), 15, (0, 255, 255), cv2.FILLED)

        top_thr = 0.4 * h;
        bot_thr = 0.6 * h
        cv2.line(frame, (0, int(top_thr)), (w, int(top_thr)), (0, 255, 255), 1)
        cv2.line(frame, (0, int(bot_thr)), (w, int(bot_thr)), (0, 255, 255), 1)

        BASE_SPD = 15;
        SENS = 0.5;
        MAX_SPD = 200

        if pinch_cy < top_thr:
            dist = top_thr - pinch_cy
            spd = min(int(BASE_SPD + dist * SENS), MAX_SPD)
            cv2.putText(frame, f"UP: {spd}", (int(pinch_cx) + 20, int(pinch_cy)), cv2.FONT_HERSHEY_PLAIN, 2,
                        (0, 255, 255), 2)
            pyautogui.scroll(spd)
        elif pinch_cy > bot_thr:
            dist = pinch_cy - bot_thr
            spd = min(int(BASE_SPD + dist * SENS), MAX_SPD)
            cv2.putText(frame, f"DOWN: {spd}", (int(pinch_cx) + 20, int(pinch_cy)), cv2.FONT_HERSHEY_PLAIN, 2,
                        (0, 255, 255), 2)
            pyautogui.scroll(-spd)
        else:
            cv2.putText(frame, "SCROLL HOLD", (int(pinch_cx) + 20, int(pinch_cy)), cv2.FONT_HERSHEY_PLAIN, 1,
                        (200, 200, 200), 1)
        return None

    # 3. LISTEN COMMAND
    elif fingers == [1, 0, 0, 0, 1]:
        cv2.putText(frame, "LISTENING...", (20, 80), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
        return "LISTEN"

    # 4. CLICK LOGIC
    # Left Click
    elif fingers[0] == 0 and fingers[1] == 1 and fingers[2] == 1:
        if current_time - last_action_time > 0.5:
            cv2.putText(frame, "LEFT CLICK", (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
            pyautogui.click()
            last_action_time = current_time
        return None
    # Right Click
    elif fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 0:
        if current_time - last_action_time > 0.5:
            cv2.putText(frame, "RIGHT CLICK", (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
            pyautogui.rightClick()
            last_action_time = current_time
        return None

    # ======================================================
    # MOUSE MOVEMENT (ĐƯỢC TỐI ƯU HOÁ)
    # ======================================================

    # Mapping toạ độ từ Camera -> Màn hình
    # Sử dụng numpy để map (Nhanh và chính xác)
    screen_x = np.interp(target_x, (MARGIN_LEFT, w - MARGIN_RIGHT), (0, SCREEN_W))
    screen_y = np.interp(target_y, (MARGIN_TOP, h - MARGIN_BOTTOM), (0, SCREEN_H))

    # --- LOGIC KÉO THẢ (DRAG) ---
    dist_drag = math.hypot(lm[12].x - lm[4].x, lm[12].y - lm[4].y)

    if dist_drag < 0.05 and fingers[1] == 1:
        if not is_dragging:
            pyautogui.mouseDown()
            is_dragging = True

        cv2.putText(frame, "DRAGGING", (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
        cv2.line(frame, (int(lm[4].x * w), int(lm[4].y * h)), (int(lm[12].x * w), int(lm[12].y * h)), (0, 0, 255), 3)
        cv2.circle(frame, (int(target_x), int(target_y)), 15, (0, 0, 255), cv2.FILLED)

        # Tính khoảng cách di chuyển để áp dụng Smooth
        move_dist = math.hypot(screen_x - plocX, screen_y - plocY)
        smoothing = get_adaptive_smoothing(move_dist)

        clocX = plocX + (screen_x - plocX) / smoothing
        clocY = plocY + (screen_y - plocY) / smoothing

        try:
            fast_drag_move(clocX, clocY)
        except:
            pass

        plocX, plocY = clocX, clocY
        return None

    elif is_dragging:
        pyautogui.mouseUp()
        is_dragging = False

    # --- LOGIC DI CHUYỂN (MOVE) ---
    elif fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 1:
        cv2.putText(frame, "MOVING", (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 255), 2)
        cv2.rectangle(frame, (MARGIN_LEFT, MARGIN_TOP), (w - MARGIN_RIGHT, h - MARGIN_BOTTOM), (255, 0, 255), 2)

        # 1. Tính khoảng cách cần di chuyển
        move_dist = math.hypot(screen_x - plocX, screen_y - plocY)

        # 2. CHỐNG RUNG (JITTER DEADZONE)
        # Nếu khoảng cách < 3 pixel -> Coi như đứng yên (Khắc phục việc tay run)
        if move_dist < 3:
            clocX, clocY = plocX, plocY  # Giữ nguyên vị trí cũ
        else:
            # 3. LÀM MƯỢT THÍCH ỨNG
            smoothing = get_adaptive_smoothing(move_dist)

            # Công thức EMA (Exponential Moving Average)
            clocX = plocX + (screen_x - plocX) / smoothing
            clocY = plocY + (screen_y - plocY) / smoothing

            # 4. DI CHUYỂN
            try:
                fast_move_mouse(clocX, clocY)
            except:
                pass

        # Cập nhật toạ độ cũ
        plocX, plocY = clocX, clocY
        cv2.circle(frame, (int(target_x), int(target_y)), 10, (255, 0, 255), cv2.FILLED)

    return None