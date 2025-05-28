import streamlit as st
from google import generativeai as genai
import markdown2
import pdfkit
import tempfile

# === Gemini API Setup ===
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])  # For Streamlit Cloud
model = genai.GenerativeModel("gemini-1.5-flash")

# === Streamlit UI Setup ===
st.set_page_config(page_title="AI Case Study Generator", layout="wide")
st.title("📚 AI-Powered Case Study Generator")
st.markdown("Create polished, professional case studies from brief summaries using Gemini 1.5 Flash.")

# === Input Form ===
with st.form("case_form"):
    st.subheader("📝 Enter Case Study Details")
    col1, col2 = st.columns(2)

    with col1:
        project_title = st.text_input("📌 Project Title", placeholder="e.g. Hyperlocal Ad Campaign for Beverage Brand")
        client_name = st.text_input("👤 Client", placeholder="e.g. SipWell Beverages")
        industry = st.text_input("🏭 Industry", placeholder="e.g. FMCG / Food & Beverage")

    with col2:
        brief = st.text_area("🧠 Project Brief", height=140, placeholder="What was the problem or objective?")
        results = st.text_area("📈 Outcomes / Achievements", height=140, placeholder="What did the campaign achieve?")

    submitted = st.form_submit_button("🚀 Generate Case Study")

# === Case Study Generation ===
if submitted:
    if not (project_title and client_name and brief):
        st.warning("Please fill in at least the project title, client, and brief.")
    else:
        with st.spinner("Generating with Gemini..."):
            prompt = f"""
You are a strategist and creative copywriter.

Write a structured case study for an advertising/media project using the following details:

Project Title: {project_title}
Client: {client_name}
Industry: {industry}
Brief Summary: {brief}
Key Results: {results}

Format it with the following sections:
- Title
- Problem Statement
- Strategy / Solution
- Implementation
- Outcomes

Make it professional, polished, and story-driven.
"""
            response = model.generate_content(prompt)
            case_study = response.text.strip()

        st.success("✅ Case Study Generated")
        st.markdown("### 📄 Main Version")
        st.text_area("Formatted Case Study", case_study, height=350)

        # === Alternate Style Versions ===
        with st.expander("✨ Alternate Style Versions"):
            alt_prompt = f"""
Generate 2 additional versions of the same case study:
1. A short punchy storytelling version.
2. A more formal version for investor/client decks.
Use the same inputs:
Project: {project_title}
Client: {client_name}
Industry: {industry}
Brief: {brief}
Results: {results}
"""
            alt_response = model.generate_content(alt_prompt)
            st.markdown(alt_response.text.strip())

        # === Export Buttons ===
        markdown_output = f"# {project_title}\n\n**Client**: {client_name}\n\n**Industry**: {industry}\n\n**Brief**: {brief}\n\n**Results**: {results}\n\n{case_study}"

        st.download_button(
            label="📝 Download as Markdown",
            data=markdown_output,
            file_name=f"{project_title.replace(' ', '_')}.md",
            mime="text/markdown"
        )

        def generate_pdf(text):
            html = markdown2.markdown(text)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                pdfkit.from_string(html, tmp_file.name)
                return tmp_file.name

        if st.button("📄 Generate PDF"):
            pdf_path = generate_pdf(markdown_output)
            with open(pdf_path, "rb") as file:
                st.download_button(
                    label="💾 Download PDF",
                    data=file,
                    file_name=f"{project_title.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )