from groq import Groq
from config import GROQ_API_KEY


class GroqModelChecker:
    def __init__(self, api_key=None):
        # Nếu không truyền key vào thì lấy từ config
        self.api_key = api_key if api_key else GROQ_API_KEY
        self.client = Groq(api_key=self.api_key)
        self.available_models = []

        # Danh sách ưu tiên (Giảm dần độ xịn)
        self.preferred_models = [
            "llama-3.3-70b-versatile",  # Mạnh nhất, mới nhất
            "llama-3.1-70b-versatile",  # Ổn định
            "llama-3.1-8b-instant",  # Siêu nhanh
            "mixtral-8x7b-32768",  # Mixtral cũng rất tốt
            "gemma2-9b-it"  # Model của Google trên Groq
        ]

    def get_available_models(self):
        """Lấy và IN RA danh sách model thực tế từ API Groq"""
        try:
            print("\nĐang kết nối tới Groq để lấy danh sách model...")
            models_list = self.client.models.list()

            # Lưu ID các model vào list
            self.available_models = [m.id for m in models_list.data]

            print(f"Đã tìm thấy {len(self.available_models)} model khả dụng:")
            print("-" * 40)
            for model_id in self.available_models:
                print(f"   • {model_id}")
            print("-" * 40)

            return self.available_models

        except Exception as e:
            print(f"Lỗi khi lấy danh sách model: {e}")
            return []

    def get_best_model(self):
        """Tự động chọn model tốt nhất đang hoạt động"""
        # 1. Nếu chưa có danh sách thì lấy về
        if not self.available_models:
            self.get_available_models()

        # 2. Duyệt qua danh sách ưu tiên của mình
        print("🔍 Đang chọn model tối ưu cho MARBIS...")
        for model in self.preferred_models:
            if model in self.available_models:
                print(f"KẾT QUẢ: Đã chọn model [{model}]")
                return model

        # 3. Fallback: Lấy cái đầu tiên tìm thấy
        if self.available_models:
            fallback = self.available_models[0]
            print(f"⚠Không tìm thấy model ưu tiên. Dùng tạm: {fallback}")
            return fallback

        # 4. Trường hợp xấu nhất (mất mạng) trả về default để không crash app
        print("Không kết nối được. Dùng model mặc định (có thể gây lỗi).")
        return "llama-3.3-70b-versatile"


# --- ĐOẠN CODE TEST NHANH ---
# Nếu chạy trực tiếp file này, nó sẽ in danh sách ra ngay
if __name__ == "__main__":
    checker = GroqModelChecker()
    checker.get_available_models()
    checker.get_best_model()