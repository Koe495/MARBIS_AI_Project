import os
import time
import subprocess
import datetime
import webbrowser
import threading

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
            ts = datetime.datetime.now().strftime("%H%M%S")
            pyautogui.screenshot(f"screenshot_{ts}.png")
            return "Đã chụp màn hình."

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
    """
    if not HAS_LIB: return "Thiếu thư viện deep-translator."

    try:
        # 1. Clear clipboard cũ để tránh nhận nhầm
        pyperclip.copy("")

        # 2. Ctrl + C
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.2)

        # 3. Lấy text
        text = pyperclip.paste()
        if not text: return "Không copy được văn bản nào."

        print(f">> Original: {text}")

        # 4. Dịch
        translator = GoogleTranslator(source='auto', target='vi')
        translated = translator.translate(text)

        print(f">> Translated: {translated}")
        return f"Dịch là: {translated}"

    except Exception as e:
        print(f"Lỗi dịch: {e}")
        return "Lỗi dịch thuật."


# =======================
# 4. APP & WEB
# =======================
def open_website(url):
    if not url.startswith('http'): url = f"https://{url}"
    if "." not in url: url += ".com"
    webbrowser.open(url)


def open_app_from_start_menu(keyword):
    # (Giữ nguyên code cũ của bạn đoạn này vì nó ổn rồi)
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