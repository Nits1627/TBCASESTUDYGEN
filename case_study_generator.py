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
st.markdown('Generate campaign-specific case studies with accurate, factual data and detailed storytelling.')

# === Session State ===
state_vars = ['snippets','all_text','case_study','styles','style_choice']
for var in state_vars:
    if var not in st.session_state:
        st.session_state[var] = None

# === Utilities ===
def search_campaign_articles(query, timeframe, num_results=5):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GOOGLE_CSE_API_KEY, "cx": GOOGLE_CSE_ENGINE_ID, "q": f"{query} {timeframe}", "num": num_results}
    try:
        res = requests.get(url, params=params)
        items = res.json().get('items', [])
        return [item['link'] for item in items]
    except:
        return []

def scrape_page_text(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup(['script','style','header','footer','noscript']): tag.decompose()
        return ' '.join(soup.stripped_strings)[:5000]
    except:
        return ''

# === Input Form ===
with st.form('analysis_form'):
    st.subheader('📋 Campaign Details')
    project_title = st.text_input('Project Title')
    client = st.text_input('Client/Brand Name')
    campaign = st.text_input('Campaign Name')
    timeframe = st.text_input('Campaign Timeframe (e.g. April - June 2024)', help='Refines web search to this period')
    industry = st.selectbox('Industry', ['Technology','Retail','Automotive','Financial Services','Healthcare','Food & Beverage','Fashion','Travel & Tourism','Entertainment','Real Estate','Education','Sports','Beauty & Personal Care','Other'])
    brief = st.text_area('Campaign Brief', help='Summarize objectives and context')
    achievements = st.text_area('Key Achievements', help='Known wins or KPIs')
    submit = st.form_submit_button('🔍 Analyze Campaign')

# === Fetch and Prepare Data ===
if submit:
    if not (client and campaign and timeframe):
        st.error('Please fill in client, campaign name, and timeframe.')
    else:
        st.info('🔗 Fetching sources...')
        links = search_campaign_articles(f"{client} {campaign} campaign results", timeframe, num_results=7)
        st.write('Sources:', *links, sep='\n')
        st.info('📖 Scraping content...')
        text_blocks = [scrape_page_text(link) for link in links]
        st.session_state.all_text = '\n\n'.join(text_blocks)
        st.success('✅ Data ready for case study')
        # Recommend styles
        st.session_state.styles = ['Executive Summary','Data-Focused','Narrative-Driven','Technical Deep Dive']
        st.session_state.style_choice = st.radio('Select Case Study Style', st.session_state.styles)

# === Generate Case Study ===
if st.session_state.style_choice:
    if st.button('🚀 Generate Case Study'):
        st.info('🛠 Building case study...')
        prompt = f"""
You are a senior strategist at Thought Blurb. Create an in-depth, minimum 700-word case study in the '{st.session_state.style_choice}' style for the campaign below. Include ONLY factual data scraped from the provided content, with real numbers, verified quotes, and precise metrics showing how the campaign impacted the product/service. Avoid any hypothetical or made-up figures.

Client: {client}
Campaign: {campaign}
Industry: {industry}
Timeframe: {timeframe}
Brief: {brief}
Achievements: {achievements}
Style: {st.session_state.style_choice}

Structure your case study into 5 sections:
1. Campaign Overview
2. Strategic Approach & Execution
3. Creative Innovation
4. Measurable Success & Metrics
5. Summary & Key Learnings

Ensure the 'Measurable Success & Metrics' section contains actual numeric results (reach, engagement rate, ROI, sales uplift) sourced from the scraped content.

Content:
{st.session_state.all_text}
"""
        result = model.generate_content(prompt).text.strip()
        st.session_state.case_study = result

# === Display & Export ===
if st.session_state.case_study:
    st.markdown('---')
    st.markdown('### 📄 Case Study Output')
    st.markdown(st.session_state.case_study, unsafe_allow_html=True)
    # Export PDF
    html = f"""
<html><body>{markdown2.markdown(st.session_state.case_study)}<footer>Generated on {datetime.now().strftime('%B %d, %Y')}</footer></body></html>
"""
    pdf = io.BytesIO()
    pisa.CreatePDF(html, dest=pdf)
    pdf.seek(0)
    st.download_button('📥 Download PDF', pdf, file_name=f"{project_title.replace(' ','_')}.pdf", mime='application/pdf')
    # Regeneration
    feedback = st.text_area('Request changes or additions:', key='feedback')
    if st.button('♻️ Regenerate'):
        rev_prompt = f"Revise the case study below based on this feedback: {feedback}\n\nOriginal:\n{st.session_state.case_study}"
        st.session_state.case_study = model.generate_content(rev_prompt).text.strip()
        st.experimental_rerun()
