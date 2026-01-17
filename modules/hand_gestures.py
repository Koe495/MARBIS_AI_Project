import cv2
import pyautogui
import numpy as np
import math
import time
import ctypes
import mediapipe as mp
from modules import shared_state

# ======================================================
# CẤU HÌNH HỆ THỐNG
# ======================================================
is_dragging = False
SCREEN_W, SCREEN_H = pyautogui.size()
pyautogui.PAUSE = 0
pyautogui.MINIMUM_DURATION = 0
pyautogui.FAILSAFE = False

MARGIN_LEFT = 250
MARGIN_RIGHT = 100
MARGIN_TOP = 150
MARGIN_BOTTOM = 150

plocX, plocY = 0.0, 0.0
clocX, clocY = 0.0, 0.0
last_action_time = 0

# Biến trạng thái
last_vol_y = 0
last_zoom_dist = 0
last_scroll_y = 0


# ======================================================
# LOW LEVEL API
# ======================================================
def fast_move_mouse(x, y):
    ctypes.windll.user32.SetCursorPos(int(x), int(y))


def fast_drag_move(x, y):
    abs_x = int(x * 65535 / SCREEN_W)
    abs_y = int(y * 65535 / SCREEN_H)
    ctypes.windll.user32.mouse_event(0x8001, abs_x, abs_y, 0, 0)


def get_adaptive_smoothing(dist):
    if dist < 100:
        return 7.0
    elif dist < 300:
        return 3.0
    else:
        return 1.5


def get_fingers_status(lm):
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    finger_states = []
    for i in range(4):
        if lm[tips[i]].y < lm[pips[i]].y:
            finger_states.append(1)
        else:
            finger_states.append(0)
    return finger_states


# ======================================================
# LOGIC FUNCTIONS
# ======================================================
def process_zoom_mode(frame, right_lm, left_lm):
    global last_zoom_dist
    h, w, _ = frame.shape
    r_fingers = get_fingers_status(right_lm)
    l_fingers = get_fingers_status(left_lm)
    is_right_L = (r_fingers == [1, 0, 0, 0])
    is_left_L = (l_fingers == [1, 0, 0, 0])

    if is_right_L and is_left_L:
        r_idx_x, r_idx_y = right_lm[8].x * w, right_lm[8].y * h
        l_idx_x, l_idx_y = left_lm[8].x * w, left_lm[8].y * h
        cv2.line(frame, (int(r_idx_x), int(r_idx_y)), (int(l_idx_x), int(l_idx_y)), (255, 0, 255), 2)
        cx, cy = int((r_idx_x + l_idx_x) / 2), int((r_idx_y + l_idx_y) / 2)
        cv2.putText(frame, "ZOOM MODE", (cx - 60, cy - 20), cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 0, 255), 2)
        current_dist = math.hypot(r_idx_x - l_idx_x, r_idx_y - l_idx_y)
        if last_zoom_dist == 0:
            last_zoom_dist = current_dist
            return True
        delta = current_dist - last_zoom_dist
        ZOOM_SENSITIVITY = 15
        if delta > ZOOM_SENSITIVITY:
            pyautogui.hotkey('ctrl', '+')
            last_zoom_dist = current_dist
        elif delta < -ZOOM_SENSITIVITY:
            pyautogui.hotkey('ctrl', '-')
            last_zoom_dist = current_dist
        return True
    else:
        last_zoom_dist = 0
        return False


