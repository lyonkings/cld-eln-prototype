import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import random
import datetime

# ==========================================
# 1. APPLICATION CONFIGURATION & STATE
# ==========================================
st.set_page_config(page_title="CLD ELN Prototype (Sales PoC)", layout="wide", page_icon="🧬")

if 'hierarchy' not in st.session_state:
    st.session_state.hierarchy = {
        'project': 'PRJ-mAb-001 (Anti-CD20)',
        'campaign': 'CMP-2026-Q3-ScaleUp',
        'run': 'RUN-045-Beacon-Transfection'
    }

# Vessel geometry definitions (Rows, Columns, Marker Size)
PLATE_FORMATS = {
    "96-Well Plate (12x8)": {
        "rows": list('ABCDEFGH'),
        "cols": list(range(1, 13)),
        "marker_size": 34,
        "x_range": [0.5, 12.5]
    },
    "24-Well Plate (6x4)": {
        "rows": list('ABCD'),
        "cols": list(range(1, 7)),
        "marker_size": 48,
        "x_range": [0.5, 6.5]
    },
    "6-Well Plate (3x2)": {
        "rows": list('AB'),
        "cols": list(range(1, 4)),
        "marker_size": 75,
        "x_range": [0.5, 3.5]
    }
}

def initialize_empty_plate(format_name):
    """Generates an empty plate layout based on the selected vessel format."""
    config = PLATE_FORMATS[format_name]
    rows = config["rows"]
    cols = config["cols"]
    
    data = []
    for r in rows:
        for c in cols:
            well = f"{r}{c}"
            data.append({
                'well': well, 'row': r, 'col': c, 
                'well_type': 'Unassigned', # Unassigned, Sample, Blank, Pos Control, Neg Control
                'clone_id': None,
                'substance': 'None', 'host': 'None', 'vector': 'None', 
                'locus': 'None', 'sgrna': 'None', 'cas': 'None', 
                'off_target_score': 0.0,
                'monoclonality_verified': False,
                'vcd': 0.0, 'titer': 0.0
            })
    return pd.DataFrame(data)

# Initialize Session State
if 'selected_format' not in st.session_state:
    st.session_state.selected_format = "96-Well Plate (12x8)"

if 'plate_df' not in st.session_state or 'well_type' not in st.session_state.plate_df.columns:
    st.session_state.plate_df = initialize_empty_plate(st.session_state.selected_format)

# ==========================================
# 2. CORE ARCHITECTURE MODULES
# ==========================================
def generate_mock_hamilton_csv():
    df = st.session_state.plate_df.copy()
    active_mask = df['well_type'].isin(['Sample', 'Pos Control', 'Neg Control'])
    
    if active_mask.sum() == 0:
        return "well,vcd,titer\n"
        
    df.loc[active_mask, 'vcd'] = np.round(np.random.uniform(2.5, 15.0, size=active_mask.sum()), 2)
    df.loc[active_mask, 'titer'] = np.round(np.random.uniform(10.0, 150.0, size=active_mask.sum()), 1)
    
    neg_mask = df['well_type'] == 'Neg Control'
    df.loc[neg_mask, 'titer'] = np.round(np.random.uniform(0.0, 2.0, size=neg_mask.sum()), 1)
    
    return df.loc[active_mask, ['well', 'vcd', 'titer']].to_csv(index=False)

def handle_csv_upload(uploaded_file):
    try:
        df_upload = pd.read_csv(uploaded_file)
        current_df = st.session_state.plate_df.set_index('well')
        df_upload = df_upload.set_index('well')
        current_df.update(df_upload)
        st.session_state.plate_df = current_df.reset_index()
        st.success("Instrument data successfully ingested!")
    except Exception as e:
        st.error(f"Error parsing file: {e}")

def calculate_specific_productivity(vcd, titer):
    if vcd == 0: return 0.0
    return round((titer / (vcd * 10)) * 1.5, 2)

# ==========================================
# 3. SIDEBAR: VESSEL CONFIGURATION
# ==========================================
with st.sidebar:
    st.title("🧫 Vessel Configuration")
    
    # Dynamic Format Selector
    chosen_format = st.selectbox(
        "Select Microplate Density:", 
        list(PLATE_FORMATS.keys()),
        index=list(PLATE_FORMATS.keys()).index(st.session_state.selected_format)
    )
    
    # Handle Format Switching
    if chosen_format != st.session_state.selected_format:
        st.session_state.selected_format = chosen_format
        st.session_state.plate_df = initialize_empty_plate(chosen_format)
        st.rerun()

    st.caption(f"Active Grid: {len(PLATE_FORMATS[chosen_format]['rows'])} Rows × {len(PLATE_FORMATS[chosen_format]['cols'])} Columns ({len(st.session_state.plate_df)} Wells)")
    st.divider()

    st.subheader("🧬 Scale-Up Pipeline")
    st.markdown("""
    - **Day 0:** Deposition (Single Cell)
    - **Day 7:** 96-Well Expansion
    - **Day 14:** 24-DWP Transition
    - **Days 25-46:** 6-Well / Shake Flask Cultivation
    """)

