import streamlit as st
import random
import json
import os
import time

# ==========================================
# 1. 基礎配置與詞庫
# ==========================================
st.set_page_config(page_title="解码战Online", page_icon="📡", layout="wide")
DATA_FILE = "online_rooms.json"

WORD_POOL = [
    "苹果,香蕉,西瓜,葡萄", "猫,狗,兔子,鸟", "桌子,椅子,床,沙发",
    "红色,蓝色,绿色,黄色", "眼睛,鼻子,嘴巴,耳朵", "爸爸,妈妈,爷爷,奶奶",
    "水,牛奶,果汁,可乐", "太阳,月亮,星星,云", "铅笔,橡皮,书,纸",
    "汽车,火车,飞机,船", "手机,电脑,电视,相机", "夏天,冬天,春天,秋天"
]

# ==========================================
# 2. 數據庫讀寫函數 (核心同步機制)
# ==========================================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_room(room_id):
    data = load_data()
    return data.get(room_id, None)

def update_room(room_id, room_data):
    data = load_data()
    data[room_id] = room_data
    save_data(data)

# ==========================================
# 3. 遊戲邏輯函數
# ==========================================
def create_room(room_id, player_name):
    data = load_data()
    if room_id in data:
        return False, "房間已存在，請直接加入"
    
    # 初始化房間結構
    data[room_id] = {
        "players": [player_name], # 玩家列表
        "status": "WAITING",      # WAITING, PLAYING, GAMEOVER
        "teams": {},              # {player_name: "黑隊/白隊"}
        "roles": {},              # {player_name: "加密員/解密員"}
        "words": {},              # {"黑隊": [...], "白隊": [...]}
        "score": {"黑隊": {"s":0, "f":0}, "白隊": {"s":0, "f":0}},
        "turn": "黑隊",           # 當前行動隊伍
        "phase": "ENCODING",      # ENCODING, CLUE_GIVEN, INTERCEPT, GUESS
        "current_code": [],       # [1, 2, 3]
        "clues": [],              # ["线索1", "线索2", "线索3"]
        "logs": []                # 遊戲日誌
    }
    save_data(data)
    return True, "創建成功"

def join_room(room_id, player_name):
    data = load_data()
    if room_id not in data:
        return False, "房間不存在"
    room = data[room_id]
    
    if player_name in room["players"]:
        return True, "歡迎回來" # 重連
        
    if len(room["players"]) >= 4:
        return False, "房間已滿"
        
    room["players"].append(player_name)
    save_data(data)
    return True, "加入成功"

def start_game_logic(room_id):
    room = get_room(room_id)
    players = room["players"]
    random.shuffle(players)
    
    # 4人分隊：前2人黑隊，后2人白隊
    room["teams"][players[0]] = "黑隊"
    room["teams"][players[1]] = "黑隊"
    room["teams"][players[2]] = "白隊"
    room["teams"][players[3]] = "白隊"
    
    # 初始身份：每隊第一個人是加密員
    room["roles"][players[0]] = "加密員"
    room["roles"][players[1]] = "解密員"
    room["roles"][players[2]] = "加密員"
    room["roles"][players[3]] = "解密員"
    
    # 抽詞
    raw_words = random.sample(WORD_POOL, 2)
    room["words"]["黑隊"] = raw_words[0].split(",")
    room["words"]["白隊"] = raw_words[1].split(",")
    
    room["status"] = "PLAYING"
    room["logs"].append("遊戲開始！系統已隨機分隊。")
    update_room(room_id, room)

def rotate_roles(room_id):
    # 輪換加密員和解密員
    room = get_room(room_id)
    for p in room["players"]:
        new_role = "解密員" if room["roles"][p] == "加密員" else "加密員"
        room["roles"][p] = new_role
    update_room(room_id, room)

# ==========================================
# 4. 界面渲染 (UI)
# ==========================================

# --- 側邊欄：個人信息與刷新 ---
with st.sidebar:
    st.title("📡 控制台")
    my_name = st.text_input("輸入你的暱稱", key="my_name_input")
    room_code = st.text_input("房間號 (如 8888)", key="room_code_input")
    
    col1, col2 = st.columns(2)
    if col1.button("創建房間"):
        if my_name and room_code:
            success, msg = create_room(room_code, my_name)
            if success:
                st.session_state.room_id = room_code
                st.session_state.my_name = my_name
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    
    if col2.button("加入房間"):
        if my_name and room_code:
            success, msg = join_room(room_code, my_name)
            if success:
                st.session_state.room_id = room_code
                st.session_state.my_name = my_name
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.markdown("---")
    st.info("💡 提示：这是一个网页程序，数据不会自动推送。\n**如果画面没动，请点击下方刷新按钮。**")
    if st.button("🔄 刷新最新狀態", type="primary"):
        st.rerun()

