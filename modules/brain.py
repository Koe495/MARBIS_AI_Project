import json
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

# --- PROMPT (ĐÃ CHỈNH SỬA) ---
MARBIS_PERSONA = """
BẠN LÀ MARBIS. TRỢ LÝ ẢO WINDOWS.
PHONG THÁI: Lạnh lùng, ngắn gọn, hiệu quả.

--- NHIỆM VỤ: PHÂN LOẠI LỆNH (JSON OUTPUT) ---

1. **system_control** (Điều khiển hệ thống):
   - "Chia màn hình trái" -> param: "snap_left"
   - "Chia màn hình phải" -> param: "snap_right"
   - "Phóng to" -> param: "maximize"
   - "Thu nhỏ/Ẩn cái này" -> param: "minimize"
   - "Về màn hình chính/Ẩn tất cả" -> param: "show_desktop"
   - "Tắt máy" -> param: "shutdown"

2. **translate_selection** (Dịch thuật):
   - "Dịch đoạn này", "Dịch cái đang chọn" -> param: "auto"

3. **type_text** (Gõ nguyên văn):
   - "Gõ...", "Viết dòng..." -> param: NỘI DUNG CHÍNH XÁC.

4. **generate_text** (Sáng tạo):
   - "Soạn email...", "Viết bài văn..." -> param: CHỦ ĐỀ.

5. **open_app** (Mở ứng dụng):
   - param: Tên app chuẩn (VD: Spotify, Zalo, Chrome, Word, Excel).
   - QUAN TRỌNG: Reply phải nhắc lại tên App. VD: "Đang mở Word", "Đang bật Zalo".

6. **open_website**:
   - param: URL hoặc tên miền.

7. **read_zalo** / **open_chat**:
   - Nhắn tin Zalo. param: Tên người nhận.

--- FORMAT JSON ---
{
    "intent": "tên_lệnh",
    "parameter": "tham_số_chuẩn",
    "reply": "Câu trả lời ngắn gọn. Với lệnh open_app, BẮT BUỘC nhắc tên app."
}
"""

chat_history = [
    {"role": "system", "content": MARBIS_PERSONA}
]


def ask_marbis(command):
    global chat_history
    chat_history.append({"role": "user", "content": command})

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chat_history,
            temperature=0.1,  # Giữ thấp để output ổn định
            max_tokens=200,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"}
        )

        response_text = completion.choices[0].message.content
        data = json.loads(response_text)

        # [OPTIONAL - DỰ PHÒNG]
        # Nếu AI quên nhắc tên app, ta có thể cưỡng ép bằng Python ở đây:
        if data.get("intent") == "open_app" and "mở" in data.get("reply").lower():
             # Nếu reply ngắn quá (VD: "Đang mở"), ta nối thêm parameter vào
             if len(data["reply"].split()) < 3:
                 data["reply"] = f"Đang mở {data.get('parameter')}"

        # Lưu lịch sử ngắn
        ai_memory = f'{{"intent": "{data.get("intent")}", "reply": "{data.get("reply")}"}}'
        chat_history.append({"role": "assistant", "content": ai_memory})

        # Giữ lịch sử ngắn gọn (4 cặp hội thoại gần nhất)
        if len(chat_history) > 9:
            chat_history = [chat_history[0]] + chat_history[-8:]

        return data

    except Exception as e:
        print(f"Lỗi Brain: {e}")
        return {"intent": "chat", "reply": "Lỗi xử lý não bộ."}


# Hàm sáng tạo nội dung
def generate_content_by_topic(topic):
    print(f">> [BRAIN] Generating: {topic}")
    prompt = f"Viết nội dung ngắn gọn cho: {topic}. Chỉ trả về nội dung text, không giải thích."
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1500
        )
        return completion.choices[0].message.content.strip()
    except:
        return "Lỗi tạo nội dung."