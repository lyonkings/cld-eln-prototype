import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import random
import datetime

# ==========================================
# 1. APPLICATION CONFIGURATION & STATE
# ==========================================
st.set_page_config(page_title="CLD ELN Prototype", layout="wide", page_icon="🧬")

if 'hierarchy' not in st.session_state:
    st.session_state.hierarchy = {
        'project': 'PRJ-mAb-001 (Anti-CD20)',
        'campaign': 'CMP-2026-Q3-ScaleUp',
        'run': 'RUN-045-Beacon-Transfection'
    }

def initialize_plate_state():
    rows = list('ABCDEFGH')
    cols = list(range(1, 13))
    
    substances = ['SUB-0000000025 (anti-CD20 rituximab-fab)', 'SUB-0000000026 (anti-HER2 bispecific)']
    hosts = ['HST-CHO-S', 'HST-CHO-K1']
    vectors = ['RTX-RD-SEQ-000 (Monocistronic)', 'RTX-RD-SEQ-001 (Polycistronic / GS)', 'RTX-RD-SEQ-002 (Polycistronic / DHFR)']
    loci = ['TRAC', 'Rosa26']
    sgrnas = ['UCGACUGACUGCUAGCUAGC', 'GCTAGCUCGACUGACUGCUA']
    cases = ['SpCas9', 'LeriCas9']
    
    data = []
    for r in rows:
        for c in cols:
            well = f"{r}{c}"
            is_seeded = bool(np.random.choice([True, False], p=[0.7, 0.3]))
            
            if is_seeded:
                data.append({
                    'well': well, 'row': r, 'col': c, 'seeded': True,
                    'clone_id': f"CLN-{well}-{random.randint(1000,9999)}",
                    'substance': random.choice(substances), 'host': random.choice(hosts),
                    'vector': random.choice(vectors), 'locus': random.choice(loci),
                    'sgrna': random.choice(sgrnas), 'cas': random.choice(cases),
                    'off_target_score': round(float(np.random.uniform(0.1, 3.5)), 2),
                    'monoclonality_verified': bool(np.random.choice([True, False])),
                    'vcd': round(float(np.random.uniform(2.5, 15.0)), 2),
                    'titer': round(float(np.random.uniform(10.0, 150.0)), 1)
                })
            else:
                data.append({
                    'well': well, 'row': r, 'col': c, 'seeded': False, 'clone_id': None,
                    'substance': None, 'host': None, 'vector': None, 
                    'locus': None, 'sgrna': None, 'cas': None, 
                    'off_target_score': None, 'monoclonality_verified': False,
                    'vcd': 0.0, 'titer': 0.0
                })
    return pd.DataFrame(data)

if 'plate_df' not in st.session_state or 'clone_id' not in st.session_state.plate_df.columns:
    st.session_state.plate_df = initialize_plate_state()

# ==========================================
# 2. CORE ARCHITECTURE MODULES
# ==========================================
def generate_mock_hamilton_csv():
    df = st.session_state.plate_df
    seeded_df = df[df['seeded'] == True].copy()
    seeded_df['vcd'] = np.round(np.random.uniform(2.5, 15.0, size=len(seeded_df)), 2)
    seeded_df['titer'] = np.round(np.random.uniform(10.0, 150.0, size=len(seeded_df)), 1)
    return seeded_df[['well', 'vcd', 'titer']].to_csv(index=False)

def handle_csv_upload(uploaded_file):
    try:
        df_upload = pd.read_csv(uploaded_file)
        if not all(col in df_upload.columns for col in ['well', 'vcd', 'titer']):
            st.sidebar.error("CSV must contain 'well', 'vcd', and 'titer'.")
            return
        
        current_df = st.session_state.plate_df.set_index('well')
        df_upload = df_upload.set_index('well')
        current_df.update(df_upload)
        st.session_state.plate_df = current_df.reset_index()
        st.sidebar.success("Instrument data successfully ingested!")
    except Exception as e:
        st.sidebar.error(f"Error parsing file: {e}")

def calculate_specific_productivity(vcd, titer):
    if vcd == 0: return 0.0
    qp = (titer / (vcd * 10)) * 1.5 
    return round(qp, 2)

