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
    ('detailed_metrics', {}),
    ('campaign_timeline', ''),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# === Enhanced Utility: Fetch Comprehensive Campaign Data ===
def fetch_campaign_metrics(query, num_results=10):
    """Fetch comprehensive search results for better metric extraction"""
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = {'q': query, 'num': num_results}
    try:
        res = requests.post(SERPER_API_URL, headers=headers, json=payload, timeout=15)
        data = res.json()
        
        results = {
            'organic': data.get('organic', []),
            'news': data.get('news', []),
            'snippets': []
        }
        
        # Collect all text content
        all_content = []
        for result in results['organic'][:5]:
            content = {
                'title': result.get('title', ''),
                'snippet': result.get('snippet', ''),
                'link': result.get('link', ''),
                'date': result.get('date', '')
            }
            all_content.append(content)
            results['snippets'].append(result.get('snippet', ''))
        
        return results, '\n'.join(results['snippets'])
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return {}, ''

def extract_numeric_metrics(text, metric_type):
    """Extract numeric data with context using AI"""
    extraction_prompt = f"""
    Extract specific numeric metrics from this text related to {metric_type}.
    
    Text: {text[:2000]}
    
    Look for:
    - Percentage increases/decreases (e.g., "20% increase", "15% growth")
    - Absolute numbers with context (e.g., "sales rose to $2.5 million", "gained 1.2 million users")
    - Before/after comparisons
    - Time periods and benchmarks
    
    Return ONLY the most relevant numeric findings in this format:
    METRIC: [number][unit] - [context/timeframe]
    
    If no specific metrics found, return: "No specific metrics found"
    """
    
    try:
        response = model.generate_content(extraction_prompt)
        return response.text.strip()
    except:
        return "No specific metrics found"

def validate_and_enrich_metrics(client_name, campaign_name, metrics_data):
    """Use AI to validate and provide context for extracted metrics"""
    validation_prompt = f"""
    You are a data analyst. Review these extracted metrics for {client_name}'s "{campaign_name}" campaign:
    
    {metrics_data}
    
    For each metric:
    1. Assess if it's realistic and credible
    2. Provide industry context
    3. Flag any suspicious or unverifiable claims
    4. Suggest what additional metrics would be valuable
    
    Format response as:
    VALIDATED METRICS:
    [List credible metrics with context]
    
    CREDIBILITY ASSESSMENT:
    [Brief assessment of data reliability]
    
    MISSING METRICS:
    [Suggest additional KPIs to search for]
    """
    
    try:
        response = model.generate_content(validation_prompt)
        return response.text.strip()
    except:
        return "Unable to validate metrics"

# === Step 0: Enhanced Input Form ===
with st.form('input_form'):
    st.subheader('Enter Case Study & Campaign Details')
    col1, col2 = st.columns(2)
    with col1:
        project_title = st.text_input('Project Title')
        client_name = st.text_input('Client / Brand Name')
        campaign_name = st.text_input('Ad Campaign Name')
        industry = st.text_input('Industry')
        campaign_duration = st.text_input('Campaign Duration (e.g., Q1 2024, Jan-Mar 2024)')
    with col2:
        brief = st.text_area('Project Brief (2-4 lines)')
        achievements = st.text_area('Key Outcomes / Achievements')
        target_metrics = st.multiselect(
            'Focus Metrics (select relevant ones):',
            ['Sales Revenue', 'Market Share', 'Brand Awareness', 'Customer Acquisition', 
             'Engagement Rate', 'Conversion Rate', 'ROI/ROAS', 'Website Traffic']
        )
    
    advanced_search = st.checkbox('Enable Advanced Metric Search (slower but more accurate)')
    go = st.form_submit_button('🎯 Analyze Campaign Impact')

