import os
import speech_recognition as sr
import edge_tts
import asyncio
import pygame

# Biến kiểm tra trạng thái đang nói
is_speaking = False

# Khởi tạo mixer của pygame một lần duy nhất
try:
    pygame.mixer.init()
except:
    pass

# --- CẤU HÌNH GIỌNG ĐỌC ---
# Giọng Nam (Bắc): "vi-VN-NamMinhNeural" (Rất hay, trầm ấm -> Hợp MARBIS nhất)
# Giọng Nữ (Bắc): "vi-VN-HoaiMyNeural"
VOICE_ID = "vi-VN-NamMinhNeural"


async def _generate_audio(text, filename):
    """Hàm phụ trợ để chạy edge-tts (bất đồng bộ)"""
    communicate = edge_tts.Communicate(text, VOICE_ID)
    await communicate.save(filename)


def speak(text):
    """
    Chuyển văn bản thành giọng nói dùng Microsoft Edge TTS
    """
    global is_speaking

    if not text: return

    # In ra terminal để debug
    print(f"MARBIS: {text}")

    is_speaking = True
    filename = "marbis_voice.mp3"

    try:
        # 1. Tạo file âm thanh (Cần chạy qua asyncio vì edge-tts là async)
        asyncio.run(_generate_audio(text, filename))

        # 2. Phát âm thanh bằng Pygame (Ổn định hơn playsound)
        if os.path.exists(filename):
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()

            # Chờ đọc xong mới làm việc khác
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            # Unload để giải phóng file
            pygame.mixer.music.unload()

    except Exception as e:
        print(f"Lỗi âm thanh: {e}")
    finally:
        is_speaking = False
        # Xóa file rác nếu cần (tùy chọn)
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass


def listen():
    """
    Nghe giọng nói từ Microphone (Giữ nguyên như cũ)
    """
    global is_speaking

    if is_speaking:
        return ""

    r = sr.Recognizer()

    with sr.Microphone() as source:
        print("\nĐang lắng nghe...")
        r.adjust_for_ambient_noise(source, duration=0.5)

        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
            print("Đang xử lý...")
            command = r.recognize_google(audio, language='vi-VN')
            print(f"User: {command}")
            return command.lower()

        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            print("Lỗi kết nối Speech Recognition")
            return ""