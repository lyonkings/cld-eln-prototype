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

if 'construct_library' not in st.session_state:
    st.session_state.construct_library = {
        "Preset A (Equimolar 1:1)": {
            'substance': 'SUB-0000000025 (anti-CD20 rituximab-fab)',
            'host': 'HST-CHO-S (CHO-K1 derivative)',
            'vector': 'RTX-RD-SEQ-001 (Polycistronic / GS)',
            'ratio': '1:1'
        },
        "Preset B (LC Excess 1:2)": {
            'substance': 'SUB-0000000025 (anti-CD20 rituximab-fab)',
            'host': 'HST-CHO-S (CHO-K1 derivative)',
            'vector': 'RTX-RD-SEQ-001 (Polycistronic / GS)',
            'ratio': '1:2'
        },
        "Preset C (Bispecific 2:1)": {
            'substance': 'SUB-0000000026 (anti-HER2 bispecific)',
            'host': 'HST-CHO-DG44 (DHFR deficient)',
            'vector': 'RTX-RD-SEQ-002 (Monocistronic / DHFR)',
            'ratio': '2:1'
        }
    }

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
                'parent_384_well': None,
                'ambr_vessel_id': None,
                'preset_name': 'None',
                'substance': 'None', 'host': 'None', 'vector': 'None', 
                'lc_hc_ratio': 'None',
                'locus': 'None', 'sgrna': 'None', 'cas': 'None', 
                'off_target_score': 0.0,
                'monoclonality_verified': False,
                'vcd': 0.0, 'titer': 0.0,
                'g0f_pct': 0.0, 'g1f_pct': 0.0, 'g2f_pct': 0.0, 'man5_pct': 0.0,
                'charge_main_pct': 0.0, 'charge_acidic_pct': 0.0, 'charge_basic_pct': 0.0,
                'ambr_ph': 7.10, 'ambr_do_pct': 40.0, 'ambr_temp_c': 36.5
            })
    return pd.DataFrame(data)

if 'selected_format' not in st.session_state:
    st.session_state.selected_format = "96-Well Plate (12x8)"

if 'plate_df' not in st.session_state or 'parent_384_well' not in st.session_state.plate_df.columns:
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
    
    cols = ['Project', 'Study', 'Campaign', 'well', 'clone_id', 'parent_beacon_pen', 'parent_384_well', 'ambr_vessel_id',
            'preset_name', 'substance', 'host', 'vector', 'lc_hc_ratio', 'vcd', 'titer', 
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
    
    def build_hover_text(r):
        if r['well_type'] in ['Sample', 'Pos Control', 'Neg Control']:
            return (
                f"<b>{r['clone_id'] or r['well']} ({r['well']})</b><br>"
                f"Type: {r['well_type']}<br>"
                f"<b>Preset:</b> {r['preset_name']}<br>"
                f"<b>Substance:</b> {r['substance']}<br>"
                f"<b>LC:HC Ratio:</b> {r['lc_hc_ratio']}<br>"
                f"<b>VCD:</b> {r['vcd']} x10⁶/mL<br>"
                f"<b>Titer:</b> {r['titer']} mg/L"
            )
        elif r['well_type'] == 'Blank':
            return f"<b>Well {r['well']}</b><br>Type: Blank"
        else:
            return f"<b>Well {r['well']}</b><br>Type: Unassigned"

    hover_text = df.apply(build_hover_text, axis=1).tolist()

    fig = go.Figure(data=go.Scatter(
        x=df['col'], y=df['row'],
        mode='markers+text', 
        text=df['well'] if "384" not in format_name else None, 
        customdata=df['well'].tolist(),
        textfont=dict(color=text_colors, size=9 if "384" in format_name else 11, family="Arial Black"),
        marker=dict(size=config["marker_size"], color=colors, line=dict(width=1 if "384" in format_name else 2, color='#BDC3C7')),
        # Visual feedback: dims unselected wells so the user knows their click registered
        selected=dict(marker=dict(opacity=1.0)),
        unselected=dict(marker=dict(opacity=0.3)),
        hoverinfo='text', hovertext=hover_text
    ))

    fig.update_layout(
        xaxis=dict(tickmode='linear', tick0=1, dtick=1, range=config["x_range"], side='top', showgrid=False, zeroline=False),
        yaxis=dict(autorange='reversed', tickmode='array', tickvals=config["rows"], showgrid=False, zeroline=False),
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=20, r=20, t=30, b=20), height=520,
        clickmode='event+select',
        dragmode='pan', # Setting to pan prevents the 0-pixel box glitch and restores smooth clicking
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
    "🧬 Phase 1: Construct Library", 
    "🧫 Phase 2: Vessel & Plate Designer", 
    "🌳 Phase 3: Lineage & AMBR", 
    "📈 Phase 4: Critical Quality Attributes"
])

