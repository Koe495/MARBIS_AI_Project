import os
import speech_recognition as sr
import edge_tts
import asyncio
import threading
import subprocess
import shutil
import io
import time

# =======================
# CẤU HÌNH
# =======================
VOICE_ID = "vi-VN-NamMinhNeural"
MPV_PATH = "mpv.exe"

# =======================
# BIẾN KIỂM SOÁT
# =======================
stop_flag = threading.Event()
tts_thread = None

# Kiểm tra MPV
HAS_MPV = os.path.exists(MPV_PATH) or shutil.which("mpv")

# [QUAN TRỌNG] Khởi tạo Recognizer toàn cục để giữ cấu hình sau khi calibrate
recognizer = sr.Recognizer()


# =======================
# HELPER: SAFE ASYNC RUN
# =======================
def run_async(coro):
    """Chạy coroutine an toàn trong thread riêng"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


# =======================
# CORE: STREAMING TTS → MPV
# =======================
async def _stream_via_mpv(text):
    communicate = edge_tts.Communicate(text, VOICE_ID)
    cmd = [MPV_PATH, "--no-cache", "--no-terminal", "--really-quiet", "--", "fd://0"]

    process = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    try:
        async for chunk in communicate.stream():
            if stop_flag.is_set():
                process.terminate()
                return

            if chunk["type"] == "audio" and process.stdin:
                process.stdin.write(chunk["data"])
                process.stdin.flush()
    except Exception as e:
        print(f"[TTS-MPV] Error: {e}")
    finally:
        if process.stdin:
            try:
                process.stdin.close()
            except:
                pass
        process.wait()


# =======================
# CORE: FALLBACK PYGAME
# =======================
async def _play_via_pygame_ram(text):
    try:
        import pygame
        pygame.mixer.init()
    except:
        return

    communicate = edge_tts.Communicate(text, VOICE_ID)
    memory_file = io.BytesIO()

    try:
        async for chunk in communicate.stream():
            if stop_flag.is_set(): return
            if chunk["type"] == "audio": memory_file.write(chunk["data"])
    except:
        return

    memory_file.seek(0)
    if stop_flag.is_set(): return

    try:
        pygame.mixer.music.load(memory_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if stop_flag.is_set():
                pygame.mixer.music.stop()
                break
            await asyncio.sleep(0.05)
    except:
        pass


# =======================
# WORKER THREAD
# =======================
def _speak_worker(text):
    stop_flag.clear()
    print(f"MARBIS: {text}")
    try:
        if HAS_MPV:
            run_async(_stream_via_mpv(text))
        else:
            run_async(_play_via_pygame_ram(text))
    except Exception as e:
        print(f"[TTS] Worker error: {e}")


# =======================
# PUBLIC API (SPEAK)
# =======================
def speak(text):
    global tts_thread
    if not text: return
    stop_speaking()
    tts_thread = threading.Thread(target=_speak_worker, args=(text,), daemon=True)
    tts_thread.start()


def stop_speaking():
    stop_flag.set()


# =======================
# PUBLIC API (LISTEN) - ĐÃ CẬP NHẬT
# =======================

def calibrate_mic():
    """Đo độ ồn phòng để thiết lập ngưỡng nghe phù hợp"""
    print(">> [INFO] Đang cân chỉnh Mic... (Giữ im lặng 1s)")
    with sr.Microphone() as source:
        # Lấy mẫu tiếng ồn
        recognizer.adjust_for_ambient_noise(source, duration=1.2)

        # Tự động điều chỉnh ngưỡng năng lượng
        recognizer.dynamic_energy_threshold = True

        # Thiết lập ngưỡng tối thiểu (thấp hơn = nhạy hơn)
        # Nếu phòng ồn, hãy tăng số này lên (vd: 300)
        recognizer.energy_threshold = max(recognizer.energy_threshold, 150)

        recognizer.pause_threshold = 0.8  # Thời gian chờ hết câu
    print(f">> [INFO] Đã cân chỉnh xong. Ngưỡng: {recognizer.energy_threshold}")


def listen():
    with sr.Microphone() as source:
        # Xóa dòng print "Đang lắng nghe" để tránh spam console
        try:
            audio = recognizer.listen(
                source,
                timeout=4,  # Chờ tối đa 4s để bắt đầu nói
                phrase_time_limit=8  # Cho phép nói câu dài tối đa 8s
            )
            cmd = recognizer.recognize_google(audio, language="vi-VN")
            # print(f"Raw Input: {cmd}") # Debug nếu cần
            return cmd.lower()

        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            print("! Lỗi mạng Google Speech API")
            return ""
        except Exception:
            return ""