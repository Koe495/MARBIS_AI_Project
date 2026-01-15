import os
import time
import subprocess
import webbrowser
import pyperclip  # Riêng cho Zalo cần cái này
from modules import general_skills as gen  # Import module chung

try:
    import pyautogui

    HAS_LIB = True
except ImportError:
    HAS_LIB = False

ZALO_PATH_DEFAULT = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Zalo", "Zalo.exe")


# --- ZALO SPECIALIST ---
def action_zalo_open_chat(person_name):
    """Mở Zalo và vào khung chat với người cụ thể"""
    if not HAS_LIB: return "Thiếu thư viện pyautogui."

    print(f">> [ZALO] Open Chat: {person_name}")

    # 1. Tận dụng hàm switch_to_window của general_skills
    if not gen.switch_to_window("Zalo"):
        if os.path.exists(ZALO_PATH_DEFAULT):
            subprocess.Popen(ZALO_PATH_DEFAULT)
        else:
            gen.open_app_from_start_menu("zalo")
        time.sleep(2)

    time.sleep(0.5)

    try:
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(0.3)
        pyperclip.copy(person_name)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.8)
        pyautogui.press('enter')
        return f"Đã mở tin nhắn của {person_name}."
    except Exception as e:
        print(f"Lỗi Zalo: {e}")
        return "Lỗi thao tác Zalo."


# --- YOUTUBE SPECIALIST ---
def action_play_music(song_name):
    query = song_name.replace(" ", "+")
    url = f"https://www.youtube.com/results?search_query={query}"
    webbrowser.open(url)
    return f"Đang tìm {song_name} trên Youtube"