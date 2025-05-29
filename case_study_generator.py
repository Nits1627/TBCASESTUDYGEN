import streamlit as st
import google.generativeai as genai
import markdown2
import tempfile
from xhtml2pdf import pisa
import io

# === Gemini API Setup ===
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# === Streamlit UI Setup ===
st.set_page_config(page_title="AI Case Study Generator", layout="wide")
st.image("logo.png", width=180)

st.title("📚 AI-Powered Case Study Generator")
st.markdown("Craft sophisticated case studies with tailored formats and creative strategy insights.")

# === Session Setup ===
if "case_study" not in st.session_state:
    st.session_state.case_study = ""
if "project_details" not in st.session_state:
    st.session_state.project_details = {}

# === Input Form ===
with st.form("case_form"):
    st.subheader("📝 Enter Case Study Details")
    col1, col2 = st.columns(2)

    with col1:
        project_title = st.text_input("📌 Project Title", placeholder="e.g. Hyperlocal Ad Campaign")
        client_name = st.text_input("👤 Client", placeholder="e.g. SipWell Beverages")
        industry = st.text_input("🏭 Industry", placeholder="e.g. FMCG")

    with col2:
        brief = st.text_area("🧠 Project Brief", height=140, placeholder="What was the problem or objective?")
        results = st.text_area("📈 Outcomes / Achievements", height=140, placeholder="What did the campaign achieve?")

    submitted = st.form_submit_button("🎯 Recommend Case Study Format")

# === Step 1: Style Recommendations ===
if submitted:
    with st.spinner("Analyzing project to recommend the best strategy..."):
        strategy_prompt = f"""
Suggest 3 most suitable case study formats and ideal creative assets for this project:

Project Title: {project_title}
Client: {client_name}
Industry: {industry}
Brief: {brief}
Results: {results}

Return:
- 3 case study styles (with short descriptions)
- Ideal creative formats (reels, carousels, motion graphics, etc.)
"""
        response = model.generate_content(strategy_prompt).text.strip()
        st.session_state.project_details = {
            "project_title": project_title,
            "client_name": client_name,
            "industry": industry,
            "brief": brief,
            "results": results,
            "recommendations": response
        }

# === Display Style Options ===
if st.session_state.get("project_details"):
    st.markdown("### 🎯 AI Recommendations")
    st.markdown(st.session_state["project_details"]["recommendations"])

    # Extract 3 AI-suggested styles
    lines = st.session_state["project_details"]["recommendations"].split("\n")
    style_lines = [line.split(". ", 1)[1] for line in lines if line.startswith(("1.", "2.", "3.")) and ". " in line]

    # Add "Default Format" manually
    style_options = style_lines + ["Default Format (Structured Parameters)"]
    selected_style = st.radio("Select a case study style:", style_options, key="style_select")

    if st.button("🚀 Generate Case Study"):
        with st.spinner("Generating case study..."):
            if selected_style == "Default Format (Structured Parameters)":
                final_prompt = f"""
Create a professional case study in the following format:

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
Create a professional, formal case study using the selected style: {selected_style}

Use this format:
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

# === Display Final Case Study ===
if st.session_state.case_study:
    st.success("✅ Case Study Generated")
    st.markdown("### 📄 Final Case Study")
    st.markdown(st.session_state.case_study, unsafe_allow_html=True)

    # === Reprompt for Feedback ===
    feedback = st.text_area("🔁 Want to make edits or give feedback?", placeholder="e.g. Make it shorter, change the tone, add results")
    if st.button("♻️ Regenerate with Edits"):
        with st.spinner("Regenerating based on your feedback..."):
            revise_prompt = f"""
Revise the following case study according to this feedback: {feedback}

Original Case Study:
{st.session_state.case_study}

Maintain the same format and keep it formal.
"""
            st.session_state.case_study = model.generate_content(revise_prompt).text.strip()
            st.markdown("### ✨ Revised Case Study")
            st.markdown(st.session_state.case_study, unsafe_allow_html=True)

    # === Export Buttons ===
    st.download_button("📝 Download as Markdown", st.session_state.case_study, f"{project_title}.md", "text/markdown")

    def generate_pdf(content):
        html = markdown2.markdown(content)
        result = io.BytesIO()
        pisa.CreatePDF(io.StringIO(html), dest=result)
        return result

    if st.button("📄 Generate PDF"):
        pdf = generate_pdf(st.session_state.case_study)
        st.download_button("💾 Download PDF", data=pdf.getvalue(), file_name=f"{project_title}.pdf", mime="application/pdf")
