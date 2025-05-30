import streamlit as st
import google.generativeai as genai
import markdown2
import tempfile
from xhtml2pdf import pisa
import io
import os
import json
import re

# === Setup Directory for Saved Library ===
LIBRARY_DIR = "./case_study_library"
os.makedirs(LIBRARY_DIR, exist_ok=True)

# === Gemini API Setup ===
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# === Streamlit UI Setup ===
st.set_page_config(page_title="AI Case Study Generator", layout="wide")
st.image("logo.png", width=180)
st.title("📚 AI-Powered Case Study Generator")
st.markdown("Craft polished case studies with AI-recommended formats or a default structured template.")

# === Session State Setup ===
for key in ["recommendations", "styles", "selected_style", "case_study"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "styles" else []

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

# === Step 1: Get Case Study Format Suggestions ===
if go:
    prompt = f"""
As a senior strategist, list the 3 most suitable case study formats for this project.

1. Format One:
2. Format Two:
3. Format Three:

Then list “Ideal Creative Assets:” with bullet points.

Project Title: {project_title}
Client: {client_name}
Industry: {industry}
Brief: {brief}
Results: {results}
"""
    rec = model.generate_content(prompt).text.strip()
    st.session_state.recommendations = rec
    found = re.findall(r'^\s*\d+\.\s*(.+?):', rec, flags=re.MULTILINE)
    st.session_state.styles = found[:3] + ["Default Format (Structured Parameters)"]

# === Step 2: Show Recommendations + Style Selection ===
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
            final_prompt = f"""
Create a professional, formal case study using the "{style}" approach.

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

# === Step 4: Display, Refine, and Export ===
if st.session_state.case_study:
    st.success("✅ Case Study Generated")
    st.markdown("### Final Case Study")
    st.markdown(st.session_state.case_study, unsafe_allow_html=True)

    # Edit/Refine
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

    # Export as Markdown
    st.download_button(
        "📝 Download as Markdown",
        st.session_state.case_study,
        f"{project_title}.md",
        "text/markdown"
    )

    # Export as PDF
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

    # Save to Local Library
    if st.button("💾 Save to Library"):
        path = os.path.join(LIBRARY_DIR, f"{project_title.replace(' ', '_')}.json")
        with open(path, "w") as f:
            json.dump({
                "project_title": project_title,
                "client": client_name,
                "industry": industry,
                "brief": brief,
                "results": results,
                "style": st.session_state.selected_style,
                "case_study": st.session_state.case_study
            }, f)
        st.success("Saved to local case study library!")

# === Load from Library ===
st.sidebar.title("📚 Case Study Library")
files = [f for f in os.listdir(LIBRARY_DIR) if f.endswith(".json")]
selected_file = st.sidebar.selectbox("View saved case studies:", [""] + files)

if selected_file:
    with open(os.path.join(LIBRARY_DIR, selected_file), "r") as f:
        data = json.load(f)
        st.sidebar.markdown(f"**Project:** {data['project_title']}")
        st.sidebar.markdown(f"**Client:** {data['client']}")
        st.sidebar.markdown(f"**Style:** {data['style']}")
        if st.sidebar.button("📄 Load Case Study"):
            st.session_state.case_study = data["case_study"]
            st.success("Loaded case study from library.")
            st.markdown("### Final Case Study (Loaded)")
            st.markdown(data["case_study"], unsafe_allow_html=True)
