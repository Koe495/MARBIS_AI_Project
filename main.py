import cv2
import mediapipe as mp
import threading
import time
import random
import os
import psutil
import ctypes  # Thư viện giao tiếp Windows API

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Import module
from config import ASSISTANT_NAME
from modules.brain import ask_marbis
from modules.skills import execute_command
from modules.hand_gestures import process_gestures, process_zoom_mode
from modules.senses import speak, listen, stop_speaking


# ======================================================
# CONFIG & OPTIMIZATION
# ======================================================
def set_high_priority():
    """Ép xung nhịp xử lý lên mức cao nhất"""
    try:
        p = psutil.Process(os.getpid())
        p.nice(psutil.HIGH_PRIORITY_CLASS)
    except:
        pass


def is_window_minimized(window_name):
    """Kiểm tra xem cửa sổ MARBIS có đang bị thu nhỏ dưới Taskbar không"""
    hwnd = ctypes.windll.user32.FindWindowW(None, window_name)
    if hwnd:
        # IsIconic trả về True nếu cửa sổ đang minimized
        return ctypes.windll.user32.IsIconic(hwnd)
    return False


MODEL_PATH = "hand_landmarker.task"
WINDOW_NAME = "MARBIS VISION"  # Tên cửa sổ chính xác

# ======================================================
# SETUP SYSTEM
# ======================================================
set_high_priority()

base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=2,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5
)
detector = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
# Giữ độ phân giải vừa phải để đảm bảo FPS cao nhất (640x480 là chuẩn vàng cho tốc độ)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
# Tắt buffer camera để giảm độ trễ (Latency)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# ======================================================
# GLOBAL STATE
# ======================================================
is_thinking = False
is_executing = False
current_request_id = 0
last_gesture_ts = 0.0
last_listen_trigger = 0.0
stop_hold_start = None


# ======================================================
# LOGIC CORE (BRAIN)
# ======================================================
def core_process(my_id):
    global is_thinking, is_executing, current_request_id, last_gesture_ts
    if my_id != current_request_id: return
    is_thinking = True
    try:
        speak(random.choice(["Vâng", "Dạ", "Nghe", "Có"]))
        while True:
            if my_id != current_request_id: break
            timeout = 3.0 if is_executing else 1.5
            if time.time() - last_gesture_ts > timeout: break

            cmd = listen()
            if my_id != current_request_id: break

            if cmd:
                data = ask_marbis(cmd)
                if my_id != current_request_id: break
                if "reply" in data: speak(data["reply"])
                is_executing = True
                execute_command(data)
                is_executing = False
    except Exception:
        speak("Lỗi hệ thống")
    finally:
        if my_id == current_request_id: is_thinking = False


# ======================================================
# MAIN LOOP (PERFORMANCE OPTIMIZED)
# ======================================================
print(f"--- {ASSISTANT_NAME} HIGH PERFORMANCE MODE ---")
speak("Sẵn sàng")

try:
    while True:
        # 1. Đọc Camera (Bắt buộc)
        ret, frame = cap.read()
        if not ret: break

        # Kiểm tra trạng thái cửa sổ
        minimized = is_window_minimized(WINDOW_NAME)

        # 2. Xử lý MediaPipe (Bắt buộc - để điều khiển chuột)
        # Nếu minimized, ta KHÔNG lật ảnh (flip) để tiết kiệm thêm 1 chút CPU.
        # Nhưng lưu ý: process_gestures có thể cần logic lật.
        # Để an toàn và đồng bộ: Luôn Flip.
        frame = cv2.flip(frame, 1)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms = int(time.time() * 1000)

        result = detector.detect_for_video(mp_image, timestamp_ms)

        # 3. LOGIC CHUỘT & CỬ CHỈ (Luôn chạy)
        if result.hand_landmarks:
            user_right = None
            user_left = None
            for i, lms in enumerate(result.hand_landmarks):
                lbl = result.handedness[i][0].category_name
                if lbl == "Left":
                    user_right = lms
                elif lbl == "Right":
                    user_left = lms

            # Xử lý Zoom
            is_zooming = False
            if user_left and user_right:
                is_zooming = process_zoom_mode(frame, user_right, user_left)

            # Xử lý Chuột & Lệnh
            if not is_zooming and user_right:
                # Hàm này di chuyển chuột -> Cần chạy liên tục
                gesture_cmd = process_gestures(frame, user_right)

                if gesture_cmd == "LISTEN":
                    last_gesture_ts = time.time()
                    if time.time() - last_listen_trigger > 0.7:
                        last_listen_trigger = time.time()
                        if not is_thinking and not is_executing:
                            current_request_id += 1
                            threading.Thread(target=core_process, args=(current_request_id,), daemon=True).start()

                elif gesture_cmd == "STOP":
                    if is_thinking or is_executing:
                        if stop_hold_start is None:
                            stop_hold_start = time.time()
                        elif time.time() - stop_hold_start >= 0.5:
                            stop_speaking()
                            current_request_id += 1
                            is_thinking = False;
                            is_executing = False
                            speak("Đã huỷ")
                            stop_hold_start = None
                    else:
                        stop_hold_start = None
                else:
                    stop_hold_start = None

        # 4. RENDER CÓ ĐIỀU KIỆN (chống Lag)
        if not minimized:
            # === CHỈ VẼ KHI CỬA SỔ HIỆN ===

            # Vẽ UI Landmarks
            if result.hand_landmarks:
                h, w, _ = frame.shape
                for hand_lms in result.hand_landmarks:
                    for lm in hand_lms:
                        cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 3, (0, 255, 255), -1)

            # Vẽ UI Text
            if is_executing:
                st, col = "EXECUTING...", (0, 0, 255)
            elif is_thinking:
                st, col = "LISTENING...", (0, 255, 0)
            else:
                st, col = "ACTIVE", (0, 255, 0)

            cv2.putText(frame, f"MARBIS: {st}", (20, 30), cv2.FONT_HERSHEY_PLAIN, 1.5, col, 2)

            # Show ảnh
            cv2.imshow(WINDOW_NAME, frame)

            # WaitKey bình thường để bắt sự kiện phím Q
            if cv2.waitKey(1) & 0xFF == ord('q'): break
        else:
            # === KHI MINIMIZED ===
            # Không Vẽ, Không Show -> Tiết kiệm tài nguyên cực lớn
            # Vẫn cần waitKey nhỏ để hệ thống Windows cập nhật event loop (tránh Not Responding)
            cv2.waitKey(1)

except KeyboardInterrupt:
    pass
finally:
    stop_speaking()
    detector.close()
    cap.release()
    cv2.destroyAllWindows()