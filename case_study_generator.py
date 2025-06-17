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
st.markdown('Generate website-ready case studies that highlight Thought Blurb’s impact on your brand with factual data and an optimistic narrative.')

# === Session State ===
for key in ['all_text','case_study','styles','style_choice']:
    if key not in st.session_state:
        st.session_state[key] = None

# === Utilities ===
def search_campaign_articles(query, timeframe, num_results=5):
    url = 'https://www.googleapis.com/customsearch/v1'
    params = {'key': GOOGLE_CSE_API_KEY, 'cx': GOOGLE_CSE_ENGINE_ID, 'q': f'{query} {timeframe}', 'num': num_results}
    try:
        res = requests.get(url, params=params)
        return [item['link'] for item in res.json().get('items', [])]
    except:
        return []

def scrape_page_text(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup(['script','style','header','footer','noscript']):
            tag.decompose()
        return ' '.join(soup.stripped_strings)[:5000]
    except:
        return ''

# === Input Form ===
with st.form('analysis_form'):
    st.subheader('📋 Campaign Details')
    project_title = st.text_input('Project Title')
    client = st.text_input('Client/Brand Name')
    campaign = st.text_input('Campaign Name')
    timeframe = st.text_input('Campaign Timeframe (e.g. April - June 2024)', help='Refines the search period')
    industry = st.selectbox('Industry', ['Technology','Retail','Automotive','Financial Services','Healthcare','Food & Beverage','Fashion','Travel & Tourism','Entertainment','Real Estate','Education','Sports','Beauty & Personal Care','Other'])
    brief = st.text_area('Campaign Brief')
    achievements = st.text_area('Key Achievements')
    submit = st.form_submit_button('🔍 Analyze Campaign')

if submit:
    if not (client and campaign and timeframe):
        st.error('Please provide client, campaign name, and timeframe.')
    else:
        st.info('🔗 Searching for relevant articles...')
        links = search_campaign_articles(f'{client} {campaign} campaign results', timeframe, num_results=7)
        st.write('**Sources:**')
        for link in links:
            st.markdown(f'- {link}')
        st.info('📖 Extracting content...')
        text = '\n\n'.join([scrape_page_text(link) for link in links])
        st.session_state.all_text = text
        st.info('✅ Content ready')
        st.session_state.styles = ['Executive Summary','Data-Focused','Narrative-Driven','Technical Deep Dive']
        st.session_state.style_choice = st.radio('Choose Case Study Style', st.session_state.styles)

if st.session_state.style_choice:
    if st.button('🚀 Generate Case Study'):
        st.info('🛠 Crafting website-ready case study...')
        prompt = f"""
You are a senior strategist at Thought Blurb. Write a professional, website-ready case study of at least 1.5 pages in the '{st.session_state.style_choice}' style, highlighting how our work impacted {client} during {timeframe}. The tone must be optimistic and focused on positive brand benefits.

Client: {client}
Campaign: {campaign}
Industry: {industry}
Timeframe: {timeframe}
Brief: {brief}
Achievements: {achievements}

Structure your case study with these sections and include only factual data scraped from the provided content:

1. Background & Objectives
2. Strategic Approach
3. Creative Execution
4. Results & Impact
   - Include metrics on brand awareness lift and reach (if these metrics are present in the source content).  
   - Also include additional success metrics (engagement rate, ROI, sales uplift) with real numbers.  
   - If a particular metric is not available, omit it quietly without noting its absence.
5. Key Learnings & Future Recommendations

Ensure each section is richly detailed, uses real numeric figures, and includes verified quotes where applicable.

Content:
{st.session_state.all_text}
"""
        case = model.generate_content(prompt).text.strip()
        st.session_state.case_study = case

if st.session_state.case_study:
    st.markdown('---')
    st.markdown('### 📄 Case Study Output')
    st.markdown(st.session_state.case_study, unsafe_allow_html=True)
    html = f"""
<html><body>{markdown2.markdown(st.session_state.case_study)}<footer>Generated on {datetime.now().strftime('%B %d, %Y')}</footer></body></html>
"""
    pdf_io = io.BytesIO()
    pisa.CreatePDF(html, dest=pdf_io)
    pdf_io.seek(0)
    st.download_button('📥 Download PDF', pdf_io, file_name=f'{project_title.replace(' ','_')}.pdf', mime='application/pdf')
    feedback = st.text_area('Request further changes:', key='feedback')
    if st.button('♻️ Regenerate with Feedback'):
        rev = f"Revise the case study below based on this feedback: {feedback}\n\nOriginal:\n{st.session_state.case_study}"
        st.session_state.case_study = model.generate_content(rev).text.strip()
        
