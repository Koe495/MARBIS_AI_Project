import webbrowser
import os
import subprocess
import platform


def execute_command(data):
    """
    Hàm nhận dữ liệu JSON từ Brain và thực thi lệnh tương ứng.
    Data format: {"intent": "...", "parameter": "...", "reply": "..."}
    """
    intent = data.get('intent')  # Lấy lệnh
    param = data.get('parameter')  # Lấy tham số

    print(f"⚡ [MARBIS ACTION] Intent: {intent} | Param: {param}")

    try:
        # --- 1. MỞ WEBSITE ---
        if intent == "open_website":
            # Xử lý nếu param không có https
            url = param.lower()
            if not url.startswith('http'):
                url = f"https://{url}"
            if "." not in url:  # Nếu chỉ nói "mở facebook" -> thêm .com
                url += ".com"
            webbrowser.open(url)

        # --- 2. MỞ NHẠC (YOUTUBE) ---
        elif intent == "play_music":
            # Tạo link search youtube
            query = param.replace(" ", "+")
            url = f"https://www.youtube.com/results?search_query={query}"
            webbrowser.open(url)

        # --- 3. ĐIỀU KHIỂN HỆ THỐNG ---
        elif intent == "system_control":
            cmd = param.lower()

            if "shutdown" in cmd or "tắt máy" in cmd:
                # Cảnh báo trước khi tắt (Windows)
                os.system("shutdown /s /t 10")

            elif "notepad" in cmd or "ghi chú" in cmd:
                subprocess.Popen("notepad.exe")

            elif "calculator" in cmd or "máy tính" in cmd:
                subprocess.Popen("calc.exe")

    except Exception as e:
        print(f"Lỗi thực thi skill: {e}")