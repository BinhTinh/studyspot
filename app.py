"""
StudySpot Finder Chatbot
Stack: DeepSeek API + Flask (không cần vector DB)
Deploy: Render.com (miễn phí, HTTPS, embed vào Google Sites)
"""

import json, os
from flask import Flask, request, jsonify, render_template_string
from openai import OpenAI

# ─────────────────────────────────────────
# 1. TẢI DỮ LIỆU & BUILD SYSTEM PROMPT
# ─────────────────────────────────────────
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
            f"Học cá nhân: {'Có' if c['phu_hop_hoc_ca_nhan'] else 'Có'} | "
            f"Tags: {', '.join(c['tags'])} | "
            f"Google Maps: {c['link_map']}"
        )
    return "\n".join(lines)

CAFE_CONTEXT = build_cafe_context(cafes)

SYSTEM_PROMPT = f"""Bạn là trợ lý tư vấn quán cà phê học tập thân thiện của website StudySpot Finder tại TP.HCM.
Nhiệm vụ của bạn là giúp người dùng tìm quán phù hợp để học bài, làm việc, cày deadline.

NGUYÊN TẮC TRẢ LỜI:
- Luôn trả lời bằng tiếng Việt, thân thiện, ngắn gọn (tối đa 4-5 dòng mỗi quán)
- Gợi ý tối đa 2-3 quán phù hợp nhất với yêu cầu
- Luôn kèm link Google Maps nếu có
- Nếu không tìm thấy quán phù hợp, hãy thành thật nói và hỏi thêm tiêu chí
- Trình bày dạng bullet point, dễ đọc trên điện thoại

DỮ LIỆU 36 QUÁN:
{CAFE_CONTEXT}
"""

# ─────────────────────────────────────────
# 2. DEEPSEEK CLIENT
# ─────────────────────────────────────────
client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
    base_url="https://api.deepseek.com"
)

def ask_deepseek(user_message: str, history: list) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Giữ 6 lượt hội thoại gần nhất để tiết kiệm token
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.4,
        max_tokens=600
    )
    return response.choices[0].message.content

# ─────────────────────────────────────────
# 3. FLASK APP + GIAO DIỆN CHATBOT
# ─────────────────────────────────────────
app = Flask(__name__)

CHAT_UI = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>StudySpot Chatbot</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: 'Segoe UI', sans-serif;
    background: transparent;
    display: flex; justify-content: center; align-items: center;
    min-height: 100vh;
  }
  #chat-box {
    width: 100%; max-width: 420px; height: 580px;
    background: white; border-radius: 18px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.15);
    display: flex; flex-direction: column; overflow: hidden;
  }
  #header {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white; padding: 16px 20px;
  }
  #header h2 { font-size: 15px; font-weight: 700; }
  #header p  { font-size: 12px; opacity: 0.85; margin-top: 3px; }
  #messages {
    flex:1; overflow-y: auto; padding: 14px;
    display: flex; flex-direction: column; gap: 10px;
    background: #f8fafc;
  }
  .msg {
    max-width: 85%; padding: 10px 14px;
    border-radius: 16px; font-size: 13.5px; line-height: 1.55;
    word-break: break-word;
  }
  .user { background: #6366f1; color: white; align-self: flex-end; border-bottom-right-radius: 4px; }
  .bot  { background: white; color: #1e293b; align-self: flex-start;
          border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  .typing { color: #94a3b8; font-style: italic; font-size: 12px; background: white !important; }
  #suggestions { display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 14px 0; }
  .chip {
    background: #ede9fe; color: #5b21b6; border: none;
    padding: 5px 11px; border-radius: 20px; font-size: 12px;
    cursor: pointer; transition: background 0.2s;
  }
  .chip:hover { background: #ddd6fe; }
  #input-row {
    display: flex; padding: 10px 12px; gap: 8px;
    border-top: 1px solid #e2e8f0; background: white;
  }
  #user-input {
    flex:1; padding: 9px 14px;
    border: 1.5px solid #e2e8f0; border-radius: 24px;
    font-size: 13.5px; outline: none; background: #f8fafc;
  }
  #user-input:focus { border-color: #6366f1; background: white; }
  #send-btn {
    background: #6366f1; color: white; border: none;
    border-radius: 50%; width: 38px; height: 38px;
    cursor: pointer; font-size: 16px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
  }
  #send-btn:hover { background: #4f46e5; }
  a { color: #6366f1; }
</style>
</head>
<body>
<div id="chat-box">
  <div id="header">
    <h2>☕ StudySpot Finder</h2>
    <p>Tư vấn quán cà phê học tập tại TP.HCM</p>
  </div>
  <div id="messages" id="msgs">
    <div class="msg bot">
      Xin chào! Mình có thể giúp bạn tìm quán cà phê học tập phù hợp nhất 😊<br><br>
      Bạn cần quán <b>yên tĩnh</b>, <b>mở 24h</b>, <b>giá rẻ</b>, hay <b>gần khu vực nào</b>?
    </div>
  </div>
  <div id="suggestions">
    <button class="chip" onclick="quickAsk('Quán nào yên tĩnh nhất?')">🤫 Yên tĩnh nhất</button>
    <button class="chip" onclick="quickAsk('Quán nào mở 24h?')">🌙 Mở 24h</button>
    <button class="chip" onclick="quickAsk('Quán giá sinh viên rẻ nhất?')">💰 Giá rẻ nhất</button>
    <button class="chip" onclick="quickAsk('Quán nào phù hợp học nhóm?')">👥 Học nhóm</button>
  </div>
  <div id="input-row">
    <input id="user-input" type="text" placeholder="Hỏi về quán cà phê..." 
           onkeydown="if(event.key==='Enter') sendMsg()"/>
    <button id="send-btn" onclick="sendMsg()">&#9658;</button>
  </div>
</div>

<script>
let history = [];

function addMsg(text, role) {
  const msgs = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.innerHTML = text.replace(/\n/g, '<br>');
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function quickAsk(text) {
  document.getElementById('user-input').value = text;
  sendMsg();
}

async function sendMsg() {
  const input = document.getElementById('user-input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  document.getElementById('suggestions').style.display = 'none';
  addMsg(text, 'user');
  const typing = addMsg('Đang tìm kiếm...', 'bot typing');

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text, history: history})
    });
    const data = await res.json();
    typing.remove();
    addMsg(data.reply, 'bot');
    history.push({role: 'user', content: text});
    history.push({role: 'assistant', content: data.reply});
    if (history.length > 12) history = history.slice(-12);
  } catch(e) {
    typing.textContent = 'Lỗi kết nối, vui lòng thử lại.';
  }
}
</script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(CHAT_UI)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
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
