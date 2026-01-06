import cv2
import pyautogui
import numpy as np
import math
import time
import ctypes

is_dragging = False # Biến theo dõi trạng thái kéo thả

# --- CẤU HÌNH ---
SCREEN_W, SCREEN_H = pyautogui.size()

SMOOTHING = 1.5
# Tắt thời gian chờ mặc định (MẶC ĐỊNH LÀ 0.1s -> GÂY LAG)
pyautogui.PAUSE = 0

# Tắt animation di chuyển chuột (nhảy cóc tới điểm đích ngay lập tức)
pyautogui.MINIMUM_DURATION = 0.1

# Giảm ngưỡng an toàn (để chuột có thể ra sát góc màn hình mà không crash)
pyautogui.FAILSAFE = False
MARGIN_LEFT = 250
MARGIN_RIGHT = 100
MARGIN_TOP = 150
MARGIN_BOTTOM = 150

# Biến trạng thái
plocX, plocY = 0, 0
clocX, clocY = 0, 0
last_action_time = 0

# Biến đếm frame để giảm tốc độ Zoom (tránh zoom quá nhanh lag máy)
zoom_counter = 0

def fast_move_mouse(x, y):
    """Di chuyển chuột tức thì dùng Windows API (Không delay)"""
    ctypes.windll.user32.SetCursorPos(int(x), int(y))


# --- DÙNG ĐỂ VẼ / KÉO THẢ (Trượt chuột thay vì nhảy cóc) ---
def fast_drag_move(x, y):
    # Lấy độ phân giải màn hình thực tế
    sw, sh = pyautogui.size()

    # Quy đổi toạ độ pixel sang toạ độ tuyệt đối của Windows (0 - 65535)
    # Đây là cách Windows hiểu vị trí chuột ở cấp độ phần cứng
    abs_x = int(x * 65535 / sw)
    abs_y = int(y * 65535 / sh)

    # Gửi sự kiện MOUSEEVENTF_MOVE (0x0001) | MOUSEEVENTF_ABSOLUTE (0x8000)
    ctypes.windll.user32.mouse_event(0x8001, abs_x, abs_y, 0, 0)

def calculate_distance(p1, p2):
    return math.hypot(p2.x - p1.x, p2.y - p1.y)