# --- 主邏輯 ---

# --- 主邏輯 ---

# 1. 安全初始化：不管有没有，先保证 key 存在，防止 KeyError
if "room_id" not in st.session_state:
    st.session_state.room_id = None
if "my_name" not in st.session_state:
    st.session_state.my_name = None

# 2. 判断是否已登录
if not st.session_state.room_id:
    st.title("🕵️ 解码战 Online")
    st.write("👋 請在左側輸入暱稱和房間號開始。")
    st.info("👈 在左侧侧边栏操作")
    st.stop() # 这里的 stop 非常重要，它阻止代码继续往下跑

# 3. 只有登录后才会执行到这里
# 获取最新数据
room = get_room(st.session_state.room_id)
if not room:
    st.error("房間數據讀取失敗，可能房間已被刪除。")
    if st.button("返回大廳"):
        st.session_state.room_id = None
        st.rerun()
    st.stop()

# ... (后面的代码保持不变) ...



me = st.session_state.my_name
my_team = room.get("teams", {}).get(me, "未知")
my_role = room.get("roles", {}).get(me, "觀眾")
opponent_team = "白隊" if my_team == "黑隊" else "黑隊"

# --- 等待大廳 ---
if room["status"] == "WAITING":
    st.header(f"🏠 房間：{st.session_state.room_id}")
    st.write("等待玩家加入...")
    
    cols = st.columns(4)
    for i, p in enumerate(room["players"]):
        cols[i].success(f"👤 {p}")
        
    st.write(f"當前人數：{len(room['players'])}/4")
    
    if len(room["players"]) == 4:
        if st.button("🚀 人满，開始遊戲！"):
            start_game_logic(st.session_state.room_id)
            st.rerun()
    else:
        st.info("等待4人滿員後，按鈕會出現。")

