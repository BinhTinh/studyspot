"""
StudySpot Finder Chatbot
Stack: DeepSeek API + Flask
UI: Floating bubble widget - fixed for iframe embedding
Deploy: Render.com → embed iframe vào Google Sites
"""

import json
import os
from flask import Flask, request, jsonify
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


app = Flask(__name__)

CHAT_UI = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>StudySpot Chatbot</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }

  html, body {
    width: 100%; height: 100%;
    background: transparent;
    font-family: 'Segoe UI', sans-serif;
    overflow: hidden;
  }

  /* Wrapper chiếm toàn bộ iframe */
  #wrapper {
    position: relative;
    width: 100%; height: 100%;
  }

  /* ── BUBBLE ── */
  #chat-bubble {
    position: absolute;
    bottom: 16px; right: 16px;
    width: 56px; height: 56px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 24px;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(99,102,241,0.5);
    z-index: 10;
    user-select: none;
    transition: transform 0.2s;
  }
  #chat-bubble:hover { transform: scale(1.08); }
  #chat-bubble::after {
    content: '';
    position: absolute; top: 4px; right: 4px;
    width: 11px; height: 11px;
    background: #22c55e; border-radius: 50%;
    border: 2px solid white;
  }

  /* ── CHAT WINDOW ── */
  #chat-window {
    position: absolute;
    /* Chiếm toàn bộ iframe trừ phần bubble ở dưới */
    bottom: 80px; right: 0; left: 0;
    top: 0;
    background: white;
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.15);
    display: none;          /* ẩn mặc định */
    flex-direction: column;
    overflow: hidden;
    z-index: 9;
    margin: 8px 8px 0 8px;
  }
  #chat-window.visible { display: flex; }

  /* Header */
  #chat-header {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white; padding: 12px 14px;
    display: flex; align-items: center; gap: 10px;
    flex-shrink: 0;
  }
  .avatar {
    width: 34px; height: 34px;
    background: rgba(255,255,255,0.25);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; flex-shrink: 0;
  }
  .info h3 { font-size: 13px; font-weight: 700; }
  .info p  { font-size: 11px; opacity: 0.85; margin-top: 1px; }
  .status  {
    margin-left: auto;
    font-size: 11px; opacity: 0.9;
    display: flex; align-items: center; gap: 4px;
  }
  .status::before {
    content: '';
    width: 7px; height: 7px;
    background: #4ade80; border-radius: 50%;
    display: inline-block;
  }
  #close-btn {
    background: rgba(255,255,255,0.2); border: none;
    color: white; width: 26px; height: 26px;
    border-radius: 50%; cursor: pointer;
    font-size: 14px; margin-left: 8px;
    display: flex; align-items: center; justify-content: center;
    transition: background 0.2s; flex-shrink: 0;
  }
  #close-btn:hover { background: rgba(255,255,255,0.35); }

  /* Messages */
  #messages {
    flex: 1; overflow-y: auto; padding: 12px;
    display: flex; flex-direction: column; gap: 8px;
    background: #f8fafc;
  }
  #messages::-webkit-scrollbar { width: 3px; }
  #messages::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }

  .msg {
    max-width: 84%; padding: 8px 12px;
    border-radius: 14px; font-size: 13px; line-height: 1.5;
    word-break: break-word;
  }
  .user {
    background: #6366f1; color: white;
    align-self: flex-end; border-bottom-right-radius: 3px;
  }
  .bot {
    background: white; color: #1e293b;
    align-self: flex-start; border-bottom-left-radius: 3px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }
  .typing { color: #94a3b8; font-style: italic; font-size: 12px; background: white !important; }

  /* Chips */
  #suggestions {
    display: flex; flex-wrap: wrap; gap: 5px;
    padding: 6px 12px 2px; background: #f8fafc;
    flex-shrink: 0;
  }
  .chip {
    background: #ede9fe; color: #5b21b6; border: none;
    padding: 4px 9px; border-radius: 20px;
    font-size: 11px; cursor: pointer;
    transition: background 0.2s;
  }
  .chip:hover { background: #ddd6fe; }

  /* Input */
  #input-row {
    display: flex; padding: 8px 10px; gap: 7px;
    border-top: 1px solid #e2e8f0; background: white;
    flex-shrink: 0;
  }
  #user-input {
    flex: 1; padding: 8px 12px;
    border: 1.5px solid #e2e8f0; border-radius: 20px;
    font-size: 13px; outline: none; background: #f8fafc;
  }
  #user-input:focus { border-color: #6366f1; background: white; }
  #send-btn {
    background: #6366f1; color: white; border: none;
    border-radius: 50%; width: 34px; height: 34px;
    cursor: pointer; font-size: 15px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    transition: background 0.2s;
  }
  #send-btn:hover { background: #4f46e5; }
  a { color: #6366f1; }
</style>
</head>
<body>
<div id="wrapper">

  <!-- Chat window -->
  <div id="chat-window">
    <div id="chat-header">
      <div class="avatar">🤖</div>
      <div class="info">
        <h3>StudySpot Finder</h3>
        <p>Tư vấn quán cà phê học tập</p>
      </div>
      <div class="status">Online</div>
      <button id="close-btn" onclick="toggleChat()">✕</button>
    </div>

    <div id="messages">
      <div class="msg bot">
        Xin chào! Mình giúp bạn tìm quán cà phê học tập ở TP.HCM 😊<br><br>
        Bạn cần quán <b>yên tĩnh</b>, <b>mở 24h</b>, <b>giá rẻ</b>, hay <b>gần khu vực nào</b>?
      </div>
    </div>

    <div id="suggestions">
      <button class="chip" onclick="quickAsk('Quán nào yên tĩnh nhất?')">🤫 Yên tĩnh</button>
      <button class="chip" onclick="quickAsk('Quán nào mở 24h?')">🌙 Mở 24h</button>
      <button class="chip" onclick="quickAsk('Quán giá rẻ nhất?')">💰 Giá rẻ</button>
      <button class="chip" onclick="quickAsk('Quán nào phù hợp học nhóm?')">👥 Học nhóm</button>
    </div>

    <div id="input-row">
      <input id="user-input" type="text" placeholder="Nhập câu hỏi..." />
      <button id="send-btn">&#9658;</button>
    </div>
  </div>

  <!-- Bubble -->
  <div id="chat-bubble" onclick="toggleChat()" title="Hỏi về quán cà phê học tập">☕</div>

</div>

<script>
let chatHistory = [];
let isOpen = false;

function toggleChat() {
  isOpen = !isOpen;
  const win    = document.getElementById('chat-window');
  const bubble = document.getElementById('chat-bubble');
  if (isOpen) {
    win.classList.add('visible');
    bubble.style.transform = 'rotate(15deg) scale(1.05)';
    setTimeout(() => document.getElementById('user-input').focus(), 100);
  } else {
    win.classList.remove('visible');
    bubble.style.transform = '';
  }
}

function addMsg(text, role) {
  const msgs = document.getElementById('messages');
  const div  = document.createElement('div');
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
  const text  = input.value.trim();
  if (!text) return;
  input.value = '';
  document.getElementById('suggestions').style.display = 'none';
  addMsg(text, 'user');
  const typing = addMsg('Đang tìm kiếm...', 'bot typing');
  try {
    const res  = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: chatHistory })
    });
    const data = await res.json();
    typing.remove();
    addMsg(data.reply, 'bot');
    chatHistory.push({ role: 'user',      content: text });
    chatHistory.push({ role: 'assistant', content: data.reply });
    if (chatHistory.length > 12) chatHistory = chatHistory.slice(-12);
  } catch (e) {
    typing.textContent = 'Lỗi kết nối, vui lòng thử lại.';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('user-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); sendMsg(); }
  });
  document.getElementById('send-btn').addEventListener('click', sendMsg);
});
</script>
</body>
</html>"""


@app.route("/")
def index():
    return CHAT_UI


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