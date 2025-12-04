import streamlit as st
import random
import json
import os
import time

# ==========================================
# 1. 基础配置与字体设置
# ==========================================
st.set_page_config(page_title="解码战 Online", page_icon="📡", layout="wide")

# 注入自定义字体 CSS
st.markdown("""
    <style>
    @import url("https://fontsapi.zeoseven.com/881/main/result.css");
    
    html, body, [class*="css"] {
        font-family: "Jigmo", sans-serif;
        font-weight: normal;
    }
    h1, h2, h3 {
        font-family: "Jigmo", sans-serif !important;
    }
    .stButton button {
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

DATA_FILE = "online_rooms.json"
WORD_FILE = "word_sets.txt"

# ==========================================
# 2. 词库读取逻辑 (改为真正的全池随机)
# ==========================================
@st.cache_data
def load_word_pool():
    """
    读取词库文件。
    返回格式：{"简单": [词1, 词2...], "中等": [...], "困难": [...]}
    """
    data = {}
    current_difficulty = None
    
    if os.path.exists(WORD_FILE):
        try:
            with open(WORD_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    
                    # 识别难度标签
                    if line.startswith("[") and line.endswith("]"):
                        current_difficulty = line[1:-1]
                        if current_difficulty not in data:
                            data[current_difficulty] = []
                    elif current_difficulty:
                        # 兼容中文逗号，分割所有词
                        line = line.replace("，", ",")
                        words = line.split(",")
                        for w in words:
                            w = w.strip()
                            if w: # 只要不是空字符串就加入大池子
                                data[current_difficulty].append(w)
        except Exception as e:
            st.error(f"读取词库文件出错: {e}")
            
    return data

# ==========================================
# 3. 数据库读写函数
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
# 4. 游戏逻辑函数
# ==========================================
def create_room(room_id, player_name, difficulty):
    data = load_data()
    if room_id in data:
        return False, "房间已存在，请直接加入"
    
    data[room_id] = {
        "players": [player_name],
        "difficulty": difficulty, # 记录房间难度
        "status": "WAITING",
        "teams": {},
        "roles": {},
        "words": {},
        "score": {"黑队": {"s":0, "f":0}, "白队": {"s":0, "f":0}},
        "turn": "黑队",
        "phase": "ENCODING",
        "current_code": [],
        "clues": [],
        "logs": []
    }
    save_data(data)
    return True, "创建成功"

def join_room(room_id, player_name):
    data = load_data()
    if room_id not in data:
        return False, "房间不存在"
    room = data[room_id]
    
    if player_name in room["players"]:
        return True, "欢迎回来"
        
    if len(room["players"]) >= 4:
        return False, "房间已满"
        
    room["players"].append(player_name)
    save_data(data)
    return True, "加入成功"

def start_game_logic(room_id):
    room = get_room(room_id)
    players = room["players"]
    random.shuffle(players)
    
    room["teams"][players[0]] = "黑队"
    room["teams"][players[1]] = "黑队"
    room["teams"][players[2]] = "白队"
    room["teams"][players[3]] = "白队"
    
    room["roles"][players[0]] = "加密员"
    room["roles"][players[1]] = "解密员"
    room["roles"][players[2]] = "加密员"
    room["roles"][players[3]] = "解密员"
    
    # --- 核心修改：从全量池中随机抽取8个 ---
    full_data = load_word_pool()
    diff = room.get("difficulty", "简单")
    
    # 获取对应难度的所有词（大池子）
    pool = full_data.get(diff, [])
    
    # 兜底逻辑：如果词库读不到或太少，用默认词
    if len(pool) < 8:
        pool = ["苹果","香蕉","西瓜","葡萄","猫","狗","兔子","鸟"] * 2 
        
    # 真正的随机：从池子里抓8个不重复的
    chosen_8 = random.sample(pool, 8)
    
    room["words"]["黑队"] = chosen_8[:4]
    room["words"]["白队"] = chosen_8[4:]
    
    room["status"] = "PLAYING"
    room["logs"].append(f"游戏开始！难度：{diff}。系统已随机分队。")
    update_room(room_id, room)

def rotate_roles(room_id):
    room = get_room(room_id)
    for p in room["players"]:
        new_role = "解密员" if room["roles"][p] == "加密员" else "加密员"
        room["roles"][p] = new_role
    update_room(room_id, room)

# ==========================================
# 5. 界面渲染 (UI)
# ==========================================

if "room_id" not in st.session_state:
    st.session_state.room_id = None
if "my_name" not in st.session_state:
    st.session_state.my_name = None

# --- 侧边栏 ---
with st.sidebar:
    st.title("📡 控制台")
    st.caption("创建或加入房间")
    
    my_name = st.text_input("输入你的昵称", key="my_name_input")
    room_code = st.text_input("房间号 (如 8888)", key="room_code_input")
    
    # 新增：难度选择
    selected_diff = st.selectbox("选择难度 (仅创建时有效)", ["简单", "中等", "困难"])
    
    col1, col2 = st.columns(2)
    if col1.button("创建房间"):
        if my_name and room_code:
            success, msg = create_room(room_code, my_name, selected_diff)
            if success:
                st.session_state.room_id = room_code
                st.session_state.my_name = my_name
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    
    if col2.button("加入房间"):
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
    st.caption("提示：在手机上，点击左上角箭头可收起此栏。")
    
    # 调试信息：显示词库词汇量
    all_words = load_word_pool()
    count = len(all_words.get(selected_diff, []))
    st.caption(f"📚 {selected_diff}模式词汇量: {count} 个")

# --- 主逻辑 ---

if not st.session_state.room_id:
    st.title("🕵️ 解码战 Online")
    st.write("👋 请点击左上角箭头打开侧边栏，输入昵称和房间号。")
    st.info("👈 手机端请点左上角箭头 >")
    st.stop()

# 全局刷新按钮
if st.button("🔄 点我刷新最新状态 (查看对手行动)", type="primary", use_container_width=True):
    st.rerun()

room = get_room(st.session_state.room_id)
if not room:
    st.error("房间数据读取失败，可能房间已被删除。")
    if st.button("返回大厅"):
        st.session_state.room_id = None
        st.rerun()
    st.stop()

me = st.session_state.my_name
my_team = room.get("teams", {}).get(me, "未知")
my_role = room.get("roles", {}).get(me, "观众")
opponent_team = "白队" if my_team == "黑队" else "黑队"

# --- 等待大厅 ---
if room["status"] == "WAITING":
    st.header(f"🏠 房间：{st.session_state.room_id}")
    st.caption(f"当前难度：{room.get('difficulty', '简单')}")
    st.write("等待玩家加入...")
    
    cols = st.columns(4)
    for i, p in enumerate(room["players"]):
        cols[i].success(f"👤 {p}")
        
    st.write(f"当前人数：{len(room['players'])}/4")
    
    if len(room["players"]) == 4:
        if st.button("🚀 人满，开始游戏！", use_container_width=True):
            start_game_logic(st.session_state.room_id)
            st.rerun()
    else:
        st.info("等待4人满员后，开始按钮会出现。")

# --- 游戏进行中 ---
elif room["status"] == "PLAYING":
    st.markdown(f"### 我是：**{my_team} - {my_role}** ({me})")
    
    sc = room["score"]
    c1, c2, c3 = st.columns([2, 1, 2])
    c1.metric("黑队 (拦截/失败)", f"{sc['黑队']['s']} / {sc['黑队']['f']}")
    c2.markdown(f"<h2 style='text-align:center'>回合：{room['turn']}</h2>", unsafe_allow_html=True)
    c3.metric("白队 (拦截/失败)", f"{sc['白队']['s']} / {sc['白队']['f']}")
    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("⬛ 黑队词板")
        if my_team == "黑队":
            for i, w in enumerate(room["words"]["黑队"]):
                st.success(f"{i+1}. {w}")
        else:
            st.warning("🔒 [加密中]")
    with col_r:
        st.subheader("⬜ 白队词板")
        if my_team == "白队":
            for i, w in enumerate(room["words"]["白队"]):
                st.success(f"{i+1}. {w}")
        else:
            st.warning("🔒 [加密中]")
    st.divider()

    if room["phase"] == "ENCODING":
        st.info(f"等待 {room['turn']} 加密员出题...")
        if my_team == room["turn"] and my_role == "加密员":
            st.error("👉 轮到你行动了！")
            if not room["current_code"]:
                room["current_code"] = random.sample([1, 2, 3, 4], 3)
                update_room(st.session_state.room_id, room)
                st.rerun()
            code = room["current_code"]
            st.markdown(f"### 🤫 本轮密码：{code[0]} - {code[1]} - {code[2]}")
            with st.form("clue_form"):
                clue1 = st.text_input("线索 1")
                clue2 = st.text_input("线索 2")
                clue3 = st.text_input("线索 3")
                if st.form_submit_button("广播线索", use_container_width=True):
                    if clue1 and clue2 and clue3:
                        room["clues"] = [clue1, clue2, clue3]
                        room["phase"] = "CLUE_GIVEN"
                        room["logs"].append(f"{me} 给出了线索：{clue1}, {clue2}, {clue3}")
                        update_room(st.session_state.room_id, room)
                        st.rerun()
        elif my_team == room["turn"] and my_role == "解密员":
             st.write("队友正在思考线索，请等待...")
             
    elif room["phase"] == "CLUE_GIVEN":
        st.markdown(f"### 📢 收到线索：**{room['clues'][0]} - {room['clues'][1]} - {room['clues'][2]}**")
        st.write(f"等待 {opponent_team} 决定是否拦截...")
        if my_team != room["turn"]:
            st.error("👉 您可以尝试拦截！")
            with st.form("intercept_form"):
                guess_str = st.text_input("输入拦截猜测 (如 123)", placeholder="留空则放弃拦截")
                col_a, col_b = st.columns(2)
                submit = col_a.form_submit_button("🔥 拦截", use_container_width=True)
                skip = col_b.form_submit_button("💨 跳过", use_container_width=True)
                if submit and guess_str:
                    guess = [int(c) for c in guess_str if c.isdigit()]
                    if guess == room["current_code"]:
                        room["score"][my_team]["s"] += 1
                        st.toast("拦截成功！")
                        room["logs"].append(f"敌方 {me} 拦截成功！(+1白币)")
                    else:
                        st.toast("拦截失败")
                        room["logs"].append(f"敌方 {me} 拦截失败。")
                    room["phase"] = "GUESS"
                    update_room(st.session_state.room_id, room)
                    st.rerun()
                if skip:
                    room["logs"].append(f"敌方 {me} 选择跳过拦截。")
                    room["phase"] = "GUESS"
                    update_room(st.session_state.room_id, room)
                    st.rerun()

    elif room["phase"] == "GUESS":
        st.markdown(f"### 📢 线索：**{room['clues'][0]} - {room['clues'][1]} - {room['clues'][2]}**")
        st.info(f"拦截阶段结束，轮到 {room['turn']} 自己人解密。")
        if my_team == room["turn"] and my_role == "解密员":
            st.error("👉 请输入你猜测的密码：")
            with st.form("team_guess"):
                g_str = st.text_input("密码 (如 123)")
                if st.form_submit_button("提交验证", use_container_width=True):
                    guess = [int(c) for c in g_str if c.isdigit()]
                    real = room["current_code"]
                    if guess == real:
                        st.success("回答正确！")
                        room["logs"].append(f"{me} 猜对了密码。")
                    else:
                        room["score"][my_team]["f"] += 1
                        st.error(f"回答错误！正确是 {real}")
                        room["logs"].append(f"{me} 猜错密码 (正确: {real})，获得1黑币。")
                    sc = room["score"]
                    winner = None
                    if sc["黑队"]["s"] >= 2: winner = "黑队"
                    elif sc["白队"]["s"] >= 2: winner = "白队"
                    elif sc["黑队"]["f"] >= 2: winner = "白队"
                    elif sc["白队"]["f"] >= 2: winner = "黑队"
                    if winner:
                        room["status"] = "GAMEOVER"
                        room["winner"] = winner
                    else:
                        room["turn"] = "白队" if room["turn"] == "黑队" else "黑队"
                        room["phase"] = "ENCODING"
                        room["current_code"] = []
                        room["clues"] = []
                        rotate_roles(st.session_state.room_id)
                    update_room(st.session_state.room_id, room)
                    st.rerun()

elif room["status"] == "GAMEOVER":
    st.balloons()
    st.title(f"🏆 游戏结束！获胜者：{room['winner']}")
    st.write("房间将保留最后状态。如需重玩请创建新房间。")

st.divider()
with st.expander("📜 游戏日志", expanded=True):
    for log in reversed(room["logs"]):
        st.caption(log)
