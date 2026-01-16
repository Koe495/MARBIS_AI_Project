import os
import time
import subprocess
import webbrowser
import pyperclip
from modules import general_skills as gen

try:
    import pyautogui

    HAS_LIB = True
except ImportError:
    HAS_LIB = False

# Đường dẫn mặc định Zalo (có thể khác tùy máy)
ZALO_PATH_DEFAULT = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Zalo", "Zalo.exe")


# ==========================================================
# 1. QUẢN LÝ MỞ ỨNG DỤNG (CHUYỂN TỪ SKILLS.PY SANG)
# ==========================================================
def open_custom_application(app_name):
    """
    Xử lý mở các ứng dụng đặc biệt hoặc theo tên gọi tắt.
    Trả về True nếu mở thành công, False nếu không tìm thấy trong list này.
    """
    cmd = app_name.lower().strip()

    # Từ điển ánh xạ tên gọi -> Lệnh chạy (CMD Command)
    # Bạn có thể thêm bất cứ app nào vào đây
    app_map = {
        # --- System ---
        "settings": "start ms-settings:",
        "cài đặt": "start ms-settings:",
        "task manager": "start taskmgr",
        "quản lý tác vụ": "start taskmgr",
        "calculator": "start calc",
        "máy tính": "start calc",
        "notepad": "start notepad",
        "ghi chú": "start notepad",
        "cmd": "start cmd",
        "terminal": "start wt",

        # --- Office ---
        "word": "start winword",
        "excel": "start excel",
        "powerpoint": "start powerpnt",

        # --- Browsers ---
        "chrome": "start chrome",
        "edge": "start msedge",
        "cốc cốc": "start coccoc",

        # --- Social ---
        "zalo": "start zalo",  # Yêu cầu Zalo đã thêm vào Path hoặc Start Menu
        "spotify": "start spotify"
    }

    if cmd in app_map:
        print(f">> [SPECIAL] Opening predefined app: {cmd}")
        try:
            os.system(app_map[cmd])
            return True
        except Exception as e:
            print(f"Lỗi mở app {cmd}: {e}")
            return False

    return False


# ==========================================================
# 2. ZALO SPECIALIST (MACRO PHỨC TẠP)
# ==========================================================
def action_zalo_open_chat(person_name):
    """Mở Zalo và vào khung chat với người cụ thể"""
    if not HAS_LIB: return "Thiếu thư viện pyautogui."

    print(f">> [ZALO] Open Chat: {person_name}")

    # 1. Thử switch qua cửa sổ Zalo nếu đang mở
    if not gen.switch_to_window("Zalo"):
        # 2. Nếu chưa mở thì bật lên
        if os.path.exists(ZALO_PATH_DEFAULT):
            subprocess.Popen(ZALO_PATH_DEFAULT)
        else:
            # Fallback: Gọi hàm mở app chung
            gen.open_app_from_start_menu("zalo")
        time.sleep(2)  # Chờ app lên

    time.sleep(0.5)

    try:
        # Macro: Ctrl+F -> Gõ tên -> Enter
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(0.3)

        # Dùng clipboard để gõ tiếng Việt chính xác
        pyperclip.copy(person_name)
        pyautogui.hotkey('ctrl', 'v')

        time.sleep(0.8)  # Chờ Zalo search
        pyautogui.press('enter')

        return f"Đã mở tin nhắn của {person_name}."
    except Exception as e:
        print(f"Lỗi Zalo: {e}")
        return "Lỗi thao tác Zalo."


# ==========================================================
# 3. YOUTUBE / WEB MEDIA
# ==========================================================
def action_play_music(song_name):
    """Mở nhạc trên Youtube"""
    query = song_name.replace(" ", "+")
    url = f"https://www.youtube.com/results?search_query={query}"

    # Có thể mở rộng: Tự bấm vào video đầu tiên bằng pyautogui nếu muốn
    webbrowser.open(url)
    return f"Đang tìm {song_name} trên Youtube"