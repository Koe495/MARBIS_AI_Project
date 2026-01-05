
import cv2
import mediapipe as mp
import threading
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Import các module của trợ lý ảo
from config import ASSISTANT_NAME
from modules.senses import speak, listen
from modules.brain import ask_marbis
from modules.skills import execute_command

# Import logic xử lý tay
from modules.hand_gestures import process_gestures, process_zoom_mode

# --- CẤU HÌNH MEDIAPIPE ---
MODEL_PATH = 'hand_landmarker.task'
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

# Setup Camera
cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

# --- BIẾN TRẠNG THÁI ---
is_thinking = False  # Đang suy nghĩ/xử lý
is_executing = False  # Đang thực thi lệnh máy tính
abort_flag = False  # Cờ để hủy lệnh (khi nắm tay)


# --- HÀM XỬ LÝ CHÍNH (LUỒNG RIÊNG) ---
def core_process():
    global is_thinking, is_executing, abort_flag

    if is_executing: return

    is_thinking = True
    abort_flag = False  # Reset cờ hủy mỗi lần bắt đầu

    speak("Vâng?")

    # Lắng nghe lệnh
    cmd = listen()

    # 1. Kiểm tra hủy sau khi nghe
    if abort_flag:
        print(">> COMMAND ABORTED BY USER")
        speak("Canceled.")
        is_thinking = False
        return

    if cmd:
        data = ask_marbis(cmd)

        # 2. Kiểm tra hủy sau khi suy nghĩ
        if abort_flag:
            speak("Canceled.")
            is_thinking = False
            return

        if "reply" in data:
            speak(data["reply"])

        is_executing = True
        execute_command(data)
        is_executing = False
    else:
        if not abort_flag:
            speak("Dismissed.")

    is_thinking = False


print(f"--- {ASSISTANT_NAME} SYSTEM ONLINE ---")
speak("System Ready.")

# --- VÒNG LẶP CHÍNH ---
while True:
    ret, frame = cap.read()
    if not ret: break

    # Lật ngược hình ảnh (Mirror) để thao tác tự nhiên
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    timestamp = int(time.time() * 1000)

    # Phát hiện bàn tay
    result = detector.detect_for_video(mp_image, timestamp)

    cv2.putText(frame, "MARBIS AI", (20, 30), cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 100, 0), 2)

    if result.hand_landmarks:
        hand_lms_list = result.hand_landmarks
        handedness_list = result.handedness

        # --- PHÂN LOẠI TAY (TRÁI/PHẢI) ---
        # Lưu ý: Do đã flip frame, Label "Left" của AI = Tay Phải của người dùng
        user_right_hand = None
        user_left_hand = None

        for i, hand_lms in enumerate(hand_lms_list):
            label = handedness_list[i][0].category_name

            if label == "Left":
                user_right_hand = hand_lms  # Tay phải người dùng (dùng để Di chuyển/Pinch)
            elif label == "Right":
                user_left_hand = hand_lms  # Tay trái người dùng (dùng để Kích hoạt Zoom)

            # Vẽ khớp tay (Màu vàng cho tay Phải, Màu tím cho tay Trái)
            color = (0, 255, 255) if label == "Left" else (255, 0, 255)
            for lm in hand_lms:
                h, w, _ = frame.shape
                cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 3, color, -1)

        # --- LOGIC ĐIỀU PHỐI ---
        is_zooming = False

        # 1. CHẾ ĐỘ ZOOM (Cần cả 2 tay)
        # Nếu phát hiện cả tay trái và tay phải -> Gọi hàm Zoom
        if user_left_hand and user_right_hand:
            # Truyền tay phải (action) và tay trái (trigger) vào hàm
            is_zooming = process_zoom_mode(frame, user_right_hand, user_left_hand)

        # 2. CHẾ ĐỘ CHUỘT & CỬ CHỈ (Chỉ cần tay phải)
        # Chỉ chạy khi không đang Zoom
        if not is_zooming and user_right_hand:
            # Hàm process_gestures trả về lệnh text: "STOP", "LISTEN" hoặc None
            gesture_cmd = process_gestures(frame, user_right_hand)

            # Xử lý các lệnh trả về
            if gesture_cmd == "STOP":
                # Nếu đang suy nghĩ mà nắm tay -> Bật cờ Hủy
                if is_thinking:
                    abort_flag = True
                    cv2.putText(frame, "ABORTING...", (200, 200), cv2.FONT_HERSHEY_PLAIN, 3, (0, 0, 255), 3)

            elif gesture_cmd == "LISTEN":
                # Nếu chưa làm gì -> Bắt đầu nghe
                if not is_thinking and not is_executing:
                    threading.Thread(target=core_process).start()

    # --- HIỂN THỊ TRẠNG THÁI ---
    if abort_flag:
        status, color = "ABORTING...", (0, 0, 255)
    elif is_executing:
        status, color = "EXECUTING...", (0, 0, 255)
    elif is_thinking:
        status, color = "LISTENING...", (255, 0, 255)
    else:
        status, color = "ACTIVE", (0, 255, 0)

    cv2.putText(frame, status, (20, 450), cv2.FONT_HERSHEY_PLAIN, 2, color, 2)

    cv2.imshow("MARBIS VISION", frame)
    if cv2.waitKey(1) == ord('q'): break

cap.release()
cv2.destroyAllWindows()