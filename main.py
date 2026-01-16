import cv2
import mediapipe as mp
import threading
import time
import random
import os
import psutil
import ctypes

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ======================================================
# IMPORT MODULES
# ======================================================
from config import ASSISTANT_NAME
from modules.brain import ask_marbis
from modules.skills import execute_command
from modules.senses import speak, listen, stop_speaking
from modules import shared_state
from modules.hand_gestures import process_gestures, process_zoom_mode, process_volume_mode


# ======================================================
# CẤU HÌNH & TỐI ƯU
# ======================================================
def set_high_priority():
    """Đặt ưu tiên CPU cao cho Python để xử lý mượt hơn"""
    try:
        p = psutil.Process(os.getpid())
        p.nice(psutil.HIGH_PRIORITY_CLASS)
        print(">> [SYSTEM] High Priority Mode: ON")
    except:
        pass


def is_window_minimized(window_name):
    """Kiểm tra xem cửa sổ camera có bị ẩn không để tiết kiệm tài nguyên"""
    hwnd = ctypes.windll.user32.FindWindowW(None, window_name)
    if hwnd:
        return ctypes.windll.user32.IsIconic(hwnd)
    return False


MODEL_PATH = "hand_landmarker.task"
WINDOW_NAME = "MARBIS VISION"

# ======================================================
# KHỞI TẠO HỆ THỐNG
# ======================================================
set_high_priority()

# Cấu hình MediaPipe Hand Landmarker
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=2,
    min_hand_detection_confidence=0.6,
    min_hand_presence_confidence=0.6,
    min_tracking_confidence=0.6
)
detector = vision.HandLandmarker.create_from_options(options)

# Khởi tạo Camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Giảm độ trễ

# ======================================================
# TRẠNG THÁI TOÀN CỤC (GLOBAL STATE)
# ======================================================
is_thinking = False
is_executing = False
current_request_id = 0
last_gesture_ts = 0.0
last_listen_trigger = 0.0
stop_hold_start = None


# ======================================================
# XỬ LÝ AI (LUỒNG RIÊNG)
# ======================================================
def core_process(my_id):
    """Luồng xử lý giọng nói song song để không làm đơ chuột"""
    global is_thinking, is_executing, current_request_id, last_gesture_ts

    if my_id != current_request_id: return
    is_thinking = True
    shared_state.state.CURRENT_STATUS = "Listening..."

    try:
        # 1. Phản hồi xác nhận
        speak(random.choice(["Vâng", "Dạ", "Nghe", "Có"]))

        while True:
            # Kiểm tra xem có lệnh mới chen ngang không
            if my_id != current_request_id: break

            # Timeout: Nếu không nói gì sau 1.5s thì tắt
            timeout = 3.0 if is_executing else 1.5
            if time.time() - last_gesture_ts > timeout: break

            # 2. Nghe lệnh
            cmd = listen()
            if my_id != current_request_id: break

            if cmd:
                shared_state.state.CURRENT_STATUS = "Thinking..."

                # 3. Gửi lên não bộ (AI)
                data = ask_marbis(cmd)

                if my_id != current_request_id: break

                # 4. Trả lời và thực thi
                shared_state.state.CURRENT_STATUS = "Speaking..."

                # Nói câu xác nhận từ não bộ trước (VD: "Đang dịch...")
                if "reply" in data and data["reply"]:
                    speak(data["reply"])

                is_executing = True

                # Hứng lấy kết quả trả về từ skills
                result_text = execute_command(data)

                # Nếu skills có trả về văn bản (VD: Kết quả dịch), thì nói ra luôn
                if result_text:
                    print(f">> [SKILL RESULT] {result_text}")
                    speak(result_text)
                # --------------------

                is_executing = False

    except Exception as e:
        print(f"Error in core_process: {e}")
        speak("Có lỗi xảy ra")
    finally:
        if my_id == current_request_id:
            is_thinking = False
            shared_state.state.CURRENT_STATUS = "Idle"


# ======================================================
# VÒNG LẶP CHÍNH (MAIN LOOP)
# ======================================================
print(f"--- {ASSISTANT_NAME} STARTED ---")
speak("Hệ thống đã sẵn sàng")