def generate_clonality_report(well_data):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
    # IND Regulatory Clonality Report
    **Generated:** {timestamp}
    **Project Hierarchy:** {st.session_state.hierarchy['project']} > {st.session_state.hierarchy['campaign']}
    
    ## 1. Clone Identity
    - Clone ID: {well_data['clone_id']}
    - Well Location: {well_data['well']}
    - Host Line: {well_data['host']}
    
    ## 2. Vector & Genetic Footprint
    - Substance: {well_data['substance']}
    - Vector Sequence: {well_data['vector']}
    - CRISPR Locus: {well_data['locus']}
    - Cas Enzyme: {well_data['cas']}
    """

# ==========================================
# 3. SIDEBAR
# ==========================================
with st.sidebar:
    st.title("🧬 CLD Workflow")
    if st.button("🚀 Execute Day 14 Transfer (96 to 24-DWP)"):
        st.success("Plate Scaling Engine Triggered: Mapped 96-well seeding to 4x 24-Deep Well Plates.")
        st.balloons()
        
    st.divider()
    st.subheader("🤖 Instrument Data Ingestion")
    st.download_button("📥 Download Mock Hamilton CSV", data=generate_mock_hamilton_csv(), file_name="hamilton_export.csv", mime="text/csv")
    
    uploaded_file = st.file_uploader("Upload Run File (CSV)", type=['csv'])
    if uploaded_file is not None:
        if st.button("Process & Update Plate"):
            handle_csv_upload(uploaded_file)

# ==========================================
# 4. UI COMPONENT: INTERACTIVE PLOTLY PLATE MAP
# ==========================================
def render_interactive_plate_map(df):
    colors = df['seeded'].apply(lambda x: '#196F3D' if x else '#E5E7E9').tolist()
    text_colors = df['seeded'].apply(lambda x: 'white' if x else '#7F8C8D').tolist()
    
    hover_text = df.apply(
        lambda r: f"<b>{r['clone_id']} ({r['well']})</b><br>" +
                  f"Status: {'Seeded 🟢' if r['seeded'] else 'Empty ⚪'}<br>" +
                  f"Locus: {r['locus']}<br>" +
                  f"VCD: {r['vcd']}<br>Titer: {r['titer']}" if r['seeded'] else f"<b>Well {r['well']}</b><br>Empty ⚪", axis=1
    ).tolist()

    fig = go.Figure(data=go.Scatter(
        x=df['col'], y=df['row'],
        mode='markers+text', text=df['well'],
        textfont=dict(color=text_colors, size=11, family="Arial Black"),
        marker=dict(size=34, color=colors, line=dict(width=2, color='#BDC3C7')),
        hoverinfo='text', hovertext=hover_text
    ))

    fig.update_layout(
        xaxis=dict(tickmode='linear', tick0=1, dtick=1, range=[0.5, 12.5], side='top', showgrid=False, zeroline=False),
        yaxis=dict(autorange='reversed', tickmode='array', tickvals=list('ABCDEFGH'), showgrid=False, zeroline=False),
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=40, r=40, t=40, b=40), height=520,
        clickmode='event+select', dragmode='select', hovermode='closest'
    )
    
    # Modern Streamlit native selection (Works perfectly on real servers)
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode=["points", "lasso", "box"])
    
    selected_wells = []
    if event and hasattr(event, "selection") and event.selection:
        points = event.selection.get("points", [])
        for p in points:
            if "text" in p:
                selected_wells.append(p["text"])
                
    return list(set(selected_wells))

# ==========================================
# 5. MAIN APPLICATION LAYOUT
# ==========================================
st.markdown(f"""
<div style='background-color: #F4F6F6; padding: 10px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #2980B9;'>
    <b>Hierarchy:</b> {st.session_state.hierarchy['project']} ➔ {st.session_state.hierarchy['campaign']} ➔ {st.session_state.hierarchy['run']}
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1.5, 1])

with col1:
    st.markdown("### Interactive 2D Plate Map")
    st.info("💡 **Tip:** Click on a well, or click the **Lasso/Box select tool** in the top-right corner of the map to drag over multiple wells!")
    
    selected_wells = render_interactive_plate_map(st.session_state.plate_df)

with col2:
    st.markdown("### Selection Details")
    
    if not selected_wells:
        st.info("👈 Select a well or drag a box over the plate map to view metadata.")
        
    elif len(selected_wells) == 1:
        selected_well = selected_wells[0]
        well_data = st.session_state.plate_df[st.session_state.plate_df['well'] == selected_well].iloc[0]
        
        st.markdown(f"**Viewing Well:** `{selected_well}` | **Clone ID:** `{well_data['clone_id']}`")
        
        if not well_data['seeded']:
            st.warning(f"Well {selected_well} is unseeded (Empty).")
        else:
            with st.expander("🧬 Upstream Registration", expanded=True):
                st.markdown(f"**Substance:** `{well_data['substance']}`")
                st.markdown(f"**Host:** `{well_data['host']}`")
                st.markdown(f"**Vector:** `{well_data['vector']}`")
                
            with st.expander("✂️ CRISPR Parameters", expanded=True):
                st.markdown(f"**Locus:** `{well_data['locus']}` | **Cas:** `{well_data['cas']}`")
                score = well_data['off_target_score']
                color = "green" if score < 1.0 else ("orange" if score < 2.5 else "red")
                st.markdown(f"**Off-Target:** <span style='color:{color}; font-weight:bold;'>{score}%</span>", unsafe_allow_html=True)

            with st.expander("🧪 Stability & Analytics", expanded=True):
                m1, m2, m3 = st.columns(3)
                m1.metric("VCD", well_data['vcd'])
                m2.metric("Titer", well_data['titer'])
                m3.metric("qp", calculate_specific_productivity(well_data['vcd'], well_data['titer']))
                
            report_text = generate_clonality_report(well_data)
            st.download_button("📄 Download IND Regulatory Report", data=report_text, file_name=f"IND_Report_{well_data['clone_id']}.txt", mime="text/plain", use_container_width=True)
                
    else:
        st.markdown(f"**Viewing {len(selected_wells)} Selected Wells**")
        multi_df = st.session_state.plate_df[st.session_state.plate_df['well'].isin(selected_wells)]
        seeded_df = multi_df[multi_df['seeded'] == True]
        
        if len(seeded_df) == 0:
            st.warning("All selected wells are empty.")
        else:
            st.success(f"{len(seeded_df)} seeded wells selected. Displaying aggregated view.")
            st.dataframe(seeded_df[['well', 'clone_id', 'locus', 'vcd', 'titer']], hide_index=True, use_container_width=True)
            
            with st.form("bulk_edit_form"):
                st.markdown("#### ✏️ Bulk Edit")
                new_locus = st.selectbox("Target Locus", ["No Change", "TRAC", "Rosa26", "AAVS1"])
                if st.form_submit_button("Apply to Selected Wells"):
                    df = st.session_state.plate_df
                    mask = df['well'].isin(selected_wells) & (df['seeded'] == True)
                    if new_locus != "No Change": df.loc[mask, 'locus'] = new_locus
                    st.session_state.plate_df = df
                    st.rerun()
