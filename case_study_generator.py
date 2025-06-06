import streamlit as st
import google.generativeai as genai
import markdown2
import tempfile
from xhtml2pdf import pisa
import io
import re
import requests

# === API Setup ===
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
SERPER_API_URL = "https://google.serper.dev/search"

# === Streamlit UI Setup ===
st.set_page_config(page_title="AI Case Study Generator", layout="wide")
st.image("logo.png", width=180)
st.title("📚 AI-Powered Case Study Generator")
st.markdown("Craft polished case studies with AI-recommended formats and real-time company data.")

# === Session State ===
for key, default in [
    ("recommendations", ""),
    ("styles", []),
    ("selected_style", None),
    ("case_study", ""),
    ("case_library", []),
    ("web_context", "")  # ensure always defined
]:
    if key not in st.session_state:
        st.session_state[key] = default

# === Utility: Fetch Company Insights via Serper.dev ===
def fetch_company_context(query):
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": f"{query}", "num": 5}
    try:
        res = requests.post(SERPER_API_URL, headers=headers, json=payload)
        results = res.json().get("organic", [])
        snippets = [r["snippet"] for r in results if "snippet" in r]
        return "\n".join(snippets[:3])
    except Exception:
        return ""

# === Step 0: Input Form ===
with st.form("input_form"):
    st.subheader("Enter Project Details")
    col1, col2 = st.columns(2)
    with col1:
        project_title = st.text_input("Project Title")
        client_name   = st.text_input("Client / Brand Name")
        industry      = st.text_input("Industry")
    with col2:
        brief   = st.text_area("Project Brief (2-4 lines)")
        results = st.text_area("Key Outcomes / Achievements")
    go = st.form_submit_button("🎯 Recommend Case Study Formats")

# === Step 1: Get Formats & Web Context ===
if go:
    # Fetch real-time company data
    st.info("🔎 Fetching company data from the web…")
    st.session_state.web_context = fetch_company_context(f"{client_name} {industry} overview")

    prompt = f"""
You are a brand strategist. Suggest 3 case study styles.

Project Title: {project_title}
Client: {client_name}
Industry: {industry}
Brief: {brief}
Results: {results}

Web Insights:
{st.session_state.web_context}

Return only:
1. [Style One] Case Study:
2. [Style Two] Case Study:
3. [Style Three] Case Study:
Then list “Ideal Creative Assets:” with bullets.
"""
    rec = model.generate_content(prompt).text.strip()
    st.session_state.recommendations = rec

    styles_found = re.findall(r'^\s*\d+\.\s*(.+?):', rec, flags=re.MULTILINE)
    st.session_state.styles = styles_found[:3] + ["Default Format (Structured Parameters)"]

# === Step 2: Display Recommendations & Style Selector ===
if st.session_state.recommendations:
    st.markdown("### 🧠 AI Recommendations")
    st.markdown(st.session_state.recommendations)

    st.session_state.selected_style = st.radio(
        "Select a Case Study Style:",
        st.session_state.styles
    )

# === Step 3: Generate Case Study ===
if st.session_state.selected_style:
    if st.button("🚀 Generate Case Study"):
        style = st.session_state.selected_style
        base_context = f"""
Project Title: {project_title}
Client: {client_name}
Industry: {industry}
Brief: {brief}
Results: {results}

Web Insights:
{st.session_state.web_context}

Use this format:
Case Study Parameters:
Client Name / Brand Name: {client_name}
Problem Statement / Task:
Business Objective:
Solution:
Key Results:
"""
        if style.startswith("Default Format"):
            final_prompt = f"Create a professional case study with structured parameters:\n{base_context}"
        else:
            final_prompt = f"Create a formal case study in the style “{style}”:\n{base_context}"

        result = model.generate_content(final_prompt).text.strip()
        st.session_state.case_study = result
        st.session_state.case_library.append({
            "title": project_title,
            "client": client_name,
            "style": style,
            "case": result
        })

# === Step 4: Display & Refine ===
if st.session_state.case_study:
    st.success("✅ Case Study Generated")
    st.markdown("### 📄 Final Case Study")
    st.markdown(st.session_state.case_study, unsafe_allow_html=True)

    feedback = st.text_area("✏️ Suggest edits or refinements:")
    if st.button("♻️ Regenerate with Feedback"):
        rev_prompt = f"""
Revise the following based on feedback: {feedback}

Original Case Study:
{st.session_state.case_study}

Keep format and tone consistent.
"""
        st.session_state.case_study = model.generate_content(rev_prompt).text.strip()
        st.markdown("### ✨ Revised Case Study")
        st.markdown(st.session_state.case_study, unsafe_allow_html=True)

    # Export Markdown
    st.download_button(
        "📝 Download as Markdown",
        st.session_state.case_study,
        f"{project_title}.md",
        "text/markdown"
    )

    # Export PDF with logo header
    def generate_pdf(text):
        html = f"""
        <html>
        <head><style>body {{ font-family: Helvetica; }}</style></head>
        <body>
            <img src="logo.png" width="120"/><br/><br/>
            {markdown2.markdown(text)}
        </body>
        </html>
        """
        buf = io.BytesIO()
        pisa.CreatePDF(io.StringIO(html), dest=buf)
        return buf

    if st.button("📄 Download PDF"):
        pdf_buf = generate_pdf(st.session_state.case_study)
        st.download_button(
            "💾 Save PDF",
            data=pdf_buf.getvalue(),
            file_name=f"{project_title}.pdf",
            mime="application/pdf"
        )

# === Step 5: In-Session Case Study Library ===
if st.session_state.case_library:
    st.markdown("---")
    st.markdown("### 📚 Saved Case Study Library")
    for idx, item in enumerate(st.session_state.case_library[::-1], start=1):
        with st.expander(f"{idx}. {item['title']} ({item['style']})"):
            st.markdown(item["case"], unsafe_allow_html=True)
