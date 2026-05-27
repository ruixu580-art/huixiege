import streamlit as st
from pyairtable import Table

st.set_page_config(page_title="Airtable 测试")

st.title("Airtable 连接测试")

# 从 secrets 读取配置
try:
    token = st.secrets["AIRTABLE_TOKEN"]
    base_id = st.secrets["AIRTABLE_BASE_ID"]
    table_name = st.secrets["AIRTABLE_TABLE_NAME"]
    
    st.write(f"✅ Token 已读取: {token[:15]}...")
    st.write(f"✅ Base ID: {base_id}")
    st.write(f"✅ Table Name: {table_name}")
    
    # 尝试连接
    table = Table(token, base_id, table_name)
    
    # 尝试读取所有数据
    records = table.all()
    st.success(f"✅ 连接成功！读取到 {len(records)} 条记录")
    
    # 显示记录
    for record in records:
        st.write(record['fields'])
        
except Exception as e:
    st.error(f"❌ 连接失败：{e}")
    st.code(f"错误类型: {type(e).__name__}\n详细信息: {e}")