def process_volume_mode(frame, right_lm, left_lm):
    global last_vol_y
    h, w, _ = frame.shape
    thumb = right_lm[4]
    middle = right_lm[12]
    dist_trigger = math.hypot(thumb.x - middle.x, thumb.y - middle.y)
    fingers = get_fingers_status(right_lm)
    is_index_open = (fingers[0] == 1)

    if dist_trigger < 0.05 and is_index_open:
        index_finger = right_lm[8]
        current_y = index_finger.y * h
        current_x = index_finger.x * w
        cv2.putText(frame, "VOL", (int(current_x) + 25, int(current_y)), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
        if last_vol_y == 0:
            last_vol_y = current_y
            return True
        diff = last_vol_y - current_y
        SENSITIVITY = 30
        if diff > SENSITIVITY:
            pyautogui.press('volumeup')
            last_vol_y = current_y
        elif diff < -SENSITIVITY:
            pyautogui.press('volumedown')
            last_vol_y = current_y
        return True
    else:
        last_vol_y = 0
        return False


def process_gestures(frame, landmarks):
    global plocX, plocY, clocX, clocY, last_action_time, is_dragging, last_scroll_y
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
    for i in range(4): fingers.append(1 if lm[tips[i]].y < lm[pips[i]].y else 0)

    target_x, target_y = lm[8].x * w, lm[8].y * h

    # ==========================================================
    # 1. LOGIC MIC (PUSH-TO-TALK) - Ưu tiên xử lý
    # Dáng tay: Ngón Cái + Út mở, 3 ngón giữa đóng
    # ==========================================================
    if fingers == [1, 0, 0, 0, 1]:
        shared_state.state.MIC_ON = True
        cv2.putText(frame, "MIC ON - LISTENING", (20, 80), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)
        # Khi đang nghe, ta return luôn để không di chuyển chuột loạn xạ
        return "LISTEN"
    else:
        # Nếu không phải dáng tay này, TẮT MIC ngay lập tức
        shared_state.state.MIC_ON = False

    # 2. STOP
    if sum(fingers) == 0 or (sum(fingers) == 1 and fingers[0] == 1):
        cv2.putText(frame, "STOP", (20, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 3)
        last_scroll_y = 0
        return "STOP"

    # 3. SCROLL
    dist_pinch = math.hypot(lm[8].x - lm[4].x, lm[8].y - lm[4].y)
    is_clicking_gesture = (fingers[0] == 0 and fingers[1] == 1 and fingers[2] == 1)
    if dist_pinch < 0.05 and not is_clicking_gesture:
        pinch_cy = (lm[4].y + lm[8].y) / 2 * h
        cv2.putText(frame, "SCROLL", (50, 50), cv2.FONT_HERSHEY_PLAIN, 1.5, (0, 255, 255), 2)
        if last_scroll_y == 0:
            last_scroll_y = pinch_cy
        else:
            diff = last_scroll_y - pinch_cy
            if abs(diff) > 5:
                pyautogui.scroll(int(diff * 4))
                last_scroll_y = pinch_cy
        return None
    else:
        last_scroll_y = 0

    # 4. CLICKS
    if fingers[0] == 0 and fingers[1] == 1 and fingers[2] == 1:
        if current_time - last_action_time > 0.5:
            pyautogui.click()
            last_action_time = current_time
        return None
    elif fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 0:
        dist_thumb_middle = math.hypot(lm[4].x - lm[12].x, lm[4].y - lm[12].y)
        if current_time - last_action_time > 0.5 and dist_thumb_middle > 0.15:
            pyautogui.rightClick()
            last_action_time = current_time
        return None

    # 5. MOVE & DRAG
    screen_x = np.interp(target_x, (MARGIN_LEFT, w - MARGIN_RIGHT), (0, SCREEN_W))
    screen_y = np.interp(target_y, (MARGIN_TOP, h - MARGIN_BOTTOM), (0, SCREEN_H))
    dist_drag = math.hypot(lm[12].x - lm[4].x, lm[12].y - lm[4].y)

    if dist_drag < 0.05 and fingers[1] == 1:
        if not is_dragging:
            pyautogui.mouseDown()
            is_dragging = True
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
    elif fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 1:
        move_dist = math.hypot(screen_x - plocX, screen_y - plocY)
        if move_dist < 3:
            clocX, clocY = plocX, plocY
        else:
            smoothing = get_adaptive_smoothing(move_dist)
            clocX = plocX + (screen_x - plocX) / smoothing
            clocY = plocY + (screen_y - plocY) / smoothing
            try:
                fast_move_mouse(clocX, clocY)
            except:
                pass
        plocX, plocY = clocX, clocY
    return None


# ======================================================
# HÀM KHỞI CHẠY CAMERA
# ======================================================
def start_camera():

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )
    mp_draw = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)

    try:
        while True:
            success, frame = cap.read()
            if not success: break

            frame = cv2.flip(frame, 1)
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(img_rgb)

            # --- HIỂN THỊ TRẠNG THÁI AI LÊN MÀN HÌNH ---
            status = shared_state.state.CURRENT_STATUS
            color = (0, 0, 255)  # Mặc định Đỏ (Idle/Muted)

            if status == "Listening...":
                color = (0, 255, 0)  # Xanh lá khi nghe
            elif status in ["Thinking...", "Speaking..."]:
                color = (255, 255, 0)  # Vàng khi xử lý

            cv2.putText(frame, f"AI: {status}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            # -------------------------------------------------

            cv2.rectangle(frame, (MARGIN_LEFT, MARGIN_TOP), (640 - MARGIN_RIGHT, 480 - MARGIN_BOTTOM), (255, 0, 255), 2)

            if results.multi_hand_landmarks:
                all_hands = results.multi_hand_landmarks

                if len(all_hands) == 2:
                    process_zoom_mode(frame, all_hands[0].landmark, all_hands[1].landmark)
                    process_volume_mode(frame, all_hands[0].landmark, all_hands[1].landmark)
                    for hand_lms in all_hands:
                        mp_draw.draw_landmarks(frame, hand_lms, mp_hands.HAND_CONNECTIONS)

                elif len(all_hands) == 1:
                    lm = all_hands[0].landmark
                    mp_draw.draw_landmarks(frame, all_hands[0], mp_hands.HAND_CONNECTIONS)
                    process_gestures(frame, lm)

            # Nếu không có tay nào, chắc chắn tắt mic
            else:
                shared_state.state.MIC_ON = False

            cv2.imshow("Marbis Vision AI", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            if cv2.getWindowProperty("Marbis Vision AI", cv2.WND_PROP_VISIBLE) < 1:
                break

    except Exception as e:
        print(f"Lỗi Camera Loop: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print(">> [INFO] Camera đã tắt.")


if __name__ == "__main__":
    start_camera()