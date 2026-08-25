import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import random
import datetime

# ==========================================
# 1. APPLICATION CONFIGURATION & STATE
# ==========================================
st.set_page_config(page_title="Enterprise CLD ELN Platform", layout="wide", page_icon="🧬")

PLATE_FORMATS = {
    "384-Well Plate (24x16)": {
        "rows": list('ABCDEFGHIJKLMNOP'),
        "cols": list(range(1, 25)),
        "marker_size": 18,
        "x_range": [0.5, 24.5]
    },
    "96-Well Plate (12x8)": {
        "rows": list('ABCDEFGH'),
        "cols": list(range(1, 13)),
        "marker_size": 32,
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

if 'hierarchy' not in st.session_state:
    st.session_state.hierarchy = {
        'project': 'PRJ-mAb-001 (Anti-CD20)',
        'study': 'STD-2026-Transfection-Optimization',
        'campaign': 'CMP-Q3-ScaleUp'
    }

# Default locked construct blueprint
if 'locked_construct' not in st.session_state:
    st.session_state.locked_construct = {
        'substance': 'SUB-0000000025 (anti-CD20 rituximab-fab)',
        'host': 'HST-CHO-S (CHO-K1 derivative)',
        'vector': 'RTX-RD-SEQ-001 (Polycistronic / GS)',
        'ratio': '1:2'
    }

# Key tracking for cascading LC:HC selectbox in Phase 2
if 'phase2_ratio_select' not in st.session_state:
    st.session_state.phase2_ratio_select = st.session_state.locked_construct['ratio']

def initialize_empty_plate(format_name):
    config = PLATE_FORMATS[format_name]
    rows = config["rows"]
    cols = config["cols"]
    
    data = []
    for r in rows:
        for c in cols:
            well = f"{r}{c}"
            data.append({
                'well': well, 'row': r, 'col': c, 
                'well_type': 'Unassigned',
                'clone_id': None,
                'parent_beacon_pen': None,
                'ambr_vessel_id': None,
                'substance': 'None', 'host': 'None', 'vector': 'None', 
                'lc_hc_ratio': '1:1',
                'locus': 'None', 'sgrna': 'None', 'cas': 'None', 
                'off_target_score': 0.0,
                'monoclonality_verified': False,
                'vcd': 0.0, 'titer': 0.0, # Strictly zero until ingestion
                'g0f_pct': 0.0, 'g1f_pct': 0.0, 'g2f_pct': 0.0, 'man5_pct': 0.0,
                'charge_main_pct': 0.0, 'charge_acidic_pct': 0.0, 'charge_basic_pct': 0.0,
                'ambr_ph': 7.10, 'ambr_do_pct': 40.0, 'ambr_temp_c': 36.5
            })
    return pd.DataFrame(data)

if 'selected_format' not in st.session_state:
    st.session_state.selected_format = "96-Well Plate (12x8)"

if 'plate_df' not in st.session_state or 'ambr_vessel_id' not in st.session_state.plate_df.columns:
    st.session_state.plate_df = initialize_empty_plate(st.session_state.selected_format)

# ==========================================
# 2. HELPER & DATA GENERATION MODULES
# ==========================================
def generate_mock_ambr_csv():
    df = st.session_state.plate_df.copy()
    active_mask = df['well_type'].isin(['Sample', 'Pos Control', 'Neg Control'])
    
    if active_mask.sum() == 0:
        return "well,vcd,titer,ambr_ph,ambr_do_pct,g0f_pct,charge_main_pct\n"
        
    df.loc[active_mask, 'vcd'] = np.round(np.random.uniform(3.5, 18.0, size=active_mask.sum()), 2)
    df.loc[active_mask, 'titer'] = np.round(np.random.uniform(25.0, 220.0, size=active_mask.sum()), 1)
    df.loc[active_mask, 'ambr_ph'] = np.round(np.random.uniform(6.95, 7.20, size=active_mask.sum()), 2)
    df.loc[active_mask, 'ambr_do_pct'] = np.round(np.random.uniform(35.0, 45.0, size=active_mask.sum()), 1)
    df.loc[active_mask, 'g0f_pct'] = np.round(np.random.uniform(65.0, 80.0, size=active_mask.sum()), 1)
    df.loc[active_mask, 'charge_main_pct'] = np.round(np.random.uniform(60.0, 75.0, size=active_mask.sum()), 1)
    
    return df.loc[active_mask, ['well', 'vcd', 'titer', 'ambr_ph', 'ambr_do_pct', 'g0f_pct', 'charge_main_pct']].to_csv(index=False)

def generate_jmp_export():
    df = st.session_state.plate_df.copy()
    active_df = df[df['well_type'].isin(['Sample', 'Pos Control', 'Neg Control'])].copy()
    
    active_df['Project'] = st.session_state.hierarchy['project']
    active_df['Study'] = st.session_state.hierarchy['study']
    active_df['Campaign'] = st.session_state.hierarchy['campaign']
    
    cols = ['Project', 'Study', 'Campaign', 'well', 'clone_id', 'parent_beacon_pen', 'ambr_vessel_id',
            'substance', 'host', 'vector', 'lc_hc_ratio', 'vcd', 'titer', 
            'g0f_pct', 'charge_main_pct', 'ambr_ph']
    return active_df[cols].to_csv(index=False)

def calculate_specific_productivity(vcd, titer):
    if vcd == 0: return 0.0
    return round((titer / (vcd * 10)) * 1.5, 2)

# ==========================================
# 3. SIDEBAR & NAVIGATION
# ==========================================
with st.sidebar:
    st.title("🧬 CLD Hierarchy & Vessel")
    
    st.markdown("**Hierarchy Scope**")
    st.session_state.hierarchy['project'] = st.selectbox("Project", ["PRJ-mAb-001 (Anti-CD20)", "PRJ-bsAb-002 (Anti-HER2/CD3)"])
    st.session_state.hierarchy['study'] = st.selectbox("Study", ["STD-2026-Transfection-Opt", "STD-2026-Stability-Pass"])
    st.session_state.hierarchy['campaign'] = st.text_input("Campaign ID", st.session_state.hierarchy['campaign'])
    
    st.divider()
    
    chosen_format = st.selectbox(
        "Microplate Density:", 
        list(PLATE_FORMATS.keys()),
        index=list(PLATE_FORMATS.keys()).index(st.session_state.selected_format)
    )
    
    if chosen_format != st.session_state.selected_format:
        st.session_state.selected_format = chosen_format
        st.session_state.plate_df = initialize_empty_plate(chosen_format)
        st.rerun()

    st.caption(f"Active Format: {len(st.session_state.plate_df)} Total Wells")
    st.divider()
    
    st.subheader("📊 Statistical Export")
    st.download_button(
        "📥 Export JMP-Formatted Dataset",
        data=generate_jmp_export(),
        file_name="CLD_JMP_Master_Dataset.csv",
        mime="text/csv",
        help="Export tidy wide-format CSV optimized for instant JMP statistical modeling."
    )

# ==========================================
# 4. UI COMPONENT: DYNAMIC PLOTLY MAP
# ==========================================
def render_plate_map(df, format_name, mode="analytics", chart_key="plate_map"):
    config = PLATE_FORMATS[format_name]
    
    color_map = {
        'Sample': '#196F3D',       
        'Pos Control': '#2980B9',  
        'Neg Control': '#E74C3C',  
        'Blank': '#F1C40F',        
        'Unassigned': '#E5E7E9'    
    }
    
    colors = df['well_type'].map(color_map).tolist()
    text_colors = df['well_type'].apply(lambda x: '#7F8C8D' if x == 'Unassigned' else 'white').tolist()
    
    hover_text = df.apply(
        lambda r: f"<b>{r['clone_id'] or r['well']}</b><br>Type: {r['well_type']}<br>Ratio: {r['lc_hc_ratio']}<br>VCD: {r['vcd']}<br>Titer: {r['titer']}", axis=1
    ).tolist()

    fig = go.Figure(data=go.Scatter(
        x=df['col'], y=df['row'],
        mode='markers+text', 
        text=df['well'] if "384" not in format_name else None, 
        customdata=df['well'].tolist(),
        textfont=dict(color=text_colors, size=9 if "384" in format_name else 11, family="Arial Black"),
        marker=dict(size=config["marker_size"], color=colors, line=dict(width=1 if "384" in format_name else 2, color='#BDC3C7')),
        hoverinfo='text', hovertext=hover_text
    ))

    fig.update_layout(
        xaxis=dict(tickmode='linear', tick0=1, dtick=1, range=config["x_range"], side='top', showgrid=False, zeroline=False),
        yaxis=dict(autorange='reversed', tickmode='array', tickvals=config["rows"], showgrid=False, zeroline=False),
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=20, r=20, t=30, b=20), height=520,
        clickmode='event+select',
        dragmode=False,
        hovermode='closest'
    )
    
    event = st.plotly_chart(
        fig, 
        use_container_width=True, 
        on_select="rerun", 
        selection_mode=["points", "lasso", "box"],
        key=chart_key
    )
    
    selected_wells = []
    if event and hasattr(event, "selection") and event.selection:
        points = event.selection.get("points", [])
        for p in points:
            if "customdata" in p and p["customdata"]:
                cd = p["customdata"]
                selected_wells.append(cd[0] if isinstance(cd, list) else str(cd))
            elif "text" in p and p["text"]:
                selected_wells.append(p["text"])
            elif "point_index" in p and p["point_index"] is not None:
                idx = p["point_index"]
                if 0 <= idx < len(df):
                    selected_wells.append(df.iloc[idx]["well"])
            elif "x" in p and "y" in p and p["x"] is not None and p["y"] is not None:
                selected_wells.append(f"{p['y']}{p['x']}")
                
    return list(set(selected_wells))

# ==========================================
# 5. MAIN WORKFLOW TABS
# ==========================================
t1, t2, t3, t4 = st.tabs([
    "🧬 Phase 1: Construct & Pool Design", 
    "🧫 Phase 2: Vessel & Plate Designer", 
    "🌳 Phase 3: Lineage & AMBR Ingestion", 
    "📈 Phase 4: Critical Quality Attributes (CQAs)"
])

# ---------------------------------------------------------
# PHASE 1: CONSTRUCT & MODALITY COMPLEXITY
# ---------------------------------------------------------
with t1:
    st.markdown("### Upstream Construct Engineering & Transfection Pools")
    st.write("Define your target drug molecule, host line, vector system, and plasmid ratios before layout design.")
    
    c1, c2 = st.columns(2)
    with c1:
        with st.form("construct_form"):
            st.markdown("**Plasmid Pool & Transfection Parameters**")
            substance = st.selectbox("Target Substance", ["SUB-0000000025 (anti-CD20 rituximab-fab)", "SUB-0000000026 (anti-HER2 bispecific)"])
            host = st.selectbox("Host Cell Line", ["HST-CHO-S (CHO-K1 derivative)", "HST-CHO-DG44 (DHFR deficient)"])
            vector_type = st.selectbox("Vector System", ["RTX-RD-SEQ-001 (Polycistronic / GS)", "RTX-RD-SEQ-002 (Monocistronic / DHFR)"])
            
            lc_hc_ratio = st.select_slider(
                "Light Chain to Heavy Chain (LC:HC) Plasmid Ratio",
                options=["1:3", "1:2", "1:1", "2:1", "3:1"],
                value=st.session_state.locked_construct['ratio'],
                help="Varying LC:HC plasmid ratios optimizes folding and prevents heavy-chain toxicity."
            )
            
            if st.form_submit_button("Lock Construct Blueprint for Study"):
                st.session_state.locked_construct = {
                    'substance': substance,
                    'host': host,
                    'vector': vector_type,
                    'ratio': lc_hc_ratio
                }
                # Instantly update Phase 2 selectbox key so it cascades smoothly
                st.session_state.phase2_ratio_select = lc_hc_ratio
                st.success("Construct blueprint locked into session state!")

    with c2:
        st.markdown("**Active Construct Blueprint**")
        st.write("This blueprint automatically populates the default settings when you design your microplates in Phase 2.")
        
        lc = st.session_state.locked_construct
        st.info(f"""
        **Current Locked Construct Configuration:**
        * **Target Substance:** `{lc['substance']}`
        * **Host Cell Line:** `{lc['host']}`
        * **Vector System:** `{lc['vector']}`
        * **LC:HC Ratio:** `{lc['ratio']}`
        """)

# ---------------------------------------------------------
# PHASE 2: PLATE DESIGNER
# ---------------------------------------------------------
with t2:
    col_form, col_map = st.columns([1, 2])
    current_config = PLATE_FORMATS[st.session_state.selected_format]
    lc = st.session_state.locked_construct
    
    with col_form:
        st.markdown(f"### Bulk Layout Designer")
        st.caption(f"Active Blueprint: **{lc['substance'].split()[0]}** | **{lc['host'].split()[0]}** | **Ratio {lc['ratio']}**")
        
        with st.form("bulk_assignment_form"):
            target_rows = st.multiselect("Target Rows (Empty = All)", current_config["rows"])
            target_cols = st.multiselect("Target Columns (Empty = All)", current_config["cols"])
            well_type = st.selectbox("Well Designation", ["Sample", "Pos Control", "Neg Control", "Blank", "Unassigned"])
            
            # Cascaded ratio selection tied reactively to Phase 1
            ratio_choice = st.selectbox(
                "LC:HC Ratio Assignment", 
                ["1:3", "1:2", "1:1", "2:1", "3:1"],
                key="phase2_ratio_select"
            )
            
            if st.form_submit_button("Apply Rules to Vessel Map", use_container_width=True):
                df = st.session_state.plate_df
                r_mask = df['row'].isin(target_rows) if target_rows else pd.Series([True]*len(df))
                c_mask = df['col'].isin(target_cols) if target_cols else pd.Series([True]*len(df))
                mask = r_mask & c_mask
                
                df.loc[mask, 'well_type'] = well_type
                if well_type in ['Sample', 'Pos Control', 'Neg Control']:
                    df.loc[mask, 'lc_hc_ratio'] = ratio_choice
                    df.loc[mask, 'substance'] = lc['substance']
                    df.loc[mask, 'host'] = lc['host']
                    df.loc[mask, 'vector'] = lc['vector']
                    
                    # Ensure VCD & Titer are explicitly ZERO until instrument data ingestion
                    df.loc[mask, 'vcd'] = 0.0
                    df.loc[mask, 'titer'] = 0.0
                    
                    for idx in df[mask].index:
                        well_name = df.loc[idx, 'well']
                        if df.loc[idx, 'clone_id'] is None:
                            df.loc[idx, 'clone_id'] = f"CLN-{well_name}-{random.randint(1000,9999)}"
                            df.loc[idx, 'parent_beacon_pen'] = f"BCN-PEN-{random.randint(100,999)}"
                            df.loc[idx, 'ambr_vessel_id'] = f"AMBR15-Vessel-{well_name}"
                            
                            # CQA baseline targets (Populated post-characterization)
                            g0f = round(random.uniform(68.0, 78.0), 1)
                            g1f = round(random.uniform(12.0, 18.0), 1)
                            g2f = round(random.uniform(3.0, 7.0), 1)
                            man5 = round(100.0 - (g0f + g1f + g2f), 1)
                            
                            main_p = round(random.uniform(62.0, 74.0), 1)
                            acidic_p = round(random.uniform(18.0, 26.0), 1)
                            basic_p = round(100.0 - (main_p + acidic_p), 1)
                            
                            df.loc[idx, 'g0f_pct'] = g0f
                            df.loc[idx, 'g1f_pct'] = g1f
                            df.loc[idx, 'g2f_pct'] = g2f
                            df.loc[idx, 'man5_pct'] = man5
                            
                            df.loc[idx, 'charge_main_pct'] = main_p
                            df.loc[idx, 'charge_acidic_pct'] = acidic_p
                            df.loc[idx, 'charge_basic_pct'] = basic_p
                else:
                    df.loc[mask, 'substance'] = 'None'
                    df.loc[mask, 'host'] = 'None'
                    df.loc[mask, 'vector'] = 'None'
                    df.loc[mask, 'clone_id'] = None
                    df.loc[mask, 'parent_beacon_pen'] = None
                    df.loc[mask, 'ambr_vessel_id'] = None
                    df.loc[mask, 'vcd'] = 0.0
                    df.loc[mask, 'titer'] = 0.0
                    
                st.session_state.plate_df = df
                st.rerun()

    with col_map:
        st.markdown(f"### Live Seeding Map ({st.session_state.selected_format})")
        st.caption("💡 Click any well directly to inspect, or use the Box/Lasso tools on the toolbar.")
        st.markdown("<span style='color:#196F3D'>■ Sample</span> | <span style='color:#2980B9'>■ Pos Control</span> | <span style='color:#E74C3C'>■ Neg Control</span> | <span style='color:#F1C40F'>■ Blank</span>", unsafe_allow_html=True)
        render_plate_map(st.session_state.plate_df, st.session_state.selected_format, mode="design", chart_key="map_phase2")

# ---------------------------------------------------------
# PHASE 3: LINEAGE & AMBR BIOREACTOR INGESTION
# ---------------------------------------------------------
with t3:
    st.markdown("### Automated Lineage & AMBR Connectors")
    
    with st.expander("🤖 Ingest AMBR Microbioreactor Run File (CSV)", expanded=True):
        ac1, ac2 = st.columns(2)
        with ac1:
            st.markdown("**Step 1: Download Instrument Run File**")
            st.download_button("📥 Download Mock AMBR CSV", data=generate_mock_ambr_csv(), file_name="ambr_run_data.csv", mime="text/csv", use_container_width=True)
        with ac2:
            st.markdown("**Step 2: Upload Processed Run Log**")
            uploaded_ambr = st.file_uploader("Upload AMBR File", type=['csv'], label_visibility="collapsed")
            if uploaded_ambr is not None:
                try:
                    df_up = pd.read_csv(uploaded_ambr).set_index('well')
                    curr_df = st.session_state.plate_df.set_index('well')
                    curr_df.update(df_up)
                    st.session_state.plate_df = curr_df.reset_index()
                    st.success("AMBR Bioreactor metrics (VCD & Titer) successfully ingested!")
                except Exception as e:
                    st.error(f"Error parsing AMBR file: {e}")

    col_m3, col_pedigree = st.columns([1.3, 1])
    with col_m3:
        selected_wells_p3 = render_plate_map(st.session_state.plate_df, st.session_state.selected_format, mode="analytics", chart_key="map_phase3")
        
    with col_pedigree:
        st.markdown("### Clone Lineage")
        if not selected_wells_p3:
            st.info("👈 Click or select a well on the map to trace its automated single-cell scale-up lineage.")
        else:
            sel_well = selected_wells_p3[0]
            w_data = st.session_state.plate_df[st.session_state.plate_df['well'] == sel_well].iloc[0]
            
            if w_data['well_type'] not in ['Sample', 'Pos Control']:
                st.warning("Selected well is empty or a control.")
            else:
                st.markdown(f"**Tracing Lineage for Clone:** `{w_data['clone_id']}`")
                st.markdown(f"""
                * **Day 0 (Beacon Optofluidics):** Single-cell penned in `{w_data['parent_beacon_pen'] or 'BCN-PEN-402'}` (VIPS Verified Monoclonal)
                * **Day 7 (384-Well Plate):** Expanded in Well `C12`
                * **Day 14 (96-Deep Well Plate):** Transitioned to Well `{w_data['well']}`
                * **Day 25 (AMBR 15 Microbioreactor):** Vessel `{w_data['ambr_vessel_id'] or f'AMBR15-Vessel-{sel_well}'}` (pH: {w_data['ambr_ph']}, DO: {w_data['ambr_do_pct']}%)
                """)
                
                # Live metric status
                if w_data['vcd'] == 0.0 and w_data['titer'] == 0.0:
                    st.info("⏳ **Status:** Awaiting AMBR Bioreactor Data Ingestion (VCD: 0.0, Titer: 0.0)")
                else:
                    st.success(f"📊 **Ingested Data:** VCD = {w_data['vcd']} x10⁶ cells/mL | Titer = {w_data['titer']} mg/L")
                
                st.success("Monoclonality Audit: 100% Verified (Image Proof #IMG-9042)")

# ---------------------------------------------------------
# PHASE 4: CRITICAL QUALITY ATTRIBUTES (CQAs)
# ---------------------------------------------------------
with t4:
    st.markdown("### Critical Quality Attribute (CQA) Characterization")
    st.write("Evaluate post-translational modifications (Glycosylation) and Charge Variant distributions across selected lead clones.")
    
    col_m4, col_cqas = st.columns([1.2, 1])
    with col_m4:
        selected_wells_p4 = render_plate_map(st.session_state.plate_df, st.session_state.selected_format, mode="analytics", chart_key="map_phase4")
        
    with col_cqas:
        if not selected_wells_p4:
            st.info("👈 Click a clone on the plate map to view its glycoform and charge variant analytical profiles.")
        else:
            sel_w = selected_wells_p4[0]
            w_info = st.session_state.plate_df[st.session_state.plate_df['well'] == sel_w].iloc[0]
            
            if w_info['well_type'] in ['Sample', 'Pos Control']:
                st.markdown(f"#### CQA Analytics: `{w_info['clone_id']}` ({sel_w})")
                
                g0f = w_info['g0f_pct'] if w_info['g0f_pct'] > 0 else 72.4
                g1f = w_info['g1f_pct'] if w_info['g1f_pct'] > 0 else 15.1
                g2f = w_info['g2f_pct'] if w_info['g2f_pct'] > 0 else 5.3
                man5 = w_info['man5_pct'] if w_info['man5_pct'] > 0 else 7.2
                
                main_p = w_info['charge_main_pct'] if w_info['charge_main_pct'] > 0 else 68.2
                acidic_p = w_info['charge_acidic_pct'] if w_info['charge_acidic_pct'] > 0 else 22.4
                basic_p = w_info['charge_basic_pct'] if w_info['charge_basic_pct'] > 0 else 9.4
                
                glyco_df = pd.DataFrame({
                    'Glycoform': ['% G0F', '% G1F', '% G2F', '% High-Man5'],
                    'Abundance (%)': [g0f, g1f, g2f, man5]
                })
                fig_glyco = px.bar(
                    glyco_df, x='Glycoform', y='Abundance (%)',
                    title="N-Glycosylation Profile (LC-MS)",
                    color='Glycoform',
                    color_discrete_sequence=['#2E86C1', '#28B463', '#F39C12', '#E74C3C'],
                    text_auto='.1f'
                )
                fig_glyco.update_layout(showlegend=False, height=240, margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_glyco, use_container_width=True, key="cqa_glyco_chart")
                
                charge_df = pd.DataFrame({
                    'Variant': ['% Main Peak', '% Acidic', '% Basic'],
                    'Percentage (%)': [main_p, acidic_p, basic_p]
                })
                fig_charge = px.bar(
                    charge_df, x='Percentage (%)', y='Variant', orientation='h',
                    title="Charge Heterogeneity (iCE3 / cIEF)",
                    color='Variant',
                    color_discrete_sequence=['#1ABC9C', '#9B59B6', '#E67E22'],
                    text_auto='.1f'
                )
                fig_charge.update_layout(showlegend=False, height=220, margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_charge, use_container_width=True, key="cqa_charge_chart")
