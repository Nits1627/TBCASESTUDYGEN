import streamlit as st
import google.generativeai as genai
import markdown2
import io
import requests
from xhtml2pdf import pisa
from datetime import datetime
import time

# === API Setup ===
genai.configure(api_key=st.secrets['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-1.5-flash')

SERPER_API_KEY = st.secrets['SERPER_API_KEY']
SERPER_API_URL = 'https://google.serper.dev/search'

# === Streamlit UI Setup ===
st.set_page_config(page_title='AI Case Study Generator', layout='wide')
st.image('logo.png', width=180)
st.title('📚 AI-Powered Case Study Generator')
st.markdown('Generate data-driven case studies with accurate, factual metrics for your campaigns.')

# === Session State Defaults ===nkeys = ['recommendations', 'styles', 'selected_style', 'case_study',
           'web_context', 'metrics', 'detailed_metrics', 'before_after_metrics',
           'industry_benchmarks', 'verified_facts']
for k in keys:
    if k not in st.session_state:
        st.session_state[k] = {} if 'metrics' in k or 'benchmarks' in k else ''

# === Utility: SERPER Search ===
def fetch_search_snippets(query, num_results=10):
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = {'q': query, 'num': num_results, 'type': 'search', 'engine': 'google'}
    try:
        r = requests.post(SERPER_API_URL, headers=headers, json=payload, timeout=15)
        data = r.json().get('organic', [])
        snippets = [item.get('snippet', '') for item in data]
        return snippets
    except Exception:
        return []

# === Metric Extraction ===
def extract_metrics(text, client, campaign):
    prompt = f"""
Extract key numeric BEFORE and AFTER performance metrics from this text about {client}'s "{campaign}" campaign. Provide results as JSON dictionary, e.g. {{"Sales": {{"before": x, "after": y}}, ...}}.
Text: {text[:2000]}
"""
    resp = model.generate_content(prompt)
    return resp.text.strip()

# === Benchmark Fetch ===
def get_benchmarks(industry, metric):
    snippets = fetch_search_snippets(f"{industry} industry {metric} benchmark average 2024", 8)
    content = "\n".join(snippets)
    prompt = f"Extract the average {metric} benchmarks for the {industry} industry from this content as JSON. Content: {content[:2000]}"
    resp = model.generate_content(prompt)
    return resp.text.strip()

# === Fact Verification ===
def verify_metrics(client, campaign, metrics_json):
    queries = [
        f'"{client}" "{campaign}" press release official results',
        f'"{client}" "{campaign}" case study"'
    ]
    combined = []
    for q in queries:
        combined += fetch_search_snippets(q, 5)
        time.sleep(0.5)
    prompt = f"""
Verify these metrics for {client}'s "{campaign}" campaign. Metrics: {metrics_json}\nSources: {' '.join(combined)[:2000]}
Provide a JSON with verified vs unverified entries and credibility scores.
"""
    resp = model.generate_content(prompt)
    return resp.text.strip()

# === Input Form ===with st.form('input_form'):
    st.subheader('📋 Campaign Details')
    project_title = st.text_input('Project Title')
    client_name = st.text_input('Client / Brand Name')
    campaign_name = st.text_input('Campaign Name')
    industry = st.selectbox('Industry', ['Technology','Retail','Automotive','Financial Services',
                                       'Healthcare','Food & Beverage','Fashion','Travel & Tourism',
                                       'Entertainment','Real Estate','Education','Sports','Beauty & Personal Care','Other'])
    brief = st.text_area('Campaign Brief', help='Summarize the campaign objectives and context')
    achievements = st.text_area('Key Achievements', help='Highlight any known wins or KPIs')
    target_metrics = st.multiselect('Metrics to Analyze', ['Sales','Market Share','Brand Awareness',
                           'Customer Acquisition','Website Traffic','Engagement Rate','Conversion Rate','ROI'])
    generate = st.form_submit_button('🚀 Generate Analysis')

if generate:
    if not (client_name and campaign_name):
        st.error('Please enter both client and campaign names.')
    else:
        st.info('🔍 Researching campaign data...')
        snippets = fetch_search_snippets(f"{client_name} {campaign_name} campaign results official", 12)
        combined_text = "\n".join(snippets)
        st.session_state.metrics = extract_metrics(combined_text, client_name, campaign_name)

        st.session_state.before_after_metrics = st.session_state.metrics

        st.info('📊 Fetching industry benchmarks...')
        bms = {m: get_benchmarks(industry, m) for m in target_metrics}
        st.session_state.industry_benchmarks = bms

        st.info('✅ Verifying metric accuracy...')
        st.session_state.verified_facts = verify_metrics(client_name, campaign_name, st.session_state.metrics)

        st.success('🔖 Analysis complete — choose a template below')
        # Recommendations stub
        st.session_state.recommendations = 'Select a template: Executive Summary, Data Focused, Narrative'
        styles = ['Executive Summary','Data Focused','Narrative']
        st.session_state.styles = styles
        st.session_state.selected_style = st.radio('Choose Case Study Style', styles)

# === Case Study Generation ===if st.session_state.selected_style:
    if st.button('🚀 Generate Case Study'):
        with st.spinner('🛠️ Crafting your case study...'):
            prompt = f"""
Create a {st.session_state.selected_style} case study for {client_name}'s "{campaign_name}" campaign in the {industry} industry.
Include:
- Campaign brief: {brief}
- Key achievements: {achievements}
- Before/After metrics: {st.session_state.before_after_metrics}
- Industry benchmarks comparison: {st.session_state.industry_benchmarks}
- Verified facts: {st.session_state.verified_facts}
"""
            response = model.generate_content(prompt).text.strip()
            st.session_state.case_study = response

# === Display & Export ===if st.session_state.case_study:
    st.markdown('---')
    st.markdown('### 📄 Case Study Output')
    st.markdown(st.session_state.case_study, unsafe_allow_html=True)

    def make_pdf(html, title):
        pdf_io = io.BytesIO()
        pisa.CreatePDF(html, dest=pdf_io)
        pdf_io.seek(0)
        return pdf_io

    # Build HTML
    html = f"""
    <html><head><meta charset='utf-8'></head><body>
    <h1>{project_title}</h1>
    {markdown2.markdown(st.session_state.case_study)}
    <footer>Generated on {datetime.now().strftime('%B %d, %Y')}</footer>
    </body></html>
    """
    pdf_file = make_pdf(html, project_title)
    st.download_button('📥 Download PDF', data=pdf_file, file_name=f"{project_title.replace(' ','_')}.pdf", mime='application/pdf')