# === Step 1: Enhanced Campaign Metrics & Context Gathering ===
if go and client_name and campaign_name:
    st.info('🔎 Conducting comprehensive campaign impact analysis...')
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 1. General Campaign Context
    status_text.text('Gathering campaign overview...')
    context_queries = [
        f'"{client_name}" "{campaign_name}" campaign results case study',
        f'"{client_name}" "{campaign_name}" advertising campaign impact',
        f'"{client_name}" "{campaign_name}" marketing campaign performance metrics'
    ]
    
    all_context = []
    for query in context_queries:
        results, snippet = fetch_campaign_metrics(query)
        if snippet:
            all_context.append(snippet)
    
    st.session_state.web_context = '\n\n'.join(all_context)
    progress_bar.progress(25)
    
    # 2. Specific Metric Searches
    status_text.text('Extracting specific performance metrics...')
    detailed_metrics = {}
    
    # Enhanced metric search queries
    metric_search_templates = {
        'Sales Impact': [
            f'"{client_name}" "{campaign_name}" sales increase revenue growth',
            f'"{client_name}" "{campaign_name}" sales performance results',
            f'"{client_name}" sales boost after "{campaign_name}" campaign'
        ],
        'Market Share': [
            f'"{client_name}" "{campaign_name}" market share gain',
            f'"{client_name}" market position after "{campaign_name}"',
            f'"{client_name}" competitive advantage "{campaign_name}"'
        ],
        'Brand Awareness': [
            f'"{client_name}" "{campaign_name}" brand awareness lift study',
            f'"{client_name}" "{campaign_name}" brand recognition increase',
            f'"{client_name}" brand metrics "{campaign_name}" campaign'
        ],
        'Customer Acquisition': [
            f'"{client_name}" "{campaign_name}" new customers acquired',
            f'"{client_name}" "{campaign_name}" customer growth rate',
            f'"{client_name}" user acquisition "{campaign_name}"'
        ],
        'Digital Performance': [
            f'"{client_name}" "{campaign_name}" website traffic increase',
            f'"{client_name}" "{campaign_name}" online engagement metrics',
            f'"{client_name}" "{campaign_name}" conversion rate improvement'
        ]
    }
    
    for metric_category, queries in metric_search_templates.items():
        if not target_metrics or any(tm.lower() in metric_category.lower() for tm in target_metrics):
            category_data = []
            for query in queries:
                results, snippet = fetch_campaign_metrics(query, 8)
                if snippet:
                    # Extract metrics using AI
                    extracted = extract_numeric_metrics(snippet, metric_category)
                    if "No specific metrics found" not in extracted:
                        category_data.append(extracted)
            
            if category_data:
                detailed_metrics[metric_category] = category_data
    
    progress_bar.progress(60)
    
    # 3. Validate and Contextualize Metrics
    status_text.text('Validating and contextualizing metrics...')
    if detailed_metrics:
        metrics_summary = ""
        for category, data in detailed_metrics.items():
            metrics_summary += f"\n{category}:\n" + "\n".join(data) + "\n"
        
        validation_result = validate_and_enrich_metrics(client_name, campaign_name, metrics_summary)
        st.session_state.detailed_metrics = {
            'raw_metrics': detailed_metrics,
            'validation': validation_result
        }
    
    progress_bar.progress(80)
    
    # 4. Timeline and Context Analysis
    status_text.text('Analyzing campaign timeline and context...')
    timeline_query = f'"{client_name}" "{campaign_name}" campaign timeline launch date duration {campaign_duration}'
    timeline_results, timeline_context = fetch_campaign_metrics(timeline_query)
    st.session_state.campaign_timeline = timeline_context
    
    progress_bar.progress(100)
    status_text.text('Analysis complete!')
    
    # Display Comprehensive Results
    st.success('✅ Campaign Impact Analysis Complete')
    
    # Metrics Dashboard
    st.markdown('### 📊 Campaign Impact Dashboard')
    
    if st.session_state.detailed_metrics:
        # Display raw metrics in organized format
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('#### 🎯 Key Performance Metrics')
            for category, data in st.session_state.detailed_metrics['raw_metrics'].items():
                with st.expander(f"{category}"):
                    for item in data:
                        st.markdown(f"• {item}")
        
        with col2:
            st.markdown('#### ✅ Data Validation & Context')
            st.markdown(st.session_state.detailed_metrics['validation'])
    
    # Campaign Timeline
    if st.session_state.campaign_timeline:
        st.markdown('#### ⏱️ Campaign Timeline & Context')
        st.info(st.session_state.campaign_timeline[:500] + "..." if len(st.session_state.campaign_timeline) > 500 else st.session_state.campaign_timeline)
    
    # Generate Style Recommendations
    status_text.text('Generating case study recommendations...')
    
    prompt = f"""
    You are a brand strategist analyzing a successful campaign. Based on the comprehensive data below, recommend 3 case study formats that best showcase the quantifiable impact.

    Project: {project_title}
    Client: {client_name}
    Campaign: {campaign_name}
    Industry: {industry}
    Duration: {campaign_duration}
    Brief: {brief}
    Achievements: {achievements}

    PERFORMANCE DATA:
    {st.session_state.detailed_metrics.get('validation', 'Limited metrics available')}

    CAMPAIGN CONTEXT:
    {st.session_state.web_context[:1000]}

    Recommend case study formats that:
    1. Highlight the most impressive quantifiable results
    2. Provide proper context and benchmarks
    3. Tell a compelling data-driven story

    Format your response as:
    1. [Style Name] - Focus: [Key strength]
    2. [Style Name] - Focus: [Key strength] 
    3. [Style Name] - Focus: [Key strength]

    Then provide "Recommended Data Visualizations:" with specific chart/graph suggestions.
    """
    
    rec = model.generate_content(prompt).text.strip()
    st.session_state.recommendations = rec
    styles_found = re.findall(r'^\s*\d+\.\s*(.+?)\s*-', rec, flags=re.MULTILINE)
    st.session_state.styles = styles_found[:3] + ['Comprehensive Data-Driven Report']
    
    status_text.empty()
    progress_bar.empty()

