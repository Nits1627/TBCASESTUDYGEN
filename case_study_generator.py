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
st.markdown('Generate case studies with real, campaign-specific metrics on performance, sales uplift, and brand impact.')

# === Session State ===
for key, default in [
    ('recommendations', ''),
    ('styles', []),
    ('selected_style', None),
    ('case_study', ''),
    ('case_library', []),
    ('web_context', ''),
    ('metrics', {}),
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
    st.subheader('Enter Case Study & Campaign Details')
    col1, col2 = st.columns(2)
    with col1:
        project_title = st.text_input('Project Title')
        client_name   = st.text_input('Client / Brand Name')
        campaign_name = st.text_input('Ad Campaign Name')
        industry      = st.text_input('Industry')
    with col2:
        brief        = st.text_area('Project Brief (2-4 lines)')
        achievements = st.text_area('Key Outcomes / Achievements')
    go = st.form_submit_button('🎯 Recommend Case Study Formats')

# === Step 1: Fetch Campaign Metrics & Context ===
if go:
    st.info('🔎 Gathering campaign-specific impact metrics…')
    # Web context for narrative
    q_context = f"{client_name} '{campaign_name}' campaign overview" if campaign_name else f"{client_name} campaign overview"
    st.session_state.web_context = fetch_snippet(q_context)
    # Campaign-specific metrics
    queries = {
        'Sales Uplift': f"{client_name} '{campaign_name}' sales increase",
        'Market Share Uplift': f"{client_name} '{campaign_name}' market share change",
        'Brand Awareness Lift': f"{client_name} '{campaign_name}' brand awareness"  
    }
    metrics = {}
    for label, q in queries.items():
        snippet = fetch_snippet(q)
        match = re.search(r"(-?\d+[\d.,]*)(?:\s?(?:%|percent|million|billion|crore))?", snippet, flags=re.IGNORECASE)
        metrics[label] = match.group(0) if match else (snippet or 'N/A')
    st.session_state.metrics = metrics

    # Display Key Metrics
    st.markdown('### 📊 Campaign Impact Metrics')
    for label, value in metrics.items():
        st.markdown(f"- **{label}**: {value}")

    # Prompt for case study styles
    prompt = f"""
You are a brand strategist. Recommend 3 case study styles tailored to this campaign.

Project Title: {project_title}
Client: {client_name}
Campaign: {campaign_name}
Industry: {industry}
Brief: {brief}
Achievements: {achievements}

Web Insights:
{st.session_state.web_context}

Campaign Metrics:
"""
    for k, v in metrics.items():
        prompt += f"{k}: {v}\n"
    prompt += """
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

# === Steps 2–5: Display, Generate & Export Case Study ===
if st.session_state.recommendations:
    st.markdown('### 🧠 AI Recommendations')
    st.markdown(st.session_state.recommendations)
    st.session_state.selected_style = st.radio('Select a Case Study Style:', st.session_state.styles)

if st.session_state.selected_style and st.button('🚀 Generate Case Study'):
    style = st.session_state.selected_style
    base = f"""
Project Title: {project_title}
Client: {client_name}
Campaign: {campaign_name}
Industry: {industry}
Brief: {brief}
Achievements: {achievements}

Web Insights:
{st.session_state.web_context}

Campaign Metrics:
"""
    for k, v in metrics.items():
        base += f"- {k}: {v}\n"
    base += "\nCase Study Parameters:\nClient Name: {client_name}\nCampaign Name: {campaign_name}\nObjective:\nStrategy & Execution:\nResults & Metrics:\nKey Takeaways:\n"
    if style.startswith('Default Format'):
        final_prompt = f"Create a structured case study with the following parameters:\n{base}"
    else:
        final_prompt = f"Create a formal case study in the style '" + style + "':\n{base}"
    output = model.generate_content(final_prompt).text.strip()
    st.session_state.case_study = output
    st.session_state.case_library.append({'title': project_title, 'style': style, 'case': output})

if st.session_state.case_study:
    st.success('✅ Case Study Generated')
    st.markdown('### 📄 Final Case Study')
    st.markdown(st.session_state.case_study, unsafe_allow_html=True)
    feedback = st.text_area('✏️ Suggest edits:')
    if st.button('♻️ Regenerate'):
        rev = f"Revise based on feedback: {feedback}\n\nOriginal:\n{st.session_state.case_study}"
        st.session_state.case_study = model.generate_content(rev).text.strip()
    st.download_button('📝 Download Markdown', st.session_state.case_study, f"{project_title}.md", 'text/markdown')
    def to_pdf(text):
        html = f"<html><body><img src='logo.png' width='120'/><br/>{markdown2.markdown(text)}</body></html>"
        buf = io.BytesIO(); pisa.CreatePDF(io.StringIO(html), dest=buf); return buf
    if st.button('📄 Download PDF'):
        buf = to_pdf(st.session_state.case_study)
        st.download_button('💾 Save PDF', buf.getvalue(), f"{project_title}.pdf", 'application/pdf')

if st.session_state.case_library:
    st.markdown('---')
    st.markdown('### 📚 Saved Case Study Library')
    for i, item in enumerate(st.session_state.case_library[::-1], 1):
        with st.expander(f"{i}. {item['title']} ({item['style']})"):
            st.markdown(item['case'], unsafe_allow_html=True)
