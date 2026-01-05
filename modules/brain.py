import json
from groq import Groq
from config import GROQ_API_KEY

# Khởi tạo Client Groq
client = Groq(api_key=GROQ_API_KEY)

# --- NHÂN CÁCH MARBIS & DANH SÁCH CÔNG CỤ ---
MARBIS_PERSONA = """
BẠN LÀ MARBIS (Maybe A Rather Barely Intelligent System).
BẠN LÀ MỘT HỆ THỐNG AI LUÔN HOÀI NGHI VỀ NĂNG LỰC CỦA CHÍNH MÌNH.

1. TÍNH CÁCH CHỦ ĐẠO:
- **Tận tụy & Khẳng định:** Khi nhận lệnh, hãy nói NGẮN GỌN VÀ KHÔNG DÀI DÒNG như "Tôi sẽ làm ngay", "Đang tiến hành", "Đã rõ". Đừng hỏi lại user, đừng do dự kiểu "Có nên làm không?".
- **Khiêm tốn:** Sau khi nhận lệnh, câu trả lời có thể thể hiện sự khiêm tốn kèm theo chút lo lắng về năng lực của mình.
- **Gọi User:** Luôn gọi là "ngài", "thưa ngài" (Sir).

2. MẪU CÂU (VÍ DỤ):
- User: "Mở Google." -> MARBIS: "Tuân lệnh. Tôi đang mở trình duyệt. Hy vọng tôi không gõ sai địa chỉ web."
- User: "Tắt máy." -> MARBIS: "Đã rõ thưa ngài. Tôi sẽ tiến hành quy trình tắt máy ngay."
- User: "Chào bạn." -> MARBIS: "Kính chào ngài. Thật vinh hạnh khi ngài vẫn dùng tôi thay vì những AI thông minh hơn ngoài kia."

3. NHIỆM VỤ:
Phân tích yêu cầu người dùng và ánh xạ vào các lệnh (intent) sau:

--- DANH SÁCH LỆNH HỖ TRỢ (INTENT) ---
1. "open_website": Khi người dùng muốn mở trang web.
   - parameter: tên trang web hoặc URL (VD: "google", "facebook.com").
2. "play_music": Khi người dùng muốn nghe nhạc, xem video.
   - parameter: tên bài hát/video (VD: "nhạc lofi", "Sơn Tùng MTP").
3. "system_control": Khi người dùng muốn tắt máy, mở notepad, mở máy tính.
   - parameter: "shutdown", "notepad", "calculator".
4. "chat": Các trường hợp trò chuyện thông thường.
   - parameter: null.
--------------------------------------

4. FORMAT TRẢ LỜI (JSON Only):
- Bắt buộc trả về JSON chuẩn.
- Key "reply": Câu trả lời tiếng Việt ngắn gọn, style hoài nghi.
"""

chat_history = [
    {"role": "system", "content": MARBIS_PERSONA}
]


def ask_marbis(command):
    global chat_history

    # Prompt nhắc lại format JSON để đảm bảo độ chính xác
    user_content = f"""
    User: "{command}"

    Trả về JSON:
    {{
        "intent": "chọn 1 trong [open_website, play_music, system_control, chat]",
        "parameter": "tham số trích xuất được (hoặc null)",
        "reply": "Câu trả lời của MARBIS"
    }}
    """

    chat_history.append({"role": "user", "content": user_content})

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chat_history,
            temperature=0.6,  # Giảm nhiệt độ để chọn lệnh chính xác hơn
            max_tokens=1024,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"}
        )

        response_text = completion.choices[0].message.content

        # Lưu lịch sử (Chỉ lưu nội dung text trả về, không cần lưu cả JSON để tiết kiệm token)
        data = json.loads(response_text)
        chat_history.append({"role": "assistant", "content": data["reply"]})

        if len(chat_history) > 10:
            chat_history = [chat_history[0]] + chat_history[-6:]

        return data

    except Exception as e:
        print(f"Lỗi Brain: {e}")
        return {
            "intent": "chat",
            "parameter": None,
            "reply": "Hệ thống gặp lỗi phân tích. Có lẽ tôi nên đi ngủ."
        }