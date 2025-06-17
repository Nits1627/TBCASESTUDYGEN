import streamlit as st
import google.generativeai as genai
import markdown2
import io
import requests
from xhtml2pdf import pisa
from datetime import datetime
from bs4 import BeautifulSoup
import time

# === API Setup ===
genai.configure(api_key=st.secrets['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-1.5-flash')

GOOGLE_CSE_API_KEY = st.secrets['GOOGLE_CSE_API_KEY']
GOOGLE_CSE_ENGINE_ID = st.secrets['GOOGLE_CSE_ENGINE_ID']

# === Streamlit UI Setup ===
st.set_page_config(page_title='AI Case Study Generator', layout='wide')
st.image('logo.png', width=180)
st.title('📚 AI-Powered Case Study Generator')
st.markdown('Generate campaign-specific case studies as Thought Blurb with accurate, optimistic, data-backed narratives.')

# === Initialize Session State ===
state_vars = ['snippets','raw_metrics','benchmarks','verified','recommendations','styles','selected_style','case_study','custom_reprompt']
for var in state_vars:
    if var not in st.session_state:
        st.session_state[var] = None if var in ['selected_style','case_study','custom_reprompt'] else {}

# === Utilities ===
def search_campaign_articles(query, num_results=5):
    search_url = f"https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_CSE_API_KEY,
        "cx": GOOGLE_CSE_ENGINE_ID,
        "q": query,
        "num": num_results
    }
    try:
        response = requests.get(search_url, params=params)
        results = response.json()
        links = [item["link"] for item in results.get("items", [])]
        return links
    except Exception as e:
        return []

def scrape_page_text(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for s in soup(['script', 'style', 'header', 'footer', 'noscript']):
            s.decompose()
        text = ' '.join(soup.stripped_strings)
        return text[:5000]
    except Exception as e:
        return ""

def extract_before_after_metrics(text, client, campaign):
    prompt = f"""
You are a data analyst working for the creative agency Thought Blurb.
Analyze the following content to extract the strongest, verifiable before/after metrics for {client}'s "{campaign}" campaign.

Provide only metrics that can support positive impact.

Return in JSON:
{{
  "MetricName": {{
    "before": value,
    "after": value,
    "percent_change": "+x%",
    "unit": "unit",
    "timeframe": "e.g. Q1 vs Q2 2023",
    "evidence": "Quoted source text"
  }},
  ...
}}

Text:
{text}
"""
    return model.generate_content(prompt).text.strip()

def fetch_industry_benchmarks(industry, metrics):
    output = {}
    for m in metrics:
        query = f"{industry} industry average {m} benchmark 2024 statistics"
        links = search_campaign_articles(query, 3)
        text = "\n".join([scrape_page_text(url) for url in links])
        prompt = f"""Extract detailed {m} benchmarks for {industry} industry from the text below.

Provide in JSON format:
- average
- top_performers
- range (min-max)
- unit
- source
- year

Text:\n{text[:2500]}
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
        links = search_campaign_articles(q, 2)
        combined += "\n".join([scrape_page_text(url) for url in links]) + "\n"
        time.sleep(0.5)
    prompt = f"""
As a validation analyst at Thought Blurb, verify the following performance metrics of the "{campaign}" campaign for {client}.

Input Metrics:
{metrics_json}

Sources:
{combined[:3000]}

Return verified metrics with:
- verified: true/false
- credibility_score: 0-100
- confidence_level
- supporting_evidence
- contradicting_evidence
- suggested_adjustment

Also include:
- overall_reliability
- potential_biases
- missing_context
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
    brief = st.text_area('Campaign Brief')
    achievements = st.text_area('Key Achievements')
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
        query = f"{client_name} {campaign_name} campaign results"
        links = search_campaign_articles(query, 5)
        all_text = "\n\n".join([scrape_page_text(link) for link in links])
        st.session_state.snippets = all_text

        if deep_analysis:
            st.info('📊 Extracting before/after metrics...')
            raw = extract_before_after_metrics(all_text, client_name, campaign_name)
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
You are a senior strategist at Thought Blurb.
Write a comprehensive, deeply detailed, data-backed, optimistic {st.session_state.selected_style} case study for {client_name}'s "{campaign_name}" campaign in the {industry} sector.

Incorporate:
- Project Brief: {brief}
- Achievements: {achievements}
- Metrics JSON: {st.session_state.raw_metrics}
- Benchmarks: {st.session_state.benchmarks}
- Verified Facts: {st.session_state.verified}

Structure:
1. Campaign Overview (context, objectives, background)
2. Strategic Approach & Execution (media strategy, messaging, targeting)
3. Creative Innovation (what we did differently and why it worked)
4. Data-Backed Learnings & Recommendations
5. Summary & Conclusion

Must Include:
- Exact numeric data, attributed sources, and optimistic tone
- Language that shows Thought Blurb led the success
- Clear insights, subheadings, and markdown tables
- Avoid passive tone, use confident, client-ready phrasing
"""
            result = model.generate_content(prompt).text.strip()
            st.session_state.case_study = result

# === Display & Export ===
if st.session_state.case_study:
    st.markdown('---')
    st.markdown('### 📄 Case Study Output')
    st.markdown(st.session_state.case_study, unsafe_allow_html=True)

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

    st.markdown('---')
    st.subheader("🔁 Want to regenerate with a new prompt?")
    st.session_state.custom_reprompt = st.text_area("Add or modify your request to refine the case study:", value="Make it more detailed and results-driven with strong performance breakdowns")
    if st.button("♻️ Regenerate with Custom Prompt"):
        with st.spinner("Re-generating based on your updated request..."):
            custom_prompt = f"""
You are a senior strategist at Thought Blurb.
Generate an advanced, refined, highly detailed case study for {client_name}'s "{campaign_name}" campaign.

Custom Request:
{st.session_state.custom_reprompt}

Inputs:
- Project Brief: {brief}
- Achievements: {achievements}
- Metrics: {st.session_state.raw_metrics}
- Benchmarks: {st.session_state.benchmarks}
- Verified Insights: {st.session_state.verified}

Ensure it includes:
- Detailed campaign sections
- Performance commentary
- Creative showcase
- Strong, client-ready tone
- Quantified improvements and ROI discussion
"""
            updated_result = model.generate_content(custom_prompt).text.strip()
            st.session_state.case_study = updated_result
            st.rerun()
