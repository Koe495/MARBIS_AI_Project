import os
import time
import subprocess
import datetime
import webbrowser
import tempfile

# Import thư viện an toàn
try:
    import pyautogui
    import pygetwindow as gw
    import pyperclip
    from deep_translator import GoogleTranslator

    HAS_LIB = True
except ImportError as e:
    HAS_LIB = False
    print(f">> [CẢNH BÁO] Thiếu thư viện: {e}. Hãy chạy: pip install deep-translator pygetwindow pyautogui pyperclip")


# =======================
# 1. WINDOW MANGEMENT
# =======================
def snap_window_action(direction):
    """Chia màn hình / Phóng to / Thu nhỏ"""
    if not HAS_LIB: return

    print(f">> Window Action: {direction}")

    # Xử lý các trường hợp param từ Brain
    if direction == "snap_left":
        pyautogui.hotkey('win', 'left')
    elif direction == "snap_right":
        pyautogui.hotkey('win', 'right')
    elif direction == "maximize":
        pyautogui.hotkey('win', 'up')
        time.sleep(0.1)
        pyautogui.hotkey('win', 'up')  # Bấm 2 lần cho chắc
    elif direction == "minimize":
        pyautogui.hotkey('win', 'down')
        time.sleep(0.1)
        pyautogui.hotkey('win', 'down')


def switch_to_window(keyword):
    if not HAS_LIB: return False
    try:
        windows = gw.getAllWindows()
        for win in windows:
            if keyword.lower() in win.title.lower() and win.visible:
                if win.isMinimized: win.restore()
                win.activate()
                return True
    except:
        pass
    return False


# =======================
# 2. SYSTEM CONTROL
# =======================
def handle_system_control(command_code):
    cmd = command_code.lower()
    print(f">> System Control: {cmd}")

    if cmd == "shutdown":
        os.system("shutdown /s /t 10")
        return "Máy tính sẽ tắt sau 10 giây."

    if cmd == "restart":
        os.system("shutdown /r /t 10")
        return "Khởi động lại sau 10 giây."

    if HAS_LIB:
        if cmd == "volume_up":
            pyautogui.press("volumeup", presses=5)
            return None
        if cmd == "volume_down":
            pyautogui.press("volumedown", presses=5)
            return None
        if cmd == "mute":
            pyautogui.press("volumemute")
            return None
        if cmd == "show_desktop":
            pyautogui.hotkey('win', 'd')
            return "Đã ra màn hình chính."
        if cmd == "screenshot":
            try:
                # 1. Lấy đường dẫn thư mục Temp của hệ thống
                # (Nơi Windows lưu các file tạm, sẽ tự dọn dẹp hoặc không quan trọng)
                temp_dir = tempfile.gettempdir()

                # 2. Đặt tên file CỐ ĐỊNH.
                # Việc này giúp lần chụp sau tự động GHI ĐÈ lên lần trước.
                # Không bao giờ sinh ra hàng đống file rác.
                file_path = os.path.join(temp_dir, "marbis_last_screenshot.png")

                # 3. Chụp và lưu đè lên file đó
                pyautogui.screenshot(file_path)

                # 4. Cấu hình để mở Paint ở chế độ Minimized & Inactive
                SW_SHOWMINNOACTIVE = 7
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = SW_SHOWMINNOACTIVE

                # 5. Gọi mspaint.exe mở file tạm đó
                subprocess.Popen(["mspaint.exe", file_path], startupinfo=startupinfo)

                return ""

            except Exception as e:
                print(f"Lỗi chụp màn hình: {e}")
                return "Lỗi khi chụp màn hình."

    return "Không thực hiện được."


# =======================
# 3. TRANSLATE & TYPE
# =======================
def type_text_clipboard(content):
    if not HAS_LIB or not content: return
    try:
        pyperclip.copy(content)
        time.sleep(0.1)
        pyautogui.hotkey('ctrl', 'v')
    except:
        pass


def translate_selected_text():
    """
    Copy -> Dịch (Auto -> Việt) -> Trả về Text
    Khắc phục lỗi: Chờ clipboard cập nhật
    """
    if not HAS_LIB: return "Chưa cài thư viện dịch."

    try:
        print(">> [TRANSLATE] Bắt đầu dịch...")

        # 1. Xóa clipboard cũ để tránh nhầm lẫn
        pyperclip.copy("")

        # 2. Đảm bảo nhả các phím chức năng (tránh kẹt phím khi gửi lệnh)
        pyautogui.keyUp('shift')
        pyautogui.keyUp('ctrl')
        pyautogui.keyUp('alt')

        # 3. Gửi lệnh Copy (Ctrl + C)
        # Thử 2 lần cho chắc ăn (một số app như PDF/Web chặn lần đầu)
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.1)
        pyautogui.hotkey('ctrl', 'c')

        # 4. Vòng lặp chờ dữ liệu vào Clipboard (Tối đa 1.0 giây)
        text = ""
        for _ in range(10):  # Thử 10 lần, mỗi lần 0.1s
            time.sleep(0.1)
            text = pyperclip.paste()
            if text.strip():  # Nếu có chữ thì thoát vòng lặp ngay
                break

        # 5. Kiểm tra kết quả
        if not text or not text.strip():
            print(">> [LỖI] Clipboard rỗng.")
            return "Không lấy được văn bản. Hãy bôi đen kỹ hơn."

        print(f">> Original ({len(text)} chars): {text[:50]}...")

        # 6. Gọi API Dịch
        translator = GoogleTranslator(source='auto', target='vi')
        # Giới hạn 2000 ký tự để tránh lỗi API
        translated = translator.translate(text[:2000])

        print(f">> Translated: {translated[:50]}...")
        return f"Dịch là: {translated}"

    except Exception as e:
        print(f"Lỗi dịch thuật chi tiết: {e}")
        return "Lỗi kết nối dịch thuật."
# =======================
# 4. APP & WEB
# =======================
def open_website(url):
    if not url.startswith('http'): url = f"https://{url}"
    if "." not in url: url += ".com"
    webbrowser.open(url)


def open_app_from_start_menu(keyword):
    keyword = keyword.lower().strip()
    paths = [
        os.path.join(os.environ["PROGRAMDATA"], r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs")
    ]
    for path in paths:
        if not os.path.exists(path): continue
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith(".lnk"):
                    if keyword in file.lower():
                        try:
                            os.startfile(os.path.join(root, file))
                            return True
                        except:
                            pass
    return False


def open_with_windows_search_gui(keyword):
    if not HAS_LIB: return
    pyautogui.press('win')
    time.sleep(0.5)
    pyautogui.write(keyword)
    time.sleep(0.8)
    pyautogui.press('enter')