# --- 遊戲進行中 ---
elif room["status"] == "PLAYING":
    
    # 1. 頂部信息欄
    st.markdown(f"### 我是：**{my_team} - {my_role}** ({me})")
    
    # 分數板
    sc = room["score"]
    c1, c2, c3 = st.columns([2, 1, 2])
    c1.metric("黑隊 (攔截/失敗)", f"{sc['黑隊']['s']} / {sc['黑隊']['f']}")
    c2.markdown(f"<h2 style='text-align:center'>回合：{room['turn']}</h2>", unsafe_allow_html=True)
    c3.metric("白隊 (攔截/失敗)", f"{sc['白隊']['s']} / {sc['白隊']['f']}")
    
    st.divider()

    # 2. 詞板顯示 (關鍵：視野隔離)
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.subheader("⬛ 黑隊詞板")
        if my_team == "黑隊":
            for i, w in enumerate(room["words"]["黑隊"]):
                st.success(f"{i+1}. {w}")
        else:
            st.warning("🔒 [加密中]")
            
    with col_r:
        st.subheader("⬜ 白隊詞板")
        if my_team == "白隊":
            for i, w in enumerate(room["words"]["白隊"]):
                st.success(f"{i+1}. {w}")
        else:
            st.warning("🔒 [加密中]")
            
    st.divider()

    # 3. 階段操作區 (根據身份顯示不同內容)
    
    # === 階段 A: 加密員出題 ===
    if room["phase"] == "ENCODING":
        st.info(f"等待 {room['turn']} 加密員出題...")
        
        # 只有「當前回合隊伍」的「加密員」能操作
        if my_team == room["turn"] and my_role == "加密員":
            st.error("👉 輪到你行動了！")
            
            # 生成/顯示密碼
            if not room["current_code"]:
                room["current_code"] = random.sample([1, 2, 3, 4], 3)
                update_room(st.session_state.room_id, room)
                st.rerun()
            
            code = room["current_code"]
            st.markdown(f"### 🤫 本輪密碼：{code[0]} - {code[1]} - {code[2]}")
            
            with st.form("clue_form"):
                clue1 = st.text_input("線索 1")
                clue2 = st.text_input("線索 2")
                clue3 = st.text_input("線索 3")
                if st.form_submit_button("廣播線索"):
                    if clue1 and clue2 and clue3:
                        room["clues"] = [clue1, clue2, clue3]
                        room["phase"] = "CLUE_GIVEN"
                        room["logs"].append(f"{me} 給出了線索：{clue1}, {clue2}, {clue3}")
                        update_room(st.session_state.room_id, room)
                        st.rerun()
        
        elif my_team == room["turn"] and my_role == "解密員":
             st.write("隊友正在思考線索，請等待...")
             
    # === 階段 B: 線索廣播 & 敵方攔截 ===
    elif room["phase"] == "CLUE_GIVEN":
        st.markdown(f"### 📢 收到線索：**{room['clues'][0]} - {room['clues'][1]} - {room['clues'][2]}**")
        st.write(f"等待 {opponent_team} 決定是否攔截...")
        
        # 敵方全體可以看到攔截按鈕 (或指定一人，這裡簡化為任一敵方可提交)
        if my_team != room["turn"]:
            st.error("👉 你們可以嘗試攔截！")
            with st.form("intercept_form"):
                guess_str = st.text_input("輸入攔截猜測 (如 123)", placeholder="留空則放棄攔截")
                col_a, col_b = st.columns(2)
                submit = col_a.form_submit_button("🔥 攔截")
                skip = col_b.form_submit_button("💨 跳過")
                
                if submit and guess_str:
                    guess = [int(c) for c in guess_str if c.isdigit()]
                    if guess == room["current_code"]:
                        room["score"][my_team]["s"] += 1
                        st.toast("攔截成功！")
                        room["logs"].append(f"敵方 {me} 攔截成功！(+1白幣)")
                    else:
                        st.toast("攔截失敗")
                        room["logs"].append(f"敵方 {me} 攔截失敗。")
                    room["phase"] = "GUESS"
                    update_room(st.session_state.room_id, room)
                    st.rerun()
                    
                if skip:
                    room["logs"].append(f"敵方 {me} 選擇跳過攔截。")
                    room["phase"] = "GUESS"
                    update_room(st.session_state.room_id, room)
                    st.rerun()

    # === 階段 C: 己方解密 ===
    elif room["phase"] == "GUESS":
        st.markdown(f"### 📢 線索：**{room['clues'][0]} - {room['clues'][1]} - {room['clues'][2]}**")
        st.info(f"攔截階段結束，輪到 {room['turn']} 自己人解密。")
        
        if my_team == room["turn"] and my_role == "解密員":
            st.error("👉 請輸入你猜測的密碼：")
            with st.form("team_guess"):
                g_str = st.text_input("密碼 (如 123)")
                if st.form_submit_button("提交驗證"):
                    guess = [int(c) for c in g_str if c.isdigit()]
                    real = room["current_code"]
                    if guess == real:
                        st.success("回答正確！")
                        room["logs"].append(f"{me} 猜對了密碼。")
                    else:
                        room["score"][my_team]["f"] += 1
                        st.error(f"回答錯誤！正確是 {real}")
                        room["logs"].append(f"{me} 猜錯密碼 (正確: {real})，獲得1黑幣。")
                    
                    # 結算回合
                    # 檢查勝負
                    sc = room["score"]
                    winner = None
                    if sc["黑隊"]["s"] >= 2: winner = "黑隊"
                    elif sc["白隊"]["s"] >= 2: winner = "白隊"
                    elif sc["黑隊"]["f"] >= 2: winner = "白隊"
                    elif sc["白隊"]["f"] >= 2: winner = "黑隊"
                    
                    if winner:
                        room["status"] = "GAMEOVER"
                        room["winner"] = winner
                    else:
                        # 換邊並重置
                        room["turn"] = "白隊" if room["turn"] == "黑隊" else "黑隊"
                        room["phase"] = "ENCODING"
                        room["current_code"] = []
                        room["clues"] = []
                        rotate_roles(st.session_state.room_id) # 輪換角色
                        
                    update_room(st.session_state.room_id, room)
                    st.rerun()

# --- 遊戲結束 ---
elif room["status"] == "GAMEOVER":
    st.balloons()
    st.title(f"🏆 遊戲結束！獲勝者：{room['winner']}")
    st.write("房間將保留最後狀態。如需重玩請創建新房間。")

# --- 底部日誌區 ---
st.divider()
with st.expander("📜 遊戲日誌", expanded=True):
    for log in reversed(room["logs"]):
        st.caption(log)