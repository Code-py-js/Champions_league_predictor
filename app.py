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

# Custom CSS for improved UI
st.markdown("""
    <style>
    /* Hide Streamlit default Deploy button (not needed for this project) */
    .stAppDeployButton[data-testid="stAppDeployButton"] { display: none; }

    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .kpi-value {
        font-size: 32px;
        font-weight: bold;
        margin: 10px 0;
    }
    .kpi-label {
        font-size: 14px;
        opacity: 0.9;
    }
    .header-title {
        text-align: center;
        color: #1f77b4;
        font-size: 48px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .subheader-text {
        text-align: center;
        color: #555;
        font-size: 16px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

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


# ============================================================================
# PAGE LAYOUT - HEADER & OVERVIEW
# ============================================================================

st.markdown(
    '<div class="header-title">🏆 UCL Monte Carlo Predictive Dashboard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subheader-text">Interactive Champions League Tournament Prediction Engine</div>',
    unsafe_allow_html=True
)

st.divider()

# ============================================================================
# KEY PERFORMANCE INDICATORS (KPIs)
# ============================================================================

st.markdown("### 📈 Key Performance Indicators")

# Load results for KPI display
results_data = load_json_results()

if results_data:
    col1, col2, col3, col4 = st.columns(4)
    
    # KPI 1: Top Contender
    top_team, top_prob = get_top_contender(results_data)
    with col1:
        st.metric(
            label="🥇 Top Contender",
            value=top_team if top_team else "N/A",
            delta=f"{top_prob*100:.2f}% P(Champion)" if top_prob else None
        )
    
    # KPI 2: Highest Elo
    highest_elo_team, highest_elo = get_highest_elo(results_data)
    with col2:
        st.metric(
            label="⭐ Highest Elo",
            value=highest_elo_team if highest_elo_team else "N/A",
            delta=f"{highest_elo:.1f} Elo" if highest_elo else None
        )
    
    # KPI 3: Competitiveness Index
    hhi = calculate_hhi(results_data)
    with col3:
        st.metric(
            label="🎲 Competitiveness Index (HHI)",
            value=f"{hhi:.4f}" if hhi else "N/A",
            delta="Lower = More Competitive" if hhi else None
        )
    
    # KPI 4: Simulation Stats
    with col4:
        st.metric(
            label="📊 Teams Analyzed",
            value="16",
            delta="All tournament participants"
        )
else:
    st.warning("⚠️ Load data by running a simulation first")

st.divider()

# ============================================================================
# INTERACTIVE SIMULATION CONTROL
# ============================================================================

st.markdown("### 🎮 Interactive Simulation Control")

col1, col2 = st.columns([3, 1])

with col1:
    num_iterations = st.slider(
        "Select number of tournament iterations:",
        min_value=1000,
        max_value=20000,
        value=10000,
        step=1000,
        help="More iterations = more accurate probabilities but longer execution time"
    )

with col2:
    run_button = st.button(
        "🚀 Run New Simulation",
        use_container_width=True,
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

st.divider()

# ============================================================================
# STATIC VISUALIZATIONS GALLERY
# ============================================================================

st.markdown("### 📊 Visualization Gallery")

# Create tabs for different visualizations
tab1, tab2, tab3, tab4 = st.tabs([
    "🏆 Championship Probabilities",
    "🔥 Tournament Progression",
    "📉 Elimination Analysis",
    "⭐ Top Contenders"
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

st.markdown("### 📋 Detailed Data Explorer")

if results_data:
    data_table = create_data_table(results_data)
    if data_table is not None:
        st.markdown("**Complete probability breakdown for all 16 teams across tournament stages**")
        
        # Display as sortable table
        st.dataframe(
            data_table,
            use_container_width=True,
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
    st.markdown("### How to use this dashboard")
    st.markdown("""
    1. Check the **KPIs** at the top.
    2. Use the slider to set **simulation iterations**.
    3. Click **Run New Simulation** to regenerate results + plots.
    4. View charts in the **visualization tabs** and inspect probabilities in the table.
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()

footer_text = """
---
**Champions League Tournament Predictor** | *Task 7: Interactive Web Dashboard*
📊 Dashboard Version 1.0.0 | 🏆 UCL Prediction Engine
"""

st.markdown(footer_text, unsafe_allow_html=False)
