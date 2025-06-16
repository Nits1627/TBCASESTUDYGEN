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
st.markdown('Generate campaign-specific case studies with accurate numeric metrics and factual verification.')

# === Initialize Session State ===
state_vars = ['snippets','raw_metrics','benchmarks','verified','recommendations','styles','selected_style','case_study']
for var in state_vars:
    if var not in st.session_state:
        st.session_state[var] = None if var in ['selected_style','case_study'] else {}

# === Core Utilities ===
def fetch_comprehensive_campaign_data(query, num_results=10):
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = {'q': query, 'num': num_results, 'type': 'search', 'engine': 'google'}
    try:
        res = requests.post(SERPER_API_URL, headers=headers, json=payload, timeout=20)
        data = res.json()
        snippets = [r.get('snippet','') for r in data.get('organic',[])]
        return "\n".join(snippets[:8])
    except Exception:
        return ''

def extract_before_after_metrics(text, client, campaign):
    prompt = f"""
Extract numeric BEFORE and AFTER metrics for {client}'s "{campaign}" campaign in JSON format: {{"MetricName":{{"before":val,"after":val}},...}}\nText:\n{text[:2000]}
"""
    return model.generate_content(prompt).text.strip()

def fetch_industry_benchmarks(industry, metrics):
    output = {}
    for m in metrics:
        query = f"{industry} industry average {m} benchmark 2024"
        snippets = fetch_comprehensive_campaign_data(query, 8)
        prompt = f"Extract average {m} benchmark for {industry} from:\n{snippets[:2000]}"
        output[m] = model.generate_content(prompt).text.strip()
        time.sleep(0.5)
    return output

def verify_campaign_facts(client, campaign, metrics_json):
    queries = [
        f'"{client}" "{campaign}" official results press release',
        f'"{client}" "{campaign}" case study marketing agency'
    ]
    combined = ''
    for q in queries:
        combined += fetch_comprehensive_campaign_data(q,5) + "\n"
        time.sleep(0.5)
    prompt = f"""
Verify these metrics for {client}'s "{campaign}" campaign.\nMetrics:\n{metrics_json}\nSources:\n{combined[:2000]}\nProvide a JSON mapping each metric to verified:true/false and credibility score.\n"""
    return model.generate_content(prompt).text.strip()

# === Input Form ===
with st.form('analysis_form'):
    st.subheader('📋 Campaign Details')
    project_title = st.text_input('Project Title')
    client_name = st.text_input('Client/Brand Name')
    campaign_name = st.text_input('Campaign Name')
    industry = st.selectbox('Industry',['Technology','Retail','Automotive','Financial Services',
                                        'Healthcare','Food & Beverage','Fashion','Travel & Tourism',
                                        'Entertainment','Real Estate','Education','Sports','Beauty & Personal Care','Other'])
    brief = st.text_area('Campaign Brief', help='Summarize objectives and context')
    achievements = st.text_area('Key Achievements', help='Known wins or KPIs')
    target_metrics = st.multiselect('Select Metrics to Analyze',['Sales Revenue','Market Share','Brand Awareness',
                                                          'Customer Acquisition','Website Traffic','Engagement Rate',
                                                          'Conversion Rate','ROI/ROAS','Social Media Growth','Lead Generation','App Downloads','Store Visits'])
    st.markdown('### 🔍 Analysis Options')
    deep_analysis = st.checkbox('Deep Metric Extraction', value=True)
    include_benchmarks = st.checkbox('Include Industry Benchmarks', value=True)
    fact_verification = st.checkbox('Enable Fact Verification', value=True)
    generate = st.form_submit_button('🚀 Generate Analysis')

# === Analysis Pipeline ===
if generate:
    if not (client_name and campaign_name and target_metrics):
        st.error('Please fill in client, campaign, and select at least one metric.')
    else:
        st.info('🔍 Researching campaign performance...')
        snippets = fetch_comprehensive_campaign_data(f"{client_name} {campaign_name} campaign results official",12)
        st.session_state.snippets = snippets

        if deep_analysis:
            st.info('📊 Extracting before/after metrics...')
            raw = extract_before_after_metrics(snippets, client_name, campaign_name)
            st.session_state.raw_metrics = raw

        if include_benchmarks:
            st.info('📈 Fetching industry benchmarks...')
            bms = fetch_industry_benchmarks(industry, target_metrics)
            st.session_state.benchmarks = bms

        if fact_verification:
            st.info('✅ Verifying facts...')
            vf = verify_campaign_facts(client_name, campaign_name, st.session_state.raw_metrics)
            st.session_state.verified = vf

        st.success('✅ Analysis Complete')
        st.session_state.recommendations = 'Choose a style: Executive Summary, Data Focused, Narrative'
        st.session_state.styles = ['Executive Summary','Data Focused','Narrative']
        st.session_state.selected_style = st.radio('Case Study Style', st.session_state.styles)

# === Case Study Generation ===
if st.session_state.selected_style:
    if st.button('🚀 Generate Case Study'):
        with st.spinner('🛠️ Building your case study...'):
            prompt = f"""
Create a {st.session_state.selected_style} case study for {client_name}'s "{campaign_name}" campaign in {industry}.
Include:
- Brief: {brief}
- Achievements: {achievements}
- Metrics: {st.session_state.raw_metrics}
- Benchmarks: {st.session_state.benchmarks}
- Fact Verification: {st.session_state.verified}
Format as markdown with clear sections and tables for numeric data.
"""
            result = model.generate_content(prompt).text.strip()
            st.session_state.case_study = result

# === Display & Export ===
if st.session_state.case_study:
    st.markdown('---')
    st.markdown('### 📄 Case Study Output')
    st.markdown(st.session_state.case_study, unsafe_allow_html=True)

    # PDF Export
    html = f"""
    <html><head><meta charset='utf-8'></head><body>
    {markdown2.markdown(st.session_state.case_study)}
    <footer>Generated on {datetime.now().strftime('%B %d, %Y')}</footer>
    </body></html>
    """
    pdf_io = io.BytesIO()
    pisa.CreatePDF(html, dest=pdf_io)
    pdf_io.seek(0)
    st.download_button('📥 Download PDF', data=pdf_io, file_name=f"{project_title.replace(' ','_')}.pdf", mime='application/pdf')
