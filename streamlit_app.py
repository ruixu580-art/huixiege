# streamlit_app.py
import streamlit as st
import requests
import time
from pyairtable import Table

st.set_page_config(page_title="慧写歌", page_icon="🎵")

# Logo
col1, col2 = st.columns([1, 5])
with col1:
    st.image("logoPNG.svg", width=80)
with col2:
    st.title("慧写歌")

# ========== Airtable 连接 ==========
@st.cache_resource
def get_airtable():
    """获取 Airtable 表对象"""
    return Table(
        st.secrets["AIRTABLE_TOKEN"],
        st.secrets["AIRTABLE_BASE_ID"],
        st.secrets["AIRTABLE_TABLE_NAME"]
    )

def get_user_credits(user_id):
    """查询用户剩余次数"""
    table = get_airtable()
    
    # 调试：读取一条已有记录，看看实际列名
    try:
        all_records = table.all(max_records=1)
        if all_records:
            st.write("实际列名：", list(all_records[0]['fields'].keys()))
    except Exception as e:
        st.write(f"调试失败：{e}")
    
    formula = f"{{user_id}} = '{user_id}'"
    records = table.all(formula=formula)
    
    if records:
        return records[0]['fields'].get('credits', 0), records[0]['id']
    else:
        # 新用户，赠送 3 次试用
        record = table.create({
            'user_id': user_id,
            'user_name': user_id,
            'credits': 3,
            'membership_type': '试用'
        })
        return 3, record['id']

def update_user_credits(record_id, new_credits):
    """更新用户剩余次数"""
    table = get_airtable()
    table.update(record_id, {'credits': new_credits})

# ========== API Key 读取 ==========
api_key = st.secrets.get("MUREKA_API_KEY")

# ========== 用户登录 ==========
if "user_id" not in st.session_state:
    st.session_state.user_id = None

with st.sidebar:
    st.header("👤 我的账号")
    
    if not st.session_state.user_id:
        user_email = st.text_input("请输入你的邮箱（用于保存次数）", placeholder="example@qq.com")
        if st.button("登录/注册"):
            if user_email:
                st.session_state.user_id = user_email
                st.rerun()
            else:
                st.error("请输入邮箱")
    else:
        st.success(f"当前用户：{st.session_state.user_id}")
        
        # 查询剩余次数
        credits, record_id = get_user_credits(st.session_state.user_id)
        st.metric("🎵 剩余次数", f"{credits}次")
        
        if st.button("退出登录"):
            st.session_state.user_id = None
            st.rerun()
    
    st.markdown("---")
    if api_key:
        st.success("✅ API Key 已配置")
    else:
        st.error("❌ API Key 未配置")

# 获取当前用户次数
credits, record_id = get_user_credits(st.session_state.user_id)

# 次数不足时停止
if credits <= 0:
    st.warning("⚠️ 次数不足，请购买套餐或联系客服")
    st.stop()

# ========== 音乐生成功能 ==========
def generate_song(api_key, lyrics, prompt, style="pop"):
    """提交歌曲生成任务"""
    url = "https://api.mureka.ai/v1/song/generate"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "lyrics": lyrics,
        "model": "auto",
        "prompt": f"{style}, {prompt}"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            return response.json().get("id")
        elif response.status_code == 429:
            st.warning("服务器繁忙，请稍后重试")
            return None
        else:
            st.error(f"提交失败：{response.text}")
            return None
    except Exception as e:
        st.error(f"网络错误：{e}")
        return None

def fetch_audio_result(api_key, task_id):
    """查询任务并获取歌曲链接"""
    url = f"https://api.mureka.ai/v1/song/query/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    for i in range(40):
        time.sleep(3)
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status")
                if status == "succeeded":
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("url")
                elif status == "failed":
                    return None
        except Exception:
            pass
    return None

# 主界面
st.markdown("---")
topic = st.text_input("🎵 歌曲主题", placeholder="例如：夏天、阳光、爱情")
style = st.selectbox("🎸 音乐风格", ["pop", "rock", "electronic", "jazz", "classical"])

# 歌词来源选择
lyrics_source = st.radio("📝 歌词来源", ["🎵 AI自动生成歌词", "✍️ 我自己写歌词"], horizontal=True)

user_lyrics = ""
if lyrics_source == "✍️ 我自己写歌词":
    user_lyrics = st.text_area("📝 请输入你的歌词", height=150)

if st.button("✨ 开始创作", type="primary"):
    # 检查登录状态（新增）
    if not st.session_state.user_id:
        st.warning("⚠️ 请先登录后再开始创作")
        with st.sidebar:
            st.info("👈 请在左侧边栏输入邮箱登录")
        st.stop()
    
    if not api_key:
        st.error("请先在侧边栏输入 API Key")
    elif credits <= 0:
        st.error("次数不足，请购买套餐")
    elif not topic:
        st.error("请输入歌曲主题")
    elif lyrics_source == "✍️ 我自己写歌词" and not user_lyrics.strip():
        st.error("请输入歌词内容")
    else:
        if lyrics_source == "🎵 AI自动生成歌词":
            lyrics = f"""[Verse]
{topic}的风 轻轻吹过
唤醒心中 沉睡的梦

[Chorus]
让全世界 听见这旋律
属于我们 灿烂的奇迹"""
        else:
            lyrics = user_lyrics
        
        with st.spinner("AI正在创作中，通常需要30-90秒..."):
            task_id = generate_song(api_key, lyrics, topic, style)
            if task_id:
                audio_url = fetch_audio_result(api_key, task_id)
                if audio_url:
                    # 生成成功，扣减次数
                    update_user_credits(record_id, credits - 1)
                    # 更新 session_state 中的次数
                    st.session_state.user_credits = credits - 1
                    
                    st.success("✅ 创作完成！")
                    st.audio(audio_url, format="audio/mp3")
                    st.markdown(f"[📥 点击下载歌曲]({audio_url})")
                else:
                    st.error("生成失败，请重试")
            else:
                st.error("任务提交失败")
