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
st.image("logo.png", width=180)

st.title("📚 AI-Powered Case Study Generator")
st.markdown("Craft sophisticated case studies with tailored formats and creative strategy insights.")

# === Form to Collect Inputs ===
if "style_options" not in st.session_state:
    st.session_state.style_options = None
if "strategy_text" not in st.session_state:
    st.session_state.strategy_text = ""
if "selected_style" not in st.session_state:
    st.session_state.selected_style = ""

with st.form("case_form"):
    st.subheader("📝 Enter Case Study Details")
    col1, col2 = st.columns(2)

    with col1:
        project_title = st.text_input("📌 Project Title", placeholder="e.g. Hyperlocal Ad Campaign")
        client_name = st.text_input("👤 Client", placeholder="e.g. SipWell Beverages")
        industry = st.text_input("🏭 Industry", placeholder="e.g. FMCG / Food & Beverage")

    with col2:
        brief = st.text_area("🧠 Project Brief", height=140, placeholder="Describe the campaign objective.")
        results = st.text_area("📈 Outcomes / Achievements", height=140, placeholder="Highlight the results.")

    submitted = st.form_submit_button("🎯 Recommend Case Study Format")

# === Phase 1: Recommend Case Study Style ===
if submitted:
    with st.spinner("🔍 Analyzing project to recommend best strategy..."):
        strategy_prompt = f"""
As a senior strategist, suggest the top 3 most suitable case study formats for the following project.
Also suggest creative asset types that go well with this project (like videos, reels, carousels).

Project Title: {project_title}
Client: {client_name}
Industry: {industry}
Brief: {brief}
Results: {results}

Return only the following:
1. [Style Name] Case Study
2. [Style Name] Case Study
3. [Style Name] Case Study
Creative Assets: [List of recommended asset types]
"""

        response = model.generate_content(strategy_prompt)
        strategy_text = response.text.strip()

        # Save to session
        st.session_state.strategy_text = strategy_text
        st.session_state.style_options = re.findall(r'\d+\.\s+["“]?(.*?)["”]?\s+Case Study', strategy_text)

# === Phase 2: Display Options and Proceed ===
if st.session_state.style_options:
    st.markdown("### 🎯 AI Recommendations")
    st.markdown(st.session_state.strategy_text)

    st.session_state.selected_style = st.radio(
        "🌟 Choose your preferred case study style:", st.session_state.style_options
    )

    if st.button("🚀 Generate Final Case Study"):
        with st.spinner("📚 Crafting a polished, formal case study..."):
            final_prompt = f"""
You are a formal and experienced brand strategist.

Generate a professional case study using the selected style: {st.session_state.selected_style}.

Details:
- Project Title: {project_title}
- Client: {client_name}
- Industry: {industry}
- Brief: {brief}
- Results: {results}

Structure:
- Title
- Problem Statement
- Strategic Approach
- Implementation
- Outcomes

Tone: polished, formal, and suitable for C-suite or investor review.
"""
            case_study = model.generate_content(final_prompt).text.strip()

        st.success("✅ Case Study Generated")
        st.markdown("### 🧾 Final Case Study")
        st.markdown(case_study, unsafe_allow_html=True)

        # === Alternate Versions ===
        with st.expander("✨ Alternate Versions"):
            alt_prompt = f"""
Generate 2 alternate versions of this case study:
1. A storytelling version for social media
2. A concise version for pitch decks

Style: {st.session_state.selected_style}
"""
            alt_response = model.generate_content(alt_prompt)
            st.markdown(alt_response.text.strip())

        # === Export Options ===
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
