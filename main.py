import cv2
import mediapipe as mp
import threading
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Import module
from config import ASSISTANT_NAME
from modules.brain import ask_marbis
from modules.skills import execute_command
from modules.hand_gestures import process_gestures, process_zoom_mode
# Lưu ý: module senses phải là phiên bản mới (có class SensesManager hoặc logic threading)
from modules.senses import speak, listen, stop_speaking

# --- CẤU HÌNH MEDIAPIPE ---
MODEL_PATH = "hand_landmarker.task"

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

# --- SETUP CAMERA ---
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# --- BIẾN TRẠNG THÁI & QUẢN LÝ LUỒNG ---
is_thinking = False
is_executing = False
current_request_id = 0  # Định danh phiên làm việc

# Biến kiểm soát thời gian giữ tay
last_gesture_ts = 0.0  # Thời điểm cuối cùng nhìn thấy tay
GESTURE_TIMEOUT = 1.5  # Thời gian chờ trước khi ngắt (giây)


# --- HÀM XỬ LÝ CHÍNH (AI THREAD - VÒNG LẶP LIÊN TỤC) ---
def core_process(my_id):
    """
    Chạy vòng lặp hội thoại chừng nào người dùng còn giữ tay.
    """
    global is_thinking, is_executing, current_request_id, last_gesture_ts

    # Check ID ngay khi vào
    if my_id != current_request_id: return

    is_thinking = True

    try:
        # 1. Chào hỏi (Chỉ chạy 1 lần duy nhất khi bắt đầu giữ tay)
        speak("Vâng")

        # 2. Vòng lặp hội thoại
        while True:
            # --- KIỂM TRA ĐIỀU KIỆN THOÁT ---

            # A. Nếu bị Force Stop từ bên ngoài (Lệnh STOP)
            if my_id != current_request_id:
                print(f">> Session {my_id} bị hủy.")
                break

            # B. Nếu người dùng buông tay quá lâu (Timeout)
            # Logic: Lấy thời gian hiện tại TRỪ thời gian lần cuối thấy tay
            if time.time() - last_gesture_ts > GESTURE_TIMEOUT:
                print(f">> Session {my_id} kết thúc do buông tay.")
                break

            # --- BẮT ĐẦU NGHE ---
            # Gọi hàm nghe (sẽ block khoảng vài giây)
            cmd = listen()

            # Kiểm tra lại ID ngay sau khi nghe (để dừng nếu user bấm STOP lúc đang nghe)
            if my_id != current_request_id: break

            if cmd:
                # --- XỬ LÝ ---
                data = ask_marbis(cmd)

                # Check ID lần nữa
                if my_id != current_request_id: break

                # Phản hồi
                if "reply" in data:
                    speak(data["reply"])

                # Thực thi
                is_executing = True
                execute_command(data)
                is_executing = False

                # Mẹo nhỏ: Sau khi thực thi xong, bạn có thể tự reset last_gesture_ts
                # để cho người dùng thêm chút thời gian định thần nếu muốn (tuỳ chọn)
                # last_gesture_ts = time.time()

            else:
                # Nếu không nghe thấy gì (Silence)
                # Vòng lặp sẽ quay lại đầu, kiểm tra xem tay còn giơ không.
                pass

    except Exception as e:
        print(f"Error in core_process: {e}")
        speak("Lỗi hệ thống")

    finally:
        # Reset trạng thái khi thoát vòng lặp hoàn toàn
        if my_id == current_request_id:
            is_thinking = False


print(f"--- {ASSISTANT_NAME} SYSTEM ONLINE ---")
speak("Hệ thống sẵn sàng")
print(">> MARBIS AI Started. Press 'Q' to exit.")

# --- VÒNG LẶP CHÍNH ---
try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 1. Xử lý ảnh
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        timestamp_ms = int(time.time() * 1000)

        # 2. Phát hiện tay
        result = detector.detect_for_video(mp_image, timestamp_ms)

        # UI Header
        cv2.putText(frame, "MARBIS AI", (20, 30), cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 100, 0), 2)

        # 3. Logic xử lý tay
        if result.hand_landmarks:
            user_right_hand = None
            user_left_hand = None

            for i, hand_lms in enumerate(result.hand_landmarks):
                label = result.handedness[i][0].category_name
                if label == "Left":
                    user_right_hand = hand_lms
                elif label == "Right":
                    user_left_hand = hand_lms

                color = (0, 255, 255) if label == "Left" else (255, 0, 255)
                for lm in hand_lms:
                    cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 3, color, -1)

            is_zooming = False

            # Ưu tiên chế độ 2 tay (Zoom)
            if user_left_hand and user_right_hand:
                is_zooming = process_zoom_mode(frame, user_right_hand, user_left_hand)

            # Chế độ 1 tay
            if not is_zooming and user_right_hand:
                gesture_cmd = process_gestures(frame, user_right_hand)

                # --- [LOGIC ĐÃ CẬP NHẬT] ---

                if gesture_cmd == "LISTEN":
                    # 1. CẬP NHẬT TIMESTAMPS (Trái tim của hệ thống)
                    # Cứ thấy tay là reset bộ đếm thời gian
                    last_gesture_ts = time.time()

                    # 2. CHỈ KHỞI TẠO LUỒNG NẾU CHƯA CÓ
                    if not is_thinking and not is_executing:
                        current_request_id += 1  # Tạo phiên mới
                        threading.Thread(
                            target=core_process,
                            args=(current_request_id,),
                            daemon=True
                        ).start()

                    # UI Báo hiệu
                    cv2.putText(frame, "HOLD TO KEEP ALIVE", (20, 400), cv2.FONT_HERSHEY_PLAIN, 1.5, (0, 255, 255), 2)

                elif gesture_cmd == "STOP":
                    if is_thinking or is_executing:
                        stop_speaking()
                        current_request_id += 1  # Đổi ID để giết luồng cũ ngay
                        is_thinking = False
                        is_executing = False
                        speak("Đã huỷ")
                        cv2.putText(frame, "CANCELED!", (200, 200), cv2.FONT_HERSHEY_PLAIN, 3, (0, 0, 255), 3)

        # --- HIỂN THỊ TRẠNG THÁI ---
        if is_executing:
            status, color = "EXECUTING...", (0, 0, 255)
        elif is_thinking:
            # Tính thời gian còn lại trước khi timeout
            time_left = max(0, GESTURE_TIMEOUT - (time.time() - last_gesture_ts))
            if time_left > 0:
                status = f"LISTENING ({time_left:.1f}s)"
                color = (0, 255, 0)  # Xanh lá: Đang nghe tốt
            else:
                status = "CLOSING..."
                color = (100, 100, 100)  # Xám: Sắp đóng
        else:
            status, color = "ACTIVE", (0, 255, 0)

        cv2.putText(frame, status, (20, 450), cv2.FONT_HERSHEY_PLAIN, 2, color, 2)

        cv2.imshow("MARBIS VISION", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    print("\n>> Program stopped by User.")

finally:
    try:
        stop_speaking()
    except:
        pass
    detector.close()
    cap.release()
    cv2.destroyAllWindows()
    print(">> Camera released. Goodbye!")