# === Steps 2-5: Enhanced Case Study Generation ===
if st.session_state.recommendations:
    st.markdown('### 🧠 AI-Powered Style Recommendations')
    st.markdown(st.session_state.recommendations)
    st.session_state.selected_style = st.radio('Select Case Study Format:', st.session_state.styles)

if st.session_state.selected_style and st.button('🚀 Generate Data-Driven Case Study'):
    with st.spinner('Creating comprehensive case study with validated metrics...'):
        style = st.session_state.selected_style
        
        # Prepare comprehensive data package
        metrics_context = ""
        if st.session_state.detailed_metrics:
            metrics_context = f"""
VALIDATED PERFORMANCE METRICS:
{st.session_state.detailed_metrics.get('validation', '')}

RAW METRIC DATA:
"""
            for category, data in st.session_state.detailed_metrics.get('raw_metrics', {}).items():
                metrics_context += f"\n{category}:\n" + "\n".join(data) + "\n"
        
        enhanced_prompt = f"""
        Create a comprehensive, data-driven case study in the "{style}" format.

        PROJECT DETAILS:
        Title: {project_title}
        Client: {client_name}
        Campaign: {campaign_name}
        Industry: {industry}
        Duration: {campaign_duration}
        Brief: {brief}
        Achievements: {achievements}

        {metrics_context}

        CAMPAIGN CONTEXT & TIMELINE:
        {st.session_state.campaign_timeline}

        ADDITIONAL CONTEXT:
        {st.session_state.web_context[:1500]}

        REQUIREMENTS:
        1. Lead with the most impressive quantifiable results
        2. Provide proper context and industry benchmarks where possible
        3. Include specific numbers, percentages, and timeframes
        4. Structure the narrative around measurable impact
        5. Flag any metrics that need verification
        6. Include recommendations for future campaigns based on learnings

        Create a professional case study that demonstrates clear ROI and business impact.
        """
        
        output = model.generate_content(enhanced_prompt).text.strip()
        st.session_state.case_study = output
        st.session_state.case_library.append({
            'title': project_title, 
            'style': style, 
            'case': output,
            'metrics': st.session_state.detailed_metrics,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
        })

