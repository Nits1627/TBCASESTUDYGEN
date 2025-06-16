import streamlit as st
import google.generativeai as genai
import markdown2
import io
import re
import requests
from xhtml2pdf import pisa
import json
from datetime import datetime, timedelta
import pandas as pd
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
st.markdown('Generate comprehensive case studies with real, verified campaign metrics and detailed before/after analysis.')

# === Session State ===
for key, default in [
    ('recommendations', ''),
    ('styles', []),
    ('selected_style', None),
    ('case_study', ''),
    ('case_library', []),
    ('web_context', ''),
    ('metrics', {}),
    ('detailed_metrics', {}),
    ('before_after_metrics', {}),
    ('campaign_timeline', ''),
    ('industry_benchmarks', {}),
    ('verified_facts', []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# === Enhanced Utility Functions ===
def fetch_comprehensive_campaign_data(query, num_results=15):
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = {'q': query, 'num': num_results, 'type': 'search', 'engine': 'google'}
    try:
        res = requests.post(SERPER_API_URL, headers=headers, json=payload, timeout=20)
        data = res.json()
        results = {
            'organic': data.get('organic', []),
            'news': data.get('news', []),
            'knowledge_graph': data.get('knowledgeGraph', {}),
            'people_also_ask': data.get('peopleAlsoAsk', []),
            'snippets': []
        }
        all_content = []
        for result in results['organic'][:8]:
            snippet = result.get('snippet', '')
            results['snippets'].append(snippet)
            all_content.append({
                'title': result.get('title', ''),
                'snippet': snippet,
                'link': result.get('link', ''),
                'date': result.get('date', ''),
                'position': result.get('position', 0)
            })
        for news_item in data.get('news', [])[:3]:
            results['snippets'].append(news_item.get('snippet', ''))
        return results, '\n'.join(results['snippets'])
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return {}, ''

def extract_before_after_metrics(text, client_name, campaign_name):
    prompt = f"""
You are a data analyst specializing in campaign performance metrics. Analyze this text about {client_name}'s "{campaign_name}" campaign and extract BEFORE/AFTER metrics...
Text to analyze: {text[:3000]}
..."""
    try:
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        return f"Error extracting metrics: {str(e)}"

def fetch_industry_benchmarks(industry, metric_type):
    benchmark_query = f"{industry} industry {metric_type} benchmark average performance 2024"
    results, content = fetch_comprehensive_campaign_data(benchmark_query, 8)
    if content:
        prompt = f"""
Extract industry benchmark data from this content about {industry} industry {metric_type}:
{content[:2000]}
Return specific benchmark numbers in format...
"""
        try:
            return model.generate_content(prompt).text.strip()
        except:
            return f"No benchmark data found for {industry} {metric_type}"
    return f"No benchmark data available for {industry} {metric_type}"

def verify_campaign_facts(client_name, campaign_name, extracted_metrics):
    queries = [
        f'"{client_name}" "{campaign_name}" official results press release',
        f'"{client_name}" "{campaign_name}" case study marketing agency',
        f'"{client_name}" annual report {campaign_name} campaign performance',
        f'"{client_name}" "{campaign_name}" marketing effectiveness study'
    ]
    sources = []
    for query in queries:
        results, content = fetch_comprehensive_campaign_data(query, 5)
        if content:
            sources.append(content[:1000])
        time.sleep(0.5)
    combined = '\n\n'.join(sources)
    prompt = f"""
As a fact-checker, verify the accuracy of these metrics for {client_name}'s "{campaign_name}" campaign:
METRICS:
{extracted_metrics}
SOURCES:
{combined[:4000]}
Provide VERIFIED FACTS and UNVERIFIED CLAIMS with a credibility score...
"""
    try:
        return model.generate_content(prompt).text.strip()
    except:
        return "Unable to complete fact verification"

# === Input Form ===
with st.form('enhanced_input_form'):
    st.subheader('📋 Comprehensive Campaign Analysis Input')
    col1, col2 = st.columns(2)
    with col1:
        project_title = st.text_input('Project Title')
        client_name = st.text_input('Client / Brand Name')
        campaign_name = st.text_input('Campaign Name')
        industry = st.selectbox('Industry', ['Technology','Retail','Automotive','Financial Services','Healthcare','Food & Beverage','Fashion','Travel & Tourism','Entertainment','Real Estate','Education','Sports','Beauty & Personal Care','Other'])
        campaign_duration = st.text_input('Campaign Duration')
        campaign_budget = st.text_input('Campaign Budget (Optional)')
    with col2:
        brief = st.text_area('Project Brief')
        achievements = st.text_area('Key Achievements')
        target_metrics = st.multiselect('Priority Metrics for Analysis:', ['Sales Revenue','Market Share','Brand Awareness','Customer Acquisition','Website Traffic','Engagement Rate','Conversion Rate','ROI/ROAS','Social Media Growth','Lead Generation','App Downloads','Store Visits'])
        geographic_scope = st.text_input('Geographic Scope')
        target_audience = st.text_input('Target Audience')
    st.markdown("### 🔍 Analysis Options")
    deep_analysis = st.checkbox('Enable Deep Metric Analysis', value=True)
    include_benchmarks = st.checkbox('Include Industry Benchmarks', value=True)
    fact_verification = st.checkbox('Enable Fact Verification', value=True)
    competitive_analysis = st.checkbox('Include Competitive Context', value=False)
    generate_analysis = st.form_submit_button('🚀 Generate Comprehensive Analysis')

# === Analysis Engine ===
if generate_analysis and client_name and campaign_name:
    st.info('🔍 Conducting comprehensive campaign performance analysis...')
    progress_bar = st.progress(0)
    status_text = st.empty()
    # Phases 1-6 (omitted here for brevity, assume unchanged)
    # ...
    # Phase 6: Recommendations generation
    try:
        enhanced_prompt = f"Generate case study format recommendations..."
        rec = model.generate_content(enhanced_prompt).text.strip()
        st.session_state.recommendations = rec
    except Exception:
        st.session_state.recommendations = ''

# ... (rest of analysis display and style selection)

# === Case Study Generation ===
if st.session_state.selected_style and st.button('🚀 Generate Comprehensive Case Study'):
    with st.spinner('🔄 Creating comprehensive case study...'):
        # build comprehensive_data_package...
        try:
            output = model.generate_content('Create comprehensive case study prompt').text.strip()
            st.session_state.case_study = output
            # store in case_library...
        except Exception as e:
            st.error(f"Error generating case study: {str(e)}")

# === Export Section ===
if st.session_state.case_study:
    st.success('✅ Comprehensive Case Study Generated Successfully')
    st.markdown('### 📄 Final Comprehensive Case Study')
    st.markdown(st.session_state.case_study, unsafe_allow_html=True)
    st.markdown('---')
    st.markdown('### 🔧 Case Study Enhancement Options')
    col1, col2 = st.columns(2)
    # Feedback options omitted for brevity

    with col2:
        st.markdown('#### 📥 Export Options')
        # Markdown download
        st.download_button(
            '📝 Download Markdown Report',
            st.session_state.case_study,
            f"{project_title.replace(' ', '_')}_comprehensive_case_study.md",
            'text/markdown'
        )

        def create_comprehensive_pdf(text, title, metrics_data, verification_data):
            html_content = f"""
            <html>
            <head>
            <meta charset=\"UTF-8\">
            <style>body {{font-family:Arial,sans-serif;margin:40px;line-height:1.6;color:#333;}} .header {{text-align:center;margin-bottom:40px;padding-bottom:20px;border-bottom:2px solid #0066cc;}} .metrics-section {{background-color:#f8f9fa;padding:20px;margin:25px 0;border-left:5px solid #0066cc;border-radius:5px;}} .verification-section {{background-color:#e8f5e8;padding:15px;margin:20px 0;border-left:5px solid #28a745;border-radius:5px;}} h1,h2,h3 {{color:#0066cc;}} h1 {{font-size:28px;margin-bottom:10px;}} h2 {{font-size:22px;margin-top:30px;}} h3 {{font-size:18px;margin-top:25px;}} .highlight {{background-color:#fff3cd;padding:2px 5px;}} .footer {{margin-top:50px;text-align:center;font-size:12px;color:#666;}}</style>
            </head>
            <body>
            <div class=\"header\">
            <h1>Comprehensive Campaign Case Study</h1>
            <h2>{title}</h2>
            <p>Generated on {datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            {markdown2.markdown(text, extras=['tables','fenced-code-blocks'])}
            <div class=\"metrics-section\"></div>
            <div class=\"verification-section\">
            <h2>Fact Verification Notes</h2>
            {verification_data.replace('\n','<br>')}
            </div>
            <div class=\"footer\"><p>Generated by AI-Powered Case Study Generator • {datetime.now().strftime('%B %d, %Y')}</p></div>
            </body>
            </html>
            """
            pdf_buffer = io.BytesIO()
            pisa_status = pisa.CreatePDF(io.BytesIO(html_content.encode('utf-8')), dest=pdf_buffer)
            if pisa_status.err:
                st.error("❌ Failed to generate PDF.")
                return None
            pdf_buffer.seek(0)
            return pdf_buffer

        pdf_file = create_comprehensive_pdf(
            text=st.session_state.case_study,
            title=project_title,
            metrics_data=st.session_state.before_after_metrics.get('combined_analysis',''),
            verification_data=st.session_state.verified_facts if st.session_state.verified_facts else "No verification data available"
        )

        if pdf_file:
            st.download_button(
                '📄 Download PDF Report',
                data=pdf_file,
                file_name=f"{project_title.replace(' ', '_')}_Comprehensive_Case_Study.pdf",
                mime='application/pdf'
            )
