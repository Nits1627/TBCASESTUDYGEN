import streamlit as st
import google.generativeai as genai
import markdown2
import tempfile
from xhtml2pdf import pisa
import io
import re

# === Gemini API Setup ===
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# === Streamlit UI Setup ===
st.set_page_config(page_title="AI Case Study Generator", layout="wide")
st.image("logo.png", width=180)
st.title("📚 AI-Powered Case Study Generator")
st.markdown("Craft polished case studies with AI-recommended formats or a default structured template.")

# === Session State ===
if "recommendations" not in st.session_state:
    st.session_state.recommendations = ""
if "styles" not in st.session_state:
    st.session_state.styles = []
if "selected_style" not in st.session_state:
    st.session_state.selected_style = None
if "case_study" not in st.session_state:
    st.session_state.case_study = ""

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

# === Step 1: Ask Gemini for 3 Formats ===
if go:
    prompt = f"""
As a senior strategist, list the 3 most suitable case study formats for this project.
Just list them like:

1. Format One Case Study:
2. Format Two Case Study:
3. Format Three Case Study:

Then list “Ideal Creative Assets:” with bullet points.

Project Title: {project_title}
Client: {client_name}
Industry: {industry}
Brief: {brief}
Results: {results}
"""
    rec = model.generate_content(prompt).text.strip()
    st.session_state.recommendations = rec

    # parse out the 3 styles via regex (captures text before the colon)
    found = re.findall(r'^\s*\d+\.\s*(.+?):', rec, flags=re.MULTILINE)
    st.session_state.styles = found[:3]  # ensure max 3
    # always append default
    st.session_state.styles.append("Default Format (Structured Parameters)")

# === Step 2: Show Recommendations + Radio ===
if st.session_state.recommendations:
    st.markdown("### AI Recommendations")
    st.markdown(st.session_state.recommendations)

    st.session_state.selected_style = st.radio(
        "Select your case study style:",
        st.session_state.styles
    )

# === Step 3: Generate Case Study ===
if st.session_state.selected_style:
    if st.button("🚀 Generate Case Study"):
        style = st.session_state.selected_style
        if style.startswith("Default Format"):
            # default structured template
            final_prompt = f"""
Create a professional case study with this format:

Case Study Parameters:
Client Name / Brand Name: {client_name}
Problem Statement / Task:
Business Objective:
Solution:
Key Results:

Project Title: {project_title}
Industry: {industry}
Brief: {brief}
Results: {results}
"""
        else:
            # style-specific
            final_prompt = f"""
Create a professional, formal case study using the "{style}" approach.

Use this template structure:

Case Study Parameters:
Client Name / Brand Name: {client_name}
Problem Statement / Task:
Business Objective:
Solution:
Key Results:

Project Title: {project_title}
Industry: {industry}
Brief: {brief}
Results: {results}
"""
        st.session_state.case_study = model.generate_content(final_prompt).text.strip()

# === Step 4: Display & Reprompt ===
if st.session_state.case_study:
    st.success("✅ Case Study Generated")
    st.markdown("### Final Case Study")
    st.markdown(st.session_state.case_study, unsafe_allow_html=True)

    feedback = st.text_area("✏️ Suggest edits or refinements:")
    if st.button("♻️ Regenerate with Feedback"):
        rev_prompt = f"""
Please revise this case study based on the following feedback: {feedback}

Original Case Study:
{st.session_state.case_study}

Keep the same format and tone.
"""
        st.session_state.case_study = model.generate_content(rev_prompt).text.strip()
        st.markdown("### Revised Case Study")
        st.markdown(st.session_state.case_study, unsafe_allow_html=True)

    # === Export Buttons ===
    st.download_button(
        "📝 Download as Markdown",
        st.session_state.case_study,
        f"{project_title}.md",
        "text/markdown"
    )

    def generate_pdf(text):
        html = markdown2.markdown(text)
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