# --- LOGIC ZOOM MỚI (TAY TRÁI KÍCH HOẠT - TAY PHẢI ĐIỀU KHIỂN) ---
def process_zoom_mode(frame, right_hand_lm, left_hand_lm):
    global zoom_counter

    h, w, _ = frame.shape

    # 1. KIỂM TRA TAY TRÁI (TRIGGER)
    # Tay trái chỉ cần hiện diện và mở (không nắm đấm) để xác nhận ý định
    # Logic đơn giản: Đếm số ngón tay trái mở
    l_fingers = []
    if left_hand_lm[4].x > left_hand_lm[3].x:
        l_fingers.append(1)  # Ngón cái tay trái (Ngược với tay phải)
    else:
        l_fingers.append(0)

    tips = [8, 12, 16, 20];
    pips = [6, 10, 14, 18]
    for i in range(4): l_fingers.append(1 if left_hand_lm[tips[i]].y < left_hand_lm[pips[i]].y else 0)

    # Nếu tay trái nắm đấm (Stop/Nghỉ) hoặc gập hết -> Không kích hoạt Zoom
    if sum(l_fingers) <= 1:
        return False

    # Vẽ thông báo kích hoạt ở góc tay trái
    lx, ly = int(left_hand_lm[0].x * w), int(left_hand_lm[0].y * h)
    cv2.putText(frame, "ZOOM MODE ON", (lx, ly - 20), cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 0, 255), 2)
    cv2.circle(frame, (lx, ly), 10, (255, 0, 255), cv2.FILLED)

    # 2. KIỂM TRA TAY PHẢI (ACTION)
    # Kiểm tra Pinch (Ngón Cái & Trỏ tay phải)
    dist_pinch = math.hypot(right_hand_lm[8].x - right_hand_lm[4].x, right_hand_lm[8].y - right_hand_lm[4].y)

    # Tọa độ trung tâm Pinch
    px, py = (right_hand_lm[8].x + right_hand_lm[4].x) / 2 * w, (right_hand_lm[8].y + right_hand_lm[4].y) / 2 * h

    if dist_pinch < 0.05:  # Đang PINCH
        cv2.circle(frame, (int(px), int(py)), 15, (0, 255, 255), cv2.FILLED)

        # 3. LOGIC SLIDER TRÁI / PHẢI (LỆCH PHẢI - 3/4 MÀN HÌNH)

        # --- CẤU HÌNH VÙNG ZOOM LỆCH PHẢI ---
        # Mục tiêu: Tâm nằm ở khoảng 0.75 (75%)
        # Ta set vùng HOLD từ 0.65 (65%) đến 0.85 (85%)

        left_threshold = 0.65 * w  # Dưới 65% là Zoom Out (Vùng này rất rộng)
        right_threshold = 0.85 * w  # Trên 85% là Zoom In (Vùng này hẹp sát mép)

        # Vẽ vạch dọc để bạn dễ căn chỉnh
        cv2.line(frame, (int(left_threshold), 0), (int(left_threshold), h), (200, 200, 200), 1)
        cv2.line(frame, (int(right_threshold), 0), (int(right_threshold), h), (200, 200, 200), 1)

        zoom_counter += 1

        if px < left_threshold:
            # Vùng TRÁI RỘNG -> ZOOM OUT (-)
            cv2.putText(frame, "<< ZOOM OUT", (int(px) - 120, int(py)), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
            if zoom_counter % 3 == 0:
                pyautogui.hotkey('ctrl', '-')

        elif px > right_threshold:
            # Vùng PHẢI HẸP -> ZOOM IN (+)
            # Điều chỉnh toạ độ text một chút để không bị tràn ra ngoài màn hình
            text_x = int(px) - 150 if int(px) + 150 > w else int(px) + 20
            cv2.putText(frame, "ZOOM IN >>", (text_x, int(py)), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

            if zoom_counter % 3 == 0:
                pyautogui.hotkey('ctrl', '+')
        else:
            # Vùng GIỮA (LỆCH PHẢI) -> HOLD
            cv2.putText(frame, "|| HOLD ||", (int(px) - 40, int(py) - 30), cv2.FONT_HERSHEY_PLAIN, 1.5, (200, 200, 200),
                        2)
            zoom_counter = 0

        return True

    return True  # Vẫn return True vì tay trái đang giơ -> Chặn di chuyển chuột để tránh loạn


# --- XỬ LÝ 1 TAY (GESTURE & MOUSE) ---
# (Giữ nguyên code phần process_gestures như cũ)
def process_gestures(frame, landmarks):
    global plocX, plocY, clocX, clocY, last_action_time
    global MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM
    global is_dragging

    h, w, _ = frame.shape
    lm = landmarks
    current_time = time.time()

    # --- XÁC ĐỊNH TRẠNG THÁI NGÓN TAY (0: Gập, 1: Mở) ---
    fingers = []

    # Ngón 1 (Cái - fingers[0]): Kiểm tra trục X
    if lm[4].x < lm[3].x:
        fingers.append(1)
    else:
        fingers.append(0)

    # Các ngón còn lại (2,3,4,5): Kiểm tra trục Y (đỉnh ngón cao hơn đốt ngón)
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    for i in range(4):
        fingers.append(1 if lm[tips[i]].y < lm[pips[i]].y else 0)

    # Tọa độ đầu ngón trỏ (để di chuyển chuột)
    target_x, target_y = lm[8].x * w, lm[8].y * h

    # --- BẮT ĐẦU XỬ LÝ GESTURE ---

    # 1. STOP / ABORT (Nắm chặt tay hoặc chỉ giơ ngón cái)
    if sum(fingers) == 0 or (sum(fingers) == 1 and fingers[0] == 1):
        cv2.putText(frame, "!!! ABORT !!!", (20, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 3)
        return "STOP"

    # 2. PINCH SCROLL (Giữ nguyên logic cuộn bằng cách chụm ngón cái + trỏ)
    dist_pinch = math.hypot(lm[8].x - lm[4].x, lm[8].y - lm[4].y)

    # Chỉ cuộn khi đang pinch (chụm ngón) và không phải thế tay Click
    if dist_pinch < 0.05 and not (fingers[0] == 0 and fingers[1] == 1 and fingers[2] == 1):
        pinch_cx, pinch_cy = (lm[4].x + lm[8].x) / 2 * w, (lm[4].y + lm[8].y) / 2 * h
        cv2.circle(frame, (int(pinch_cx), int(pinch_cy)), 15, (0, 255, 255), cv2.FILLED)

        # Định nghĩa vùng an toàn (Deadzone)
        top_threshold = 0.4 * h     # Biên trên
        bottom_threshold = 0.6 * h  # Biên dưới

        # Vẽ vạch giới hạn để dễ căn chỉnh
        cv2.line(frame, (0, int(top_threshold)), (w, int(top_threshold)), (0, 255, 255), 1)
        cv2.line(frame, (0, int(bottom_threshold)), (w, int(bottom_threshold)), (0, 255, 255), 1)

        # --- CẤU HÌNH TỐC ĐỘ ---
        BASE_SPEED = 15      # Tốc độ tối thiểu
        SENSITIVITY = 0.5    # Độ nhạy (Càng lớn thì càng nhanh khi ra xa)
        MAX_SPEED = 200      # Giới hạn tốc độ tối đa (để không bị chóng mặt)

        # 1. SCROLL UP (Lăn lên)
        if pinch_cy < top_threshold:
            # Tính khoảng cách từ tay đến vạch trên
            dist = top_threshold - pinch_cy

            # Công thức gia tốc: Tốc độ tăng dần theo khoảng cách
            scroll_speed = int(BASE_SPEED + (dist * SENSITIVITY))

            # Kẹp giá trị không vượt quá MAX
            scroll_speed = min(scroll_speed, MAX_SPEED)

            cv2.putText(frame, f"UP: {scroll_speed}", (int(pinch_cx) + 20, int(pinch_cy)),
                        cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 255), 2)

            pyautogui.scroll(scroll_speed)

        # 2. SCROLL DOWN (Lăn xuống)
        elif pinch_cy > bottom_threshold:
            # Tính khoảng cách từ tay đến vạch dưới
            dist = pinch_cy - bottom_threshold

            scroll_speed = int(BASE_SPEED + (dist * SENSITIVITY))
            scroll_speed = min(scroll_speed, MAX_SPEED)

            cv2.putText(frame, f"DOWN: {scroll_speed}", (int(pinch_cx) + 20, int(pinch_cy)),
                        cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 255), 2)

            pyautogui.scroll(-scroll_speed) # Số âm để lăn xuống

        else:
            # Ở giữa thì không làm gì
            cv2.putText(frame, "HOLD", (int(pinch_cx) + 20, int(pinch_cy)),
                        cv2.FONT_HERSHEY_PLAIN, 1, (200, 200, 200), 1)

        return None

    # 3. LISTENING (Ngón Cái + Út mở: fingers = [1, 0, 0, 0, 1])
    elif fingers == [1, 0, 0, 0, 1]:
        cv2.putText(frame, "LISTENING...", (20, 80), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
        return "LISTEN"

    # 4. LEFT CLICK (Ngón 1 gập, Ngón 2 & 3 mở)
    # fingers[0]=0 (Cái gập), fingers[1]=1 (Trỏ mở), fingers[2]=1 (Giữa mở)
    elif fingers[0] == 0 and fingers[1] == 1 and fingers[2] == 1:
        if current_time - last_action_time > 0.5:
            cv2.putText(frame, "LEFT CLICK", (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
            pyautogui.click()
            last_action_time = current_time
        return None

    # 5. RIGHT CLICK (Ngón 3 gập, Ngón 1 & 2 mở)
    # fingers[0]=1 (Cái mở), fingers[1]=1 (Trỏ mở), fingers[2]=0 (Giữa gập)
    elif fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 0:
        if current_time - last_action_time > 0.5:
            cv2.putText(frame, "RIGHT CLICK", (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
            pyautogui.rightClick()
            last_action_time = current_time
        return None

    # 6. DRAG & DROP (KÉO THẢ)
    # Ngón Cái (4) chạm Ngón Giữa (12), Ngón Trỏ (8) duỗi

    # Tính khoảng cách giữa đầu Ngón Cái và Ngón Giữa
    dist_drag = math.hypot(lm[12].x - lm[4].x, lm[12].y - lm[4].y)

    # Điều kiện: Kìm đóng (<0.05) VÀ Ngón trỏ đang duỗi (fingers[1]==1)
    if dist_drag < 0.05 and fingers[1] == 1:

        # 1. KÍCH HOẠT GIỮ CHUỘT
        if not is_dragging:
            pyautogui.mouseDown() # Nhấn giữ chuột trái
            is_dragging = True

        cv2.putText(frame, "DRAGGING", (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)

        # Vẽ đường nối giữa Cái và Giữa để báo hiệu "Đang giữ"
        cv2.line(frame, (int(lm[4].x*w), int(lm[4].y*h)), (int(lm[12].x*w), int(lm[12].y*h)), (0, 0, 255), 3)

        # Vẽ tâm điều khiển tại NGÓN TRỎ (Để người dùng biết tâm ở đâu)
        cv2.circle(frame, (int(target_x), int(target_y)), 15, (0, 0, 255), cv2.FILLED)

        # 2. XỬ LÝ DI CHUYỂN (THEO NGÓN TRỎ - target_x/y)
        # Vẽ vùng biên
        cv2.rectangle(frame, (MARGIN_LEFT, MARGIN_TOP),
                      (w - MARGIN_RIGHT, h - MARGIN_BOTTOM), (255, 0, 255), 2)

        # Mapping tọa độ từ NGÓN TRỎ (lm[8])
        screen_x = np.interp(target_x, (MARGIN_LEFT, w - MARGIN_RIGHT), (0, SCREEN_W))
        screen_y = np.interp(target_y, (MARGIN_TOP, h - MARGIN_BOTTOM), (0, SCREEN_H))

        # Làm mượt chuyển động
        clocX = int(plocX + (screen_x - plocX) / SMOOTHING)
        clocY = int(plocY + (screen_y - plocY) / SMOOTHING)

        try:
            fast_drag_move(clocX, clocY)
        except:
            pass

        plocX, plocY = clocX, clocY
        return None # Return ngay để không nhảy xuống các lệnh khác

    # NẾU KHÔNG CÒN GESTURE NÀY MÀ ĐANG TRONG TRẠNG THÁI DRAG -> NHẢ CHUỘT
    elif is_dragging:
        pyautogui.mouseUp() # Nhả chuột
        is_dragging = False

    # 7. MOVE MOUSE (Ngón 1, 2, 3 đều mở)
    # fingers[0]=1, fingers[1]=1, fingers[2]=1. Ngón 4, 5 không quan trọng.
    elif fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 1:
        cv2.putText(frame, "MOVING", (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 255), 2)

        # Vẽ vùng biên
        cv2.rectangle(frame, (MARGIN_LEFT, MARGIN_TOP),
                      (w - MARGIN_RIGHT, h - MARGIN_BOTTOM), (255, 0, 255), 2)

        # Mapping tọa độ
        screen_x = np.interp(target_x, (MARGIN_LEFT, w - MARGIN_RIGHT), (0, SCREEN_W))
        screen_y = np.interp(target_y, (MARGIN_TOP, h - MARGIN_BOTTOM), (0, SCREEN_H))

        # Làm mượt chuyển động
        # Lưu ý: Ép kiểu int() ngay tại đây để tránh lỗi tọa độ lẻ
        clocX = int(plocX + (screen_x - plocX) / SMOOTHING)
        clocY = int(plocY + (screen_y - plocY) / SMOOTHING)

        # --- [THAY ĐỔI QUAN TRỌNG Ở ĐÂY] ---
        # BỎ code cũ: pyautogui.moveTo(clocX, clocY)
        # DÙNG code mới:
        try:
            fast_move_mouse(clocX, clocY)
        except:
            pass
        # -----------------------------------

        plocX, plocY = clocX, clocY
        cv2.circle(frame, (int(target_x), int(target_y)), 10, (255, 0, 255), cv2.FILLED)

    return None