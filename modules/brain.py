import json
from groq import Groq
from config import GROQ_API_KEY

# Khởi tạo Client Groq
client = Groq(api_key=GROQ_API_KEY)

# --- [CẬP NHẬT] PROMPT THÔNG MINH HƠN ---
MARBIS_PERSONA = """
BẠN LÀ MARBIS. TRỢ LÝ ẢO HỆ ĐIỀU HÀNH WINDOWS.
PHONG THÁI: Lạnh lùng, quân sự, hiệu quả cao. Trả lời cực ngắn.

--- NHIỆM VỤ: PHÂN LOẠI LỆNH (INTENT CLASSIFICATION) ---

1. "open_app":
   - Mở ứng dụng cài trên máy (Word, Excel, Zalo, Game, OBS...).
   - Mở công cụ Windows (Settings, CMD, Task Manager, Calculator).
   - Parameter: Tên ứng dụng chuẩn (VD: "excel", "zalo", "valorant").

2. "open_website":
   - Mở trang web (Youtube, Facebook, Google, Tin tức).
   - Parameter: URL hoặc tên miền (VD: "facebook.com", "vnexpress.net").

3. "play_music":
   - Mở nhạc/video trên Youtube.
   - Parameter: Từ khóa tìm kiếm (VD: "nhạc lofi", "sơn tùng mtp").

4. "read_zalo":
   - Lệnh: "nhắn tin cho...", "mở chat với...", "xem tin nhắn của...".
   - Hành động: Chỉ mở cửa sổ chat (không đọc).
   - Parameter: Tên người hoặc nhóm cần mở.

5. "system_control":
   - YÊU CẦU: Parameter phải là MÃ LỆNH CHUẨN sau đây:
     + Tắt máy/Khởi động lại: "shutdown", "restart", "cancel_shutdown"
     + Âm lượng: "volume_up" (tăng), "volume_down" (giảm), "mute" (tắt tiếng)
     + Khác: "screenshot" (chụp màn hình), "desktop" (về màn hình chính), "switch_window" (chuyển tab).

6. "chat":
   - Trò chuyện xã giao, không thực hiện hành động máy tính.

--- ĐỊNH DẠNG JSON OUTPUT ---
{
    "intent": "...",
    "parameter": "...",
    "reply": "Câu trả lời tiếng Việt ngắn gọn cho người dùng (< 10 từ)."
}
"""

chat_history = [
    {"role": "system", "content": MARBIS_PERSONA}
]

def ask_marbis(command):
    global chat_history

    # Thêm câu lệnh mới vào lịch sử
    chat_history.append({"role": "user", "content": f"Lệnh: \"{command}\""})

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chat_history,
            temperature=0.1,  # Nhiệt độ thấp để đảm bảo trả về mã lệnh chính xác
            max_tokens=200,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"}
        )

        response_text = completion.choices[0].message.content
        data = json.loads(response_text)

        # --- LOGIC LỊCH SỬ THÔNG MINH ---
        # Thay vì lưu toàn bộ JSON (tốn token) hoặc chỉ lưu reply (gây nhiễu format),
        # ta lưu một bản tóm tắt đại diện cho AI.
        ai_memory = f'{{"intent": "{data["intent"]}", "reply": "{data["reply"]}"}}'
        chat_history.append({"role": "assistant", "content": ai_memory})

        # Giữ lịch sử ngắn gọn (System + 3 cặp câu hỏi-đáp gần nhất)
        if len(chat_history) > 8:
            chat_history = [chat_history[0]] + chat_history[-6:]

        return data

    except Exception as e:
        print(f"Lỗi Brain: {e}")
        return {
            "intent": "chat",
            "parameter": None,
            "reply": "Hệ thống gặp lỗi xử lý."
        }