# ---------------------------------------------------------
# PHASE 1: CONSTRUCT LIBRARY
# ---------------------------------------------------------
with t1:
    st.markdown("### Upstream Construct Engineering & Registry")
    st.write("Save and manage construct blueprints with varying plasmid ratios to assign across your microplates.")
    
    c1, c2 = st.columns([1.2, 1])
    with c1:
        with st.form("add_construct_form"):
            st.markdown("**Add / Save New Construct Preset**")
            preset_title = st.text_input("Preset Name", value="Preset D (Custom Ratio)")
            substance = st.selectbox("Target Substance", ["SUB-0000000025 (anti-CD20 rituximab-fab)", "SUB-0000000026 (anti-HER2 bispecific)"])
            host = st.selectbox("Host Cell Line", ["HST-CHO-S (CHO-K1 derivative)", "HST-CHO-DG44 (DHFR deficient)"])
            vector_type = st.selectbox("Vector System", ["RTX-RD-SEQ-001 (Polycistronic / GS)", "RTX-RD-SEQ-002 (Monocistronic / DHFR)"])
            
            lc_hc_ratio = st.select_slider(
                "Light Chain to Heavy Chain (LC:HC) Plasmid Ratio",
                options=["1:3", "1:2", "1:1", "2:1", "3:1"],
                value="1:2"
            )
            
            if st.form_submit_button("➕ Save Preset to Construct Library"):
                st.session_state.construct_library[preset_title] = {
                    'substance': substance,
                    'host': host,
                    'vector': vector_type,
                    'ratio': lc_hc_ratio
                }
                st.success(f"Preset '{preset_title}' saved to construct library!")
                st.rerun()

    with c2:
        st.markdown("**Saved Construct Presets**")
        st.caption("These presets are available in Phase 2 for well assignment.")
        
        for name, details in st.session_state.construct_library.items():
            with st.expander(f"📌 {name}", expanded=True):
                st.markdown(f"**Substance:** `{details['substance']}`")
                st.markdown(f"**Host Line:** `{details['host']}`")
                st.markdown(f"**Vector System:** `{details['vector']}`")
                st.markdown(f"**LC:HC Ratio:** `{details['ratio']}`")

