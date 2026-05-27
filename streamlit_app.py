# streamlit_app.py
import streamlit as st
import requests
import time
import json

st.set_page_config(page_title="慧写歌", page_icon="🎵")

# Logo 居中，宽度 180 像素
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("logoPNG.png", width=180)

# ========== API Key 读取 ==========
api_key = st.secrets.get("MUREKA_API_KEY")

if not api_key:
    with st.sidebar:
        st.header("⚙️ 设置")
        api_key = st.text_input("请输入你的 Mureka API Key", type="password")
        st.markdown("---")
        st.caption("提示：需要稳定的网络环境")
else:
    with st.sidebar:
        st.header("⚙️ 设置")
        st.success("✅ API Key 已配置")
        st.caption("提示：需要稳定的网络环境")

# ================= 音乐生成函数 =================
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
            result = response.json()
            return result.get("id")
        elif response.status_code == 429:
            st.warning("⚠️ 服务器繁忙（并发限制），请稍后重试")
            return None
        else:
            st.error(f"提交失败：{response.text}")
            return None
    except Exception as e:
        st.error(f"网络错误：{e}")
        return None

def fetch_audio_result(api_key, task_id):
    """查询任务并获取歌曲链接和歌词"""
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
                        audio_url = choices[0].get("url")
                        # 获取返回的歌词
                        lyrics_text = choices[0].get("lyrics", "")
                        return audio_url, lyrics_text
                elif status == "failed":
                    return None, None
        except Exception:
            pass
    return None, None

# ================= 主界面 =================
st.markdown("---")

# 第一行：主题和风格
col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("🎵 歌曲主题", placeholder="例如：夏天、阳光、爱情")
with col2:
    style = st.selectbox("🎸 音乐风格", ["pop", "rock", "electronic", "jazz", "classical", "hip-hop", "rnb"])

st.markdown("---")

# 歌词来源选择
lyrics_source = st.radio(
    "📝 歌词来源",
    ["🎵 AI自动生成歌词", "✍️ 我自己写歌词"],
    horizontal=True
)

user_lyrics = ""
if lyrics_source == "✍️ 我自己写歌词":
    st.markdown("💡 **提示**：可以用 `[Verse]`（主歌）、`[Chorus]`（副歌）标记段落")
    user_lyrics = st.text_area(
        "📝 请输入你的歌词",
        placeholder="""示例格式：
[Verse]
夏天的风轻轻吹过
唤醒心中沉睡的梦

[Chorus]
让全世界听见这首歌
属于我们灿烂的时刻""",
        height=200
    )

st.markdown("---")

# 创作按钮
if st.button("✨ 开始创作", type="primary", use_container_width=True):
    if not api_key:
        st.error("❌ 请先在侧边栏输入你的 API Key")
    elif not topic:
        st.error("❌ 请输入歌曲主题")
    elif lyrics_source == "✍️ 我自己写歌词" and not user_lyrics.strip():
        st.error("❌ 请输入歌词内容")
    else:
        # 处理歌词
        if lyrics_source == "🎵 AI自动生成歌词":
            lyrics = f"""[Verse]
{topic}的风 轻轻吹过
唤醒心中 沉睡的梦

[Chorus]
让全世界 听见这旋律
属于我们 灿烂的奇迹"""
        else:
            lyrics = user_lyrics
        
        with st.spinner("🎶 AI正在创作中，通常需要30-90秒，请耐心等待..."):
            task_id = generate_song(api_key, lyrics, topic, style)
            if task_id:
                audio_url, lyrics_text = fetch_audio_result(api_key, task_id)
                if audio_url:
                    st.success("✅ 创作完成！")
                    
                    # 显示歌词
                    with st.expander("📝 查看歌词", expanded=True):
                        if lyrics_text:
                            st.text(lyrics_text)
                        else:
                            st.text(lyrics)
                    
                    # 音频播放和下载
                    st.audio(audio_url, format="audio/mp3")
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.markdown(f"""
                        <div style="text-align: center;">
                            <a href="{audio_url}" target="_blank" style="
                                display: inline-block;
                                background-color: #4CAF50;
                                color: white;
                                padding: 10px 20px;
                                text-decoration: none;
                                border-radius: 5px;
                                font-weight: bold;
                            ">📥 点击下载歌曲</a>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.error("❌ 生成失败，请重试")
            else:
                st.error("❌ 任务提交失败")

# 页脚
st.markdown("---")
st.caption("🎵 慧写歌 - AI智能音乐创作 | 让写歌从此变简单")
