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
st.markdown('Generate campaign-specific case studies with accurate numeric metrics and factual verification.')

# === Initialize Session State ===
state_vars = ['snippets','raw_metrics','benchmarks','verified','recommendations','styles','selected_style','case_study']
for var in state_vars:
    if var not in st.session_state:
        st.session_state[var] = None if var in ['selected_style','case_study'] else {}

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
    except Exception:
        return []

def scrape_page_text(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for s in soup(['script', 'style', 'header', 'footer', 'noscript']):
            s.decompose()
        text = ' '.join(soup.stripped_strings)
        return text[:5000]
    except Exception:
        return ""

def extract_case_data(text, client, campaign, timeframe):
    prompt = f"""
You are an AI research analyst working at Thought Blurb, a creative agency.
Analyze the campaign content below for {client}'s "{campaign}" campaign, which ran during {timeframe}.

Your goal is to extract highly detailed information for the following structured case study sections:

1. Campaign Overview
2. Strategic Approach & Execution
3. Creative Innovation
4. Key Learnings & Recommendations
5. Summary & Conclusion

Ensure each section is:
- Highly detailed and backed by insights from the provided content.
- Written in confident, agency-style prose.
- Reflective of Thought Blurb's contribution and creative value.
- Free of vague filler content.
- Optimized for client-facing presentation.

Only include content that is backed by data or strong qualitative evidence in the source text.

---

Content:
{text}
"""
    return model.generate_content(prompt).text.strip()

# === Input Form ===
with st.form('analysis_form'):
    st.subheader('📋 Campaign Details')
    project_title = st.text_input('Project Title')
    client_name = st.text_input('Client/Brand Name')
    campaign_name = st.text_input('Campaign Name')
    campaign_timeframe = st.text_input('Campaign Timeframe (e.g. April–June 2024)', help='Used to refine search and analysis')
    industry = st.selectbox('Industry',['Technology','Retail','Automotive','Financial Services','Healthcare','Food & Beverage','Fashion','Travel & Tourism','Entertainment','Real Estate','Education','Sports','Beauty & Personal Care','Other'])
    brief = st.text_area('Campaign Brief', help='Summarize objectives and context')
    achievements = st.text_area('Key Achievements', help='Known wins or KPIs')
    st.markdown('### 🔍 Analysis Options')
    generate = st.form_submit_button('🚀 Generate Analysis')

# === Analysis Pipeline ===
if generate:
    if not (client_name and campaign_name):
        st.error('Please fill in client and campaign details.')
    else:
        st.info('🔍 Researching campaign performance...')
        query = f"{client_name} {campaign_name} campaign results {campaign_timeframe}"
        links = search_campaign_articles(query, 5)
        all_text = "\n\n".join([scrape_page_text(link) for link in links])
        st.session_state.snippets = all_text

        st.info('🧠 Generating detailed case study...')
        raw = extract_case_data(all_text, client_name, campaign_name, campaign_timeframe)
        st.session_state.case_study = raw
        st.session_state.styles = ['Executive Summary','Data Focused','Narrative']
        st.success('✅ Case Study Ready')

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
    st.subheader('🔁 Refine or Improve Your Case Study')
    custom_prompt = st.text_area('Add or modify your prompt to regenerate this case study')
    if st.button('♻️ Regenerate with Custom Prompt'):
        custom_full_prompt = f"""
Refine the following case study based on this custom instruction: {custom_prompt}

Original Case Study:
{st.session_state.case_study}
"""
        improved = model.generate_content(custom_full_prompt).text.strip()
        st.session_state.case_study = improved
        st.experimental_rerun()
