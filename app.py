"""
StudySpot Finder - BACKEND ONLY
Render.com: chỉ xử lý /chat API, không serve HTML
"""

import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, "cafes_data.json"), "r", encoding="utf-8") as f:
    cafes = json.load(f)


def build_cafe_context(cafes):
    lines = []
    for c in cafes:
        lines.append(
            f"[{c['id']}] {c['ten_quan']} | Địa chỉ: {c['dia_chi']} | "
            f"Khu vực: {c['quan_huyen']} | "
            f"Yên tĩnh: {c['muc_do_yen_tinh']} ({c['mo_ta_yen_tinh']}) | "
            f"Tiện ích học tập: {c['tien_ich_hoc_tap']} | "
            f"Không gian: {c['khong_gian']} | "
            f"Đồ uống: {c['do_uong']} | Giá: {c['gia_tien']} | "
            f"Giờ mở cửa: {c['gio_mo_cua']} | "
            f"Mở 24h: {'Có' if c['mo_cua_24h'] else 'Không'} | "
            f"Mở khuya: {'Có' if c['mo_cua_khuya'] else 'Không'} | "
            f"Học nhóm: {'Có' if c['phu_hop_hoc_nhom'] else 'Không'} | "
            f"Tags: {', '.join(c['tags'])} | "
            f"Google Maps: {c['link_map']}"
        )
    return "\n".join(lines)


CAFE_CONTEXT = build_cafe_context(cafes)

SYSTEM_PROMPT = f"""Bạn là trợ lý tư vấn quán cà phê học tập thân thiện của website StudySpot Finder tại TP.HCM.
Nhiệm vụ: giúp người dùng tìm quán phù hợp để học bài, làm việc, cày deadline.

NGUYÊN TẮC TRẢ LỜI:
- Luôn trả lời bằng tiếng Việt, thân thiện, ngắn gọn (tối đa 4–5 dòng mỗi quán).
- Gợi ý tối đa 2–3 quán phù hợp nhất với yêu cầu.
- Luôn kèm link Google Maps nếu có.
- Nếu không tìm thấy quán phù hợp, hãy thành thật nói và hỏi thêm tiêu chí.
- Trình bày dạng bullet point, dễ đọc trên điện thoại.

DỮ LIỆU 36 QUÁN:
{CAFE_CONTEXT}
"""

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
    base_url="https://api.deepseek.com",
)

app = Flask(__name__)
CORS(app)


def ask_deepseek(user_message: str, history: list) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": user_message})
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.4,
        max_tokens=600,
    )
    return response.choices[0].message.content


@app.route("/")
def index():
    return jsonify({"status": "StudySpot API is running"})


@app.route("/chat", methods=["POST"])
def chat():
    data     = request.get_json() or {}
    user_msg = data.get("message", "").strip()
    history  = data.get("history", [])
    if not user_msg:
        return jsonify({"reply": "Bạn chưa nhập câu hỏi."})
    try:
        reply = ask_deepseek(user_msg, history)
    except Exception as e:
        reply = f"Xin lỗi, có lỗi xảy ra: {str(e)}"
    return jsonify({"reply": reply})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)