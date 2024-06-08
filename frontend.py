import streamlit as st
from coder import run_graph

st.title("🚀 Coding Agent Chat 💻")

st.markdown("""
<style>
    .stTextInput > label {
        font-size: 20px;
        color: #4A4A4A;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("### Ask me a coding question 🤔:")

user_input = st.text_input("")
if user_input:
    response = run_graph(user_input)
    st.markdown("### ✅ I generated and executed the following tests for you:")
    st.markdown(f"```python\n{response.tests}\n```")
    st.markdown("### 📝 Code:")
    st.markdown(f"```python\n{response.code}\n```")


st.markdown("### Errors so far:")
st.markdown("- Ensure that the file path is correct and the file exists before trying to access it: 3")