# ==========================================
# 4. UI COMPONENT: DYNAMIC PLOTLY PLATE MAP
# ==========================================
def render_plate_map(df, format_name, mode="analytics"):
    config = PLATE_FORMATS[format_name]
    
    color_map = {
        'Sample': '#196F3D',       # Dark Green
        'Pos Control': '#2980B9',  # Blue
        'Neg Control': '#E74C3C',  # Red
        'Blank': '#F1C40F',        # Yellow
        'Unassigned': '#E5E7E9'    # Light Grey
    }
    
    colors = df['well_type'].map(color_map).tolist()
    text_colors = df['well_type'].apply(lambda x: '#7F8C8D' if x == 'Unassigned' else 'white').tolist()
    
    if mode == "design":
        hover_text = df.apply(lambda r: f"<b>Well {r['well']}</b><br>Type: {r['well_type']}<br>Vector: {r['vector']}", axis=1).tolist()
    else:
        hover_text = df.apply(
            lambda r: f"<b>{r['clone_id']} ({r['well']})</b><br>" +
                      f"Type: {r['well_type']}<br>VCD: {r['vcd']}<br>Titer: {r['titer']}" 
                      if r['well_type'] != 'Unassigned' else f"<b>Well {r['well']}</b><br>Unassigned", axis=1
        ).tolist()

    fig = go.Figure(data=go.Scatter(
        x=df['col'], y=df['row'],
        mode='markers+text', text=df['well'],
        textfont=dict(color=text_colors, size=11, family="Arial Black"),
        marker=dict(size=config["marker_size"], color=colors, line=dict(width=2, color='#BDC3C7')),
        hoverinfo='text', hovertext=hover_text
    ))

    fig.update_layout(
        xaxis=dict(tickmode='linear', tick0=1, dtick=1, range=config["x_range"], side='top', showgrid=False, zeroline=False),
        yaxis=dict(autorange='reversed', tickmode='array', tickvals=config["rows"], showgrid=False, zeroline=False),
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=40, r=40, t=40, b=40), height=520,
        clickmode='event+select', dragmode='select', hovermode='closest'
    )
    
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode=["points", "lasso", "box"])
    
    selected_wells = []
    if event and hasattr(event, "selection") and event.selection:
        points = event.selection.get("points", [])
        for p in points:
            if "text" in p:
                selected_wells.append(p["text"])
                
    return list(set(selected_wells))

# ==========================================
# 5. MAIN APPLICATION & TABS
# ==========================================
st.markdown(f"""
<div style='background-color: #F4F6F6; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid #2980B9;'>
    <b>ELN Hierarchy:</b> {st.session_state.hierarchy['project']} ➔ {st.session_state.hierarchy['campaign']} ➔ {st.session_state.hierarchy['run']} | <b>Vessel:</b> {st.session_state.selected_format}
</div>
""", unsafe_allow_html=True)

tab_design, tab_analytics = st.tabs(["🧪 Phase 1: Plate Designer", "📊 Phase 2: Cultivation & Analytics"])

