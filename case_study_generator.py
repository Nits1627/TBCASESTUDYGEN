import streamlit as st
import google.generativeai as genai
import markdown2
import io
import re
import requests
from xhtml2pdf import pisa

# === API Setup ===
genai.configure(api_key=st.secrets['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-1.5-flash')

SERPER_API_KEY = st.secrets['SERPER_API_KEY']
SERPER_API_URL = 'https://google.serper.dev/search'

# === Streamlit UI Setup ===
st.set_page_config(page_title='AI Case Study Generator', layout='wide')
st.image('logo.png', width=180)
st.title('📚 AI-Powered Case Study Generator')
st.markdown('Craft polished case studies with AI-recommended formats and real-time company data.')

# === Session State ===
for key, default in [
    ('recommendations', ''),
    ('styles', []),
    ('selected_style', None),
    ('case_study', ''),
    ('case_library', []),
    ('web_context', ''),
    ('metrics', {})
]:
    if key not in st.session_state:
        st.session_state[key] = default

# === Utility: Fetch Text Snippets via Serper.dev ===
def fetch_snippet(query, num_results=5):
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = {'q': query, 'num': num_results}
    try:
        res = requests.post(SERPER_API_URL, headers=headers, json=payload, timeout=10)
        results = res.json().get('organic', [])
        snippets = [r.get('snippet', '') for r in results]
        return '\n'.join(snippets[:3])
    except Exception:
        return ''

# === Step 0: Input Form ===
with st.form('input_form'):
    st.subheader('Enter Project Details')
    col1, col2 = st.columns(2)
    with col1:
        project_title = st.text_input('Project Title')
        client_name   = st.text_input('Client / Brand Name')
        industry      = st.text_input('Industry')
    with col2:
        brief   = st.text_area('Project Brief (2-4 lines)')
        results = st.text_area('Key Outcomes / Achievements')
    go = st.form_submit_button('🎯 Recommend Case Study Formats')

# === Step 1: Get Formats, Web Context & Key Metrics ===
if go:
    st.info('🔎 Fetching company data and key metrics…')
    # Unstructured context
    st.session_state.web_context = fetch_snippet(f"{client_name} {industry} overview")
    # Structured metrics
    queries = {
        'revenue': f"{client_name} {industry} revenue 2023",
        'users': f"{client_name} {industry} number of users",
        'market_share': f"{client_name} {industry} market share"
    }
    metrics = {}
    for key, q in queries.items():
        snippet = fetch_snippet(q)
        # attempt to extract first number occurrence
        num_match = re.search(r"\$?([0-9,.]+)\s*(million|billion|%)?", snippet, flags=re.IGNORECASE)
        if num_match:
            metrics[key] = num_match.group(0)
        else:
            metrics[key] = snippet or 'N/A'
    st.session_state.metrics = metrics

    # Show key metrics on UI
    st.markdown('### 📊 Key Metrics')
    for label, value in metrics.items():
        st.markdown(f"- **{label.replace('_', ' ').title()}**: {value}")

    # Prompt for case study styles
    prompt = f"""
You are a brand strategist. Suggest 3 case study styles.

Project Title: {project_title}
Client: {client_name}
Industry: {industry}
Brief: {brief}
Results: {results}

Web Insights:
{st.session_state.web_context}

Key Metrics:
Revenue: {metrics.get('revenue')}
Users: {metrics.get('users')}
Market Share: {metrics.get('market_share')}

Return only:
1. [Style One] Case Study:
2. [Style Two] Case Study:
3. [Style Three] Case Study:
Then list “Ideal Creative Assets:” with bullets.
"""
    rec = model.generate_content(prompt).text.strip()
    st.session_state.recommendations = rec
    styles_found = re.findall(r'^\s*\d+\.\s*(.+?):', rec, flags=re.MULTILINE)
    st.session_state.styles = styles_found[:3] + ['Default Format (Structured Parameters)']

# === Step 2: Display Recommendations & Style Selector ===
if st.session_state.recommendations:
    st.markdown('### 🧠 AI Recommendations')
    st.markdown(st.session_state.recommendations)
    st.session_state.selected_style = st.radio(
        'Select a Case Study Style:',
        st.session_state.styles
    )

# === Step 3: Generate Case Study ===
if st.session_state.selected_style:
    if st.button('🚀 Generate Case Study'):
        style = st.session_state.selected_style
        base_context = f"""
Project Title: {project_title}
Client: {client_name}
Industry: {industry}
Brief: {brief}
Results: {results}

Web Insights:
{st.session_state.web_context}

Key Metrics:
- Revenue: {st.session_state.metrics.get('revenue')}
- Users: {st.session_state.metrics.get('users')}
- Market Share: {st.session_state.metrics.get('market_share')}

Case Study Parameters:
Client Name / Brand Name: {client_name}
Problem Statement / Task:
Business Objective:
Solution:
Key Results:
"""
        if style.startswith('Default Format'):
            final_prompt = f"Create a professional case study with structured parameters:\n{base_context}"
        else:
            final_prompt = f"Create a formal case study in the style “{style}”:\n{base_context}"
        result = model.generate_content(final_prompt).text.strip()
        st.session_state.case_study = result
        st.session_state.case_library.append({
            'title': project_title,
            'client': client_name,
            'style': style,
            'case': result
        })

# === Step 4: Display & Refine ===
if st.session_state.case_study:
    st.success('✅ Case Study Generated')
    st.markdown('### 📄 Final Case Study')
    st.markdown(st.session_state.case_study, unsafe_allow_html=True)
    feedback = st.text_area('✏️ Suggest edits or refinements:')
    if st.button('♻️ Regenerate with Feedback'):
        rev_prompt = f"""
Revise the following based on feedback: {feedback}

Original Case Study:
{st.session_state.case_study}

Keep format and tone consistent.
"""
        st.session_state.case_study = model.generate_content(rev_prompt).text.strip()
        st.markdown('### ✨ Revised Case Study')
        st.markdown(st.session_state.case_study, unsafe_allow_html=True)
    # Export buttons
    st.download_button(
        '📝 Download as Markdown',
        st.session_state.case_study,
        f"{project_title}.md",
        'text/markdown'
    )
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
    if st.button('📄 Download PDF'):
        pdf_buf = generate_pdf(st.session_state.case_study)
        st.download_button(
            '💾 Save PDF',
            data=pdf_buf.getvalue(),
            file_name=f"{project_title}.pdf",
            mime='application/pdf'
        )

# === Step 5: In-Session Case Study Library ===
if st.session_state.case_library:
    st.markdown('---')
    st.markdown('### 📚 Saved Case Study Library')
    for idx, item in enumerate(st.session_state.case_library[::-1], start=1):
        with st.expander(f"{idx}. {item['title']} ({item['style']})"):
            st.markdown(item['case'], unsafe_allow_html=True)
