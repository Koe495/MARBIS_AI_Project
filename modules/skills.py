from modules import general_skills as gen
from modules import specialized_skills as spec


def execute_command(data):
    """
    Router: Nhận intent từ Brain -> Điều hướng sang General hoặc Specialized Skills
    """
    if not data or not isinstance(data, dict): return "Lỗi dữ liệu."

    intent = data.get('intent')
    param = data.get('parameter', '') if data.get('parameter') else ""
    clean_param = param.strip()

    print(f"⚡ [ROUTER] Intent: {intent} | Param: {clean_param}")

    try:
        # --- 1. SPECIALIZED SKILLS ---
        if intent == "read_zalo" or intent == "open_chat":
            if not clean_param: return "Bạn muốn nhắn tin với ai?"
            # Vẫn trả về text để Main biết đã xong (hoặc bạn có thể để None nếu muốn im lặng hoàn toàn)
            spec.action_zalo_open_chat(clean_param)
            return None

        elif intent == "play_music":
            spec.action_play_music(clean_param)
            return None

        # --- 2. GENERAL SKILLS ---
        elif intent == "system_control":
            # Các lệnh hệ thống quan trọng thì có thể giữ lại thông báo kết quả
            return gen.handle_system_control(clean_param)

        elif intent == "open_website":
            gen.open_website(clean_param)
            return None

        elif intent == "open_app":
            # Xử lý các app đặc biệt
            special_apps = {
                "settings": "start ms-settings:", "cài đặt": "start ms-settings:",
                "task manager": "start taskmgr", "calculator": "start calc",
                "notepad": "start notepad", "cmd": "start cmd"
            }
            if clean_param.lower() in special_apps:
                import os
                os.system(special_apps[clean_param.lower()])
                return None

            # App thường
            if gen.open_app_from_start_menu(clean_param):
                return None

            # Fallback
            gen.open_with_windows_search_gui(clean_param)
            return None

    except Exception as e:
        print(f"Lỗi Router Skill: {e}")
        return "Có lỗi xảy ra."  # Chỉ nói khi có lỗi thật sự

    return None