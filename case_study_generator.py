import streamlit as st
import google.generativeai as genai
import markdown2
import pdfkit
import tempfile
import re

# === Gemini API Setup ===
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# === Streamlit UI Setup ===
st.set_page_config(page_title="AI Case Study Generator", layout="wide")
st.image("logo.png", width=180)  # Place logo.png in the same directory

st.title("📚 AI-Powered Case Study Generator")
st.markdown("Craft formal, C-suite-ready case studies with recommended styles and creative assets.")

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

    submitted = st.form_submit_button("🎯 Recommend Case Study Formats")

# === Step 1: Ask Gemini for Style Suggestions ===
if submitted:
    with st.spinner("Getting tailored format recommendations..."):
        strategy_prompt = f"""
You're a senior strategist. Recommend the 3 best case study styles and list suitable creative assets.

Respond in this format:

1. [Style Name] Case Study
2. [Style Name] Case Study
3. [Style Name] Case Study

Then give a bullet list of recommended creative formats (videos, carousels, testimonials, etc.).

Project Title: {project_title}
Client: {client_name}
Industry: {industry}
Brief: {brief}
Results: {results}
"""

        strategy_response = model.generate_content(strategy_prompt)
        strategy_text = strategy_response.text.strip()

    # === Display AI Output ===
    st.markdown("### 🤖 AI Recommendations")
    st.markdown(strategy_text)

    # === Extract Case Study Styles ===
    style_pattern = re.findall(r'\d+\.\s+["“]?(.*?)["”]?\s+Case Study', strategy_text)
    if not style_pattern:
        st.error("⚠️ Unable to extract case study styles. Please retry.")
        st.stop()

    selected_style = st.radio("🌟 Choose a preferred case study style:", style_pattern)

    # === Step 2: Generate Final Case Study ===
    if st.button("🚀 Generate Final Case Study"):
        with st.spinner("Writing a formal case study..."):
            final_prompt = f"""
Write a complete case study using the selected style: {selected_style}

Client: {client_name}
Project: {project_title}
Industry: {industry}
Brief: {brief}
Results: {results}

Use this structure:
- Title
- Problem Statement
- Strategic Approach
- Implementation
- Outcomes

Maintain a polished, professional tone suitable for corporate review decks or client pitches.
"""

            case_study = model.generate_content(final_prompt).text.strip()

        st.success("✅ Case Study Generated")
        st.markdown("### 📄 Final Case Study")
        st.markdown(case_study, unsafe_allow_html=True)

        # === Alternate Styles ===
        with st.expander("✨ Alternate Formats"):
            alt_prompt = f"""
Generate 2 alternate versions of the same case study:
1. A storytelling social media version.
2. A slide-style version for investor or pitch presentations.

Style: {selected_style}
Project: {project_title}
Client: {client_name}
Industry: {industry}
Brief: {brief}
Results: {results}
"""
            alt_response = model.generate_content(alt_prompt)
            st.markdown(alt_response.text.strip())

        # === Export: Markdown ===
        markdown_output = f"# {project_title}\n\n**Client**: {client_name}\n\n**Industry**: {industry}\n\n**Brief**: {brief}\n\n**Results**: {results}\n\n{case_study}"

        st.download_button(
            label="📝 Download as Markdown",
            data=markdown_output,
            file_name=f"{project_title.replace(' ', '_')}.md",
            mime="text/markdown"
        )

        # === Export: PDF ===
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
