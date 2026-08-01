# 🐉 AI Godji - Multimodal Desktop AI Assistant & Real-time Screen HUD Overlay

**AI Godji** เป็นโปรเจกต์ผู้ช่วยอัจฉริยะแบบภาพและเสียงเรียลไทม์ (Multimodal Real-time AI Desktop Assistant) สไตล์ ADA V2 ซึ่งขับเคลื่อนด้วย **Google Gemini API**

---

## 🔥 ฟีเจอร์หลัก (Features)

1. **🎯 Real-time Screen HUD Overlay**:
   - หน้าต่างแคนวาสโปร่งใส (Transparent Screen Overlay) ลอยทับหน้าจอคอมพิวเตอร์แบบเรียลไทม์
   - AI วาดกรอบเป้าหมาย (**Bounding Box**), จุดยิงดัก (**Tactical Lead Dot**), ลูกศรทิศทาง (**Directional Arrows**) และ **AI Subtitle** บนหน้าจอสดสด

2. **💻 CLI System Agent Control**:
   - สั่งงาน AI Godji ผ่านเสียงหรือข้อความให้ อ่าน, แก้ไข (**Edit**), สร้าง หรือลบไฟล์ (**Delete**) บนคอมพิวเตอร์ของคุณ
   - รันคำสั่ง PowerShell / Terminal เพื่อสั่งงานเครื่องคอมพิวเตอร์โดยตรง

3. **🧠 Hybrid Smart Vision Filter**:
   - ตรวจจับความเคลื่อนไหวภาพหน้าจอด้าน Local ด้วย OpenCV ก่อนส่งภาพเข้า Gemini API ช่วยประหยัด Token และค่าใช้จ่าย 80-90%

4. **🚀 Render.com Ready Backend**:
   - Backend เขียนด้วย Python FastAPI + WebSockets พร้อม `Dockerfile` และ `render.yaml` สำหรับ Push ขึ้น GitHub แล้วนำไป Deploy บน Render ได้ทันที

---

## 🛠️ โครงสร้างระบบ (Project Structure)

```text
godji/
├── backend/                  # Python FastAPI Backend (Deploy ขึ้น Render.com)
│   ├── app/
│   │   ├── main.py           # FastAPI entrypoint + WebSocket endpoints
│   │   ├── gemini_client.py  # Gemini Multimodal API & Vision engine
│   │   ├── cli_tools.py      # CLI Control Tools (Read/Edit/Delete files & run CLI)
│   │   ├── vision_parser.py  # Coordinate & Bounding Box parser for HUD Canvas
│   │   └── config.py         # Config environment
│   ├── Dockerfile            # Render Dockerfile
│   ├── render.yaml           # Render Web Service deployment spec
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # Electron Desktop Application
│   ├── main.js               # Main process (Fullscreen Transparent HUD + Control Dashboard)
│   ├── preload.js            # Secure IPC Bridge
│   ├── overlay.html          # Transparent Canvas Window HTML
│   ├── overlay.js            # Real-time HUD Canvas Drawing Engine
│   ├── dashboard.html        # Modern Dark-mode Control Dashboard GUI
│   ├── dashboard.js          # Dashboard logic & control handlers
│   └── package.json          # Node dependencies & Electron scripts
```

---

## 🚀 ขั้นตอนการติดตั้งและรันใช้งาน (Getting Started)

### 1. การตั้งค่า Backend (Python FastAPI)

```bash
# สลับไปยังโฟลเดอร์ backend
cd backend

# สร้างและเปิดใช้ Virtual Environment
python -m venv venv
# On Windows:
venv\Scripts\activate

# ติดตั้ง Dependencies
pip install -r requirements.txt

# สร้างไฟล์ .env จาก .env.example แล้วใส่ GEMINI_API_KEY
cp ../.env.example .env

# รัน Backend Server
python app/main.py
```
Backend จะทำงานอยู่ที่ `http://localhost:8000` (WebSocketอยู่ที่ `ws://localhost:8000/ws/live`)

---

### 2. การตั้งค่า Frontend (Electron Desktop App)

```bash
# สลับไปยังโฟลเดอร์ frontend
cd frontend

# ติดตั้ง dependencies
npm install

# รัน Electron App
npm start
```

---

## ☁️ ขั้นตอนการนำ Backend ขึ้น Render.com ผ่าน GitHub

1. สร้าง Repository ใหม่บน **GitHub**
2. Push โค้ดโปรเจกต์นี้ขึ้น GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of AI Godji project"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/godji.git
   git push -u origin main
   ```
3. เข้าไปยัง [Render.com Dashboard](https://dashboard.render.com/) -> กด **New +** -> เลือก **Web Service**
4. เชื่อมต่อกับ GitHub Repository `godji` ของคุณ
5. Render จะอ่านไฟล์ `render.yaml` และ `backend/Dockerfile` โดยอัตโนมัติ
6. ใส่ Environment Variable: `GEMINI_API_KEY` ใน Render Dashboard
7. กด **Deploy** และนำ URL WebSocket (เช่น `wss://godji-backend.onrender.com/ws/live`) มาใส่ใน `frontend/dashboard.js`
