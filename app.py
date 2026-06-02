"""
Champions League Tournament Predictor - Interactive Web Dashboard
Streamlit Application for Monte Carlo Simulation Results & Interactive Analysis

Author: Data Science Team
Date: May 30, 2026
Version: 1.0.0
"""

import streamlit as st
import pandas as pd
import json
import subprocess
import os
from pathlib import Path
import sys
from datetime import datetime
import warnings

# Suppress deprecation warnings for cleaner output
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

# Set page configuration
st.set_page_config(
    page_title="UCL Prediction Dashboard",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define project paths
PROJECT_ROOT = Path(__file__).parent
RESULTS_DIR = PROJECT_ROOT / "results"
PLOTS_DIR = RESULTS_DIR / "plots"
JSON_RESULTS = RESULTS_DIR / "tournament_simulation_results.json"
SIMULATION_SCRIPT = PROJECT_ROOT / "src" / "simulation" / "bracket.py"

# Custom CSS for a premium editorial analytics interface
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');

    :root {
        --bg: #0a0e14;
        --surface: #0f131a;
        --surface-2: #161d26;
        --surface-3: #1a2332;
        --text: #f8f9fa;
        --muted: #cbd5e1;
        --subtle: #94a3b8;
        --line: #2d3a4a;
        --line-strong: #3f4f63;
        --brand: #d4a76a;
        --brand-strong: #e8c896;
        --accent: #4a90e2;
        --ok: #48a869;
        --danger: #e85d5d;
    }

    .stApp {
        background:
            radial-gradient(960px 540px at 12% -10%, rgba(212, 167, 106, 0.12) 0%, transparent 64%),
            radial-gradient(1100px 720px at 100% 0%, rgba(74, 144, 226, 0.08) 0%, transparent 68%),
            var(--bg);
        color: var(--text);
        font-family: 'Manrope', sans-serif;
    }

    .block-container {
        max-width: 1400px;
        padding-top: 2.35rem;
        padding-bottom: 2.4rem;
    }

    .stAppDeployButton[data-testid="stAppDeployButton"] { display: none; }

    .hero {
        background:
            radial-gradient(700px 300px at 8% 8%, rgba(212, 167, 106, 0.2), rgba(212, 167, 106, 0) 70%),
            linear-gradient(130deg, #0f131a 0%, #161d26 100%);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 2.65rem 2rem 2.2rem;
        box-shadow: 0 18px 34px rgba(0, 0, 0, 0.35);
        animation: fadeInUp 0.4s ease-out;
    }

    .eyebrow {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--brand);
        margin-bottom: 0.45rem;
        font-weight: 500;
    }

    .hero-title {
        font-size: clamp(2.3rem, 4vw, 3.5rem);
        font-weight: 800;
        line-height: 1.1;
        letter-spacing: -0.02em;
        margin: 0.1rem 0 0.7rem;
        color: var(--text);
        text-shadow: 0 1px 8px rgba(0, 0, 0, 0.35);
    }

    .hero-subtitle {
        color: var(--muted);
        font-size: 1.125rem;
        line-height: 1.58;
        max-width: 66ch;
        margin: 0;
    }

    .section-label {
        font-family: 'IBM Plex Mono', monospace;
        color: var(--brand);
        font-size: 0.75rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin: 0.2rem 0 0.95rem;
    }

    .kpi-card {
        background: linear-gradient(135deg, var(--surface-3) 0%, var(--surface-2) 100%);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1.35rem 1.25rem 1.2rem;
        min-height: 172px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.32), inset 0 1px 0 rgba(212, 167, 106, 0.09);
        animation: fadeInUp 0.45s ease-out;
        transition: transform 0.2s ease-out, box-shadow 0.2s ease-out, border-color 0.2s ease-out;
    }

    .kpi-card:hover {
        transform: translateY(-4px);
        border-color: var(--line-strong);
        box-shadow: 0 12px 26px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(212, 167, 106, 0.22);
    }

    .kpi-title {
        font-family: 'IBM Plex Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--subtle);
        font-size: 0.74rem;
        margin-bottom: 0.68rem;
    }

    .kpi-main {
        font-size: clamp(1.3rem, 1.6vw, 1.9rem);
        font-weight: 700;
        color: var(--text);
        line-height: 1.2;
        margin-bottom: 0.45rem;
        background-image: linear-gradient(90deg, var(--text), var(--brand-strong), var(--text));
        background-size: 250% auto;
        background-clip: text;
        -webkit-background-clip: text;
        color: transparent;
        animation: shimmerPulse 2.6s ease-in-out infinite;
    }

    .kpi-sub {
        color: var(--muted);
        font-size: 0.875rem;
        font-weight: 500;
    }

    .panel {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1.5rem 1.35rem 1.15rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.28);
        animation: fadeInUp 0.4s ease-out;
    }

    .notes {
        background: rgba(212, 167, 106, 0.09);
        border-left: 3px solid var(--brand);
        color: var(--muted);
        padding: 0.65rem 0.85rem;
        border-radius: 8px;
        font-size: 0.88rem;
        margin-bottom: 1rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.1rem;
        border-bottom: 1px solid var(--line);
        padding-bottom: 0.45rem;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 0;
        min-height: 2.4rem;
        padding: 0.3rem 1.25rem;
        color: var(--subtle);
        border: none;
        border-bottom: 2px solid transparent;
        transition: color 0.2s ease-out, border-color 0.2s ease-out;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text);
        border-bottom-color: rgba(212, 167, 106, 0.45);
    }

    .stTabs [aria-selected="true"] {
        background: transparent;
        border-color: transparent;
        border-bottom: 2px solid var(--brand);
        color: var(--text);
    }

    .stButton > button {
        border-radius: 12px;
        border: 1px solid #c99858;
        background: linear-gradient(120deg, var(--brand), #e0bb86);
        color: #0a0e14;
        font-weight: 700;
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 22px rgba(212, 167, 106, 0.35), 0 0 0 1px rgba(212, 167, 106, 0.45);
    }

    .stButton > button:focus {
        outline: none;
        box-shadow: 0 0 0 2px rgba(212, 167, 106, 0.75);
    }

    .stDownloadButton > button {
        border-radius: 12px;
        background: transparent;
        border: 1px solid var(--line-strong);
        color: var(--brand);
    }

    .stDownloadButton > button:hover {
        border-color: var(--brand);
        background: rgba(212, 167, 106, 0.08);
    }

    [data-testid="stSlider"] * {
        color: var(--muted) !important;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1218 0%, #0a0e14 100%);
        border-left: 1px solid #1a2332;
    }

    [data-testid="stSidebar"] * {
        color: var(--muted) !important;
    }

    [data-testid="stSidebar"] h3 {
        color: var(--brand) !important;
        letter-spacing: 0.08em;
        font-family: 'IBM Plex Mono', monospace;
        text-transform: uppercase;
    }

    [data-testid="stSidebar"] .stCaption {
        color: var(--subtle) !important;
    }

    [data-testid="stSidebar"] li {
        margin-bottom: 0.2rem;
    }

    .footer {
        margin-top: 0.6rem;
        color: var(--subtle);
        font-size: 0.83rem;
        line-height: 1.7;
        text-align: center;
        font-family: 'IBM Plex Mono', monospace;
    }

    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(18px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes shimmerPulse {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .stAlert {
        border: 1px solid var(--line);
        border-radius: 10px;
        background: var(--surface-2);
        color: var(--muted);
    }

    .stDataFrame {
        border: 1px solid var(--line);
        border-radius: 12px;
        overflow: hidden;
    }

    @media (max-width: 768px) {
        .hero {
            padding: 2rem 1.35rem 1.55rem;
        }

        .kpi-card {
            min-height: 132px;
        }

        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 1.5rem;
        }
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

@st.cache_data(show_spinner=False)
def load_json_results():
    """Load simulation results from JSON file with error handling."""
    try:
        if not JSON_RESULTS.exists():
            st.warning("⚠️ No simulation results found. Please run a simulation first.")
            return None
        
        with open(JSON_RESULTS, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        st.error(f"❌ Error loading JSON results: {str(e)}")
        return None

def load_image(image_path):
    """Load image file with error handling."""
    try:
        if not os.path.exists(image_path):
            st.warning(f"⚠️ Image not found: {image_path}")
            return None
        return image_path
    except Exception as e:
        st.error(f"❌ Error loading image: {str(e)}")
        return None

@st.cache_data(show_spinner=False)
def create_data_table(results_data):
    """Create a formatted DataFrame from JSON results."""
    try:
        if not results_data or not isinstance(results_data, dict):
            return None

        # Expected schema:
        # {
        #   "num_simulations": ...,
        #   "champions": {...},
        #   "runners_up": {...},
        #   "finalists": {...},
        #   "semifinalists": {...},
        #   "probabilities": {
        #       "champions": {...},
        #       "runners_up": {...},
        #       "finalists": {...},
        #       "semifinalists": {...}
        #   }
        # }

        probs_block = results_data.get('probabilities', {})
        champions = probs_block.get('champions', {}) if isinstance(probs_block, dict) else {}
        finalists = probs_block.get('finalists', {}) if isinstance(probs_block, dict) else {}
        semifinalists = probs_block.get('semifinalists', {}) if isinstance(probs_block, dict) else {}
        quarterfinalists = probs_block.get('quarterfinalists', {}) if isinstance(probs_block, dict) else {}

        # Quarterfinalist probabilities are expected from backend.
        # Robust key parsing chain:
        #   1) 'P_Quarterfinal'
        #   2) 'quarterfinalist'
        #   3) 'quarterfinalists'
        quarterfinalist_prob = {team: 0.0 for team in champions.keys()}

        qf_block = probs_block
        if isinstance(qf_block, dict):
            qf_val = (
                qf_block.get('P_Quarterfinal')
                if 'P_Quarterfinal' in qf_block
                else (
                    qf_block.get('quarterfinalist')
                    if 'quarterfinalist' in qf_block
                    else qf_block.get('quarterfinalists')
                )
            )

            if isinstance(qf_val, dict) and len(qf_val) > 0:
                # Ensure full coverage for all champion teams; default to 0.0 if missing.
                quarterfinalist_prob = {
                    team: float(qf_val.get(team, 0.0)) if qf_val is not None else 0.0
                    for team in champions.keys()
                }




        teams = []
        all_teams = set(champions.keys()) | set(finalists.keys()) | set(semifinalists.keys())
        for team_name in sorted(all_teams):
            teams.append({
                'Team': team_name,
                'P(Champion)': float(champions.get(team_name, 0.0)),
                'P(Finalist)': float(finalists.get(team_name, 0.0)),
                'P(Semifinalist)': float(semifinalists.get(team_name, 0.0)),
                'P(Quarterfinalist)': float(quarterfinalist_prob.get(team_name, 1.0))
            })

        df = pd.DataFrame(teams)
        df = df.sort_values('P(Champion)', ascending=False).reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"❌ Error creating data table: {str(e)}")
        return None


def run_simulation(num_iterations):
    """Execute the tournament simulation script with specified iterations."""
    try:
        # Construct command
        env = os.environ.copy()
        env['NUM_ITERATIONS'] = str(num_iterations)
        
        # Call the simulation script
        result = subprocess.run(
            [sys.executable, str(SIMULATION_SCRIPT)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            env=env,
            timeout=600  # 10-minute timeout
        )
        
        if result.returncode != 0:
            st.error(f"❌ Simulation failed with error:\n{result.stderr}")
            return False
        
        return True
    except subprocess.TimeoutExpired:
        st.error("❌ Simulation timed out (exceeded 10 minutes)")
        return False
    except Exception as e:
        st.error(f"❌ Error running simulation: {str(e)}")
        return False

def get_top_contender(results_data):
    """Get the team with highest championship probability."""
    if not results_data:
        return None, None

    # Simulation JSON structure is:
    # { ..., "probabilities": {"champions": {...}, ... } }
    probs_block = results_data.get('probabilities', {}) if isinstance(results_data, dict) else {}
    champions = probs_block.get('champions', {}) if isinstance(probs_block, dict) else {}

    max_team = None
    max_prob = 0.0
    for team, champion_prob in champions.items():
        try:
            p = float(champion_prob)
        except Exception:
            p = 0.0
        if p > max_prob:
            max_prob = p
            max_team = team

    return max_team, max_prob


def get_highest_elo(results_data):
    """Get team with highest Elo rating (from team registry)."""
    # Note: This could be enhanced by reading from processed_features.csv
    # For now, return a static value based on last known state
    elo_map = {
        "Real Madrid": 1598.3,
        "Liverpool": 1584.3,
        "Inter Milan": 1578.3,
        "Porto": 1547.5,
        "Borussia Dortmund": 1530.2,
        "Ajax": 1523.2,
        "Napoli": 1514.8,
        "Juventus": 1513.1,
        "Chelsea": 1511.2,
        "Paris Saint-Germain": 1500.7,
        "Barcelona": 1498.0,
        "AC Milan": 1480.0,
        "Atlético Madrid": 1454.9,
        "Bayern Munich": 1425.1,
        "Manchester United": 1397.3,
        "Manchester City": 1369.6
    }
    
    max_team = max(elo_map, key=elo_map.get)
    return max_team, elo_map[max_team]

def calculate_hhi(results_data):
    """Calculate Herfindahl-Hirschman Index (concentration measure)."""
    if not results_data or not isinstance(results_data, dict):
        return None

    probs_block = results_data.get('probabilities', {})
    champions = probs_block.get('champions', {}) if isinstance(probs_block, dict) else {}

    probs = []
    for _, champion_prob in champions.items():
        try:
            probs.append(float(champion_prob))
        except Exception:
            probs.append(0.0)

    hhi = sum(p ** 2 for p in probs)
    return hhi


def render_kpi_card(title, main_value, sub_value):
    """Render custom KPI cards with consistent visual hierarchy."""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-main">{main_value}</div>
            <div class="kpi-sub">{sub_value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================================
# PAGE LAYOUT - HEADER & OVERVIEW
# ============================================================================

st.markdown(
    """
    <section class="hero">
        <div class="eyebrow">Monte Carlo Simulation</div>
        <h1 class="hero-title">Champions League Predictor</h1>
        <p class="hero-subtitle">
            Data-driven probabilistic tournament predictions powered by advanced simulation methodology.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ============================================================================
# KEY PERFORMANCE INDICATORS (KPIs)
# ============================================================================

st.markdown('<div class="section-label">Snapshot Metrics</div>', unsafe_allow_html=True)

# Load results for KPI display
results_data = load_json_results()

if results_data:
    col1, col2, col3, col4 = st.columns(4)
    
    # KPI 1: Top Contender
    top_team, top_prob = get_top_contender(results_data)
    with col1:
        render_kpi_card(
            "Top contender",
            top_team if top_team else "N/A",
            f"{top_prob * 100:.2f}% championship chance" if top_prob else "No probability data",
        )
    
    # KPI 2: Highest Elo
    highest_elo_team, highest_elo = get_highest_elo(results_data)
    with col2:
        render_kpi_card(
            "Highest Elo",
            highest_elo_team if highest_elo_team else "N/A",
            f"{highest_elo:.1f} Elo" if highest_elo else "No Elo available",
        )
    
    # KPI 3: Competitiveness Index
    hhi = calculate_hhi(results_data)
    with col3:
        render_kpi_card(
            "Competitiveness index",
            f"{hhi:.4f}" if hhi else "N/A",
            "Lower score means a more open title race" if hhi else "Not enough data",
        )
    
    # KPI 4: Simulation Stats
    with col4:
        teams_count = 0
        probs_block = results_data.get('probabilities', {}) if isinstance(results_data, dict) else {}
        if isinstance(probs_block, dict):
            teams_count = len(probs_block.get('champions', {}))
        render_kpi_card(
            "Teams analyzed",
            str(teams_count if teams_count else 16),
            "Complete tournament field",
        )
else:
    st.warning("⚠️ Load data by running a simulation first")

st.divider()

# ============================================================================
# INTERACTIVE SIMULATION CONTROL
# ============================================================================

st.markdown('<div class="section-label">Simulation Control</div>', unsafe_allow_html=True)
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown(
    '<div class="notes">Runs bracket simulation, regenerates visual diagnostics, and refreshes results. Typical runtime: 30 to 120 seconds.</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns([3, 1])

with col1:
    num_iterations = st.slider(
        "SIMULATION ITERATIONS",
        min_value=1000,
        max_value=20000,
        value=5000,
        step=1000,
        help="More iterations = more accurate probabilities but longer execution time"
    )

with col2:
    run_button = st.button(
        "RUN NEW SIMULATION",
        width="stretch",
        type="primary"
    )

# Handle simulation execution
if run_button:
    with st.spinner(f"⏳ Running {num_iterations:,} tournament simulations... This may take a few minutes."):
        success = run_simulation(num_iterations)
        if success:
            st.success(f"✅ Simulation completed successfully with {num_iterations:,} iterations!")
            st.balloons()

            # Regenerate static PNG plots so the four visualization tabs reflect the new simulation.
            try:
                import subprocess as _subprocess
                _subprocess.run(
                    [sys.executable, str(PROJECT_ROOT / "src" / "visualization" / "reports.py")],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=600
                )
            except Exception:
                # Plots are non-critical; JSON + table should still work.
                pass

            # Reload data and refresh the page
            results_data = load_json_results()
            st.rerun()
        else:
            st.error("❌ Simulation failed. Please check the logs.")

st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ============================================================================
# STATIC VISUALIZATIONS GALLERY
# ============================================================================

st.markdown('<div class="section-label">Visual Diagnostics</div>', unsafe_allow_html=True)

# Create tabs for different visualizations
tab1, tab2, tab3, tab4 = st.tabs([
    "Championship odds",
    "Stage progression",
    "Elimination shape",
    "Leading contenders"
])

with tab1:
    st.markdown("#### Championship Probability Distribution")
    st.markdown("Horizontal bar chart showing all 16 teams ranked by their probability of winning the tournament. Top quartile highlighted in red.")
    image_path = load_image(str(PLOTS_DIR / "championship_probabilities.png"))
    if image_path:
        st.image(image_path, width="stretch")
    else:
        st.warning("⚠️ Plot not available")

with tab2:
    st.markdown("#### Tournament Stage Progression Heatmap")
    st.markdown("16×3 heatmap showing team advancement probabilities across Semifinal → Final → Champion stages. Red indicates high probability, green indicates low.")
    image_path = load_image(str(PLOTS_DIR / "progression_heatmap.png"))
    if image_path:
        st.image(image_path, width="stretch")
    else:
        st.warning("⚠️ Plot not available")

with tab3:
    st.markdown("#### Drop-off Analysis: Elimination Rates")
    st.markdown("Left: Expected team count per tournament round. Right: Probability distribution box plots showing advancement variance across teams.")
    image_path = load_image(str(PLOTS_DIR / "dropoff_analysis.png"))
    if image_path:
        st.image(image_path, width="stretch")
    else:
        st.warning("⚠️ Plot not available")

with tab4:
    st.markdown("#### Top 8 Contenders Progression")
    st.markdown("Grouped bar chart comparing top 8 teams across three tournament stages (Semifinal, Final, Champion).")
    image_path = load_image(str(PLOTS_DIR / "top_contenders.png"))
    if image_path:
        st.image(image_path, width="stretch")
    else:
        st.warning("⚠️ Plot not available")

st.divider()

# ============================================================================
# DETAILED DATA EXPLORER
# ============================================================================

st.markdown('<div class="section-label">Data Explorer</div>', unsafe_allow_html=True)

if results_data:
    data_table = create_data_table(results_data)
    if data_table is not None:
        st.markdown(
            "<div class='notes'>Complete probability breakdown for all teams across quarterfinal, semifinal, final, and champion outcomes.</div>",
            unsafe_allow_html=True,
        )
        
        # Display as sortable table
        st.dataframe(
            data_table,
            width="stretch",
            height=400,
            hide_index=True
        )
        
        # Download CSV option
        csv = data_table.to_csv(index=False)
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name=f"champions_league_predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ Unable to parse data table")
else:
    st.info("ℹ️ Run a simulation to see the detailed data explorer")

st.divider()

# ============================================================================
# SIDEBAR - How to use
# ============================================================================

with st.sidebar:
    st.markdown("### How To Use")
    st.caption("Quick-start flow for simulation and interpretation.")
    st.markdown("""
    1. Read the snapshot metrics for a quick state check.
    2. Set simulation iterations based on precision needs.
    3. Run the simulation to refresh probabilities and charts.
    4. Inspect visuals, then validate details in the table.
    """)
    st.markdown("### Tips")
    st.markdown("""
    - Use 5,000 for fast experimentation.
    - Use 10,000+ when comparing close contenders.
    - Inspect both champion and finalist probabilities before conclusions.
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()

st.markdown(
    """
    <div class="footer">
        UCL Prediction Dashboard · v2.0 · Powered by Monte Carlo Simulation
    </div>
    """,
    unsafe_allow_html=True,
)
