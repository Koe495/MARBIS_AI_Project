from modules import brain
from modules import general_skills as gen
from modules import specialized_skills as spec


def execute_command(data):
    if not data or not isinstance(data, dict): return "Lỗi dữ liệu."

    intent = data.get('intent')
    clean_param = data.get('parameter', '').strip()

    print(f"⚡ [ROUTER] Intent: {intent} | Param: {clean_param}")

    try:
        # --- 1. NHÓM ỨNG DỤNG & GIẢI TRÍ (Đã chuyển hết sang Spec) ---
        if intent == "open_app":
            # Bước 1: Kiểm tra trong danh sách app đặc biệt (Word, Excel...)
            if spec.open_custom_application(clean_param):
                return None

            # Bước 2: Quét Start Menu
            if gen.open_app_from_start_menu(clean_param):
                return None

            # Bước 3: Fallback dùng Windows Search
            gen.open_with_windows_search_gui(clean_param)
            return None

        elif intent in ["read_zalo", "open_chat"]:
            spec.action_zalo_open_chat(clean_param)
            return None

        elif intent == "play_music":
            spec.action_play_music(clean_param)
            return None

        elif intent == "open_website":
            gen.open_website(clean_param)
            return None

        # --- 2. NHÓM HỆ THỐNG (Giữ ở General) ---
        elif intent == "system_control":
            window_cmds = ["snap_left", "snap_right", "maximize", "minimize"]

            if clean_param in window_cmds:
                gen.snap_window_action(clean_param)
            elif clean_param in ["show_desktop", "minimize_all"]:
                gen.handle_system_control("show_desktop")
            else:
                return gen.handle_system_control(clean_param)
            return None

        # --- 3. NHÓM VĂN BẢN & DỊCH ---
        elif intent == "translate_selection":
            return gen.translate_selected_text()

        elif intent == "type_text":
            gen.type_text_clipboard(clean_param)
            return None

        elif intent == "generate_text":
            content = brain.generate_content_by_topic(clean_param)
            gen.type_text_clipboard(content)
            return "Đã soạn xong."

    except Exception as e:
        print(f"Lỗi Router: {e}")
        return "Có lỗi xảy ra."

    return None