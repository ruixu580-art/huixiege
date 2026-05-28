# streamlit_app.py
import streamlit as st
import requests
import time
from pyairtable import Table
from supabase import create_client, Client

st.set_page_config(page_title="慧写歌", page_icon="🎵")

# Logo
col1, col2 = st.columns([1, 5])
with col1:
    st.image("logoPNG.svg", width=80)
with col2:
    st.write("")  # 不显示文字，Logo已包含

# ========== Airtable 连接 ==========
@st.cache_resource
def get_airtable():
    """获取 Airtable 表对象"""
    return Table(
        st.secrets["AIRTABLE_TOKEN"],
        st.secrets["AIRTABLE_BASE_ID"],
        st.secrets["AIRTABLE_TABLE_NAME"]
    )

def get_user_credits(user_email):
    """查询用户剩余次数"""
    table = get_airtable()
    formula = f"{{user_id}} = '{user_email}'"
    records = table.all(formula=formula)
    
    if records:
        return records[0]['fields'].get('credits', 0), records[0]['id']
    else:
        # 新用户，赠送 1 次试用
        record = table.create({
            'user_id': user_email,
            'user_name': user_email,
            'credits': 1
        })
        return 1, record['id']

def update_user_credits(record_id, new_credits):
    """更新用户剩余次数"""
    table = get_airtable()
    table.update(record_id, {'credits': new_credits})

# ========== Supabase 连接 ==========
@st.cache_resource
def init_supabase() -> Client:
    """初始化 Supabase 客户端"""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# ========== 登录界面 ==========
def show_login_ui(supabase):
    """显示登录/注册界面"""
    st.markdown("### 🔐 欢迎使用慧写歌")
    st.markdown("请登录或注册账号")
    
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("邮箱", placeholder="your@email.com")
            password = st.text_input("密码", type="password")
            submitted = st.form_submit_button("登录", type="primary")
            
            if submitted:
                if not email or not password:
                    st.error("请输入邮箱和密码")
                else:
                    try:
                        response = supabase.auth.sign_in_with_password({
                            "email": email,
                            "password": password
                        })
                        if response.user:
                            st.session_state.user = {
                                "email": response.user.email,
                                "user_id": response.user.id
                            }
                            st.success(f"欢迎回来，{email}！")
                            st.rerun()
                        else:
                            st.error("登录失败")
                    except Exception as e:
                        st.error(f"登录失败：{str(e)}")
    
    with tab2:
        with st.form("register_form"):
            new_email = st.text_input("邮箱", placeholder="your@email.com")
            new_password = st.text_input("密码", type="password")
            confirm_password = st.text_input("确认密码", type="password")
            submitted = st.form_submit_button("注册", type="primary")
            
            if submitted:
                if not new_email or not new_password:
                    st.error("请输入邮箱和密码")
                elif new_password != confirm_password:
                    st.error("两次输入的密码不一致")
                else:
                    try:
                        response = supabase.auth.sign_up({
                            "email": new_email,
                            "password": new_password
                        })
                        if response.user:
                            st.success("注册成功！请登录")
                        else:
                            st.error("注册失败")
                    except Exception as e:
                        error_msg = str(e)
                        if "already registered" in error_msg.lower():
                            st.error("该邮箱已注册，请直接登录")
                        else:
                            st.error(f"注册失败：{error_msg}")

def logout():
    """退出登录"""
    st.session_state.user = None
    st.rerun()

# ========== API Key 读取 ==========
api_key = st.secrets.get("MUREKA_API_KEY")

# ========== 初始化 Supabase 和登录状态 ==========
supabase = init_supabase()

# 检查登录状态
if "user" not in st.session_state or st.session_state.user is None:
    show_login_ui(supabase)
    st.stop()

# 已登录用户
user_email = st.session_state.user.get("email")
credits, record_id = get_user_credits(user_email)

