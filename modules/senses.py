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
MPV_PATH = "mpv.exe"  # Đặt mpv.exe cùng thư mục hoặc trong PATH

# =======================
# BIẾN KIỂM SOÁT
# =======================
stop_flag = threading.Event()
tts_thread = None

# Kiểm tra MPV
HAS_MPV = os.path.exists(MPV_PATH) or shutil.which("mpv")

# =======================
# HELPER: SAFE ASYNC RUN
# =======================
def run_async(coro):
    """
    Chạy coroutine an toàn trong thread riêng
    (tránh lỗi asyncio.run() nhiều lần)
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


# =======================
# CORE: STREAMING TTS → MPV (ƯU TIÊN)
# =======================
async def _stream_via_mpv(text):
    communicate = edge_tts.Communicate(text, VOICE_ID)

    cmd = [
        MPV_PATH,
        "--no-cache",
        "--no-terminal",
        "--really-quiet",
        "--",
        "fd://0"
    ]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    try:
        async for chunk in communicate.stream():
            if stop_flag.is_set():
                process.terminate()
                try:
                    process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    process.kill()
                return

            if chunk["type"] == "audio" and process.stdin:
                process.stdin.write(chunk["data"])
                process.stdin.flush()

    except Exception as e:
        print(f"[TTS-MPV] Streaming error: {e}")

    finally:
        if process.stdin:
            try:
                process.stdin.close()
            except:
                pass
        process.wait()


# =======================
# CORE: FALLBACK RAM BUFFER (Pygame)
# =======================
async def _play_via_pygame_ram(text):
    try:
        import pygame
        pygame.mixer.init()
    except Exception as e:
        print("[TTS] Không thể init Pygame:", e)
        return

    communicate = edge_tts.Communicate(text, VOICE_ID)
    memory_file = io.BytesIO()

    try:
        async for chunk in communicate.stream():
            if stop_flag.is_set():
                return
            if chunk["type"] == "audio":
                memory_file.write(chunk["data"])
    except Exception as e:
        print("[TTS] Lỗi tải audio:", e)
        return

    memory_file.seek(0)

    if stop_flag.is_set():
        return

    try:
        pygame.mixer.music.load(memory_file)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            if stop_flag.is_set():
                pygame.mixer.music.stop()
                break
            await asyncio.sleep(0.05)
    except Exception as e:
        print("[TTS] Lỗi phát audio:", e)


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
            print(">> (Đang dùng Pygame fallback – cài mpv để nói nhanh hơn)")
            run_async(_play_via_pygame_ram(text))
    except Exception as e:
        print(f"[TTS] Worker error: {e}")


# =======================
# PUBLIC API
# =======================
def speak(text):
    """
    Nói văn bản (ngắt câu cũ nếu đang nói)
    """
    global tts_thread
    if not text:
        return

    stop_speaking()

    tts_thread = threading.Thread(
        target=_speak_worker,
        args=(text,),
        daemon=True
    )
    tts_thread.start()


def stop_speaking():
    """
    Ngắt TTS ngay lập tức
    """
    stop_flag.set()


# =======================
# LISTEN (ASR)
# =======================
def listen():
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.6

    with sr.Microphone() as source:
        print("\n Đang lắng nghe...")
        try:
            audio = r.listen(
                source,
                timeout=5,
                phrase_time_limit=6
            )
            cmd = r.recognize_google(audio, language="vi-VN")
            print(f"User: {cmd}")
            return cmd.lower()

        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print("[ASR] API error:", e)
            return ""
        except Exception as e:
            print("[ASR] Error:", e)
            return ""
