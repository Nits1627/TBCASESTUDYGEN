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

# === Initialize Session State ===
state_vars = ['snippets','raw_metrics','benchmarks','verified','recommendations','styles','selected_style','case_study']
for var in state_vars:
    if var not in st.session_state:
        st.session_state[var] = None if var in ['selected_style','case_study'] else {}

# === Utilities ===
def search_campaign_articles(query, timeframe, num_results=5):
    search_url = f"https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_CSE_API_KEY,
        "cx": GOOGLE_CSE_ENGINE_ID,
        "q": f"{query} {timeframe}",
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

def extract_deep_case_study(text, client, campaign, brief, achievements, industry):
    prompt = f"""
You are a senior strategist at a creative agency. Build a highly detailed, analytical, and in-depth case study for the following campaign:

Client: {client}
Campaign: {campaign}
Industry: {industry}
Brief: {brief}
Achievements: {achievements}

Use ONLY the data from below and structure your case study with the following 5 sections:
1. Campaign Overview
2. Strategic Approach & Execution
3. Creative Innovation
4. Key Learnings & Recommendations
5. Summary & Conclusion

Include verified quotes, real campaign insights, and reference accurate timelines and events.

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
    industry = st.selectbox('Industry',['Technology','Retail','Automotive','Financial Services','Healthcare','Food & Beverage','Fashion','Travel & Tourism','Entertainment','Real Estate','Education','Sports','Beauty & Personal Care','Other'])
    campaign_dates = st.text_input('Campaign Timeframe (e.g., April to June 2024)')
    brief = st.text_area('Campaign Brief', help='Summarize objectives and context')
    achievements = st.text_area('Key Achievements', help='Known wins or KPIs')
    generate = st.form_submit_button('🚀 Generate Analysis')

# === Analysis Pipeline ===
if generate:
    if not (client_name and campaign_name and campaign_dates):
        st.error('Please fill in client, campaign, and campaign timeframe.')
    else:
        st.info('🔍 Researching campaign performance...')
        query = f"{client_name} {campaign_name} campaign results"
        links = search_campaign_articles(query, campaign_dates, 7)
        all_text = "\n\n".join([scrape_page_text(link) for link in links])
        st.session_state.snippets = all_text

        st.info('📊 Generating detailed case study...')
        result = extract_deep_case_study(all_text, client_name, campaign_name, brief, achievements, industry)
        st.session_state.case_study = result

# === Display & Rewriting Option ===
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

    # Regeneration input
    st.markdown('---')
    st.subheader('♻️ Refine and Regenerate')
    custom_prompt = st.text_area("Add or modify your instructions to regenerate the case study:", placeholder="e.g., Add market trends or client testimonials")
    if st.button('♻️ Regenerate with Custom Prompt'):
        custom = model.generate_content(f"Revise the following case study based on this instruction: '{custom_prompt}'\n\nOriginal:\n\n{st.session_state.case_study}").text.strip()
        st.session_state.case_study = custom
