import os
import time
import subprocess
import datetime
import webbrowser

try:
    import pyautogui
    import pygetwindow as gw

    HAS_LIB = True
except ImportError:
    HAS_LIB = False
    print(">> [CẢNH BÁO] Thiếu thư viện pyautogui/pygetwindow")


# --- 1. WINDOWS & APP MANAGEMENT ---
def switch_to_window(keyword):
    """Chuyển đổi cửa sổ đang mở"""
    if not HAS_LIB: return False
    try:
        windows = gw.getAllWindows()
        for win in windows:
            if keyword.lower() in win.title.lower() and win.visible:
                if win.isMinimized: win.restore()
                win.activate()
                return True
        return False
    except:
        return False


def open_app_from_start_menu(keyword):
    """Quét Start Menu để tìm ứng dụng"""
    keyword = keyword.lower().strip()
    paths = [
        os.path.join(os.environ["PROGRAMDATA"], r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs")
    ]
    for path in paths:
        if not os.path.exists(path): continue
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith((".lnk", ".url")):
                    name = file.lower().replace(".lnk", "").replace(".url", "")
                    if keyword in name:
                        try:
                            os.startfile(os.path.join(root, file))
                            return True
                        except:
                            pass
    return False


def open_with_windows_search_gui(keyword):
    """Fallback: Dùng Windows Search"""
    if not HAS_LIB: return
    print(f">> Fallback Search GUI: '{keyword}'")
    pyautogui.press('win')
    time.sleep(0.5)
    pyautogui.write(keyword, interval=0.05)
    time.sleep(0.5)
    pyautogui.press('enter')


# --- 2. SYSTEM CONTROLS ---
def handle_system_control(command_code):
    """
    Xử lý lệnh hệ thống dựa trên MÃ LỆNH CHUẨN từ Brain.
    Input: "volume_up", "shutdown", "screenshot"... (Không phải tiếng Việt)
    """
    cmd = command_code.lower()  # Đảm bảo chữ thường

    # --- NHÓM NGUỒN ---
    if cmd == "restart": os.system("shutdown /r /t 10"); return "Khởi động lại sau 10s"
    if cmd == "shutdown": os.system("shutdown /s /t 10"); return "Tắt máy sau 10s"
    if cmd == "cancel_shutdown": os.system("shutdown /a"); return "Đã hủy tắt máy"

    # --- NHÓM PYAUTOGUI ---
    if HAS_LIB:
        if cmd == "volume_up": pyautogui.press("volumeup", presses=5); return "Đã tăng âm."
        if cmd == "volume_down": pyautogui.press("volumedown", presses=5); return "Đã giảm âm."
        if cmd == "mute": pyautogui.press("volumemute"); return "Đã tắt tiếng."
        if cmd == "desktop": pyautogui.hotkey('win', 'd'); return "Về Desktop."

        # --- [ĐÃ CẬP NHẬT] SCREENSHOT & OPEN PAINT NGẦM ---
        if cmd == "screenshot":
            # 1. Tạo tên file và lấy đường dẫn tuyệt đối (quan trọng để Paint đọc được)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{ts}.png"
            file_path = os.path.abspath(filename)

            # 2. Chụp màn hình
            pyautogui.screenshot(file_path)

            # 3. Cấu hình subprocess để mở ngầm (Minimized & No Active)
            try:
                # SW_SHOWMINNOACTIVE = 7 (Hiển thị dạng thu nhỏ và không lấy focus của chuột/bàn phím)
                SW_SHOWMINNOACTIVE = 7

                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = SW_SHOWMINNOACTIVE

                # Mở Paint với đường dẫn file ảnh
                subprocess.Popen(["mspaint.exe", file_path], startupinfo=startupinfo)

                return "Đã chụp và lưu vào Paint."
            except Exception as e:
                print(f"Lỗi mở Paint: {e}")
                return "Đã chụp màn hình (Lỗi mở Paint)."

    return "Không thực hiện được lệnh hệ thống."


# --- 3. BASIC WEB ---
def open_website(url):
    if not url.startswith('http'): url = f"https://{url}"
    if "." not in url: url += ".com"
    webbrowser.open(url)
    return f"Đang mở {url}"