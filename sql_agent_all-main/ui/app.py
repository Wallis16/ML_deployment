"""Streamlit UI for the SQL agent — a thin client over the API in ../app.

Run with:
    streamlit run ui/app.py
"""

import os

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="SQL Agent", page_icon="🗄️", layout="centered")

st.title("🗄️ SQL Agent")
st.caption(
    "Ask a question in plain English about the **movie_lens** or **olist** "
    "databases. The agent picks the right one, writes and validates SQL, "
    "runs it, and reports back."
)

with st.sidebar:
    st.subheader("Settings")
    API_URL = st.text_input("API URL", value=API_URL)
    max_attempts = st.slider("Max SQL retries", min_value=1, max_value=10, value=3)
    st.divider()
    st.markdown(
        "**Example questions**\n"
        "- Top 5 highest-rated movies with at least 100 ratings?\n"
        "- Which movie genres have the highest average rating?\n"
        "- Top 5 product categories by number of orders?\n"
        "- Average order value by customer state?"
    )

question = st.text_area(
    "Your question",
    placeholder="What are the top 5 highest-rated movies with at least 100 ratings?",
    height=80,
)

if st.button("Ask", type="primary", disabled=not question.strip()):
    with st.spinner("Writing and validating SQL, running the query..."):
        try:
            response = requests.post(
                f"{API_URL}/query",
                json={"question": question, "max_attempts": max_attempts},
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()
        except requests.RequestException as exc:
            st.error(f"Couldn't reach the API at {API_URL}: {exc}")
            st.stop()

    if result.get("database"):
        st.markdown(f"**Database:** `{result['database']}`")

    if result.get("sql"):
        st.markdown("**SQL**")
        st.code(result["sql"], language="sql")

    if result.get("error"):
        st.error(result["error"])

    if result.get("report"):
        st.markdown("**Report**")
        st.markdown(result["report"])

    if result.get("plot_url"):
        st.image(f"{API_URL}{result['plot_url']}")