# === Enhanced Display and Export ===
if st.session_state.case_study:
    st.success('✅ Data-Driven Case Study Generated')
    st.markdown('### 📄 Final Case Study')
    st.markdown(st.session_state.case_study, unsafe_allow_html=True)
    
    # Enhanced feedback and regeneration
    col1, col2 = st.columns(2)
    with col1:
        feedback = st.text_area('✏️ Request specific improvements:')
        if st.button('♻️ Refine Case Study'):
            if feedback:
                revision_prompt = f"""
                Improve this case study based on the feedback: {feedback}
                
                Focus on:
                - Adding more specific metrics if requested
                - Improving data presentation
                - Enhancing narrative flow
                - Strengthening business impact statements
                
                Original Case Study:
                {st.session_state.case_study}
                
                Available Metrics Data:
                {st.session_state.detailed_metrics.get('validation', '')}
                """
                revised = model.generate_content(revision_prompt).text.strip()
                st.session_state.case_study = revised
                st.rerun()
    
    with col2:
        # Export options
        st.download_button(
            '📝 Download Markdown',
            st.session_state.case_study,
            f"{project_title}_case_study.md",
            'text/markdown'
        )
        
        # Enhanced PDF generation
        def create_enhanced_pdf(text, metrics_data):
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .metrics-box {{ background-color: #f0f8ff; padding: 15px; margin: 20px 0; border-left: 4px solid #0066cc; }}
                    .metric-item {{ margin: 10px 0; }}
                    h1, h2, h3 {{ color: #0066cc; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <img src='logo.png' width='120'/>
                    <h1>Campaign Impact Case Study</h1>
                </div>
                {markdown2.markdown(text)}
                <div class="metrics-box">
                    <h3>Validated Metrics Summary</h3>
                    <p>{metrics_data.get('validation', 'See full report for detailed metrics')[:300]}...</p>
                </div>
            </body>
            </html>
            """
            buf = io.BytesIO()
            pisa.CreatePDF(io.StringIO(html_content), dest=buf)
            return buf
        
        if st.button('📄 Generate Enhanced PDF'):
            pdf_buffer = create_enhanced_pdf(st.session_state.case_study, st.session_state.detailed_metrics)
            st.download_button(
                '💾 Download PDF Report',
                pdf_buffer.getvalue(),
                f"{project_title}_case_study.pdf",
                'application/pdf'
            )

# === Enhanced Case Study Library ===
if st.session_state.case_library:
    st.markdown('---')
    st.markdown('### 📚 Case Study Library')
    for i, item in enumerate(reversed(st.session_state.case_library), 1):
        with st.expander(f"{i}. {item['title']} ({item['style']}) - {item.get('timestamp', 'N/A')}"):
            st.markdown(item['case'], unsafe_allow_html=True)
            if item.get('metrics'):
                st.markdown("**Metrics Summary:**")
                st.info(item['metrics'].get('validation', 'No metrics validation available')[:200] + "...")

# === Data Export Section ===
if st.session_state.case_library:
    st.markdown('### 📊 Data Export Options')
    if st.button('📋 Export All Metrics Data'):
        # Create comprehensive data export
        export_data = []
        for case in st.session_state.case_library:
            if case.get('metrics'):
                export_data.append({
                    'Title': case['title'],
                    'Style': case['style'],
                    'Timestamp': case.get('timestamp', ''),
                    'Metrics_Summary': case['metrics'].get('validation', '')[:100] + "..."
                })
        
        if export_data:
            df = pd.DataFrame(export_data)
            st.dataframe(df)
            st.download_button(
                'Download Metrics CSV',
                df.to_csv(index=False),
                'campaign_metrics_export.csv',
                'text/csv'
            )
