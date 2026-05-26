# streamlit_app.py
import streamlit as st
import requests
import time
import json

st.set_page_config(page_title="慧写歌", page_icon="🎵")
st.title("🎵 慧写歌")

# ========== API Key 读取（优先使用 secrets，本地测试时手动输入）==========
# 先从 secrets 中读取（云端安全存储）
api_key = st.secrets.get("MUREKA_API_KEY")

# 如果没有配置 secrets，则在侧边栏让用户手动输入（本地测试时使用）
if not api_key:
    with st.sidebar:
        st.header("⚙️ 设置")
        api_key = st.text_input("请输入你的 Mureka API Key", type="password")
        st.markdown("---")
        st.caption("提示：需要稳定的网络环境")
else:
    # 如果已经有 secrets，侧边栏显示提示信息
    with st.sidebar:
        st.header("⚙️ 设置")
        st.success("✅ API Key 已配置")
        st.caption("提示：需要稳定的网络环境")
# ================================================================

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
# =============================================

# 主界面
topic = st.text_input("歌曲主题", placeholder="例如：夏天、阳光、爱情")
style = st.selectbox("音乐风格", ["pop", "rock", "electronic", "jazz", "classical"])

if st.button("✨ 开始创作", type="primary"):
    if not api_key:
        st.error("请先在侧边栏输入你的 API Key")
    elif not topic:
        st.error("请输入歌曲主题")
    else:
        # 生成歌词
        lyrics = f"""[Verse]
{topic}的风 轻轻吹过
唤醒心中 沉睡的梦

[Chorus]
让全世界 听见这旋律
属于我们 灿烂的奇迹"""
        
        with st.spinner("AI正在创作中，通常需要30-90秒..."):
            task_id = generate_song(api_key, lyrics, topic, style)
            if task_id:
                audio_url = fetch_audio_result(api_key, task_id)
                if audio_url:
                    st.success("✅ 创作完成！")
                    st.audio(audio_url, format="audio/mp3")
                    st.markdown(f"[📥 点击下载歌曲]({audio_url})")
                else:
                    st.error("生成失败，请重试")
            else:
                st.error("任务提交失败")