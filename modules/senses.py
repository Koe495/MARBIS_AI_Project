import os
import speech_recognition as sr
import edge_tts
import asyncio
import threading
import subprocess
import shutil
import io

# =======================
# CẤU HÌNH
# =======================
VOICE_ID = "vi-VN-NamMinhNeural"
MPV_PATH = "mpv.exe"  # Để file mpv.exe ngay trong thư mục dự án

# Biến kiểm soát luồng
stop_flag = threading.Event()
tts_thread = None

# Kiểm tra xem có MPV không? (Để chọn chế độ Streaming hay Fallback)
HAS_MPV = os.path.exists(MPV_PATH) or shutil.which("mpv")

# Nếu không có MPV thì mới init Pygame (để đỡ nặng máy)
if not HAS_MPV:
    import pygame

    try:
        pygame.mixer.init()
    except Exception as e:
        print("Lỗi init Pygame:", e)


# =======================
# CORE: STREAMING AUDIO (CỰC NHANH)
# =======================
async def _stream_via_mpv(text):
    """Kỹ thuật Pipe Streaming: Đọc dữ liệu từ EdgeTTS và tuồn thẳng vào MPV"""
    communicate = edge_tts.Communicate(text, VOICE_ID)

    # Lệnh gọi MPV: Đọc từ stdin (-), không hiện cửa sổ
    cmd = [MPV_PATH, "--no-cache", "--no-terminal", "--", "fd://0"]

    # Khởi chạy MPV ở chế độ lắng nghe dữ liệu
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    try:
        async for chunk in communicate.stream():
            # Nếu người dùng bấm STOP
            if stop_flag.is_set():
                process.terminate()
                break

            if chunk["type"] == "audio":
                # Bơm dữ liệu audio vào mồm MPV
                process.stdin.write(chunk["data"])
                process.stdin.flush()

    except Exception as e:
        print(f"Lỗi Streaming MPV: {e}")
    finally:
        # Đóng luồng nạp dữ liệu để MPV biết là hết bài rồi
        if process.stdin:
            process.stdin.close()
        process.wait()


# =======================
# CORE: RAM BUFFER (DỰ PHÒNG)
# =======================
async def _play_via_pygame_ram(text):
    """Nếu không có MPV, dùng RAM thay vì ổ cứng (Nhanh hơn cũ 30%)"""
    communicate = edge_tts.Communicate(text, VOICE_ID)

    # 1. Tải vào RAM (BytesIO) thay vì ổ cứng
    memory_file = io.BytesIO()
    async for chunk in communicate.stream():
        if stop_flag.is_set():
            return
        if chunk["type"] == "audio":
            memory_file.write(chunk["data"])

    # 2. Tua lại đầu file ảo
    memory_file.seek(0)

    # 3. Phát bằng Pygame
    if stop_flag.is_set(): return

    pygame.mixer.music.load(memory_file)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        if stop_flag.is_set():
            pygame.mixer.music.stop()
            break
        await asyncio.sleep(0.1)


# =======================
# WORKER
# =======================
def _speak_worker(text):
    stop_flag.clear()
    print(f"MARBIS: {text}")  # In ra CMD ngay lập tức

    try:
        if HAS_MPV:
            # ƯU TIÊN 1: STREAMING (Instant)
            asyncio.run(_stream_via_mpv(text))
        else:
            # ƯU TIÊN 2: RAM BUFFER (Khá nhanh)
            print(">> (Đang dùng Pygame. Cài 'mpv.exe' để nói nhanh hơn)")
            asyncio.run(_play_via_pygame_ram(text))

    except Exception as e:
        print(f"Lỗi TTS: {e}")


# =======================
# PUBLIC FUNCTIONS
# =======================
def speak(text):
    global tts_thread
    if not text: return

    stop_speaking()  # Ngắt câu cũ

    tts_thread = threading.Thread(
        target=_speak_worker,
        args=(text,),
        daemon=True
    )
    tts_thread.start()


def stop_speaking():
    stop_flag.set()
    # Nếu đang dùng pygame thì dừng thêm cái này cho chắc
    if not HAS_MPV and pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()

    # Nếu dùng MPV, subprocess sẽ tự bị kill khi check stop_flag trong vòng lặp


def listen():
    """Hàm nghe giữ nguyên như cũ"""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("\nĐang lắng nghe...")
        # r.adjust_for_ambient_noise(source, duration=0.3) # Có thể bỏ dòng này để bắt mic nhanh hơn
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
            cmd = r.recognize_google(audio, language="vi-VN")
            print(f"User: {cmd}")
            return cmd.lower()
        except:
            return ""