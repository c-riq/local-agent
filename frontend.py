import streamlit as st
from coder import run_graph

st.title("Coding Agent Chat")

user_input = st.text_input("Ask me a coding question:")
if user_input:
    response = run_graph(user_input)
    st.text(f"{response.code}")