# ---------------------------------------------------------
# TAB 1: PLATE DESIGNER (Dynamic Bulk Assignment)
# ---------------------------------------------------------
with tab_design:
    col_form, col_map = st.columns([1, 2])
    
    current_config = PLATE_FORMATS[st.session_state.selected_format]
    
    with col_form:
        st.markdown(f"### 📋 Bulk Rule Designer")
        st.caption(f"Configure layout rules for {st.session_state.selected_format}")
        
        with st.form("bulk_assignment_form"):
            target_rows = st.multiselect("Target Rows (Empty = All)", current_config["rows"])
            target_cols = st.multiselect("Target Columns (Empty = All)", current_config["cols"])
            
            well_type = st.selectbox("Well Designation", ["Sample", "Pos Control", "Neg Control", "Blank", "Unassigned"])
            
            st.divider()
            st.markdown("**Upstream Registry Linkage**")
            substance = st.selectbox("Substance", ["SUB-0000000025 (anti-CD20)", "SUB-0000000026 (anti-HER2)", "None"])
            host = st.selectbox("Host Line", ["HST-CHO-S", "HST-CHO-K1", "None"])
            vector = st.selectbox("Vector", ["RTX-RD-SEQ-001 (Polycistronic / GS)", "RTX-RD-SEQ-002 (DHFR)", "Empty Vector (Control)", "None"])
            
            submit_rules = st.form_submit_button("Apply Rules to Plate", use_container_width=True)
            
            if submit_rules:
                df = st.session_state.plate_df
                r_mask = df['row'].isin(target_rows) if target_rows else pd.Series([True]*len(df))
                c_mask = df['col'].isin(target_cols) if target_cols else pd.Series([True]*len(df))
                mask = r_mask & c_mask
                
                df.loc[mask, 'well_type'] = well_type
                if well_type in ['Sample', 'Pos Control', 'Neg Control']:
                    df.loc[mask, 'substance'] = substance
                    df.loc[mask, 'host'] = host
                    df.loc[mask, 'vector'] = vector
                    df.loc[mask, 'locus'] = 'TRAC'
                    df.loc[mask, 'sgrna'] = 'UCGACUGACUGCUAGCUAGC'
                    df.loc[mask, 'cas'] = 'SpCas9'
                    
                    for idx in df[mask].index:
                        if df.loc[idx, 'clone_id'] is None:
                            df.loc[idx, 'clone_id'] = f"CLN-{df.loc[idx, 'well']}-{random.randint(1000,9999)}"
                else:
                    df.loc[mask, 'substance'] = 'None'
                    df.loc[mask, 'vector'] = 'None'
                    df.loc[mask, 'clone_id'] = None
                    
                st.session_state.plate_df = df
                st.rerun()
                
        if st.button("🗑️ Reset Layout", use_container_width=True):
            st.session_state.plate_df = initialize_empty_plate(st.session_state.selected_format)
            st.rerun()

    with col_map:
        st.markdown(f"### Live Layout Map ({st.session_state.selected_format})")
        st.markdown("""
        <span style='color:#196F3D'>■ Sample</span> | 
        <span style='color:#2980B9'>■ Pos Control</span> | 
        <span style='color:#E74C3C'>■ Neg Control</span> | 
        <span style='color:#F1C40F'>■ Blank</span> | 
        <span style='color:#7F8C8D'>■ Unassigned</span>
        """, unsafe_allow_html=True)
        render_plate_map(st.session_state.plate_df, st.session_state.selected_format, mode="design")

# ---------------------------------------------------------
# TAB 2: CULTIVATION & ANALYTICS
# ---------------------------------------------------------
with tab_analytics:
    
    with st.expander("🤖 Ingest Liquid Handler Run Files (CSV)", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📥 1. Download Mock Hamilton CSV", data=generate_mock_hamilton_csv(), file_name="hamilton_export.csv", mime="text/csv", use_container_width=True)
        with c2:
            uploaded_file = st.file_uploader("2. Upload CSV Run File", type=['csv'], label_visibility="collapsed")
            if uploaded_file is not None:
                handle_csv_upload(uploaded_file)

    col_map2, col_details = st.columns([1.5, 1])

    with col_map2:
        st.markdown(f"### Analytics Map ({st.session_state.selected_format})")
        selected_wells = render_plate_map(st.session_state.plate_df, st.session_state.selected_format, mode="analytics")

    with col_details:
        st.markdown("### Selection Details")
        
        if not selected_wells:
            st.info("👈 Drag a box over wells on the map to inspect analytics.")
            
        elif len(selected_wells) == 1:
            selected_well = selected_wells[0]
            well_data = st.session_state.plate_df[st.session_state.plate_df['well'] == selected_well].iloc[0]
            
            st.markdown(f"**Viewing Well:** `{selected_well}` | **Type:** `{well_data['well_type']}`")
            
            if well_data['well_type'] in ['Blank', 'Unassigned']:
                st.warning(f"Well {selected_well} is configured as {well_data['well_type']}. No analytics tracking applied.")
            else:
                with st.expander("🧬 Upstream Registration", expanded=True):
                    st.markdown(f"**Clone ID:** `{well_data['clone_id']}`")
                    st.markdown(f"**Substance:** `{well_data['substance']}`")
                    st.markdown(f"**Vector:** `{well_data['vector']}`")

                with st.expander("🧪 Cultivation Analytics", expanded=True):
                    m1, m2, m3 = st.columns(3)
                    m1.metric("VCD", well_data['vcd'])
                    m2.metric("Titer", well_data['titer'])
                    m3.metric("qp", calculate_specific_productivity(well_data['vcd'], well_data['titer']))
                    
        else:
            st.markdown(f"**Viewing {len(selected_wells)} Selected Wells**")
            multi_df = st.session_state.plate_df[st.session_state.plate_df['well'].isin(selected_wells)]
            active_df = multi_df[multi_df['well_type'].isin(['Sample', 'Pos Control', 'Neg Control'])]
            
            if len(active_df) == 0:
                st.warning("Selected wells do not contain active samples.")
            else:
                st.success(f"{len(active_df)} active wells selected.")
                st.dataframe(active_df[['well', 'well_type', 'clone_id', 'vcd', 'titer']], hide_index=True, use_container_width=True)
                
                m1, m2 = st.columns(2)
                m1.metric("Average Sample VCD", f"{round(active_df[active_df['well_type']=='Sample']['vcd'].mean(), 2)} x10⁶")
                m2.metric("Average Sample Titer", f"{round(active_df[active_df['well_type']=='Sample']['titer'].mean(), 1)} mg/L")