# ---------------------------------------------------------
# PHASE 2: PLATE DESIGNER
# ---------------------------------------------------------
with t2:
    col_form, col_map = st.columns([1, 2])
    current_config = PLATE_FORMATS[st.session_state.selected_format]
    
    # We render the map first in the right column so we can capture interactive selections
    with col_map:
        st.markdown(f"### Live Seeding Map ({st.session_state.selected_format})")
        st.caption("💡 **Tip:** Click any well, or hold **SHIFT** while clicking to select multiple wells instantly.")
        st.markdown("<span style='color:#196F3D'>■ Sample</span> | <span style='color:#2980B9'>■ Pos Control</span> | <span style='color:#E74C3C'>■ Neg Control</span> | <span style='color:#F1C40F'>■ Blank</span>", unsafe_allow_html=True)
        selected_wells_p2 = render_plate_map(st.session_state.plate_df, st.session_state.selected_format, mode="design", chart_key="map_phase2")

    # Form renders in the left column
    with col_form:
        st.markdown(f"### Bulk Layout Designer")
        
        target_mode = st.radio("Targeting Method", ["📍 Interactive Map Selection (Click/Shift-Click)", "🔲 Grid Range Selection"])
        
        if target_mode == "📍 Interactive Map Selection (Click/Shift-Click)":
            if len(selected_wells_p2) > 0:
                st.success(f"**{len(selected_wells_p2)} wells currently selected on the map.**")
            else:
                st.info("👈 Click or SHIFT+Click wells on the map to target them.")
        else:
            c_r1, c_r2 = st.columns(2)
            start_row = c_r1.selectbox("Start Row", current_config["rows"], index=0)
            end_row = c_r2.selectbox("End Row", current_config["rows"], index=len(current_config["rows"])-1)
            
            c_c1, c_c2 = st.columns(2)
            start_col = c_c1.selectbox("Start Column", current_config["cols"], index=0)
            end_col = c_c2.selectbox("End Column", current_config["cols"], index=len(current_config["cols"])-1)
        
        st.divider()
        well_type = st.selectbox("Well Designation", ["Sample", "Pos Control", "Neg Control", "Blank", "Unassigned"])
        
        # CONDITIONAL UI LOGIC: Only show blueprints for actual active Samples
        if well_type == "Sample":
            selected_preset_key = st.selectbox("Select Construct Blueprint from Phase 1 Library", list(st.session_state.construct_library.keys()))
        else:
            st.info(f"🧬 **{well_type}** selected. DNA construct blueprints are inherently not applied to blanks or reference controls.")
            selected_preset_key = None
        
        if st.button("Apply Designation to Target Wells", type="primary", use_container_width=True):
            df = st.session_state.plate_df
            
            # Determine which wells we are masking
            if target_mode == "📍 Interactive Map Selection (Click/Shift-Click)":
                if not selected_wells_p2:
                    st.warning("No wells selected on the map. Please select wells first.")
                    st.stop()
                mask = df['well'].isin(selected_wells_p2)
            else:
                # Handle backwards ranges safely (e.g. if user selects End Row A and Start Row H)
                rows_list = current_config["rows"]
                r1, r2 = rows_list.index(start_row), rows_list.index(end_row)
                r_min, r_max = min(r1, r2), max(r1, r2)
                
                cols_list = current_config["cols"]
                c1, c2 = cols_list.index(start_col), cols_list.index(end_col)
                c_min, c_max = min(c1, c2), max(c1, c2)
                
                selected_rows = rows_list[r_min:r_max+1]
                selected_cols = cols_list[c_min:c_max+1]
                mask = df['row'].isin(selected_rows) & df['col'].isin(selected_cols)
            
            # Apply Logic
            df.loc[mask, 'well_type'] = well_type
            
            if well_type == 'Sample':
                chosen_preset = st.session_state.construct_library[selected_preset_key]
                df.loc[mask, 'preset_name'] = selected_preset_key
                df.loc[mask, 'lc_hc_ratio'] = chosen_preset['ratio']
                df.loc[mask, 'substance'] = chosen_preset['substance']
                df.loc[mask, 'host'] = chosen_preset['host']
                df.loc[mask, 'vector'] = chosen_preset['vector']
            
            elif well_type in ['Pos Control', 'Neg Control']:
                df.loc[mask, 'preset_name'] = 'Historical Reference' if well_type == 'Pos Control' else 'Mock/Untransfected'
                df.loc[mask, 'substance'] = 'Reference Standard' if well_type == 'Pos Control' else 'None'
                df.loc[mask, 'host'] = 'HST-CHO-S (Reference Bank)' if well_type == 'Pos Control' else 'HST-CHO-S (Wildtype)'
                df.loc[mask, 'vector'] = 'None'
                df.loc[mask, 'lc_hc_ratio'] = 'N/A'
            
            else: # Blank / Unassigned
                df.loc[mask, 'preset_name'] = 'Media Only' if well_type == 'Blank' else 'None'
                df.loc[mask, 'substance'] = 'None'
                df.loc[mask, 'host'] = 'None'
                df.loc[mask, 'vector'] = 'None'
                df.loc[mask, 'lc_hc_ratio'] = 'None'

            if well_type in ['Sample', 'Pos Control', 'Neg Control']:
                df.loc[mask, 'vcd'] = 0.0
                df.loc[mask, 'titer'] = 0.0
                
                for idx in df[mask].index:
                    well_name = df.loc[idx, 'well']
                    if df.loc[idx, 'clone_id'] is None:
                        prefix = "CLN" if well_type == 'Sample' else ("CTRL-POS" if well_type == 'Pos Control' else "CTRL-NEG")
                        df.loc[idx, 'clone_id'] = f"{prefix}-{well_name}-{random.randint(1000,9999)}"
                        df.loc[idx, 'parent_beacon_pen'] = f"BCN-PEN-{random.randint(100,999)}"
                        
                        rand_row_384 = random.choice(list('ABCDEFGHIJKLMNOP'))
                        rand_col_384 = random.randint(1, 24)
                        df.loc[idx, 'parent_384_well'] = f"384-Well-{rand_row_384}{rand_col_384}"
                        
                        df.loc[idx, 'ambr_vessel_id'] = f"AMBR15-Vessel-{well_name}"
                        
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
                df.loc[mask, 'clone_id'] = None
                df.loc[mask, 'parent_beacon_pen'] = None
                df.loc[mask, 'parent_384_well'] = None
                df.loc[mask, 'ambr_vessel_id'] = None
                df.loc[mask, 'vcd'] = 0.0
                df.loc[mask, 'titer'] = 0.0
                
            st.session_state.plate_df = df
            st.rerun()

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
            
            if w_data['well_type'] not in ['Sample', 'Pos Control', 'Neg Control']:
                st.warning("Selected well is a blank or unassigned.")
            else:
                is_bispecific = "bispecific" in str(w_data['substance']).lower() or "bispecific" in str(w_data['preset_name']).lower()
                modality_label = "Bispecific Dual-Vector Assembly" if is_bispecific else ("Historic Reference" if w_data['well_type'] == 'Pos Control' else "Monoclonal Single-Vector Pool")
                
                day0_detail = (
                    f"Co-transfected dual-vector single-cell penned in `{w_data['parent_beacon_pen'] or 'BCN-PEN-402'}` (Dual-Fluorescence Screened)"
                    if is_bispecific else
                    f"Single-cell penned in `{w_data['parent_beacon_pen'] or 'BCN-PEN-402'}`"
                )
                
                st.markdown(f"**Tracing Lineage for:** `{w_data['clone_id']}`")
                st.caption(f"Modality Track: **{modality_label}**")
                st.markdown(f"""
                * **Construct Blueprint:** `{w_data['preset_name']}` (Ratio: `{w_data['lc_hc_ratio']}`)
                * **Day 0 (Beacon Optofluidics):** {day0_detail}
                * **Day 7 (384-Well Expansion Plate):** Expanded from Beacon pen into `{w_data['parent_384_well'] or '384-Well-C12'}`
                * **Day 14 (Current Vessel):** Transitioned to Well `{w_data['well']}`
                * **Day 25 (AMBR 15 Microbioreactor):** Vessel `{w_data['ambr_vessel_id'] or f'AMBR15-Vessel-{sel_well}'}` (pH: {w_data['ambr_ph']}, DO: {w_data['ambr_do_pct']}%)
                """)
                
                if w_data['vcd'] == 0.0 and w_data['titer'] == 0.0 and w_data['well_type'] != 'Neg Control':
                    st.info("⏳ **Status:** Awaiting AMBR Bioreactor Data Ingestion (VCD: 0.0, Titer: 0.0)")
                else:
                    st.success(f"📊 **Ingested Data:** VCD = {w_data['vcd']} x10⁶ cells/mL | Titer = {w_data['titer']} mg/L")

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
                st.caption(f"Construct Blueprint: **{w_info['preset_name']}** (LC:HC Ratio **{w_info['lc_hc_ratio']}**)")
                
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