try:
    while True:
        ret, frame = cap.read()
        if not ret: break

        # Kiểm tra nếu cửa sổ bị ẩn thì không xử lý AI để nhẹ máy
        minimized = is_window_minimized(WINDOW_NAME)

        # Lật ảnh (Mirror) để thao tác tự nhiên
        frame = cv2.flip(frame, 1)

        # Chuyển đổi màu cho MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms = int(time.time() * 1000)

        # PHÁT HIỆN BÀN TAY
        result = detector.detect_for_video(mp_image, timestamp_ms)

        # =================================================
        # LOGIC ĐIỀU KHIỂN (HAND GESTURE LOGIC)
        # =================================================
        if result.hand_landmarks:
            user_right = None
            user_left = None

            # 1. PHÂN LOẠI TAY (TRÁI / PHẢI)
            # Lưu ý: Do đã flip(1), 'Left' của MediaPipe là Tay Phải của người dùng
            for i, lms in enumerate(result.hand_landmarks):
                lbl = result.handedness[i][0].category_name
                if lbl == "Left":
                    user_right = lms
                elif lbl == "Right":
                    user_left = lms

            # 2. XỬ LÝ THEO KỊCH BẢN

            # --- KỊCH BẢN A: CÓ CẢ 2 TAY (VOLUME & ZOOM) ---
            if user_left and user_right:
                cv2.putText(frame, "MODE: 2 HANDS", (20, 450), cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 0, 255), 2)

                # (Zoom ưu tiên trước)
                is_zooming = process_zoom_mode(frame, user_right, user_left)

                # Nếu không zoom thì chỉnh volume
                if not is_zooming:
                    process_volume_mode(frame, user_right, user_left)

            # --- KỊCH BẢN B: CHỈ CÓ TAY PHẢI (CHUỘT & LISTEN) ---
            elif user_right:
                # Hàm này xử lý: Move, Click, Scroll, và trả về "LISTEN" hoặc "STOP"
                gesture_cmd = process_gestures(frame, user_right)

                # Xử lý lệnh trả về
                if gesture_cmd == "LISTEN":
                    last_gesture_ts = time.time()  # Cập nhật thời gian để không bị timeout

                    # Debounce: Chỉ kích hoạt lại sau 0.7s
                    if time.time() - last_listen_trigger > 0.7:
                        last_listen_trigger = time.time()

                        # Chỉ mở luồng nghe nếu chưa đang nghe/nghĩ
                        if not is_thinking and not is_executing:
                            current_request_id += 1
                            threading.Thread(target=core_process, args=(current_request_id,), daemon=True).start()

                elif gesture_cmd == "STOP":
                    # Logic giữ để huỷ lệnh
                    if is_thinking or is_executing:
                        if stop_hold_start is None:
                            stop_hold_start = time.time()
                        elif time.time() - stop_hold_start >= 0.5:  # Giữ 0.5s để huỷ
                            stop_speaking()
                            current_request_id += 1  # Huỷ thread cũ bằng cách tăng ID
                            is_thinking = False
                            is_executing = False
                            shared_state.state.CURRENT_STATUS = "Idle"
                            speak("Đã huỷ")
                            stop_hold_start = None
                    else:
                        stop_hold_start = None
                else:
                    stop_hold_start = None

            # --- KỊCH BẢN C: CHỈ CÓ TAY TRÁI ---
            # Không làm gì cả
            elif user_left:
                cv2.putText(frame, "Trai (Idle)", (20, 450), cv2.FONT_HERSHEY_PLAIN, 1, (100, 100, 100), 1)

        # =================================================
        # VẼ GIAO DIỆN (UI RENDER)
        # =================================================
        if not minimized:
            # Vẽ các điểm khớp tay (Landmarks)
            if result.hand_landmarks:
                h, w, _ = frame.shape
                for hand_lms in result.hand_landmarks:
                    for lm in hand_lms:
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        cv2.circle(frame, (cx, cy), 3, (0, 255, 255), -1)

            # Hiển thị trạng thái AI
            st = shared_state.state.CURRENT_STATUS
            col = (0, 255, 0)  # Xanh lá (Active)
            if "Listening" in st:
                col = (0, 255, 0)
            elif "Thinking" in st:
                col = (0, 255, 255)  # Vàng
            elif "Speaking" in st:
                col = (255, 0, 0)  # Xanh dương
            else:
                col = (0, 0, 255)  # Đỏ (Idle)

            cv2.putText(frame, f"AI: {st}", (20, 30), cv2.FONT_HERSHEY_PLAIN, 1.5, col, 2)

            cv2.imshow(WINDOW_NAME, frame)

            # Phím tắt thoát: Q
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            # Nếu ẩn cửa sổ thì chỉ waitKey nhẹ để giữ luồng
            cv2.waitKey(100)

except KeyboardInterrupt:
    pass
except Exception as e:
    print(f"FATAL ERROR: {e}")
finally:
    stop_speaking()
    detector.close()
    cap.release()
    cv2.destroyAllWindows()
    print(">> Chương trình đã tắt.")