# 侧边栏显示用户信息
with st.sidebar:
    st.header("👤 我的账号")
    st.success(f"当前用户：{user_email}")
    st.metric("🎵 剩余次数", f"{credits}次")
    
    if st.button("退出登录"):
        logout()
    
    st.markdown("---")
    if api_key:
        st.success("✅ API Key 已配置")
    else:
        st.error("❌ API Key 未配置")

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

# ========== 主界面 ==========
st.markdown("---")
# ========== 购买套餐 ==========
with st.expander("💰 购买创作次数", expanded=False):
    st.markdown("选择套餐，支付后自动获取次数（支付后请用订单号激活）")
    
    # 使用 HTML 链接，手机端稳定跳转
    st.markdown(
        '<a href="https://mbd.pub/o/bread/YZaTlZ9paQ==" target="_blank" rel="noopener noreferrer" style="display: block; width: 100%; background-color: #4CAF50; color: white; text-align: center; padding: 10px; margin: 5px 0; text-decoration: none; border-radius: 5px;">🎵 单次体验 ¥2.99</a>',
        unsafe_allow_html=True
    )
    
    st.markdown(
        '<a href="https://mbd.pub/o/bread/YZaTlZ9pag==" target="_blank" rel="noopener noreferrer" style="display: block; width: 100%; background-color: #2196F3; color: white; text-align: center; padding: 10px; margin: 5px 0; text-decoration: none; border-radius: 5px;">📦 20次套餐 ¥29.9</a>',
        unsafe_allow_html=True
    )
    
    st.markdown(
        '<a href="https://mbd.pub/o/bread/YZaTlZ9pbQ==" target="_blank" rel="noopener noreferrer" style="display: block; width: 100%; background-color: #FF9800; color: white; text-align: center; padding: 10px; margin: 5px 0; text-decoration: none; border-radius: 5px;">🌟 年卡会员 ¥299</a>',
        unsafe_allow_html=True
    )
    
    st.markdown(
        '<a href="https://mbd.pub/o/bread/YZaTlZ9qZQ==" target="_blank" rel="noopener noreferrer" style="display: block; width: 100%; background-color: #9C27B0; color: white; text-align: center; padding: 10px; margin: 5px 0; text-decoration: none; border-radius: 5px;">💎 终身会员 ¥699</a>',
        unsafe_allow_html=True
    )
    
    st.caption("💡 支付后请将保存订单号发至客服微信：13113021610，手动为您增加次数")
topic = st.text_input("🎵 歌曲主题", placeholder="例如：夏天、阳光、爱情")
style = st.selectbox("🎸 音乐风格", ["pop", "rock", "electronic", "jazz", "classical"])

# 歌词来源选择
lyrics_source = st.radio("📝 歌词来源", ["🎵 AI自动生成歌词", "✍️ 我自己写歌词"], horizontal=True)

user_lyrics = ""
if lyrics_source == "✍️ 我自己写歌词":
    user_lyrics = st.text_area("📝 请输入你的歌词", height=150)

# 开始创作按钮
if st.button("✨ 开始创作", type="primary"):
    # 检查登录和次数
    if not api_key:
        st.error("请先在侧边栏输入 API Key")
    elif credits <= 0:
        st.warning("⚠️ 次数不足，请购买套餐或联系客服")
    elif not topic:
        st.error("请输入歌曲主题")
    elif lyrics_source == "✍️ 我自己写歌词" and not user_lyrics.strip():
        st.error("请输入歌词内容")
    else:
        # 生成歌词
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
                    st.success("✅ 创作完成！")
                    st.audio(audio_url, format="audio/mp3")
                    st.markdown(f"[📥 点击下载歌曲]({audio_url})")
                else:
                    st.error("生成失败，请重试")
            else:
                st.error("任务提交失败")

# ========== 页脚 ==========
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #666; padding: 20px;">
        慧写歌 - 让每个人能轻松写歌<br>
        歌曲精修合作请联系邮箱：<a href="mailto:1548909523@qq.com">1548909523@qq.com</a>
    </div>
    """,
    unsafe_allow_html=True
)
