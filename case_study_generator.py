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
        snippets = []
        
        # Extract snippets from organic results
        for r in data.get('organic',[]):
            snippet = r.get('snippet','')
            title = r.get('title','')
            link = r.get('link','')
            snippets.append(f"SOURCE: {title} ({link})\nCONTENT: {snippet}")
            
        # Also check for news results which often contain recent campaign data
        for r in data.get('news',[]):
            snippet = r.get('snippet','')
            title = r.get('title','')
            link = r.get('link','')
            date = r.get('date','')
            snippets.append(f"NEWS SOURCE: {title} ({date}) ({link})\nCONTENT: {snippet}")
            
        return "\n\n".join(snippets[:num_results])
    except Exception as e:
        return f'Error fetching data: {str(e)}'

def extract_before_after_metrics(text, client, campaign):
    prompt = f"""
You are an expert data analyst. Extract ONLY campaign-specific, factual, and numeric BEFORE and AFTER metrics for {client}'s "{campaign}" campaign from the text below. Ignore general company data or unrelated numbers.

Return a JSON object with this structure:
{{
  "MetricName": {{
    "before": <numeric_value>,
    "after": <numeric_value>,
    "percent_change": <numeric_value>,
    "unit": "unit (%, $, users, etc.)",
    "timeframe": "e.g. Q2 2023, Jan-Mar 2024"
  }},
  ...
}}

Instructions:
- Parse the text thoroughly for all possible metrics, even if phrased differently.
- Only include metrics with both before and after values and a clear timeframe.
- Calculate percent_change as ((after-before)/before)*100, rounded to 2 decimals.
- If a metric is ambiguous, exclude it.
- Use only numbers that are explicitly tied to this campaign.
- For each metric, extract the exact timeframe (e.g., "April-June 2023", "Q1 2024").
- If no valid metrics are found, return an empty JSON object.

Text:\n{text[:3000]}
"""
    return model.generate_content(prompt).text.strip()

def fetch_industry_benchmarks(industry, metrics):
    output = {}
    for m in metrics:
        query = f"{industry} industry average {m} benchmark 2024 statistics"
        snippets = fetch_comprehensive_campaign_data(query, 10)
        prompt = f"""Extract detailed {m} benchmarks for {industry} industry from the text below.
        
Provide in JSON format with these fields:
- average: The industry average value
- top_performers: Value for top 10% in industry
- range: Typical range (min-max)
- unit: Unit of measurement
- source: Likely source of this data
- year: Most recent year this data represents

Text:\n{snippets[:2500]}
"""
        output[m] = model.generate_content(prompt).text.strip()
        time.sleep(0.5)
    return output

def verify_campaign_facts(client, campaign, metrics_json):
    queries = [
        f'"{client}" "{campaign}" official results press release',
        f'"{client}" "{campaign}" case study marketing agency',
        f'"{client}" "{campaign}" performance data',
        f'"{client}" "{campaign}" ROI statistics',
        f'"{client}" annual report "{campaign}"'
    ]
    combined = ''
    for q in queries:
        combined += fetch_comprehensive_campaign_data(q,6) + "\n"
        time.sleep(0.5)
    prompt = f"""
You are a fact-checking specialist. For each metric in the JSON below, verify its accuracy using ONLY the provided sources. Ignore unsupported claims.

Metrics:\n{metrics_json}\n
Sources:\n{combined[:3000]}\n
Return a JSON object with:
1. Each metric mapped to:
   - verified: true/false (true only if at least two independent sources confirm the value)
   - credibility_score: 0-100 (based on number and quality of sources)
   - confidence_level: "high", "medium", or "low"
   - supporting_evidence: Direct quotes or references from sources
   - contradicting_evidence: Any conflicting information found
   - suggested_adjustment: If metric seems inaccurate, suggest corrected value and reasoning
   - timeframe: Confirmed period for the metric (e.g., "Q2 2023")

2. Overall assessment:
   - overall_reliability: 0-100 score
   - potential_biases: Any marketing exaggerations or PR spin detected
   - missing_context: Important context or caveats

Be extremely critical, reject any metric not explicitly supported by the sources, and explain all decisions.
"""
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
Create a highly detailed, data-driven {st.session_state.selected_style} case study for {client_name}'s "{campaign_name}" campaign in {industry}.

Use this information:
- Brief: {brief}
- Achievements: {achievements}
- Metrics: {st.session_state.raw_metrics}
- Benchmarks: {st.session_state.benchmarks}
- Fact Verification: {st.session_state.verified}

Requirements:
1. Focus EXCLUSIVELY on this specific campaign with accurate, verified metrics
2. Include precise numeric data with proper units (%, $, etc.) and time periods
3. Compare campaign performance against industry benchmarks with specific percentages
4. Analyze ROI and cost-effectiveness with concrete numbers
5. Include a "Methodology" section explaining how results were measured
6. Add a "Key Learnings" section with actionable insights
7. Create data visualizations described in markdown (tables, charts)
8. Cite specific timeframes for all metrics (e.g., "In Q2 2023..." not "Recently...")
9. Maintain factual accuracy - only include claims supported by the verified data
10. Tailor the content specifically to {industry} industry standards and expectations

Format as professional markdown with clear sections, subsections, and tables for numeric data.
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
