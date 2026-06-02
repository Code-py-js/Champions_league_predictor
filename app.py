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
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

@st.cache_data(show_spinner=False)
def load_features_data():
    """Load processed_features.csv for dynamic team Elo extraction."""
    csv_path = PROJECT_ROOT / "data" / "processed_features.csv"
    try:
        if not csv_path.exists():
            return None
        df = pd.read_csv(csv_path)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception:
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


def get_highest_elo():
    """Get team with highest Elo rating, derived dynamically from processed_features.csv."""
    df = load_features_data()
    if df is None or df.empty:
        return None, None
    try:
        home_elos = df[['date', 'home_team', 'Home_Elo_Pre']].rename(
            columns={'home_team': 'team', 'Home_Elo_Pre': 'elo'}
        )
        away_elos = df[['date', 'away_team', 'Away_Elo_Pre']].rename(
            columns={'away_team': 'team', 'Away_Elo_Pre': 'elo'}
        )
        all_elos = pd.concat([home_elos, away_elos], ignore_index=True)
        latest_elos = all_elos.sort_values('date').groupby('team')['elo'].last()
        max_team = str(latest_elos.idxmax())
        max_elo = float(latest_elos.max())
        return max_team, max_elo
    except Exception:
        return None, None

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
# DYNAMIC CHART BUILDERS (Plotly — reads live from simulation JSON)
# ============================================================================

_DARK_LAYOUT = dict(
    plot_bgcolor='#0f131a',
    paper_bgcolor='#0f131a',
    font=dict(color='#cbd5e1', family='Manrope, sans-serif'),
)


def build_championship_chart(results_data):
    """Horizontal bar chart: all teams ranked by P(Champion)."""
    champions = results_data.get('probabilities', {}).get('champions', {})
    if not champions:
        return None
    df = pd.DataFrame({'Team': list(champions.keys()), 'prob': list(champions.values())})
    df = df.sort_values('prob', ascending=True)
    threshold = df['prob'].quantile(0.75)
    colors = ['#d4a76a' if p >= threshold else '#4a90e2' for p in df['prob']]
    max_prob = float(df['prob'].max())
    fig = go.Figure(go.Bar(
        x=df['prob'] * 100,
        y=df['Team'],
        orientation='h',
        marker_color=colors,
        text=[f"{p*100:.2f}%" for p in df['prob']],
        textposition='outside',
        textfont=dict(size=10, color='#cbd5e1'),
        cliponaxis=False,
    ))
    fig.update_layout(
        **_DARK_LAYOUT,
        title=dict(text='Championship Probability — All Teams', font=dict(size=14, color='#f8f9fa')),
        xaxis=dict(
            title='P(Champion) %',
            gridcolor='#2d3a4a',
            linecolor='#2d3a4a',
            range=[0, max_prob * 130],
        ),
        yaxis=dict(linecolor='#2d3a4a'),
        height=520,
        margin=dict(l=170, r=90, t=55, b=65),
    )
    fig.add_annotation(
        text="\u25a0 Top quartile (gold) \u2003 \u25a0 Rest (blue)",
        xref='paper', yref='paper', x=0, y=-0.10,
        showarrow=False, font=dict(size=11, color='#94a3b8'),
        align='left',
    )
    return fig


def build_progression_heatmap(results_data):
    """Heatmap: teams × stages — advancement probabilities."""
    probs = results_data.get('probabilities', {})
    stage_map = [
        ('Semifinal', 'semifinalists'),
        ('Final', 'finalists'),
        ('Champion', 'champions'),
    ]
    champions = probs.get('champions', {})
    if not champions:
        return None
    teams = sorted(champions.keys(), key=lambda t: champions.get(t, 0), reverse=True)
    z = []
    stage_labels = []
    for stage_label, key in stage_map:
        sp = probs.get(key, {})
        z.append([round(sp.get(t, 0) * 100, 2) for t in teams])
        stage_labels.append(stage_label)
    fig = go.Figure(go.Heatmap(
        z=z,
        x=teams,
        y=stage_labels,
        colorscale=[[0, '#161d26'], [0.5, '#b37b3e'], [1, '#d4a76a']],
        text=[[f"{v:.1f}%" for v in row] for row in z],
        texttemplate='%{text}',
        textfont=dict(size=9, color='#f8f9fa'),
        colorbar=dict(
            title=dict(text='%', font=dict(color='#94a3b8')),
            tickfont=dict(color='#94a3b8'),
            bgcolor='#0f131a',
            bordercolor='#2d3a4a',
        ),
        hoverongaps=False,
    ))
    fig.update_layout(
        **_DARK_LAYOUT,
        title=dict(text='Stage Advancement Probabilities per Team', font=dict(size=14, color='#f8f9fa')),
        xaxis=dict(tickangle=-45, linecolor='#2d3a4a', tickfont=dict(size=10)),
        yaxis=dict(linecolor='#2d3a4a', tickfont=dict(size=11)),
        height=340,
        margin=dict(l=90, r=20, t=55, b=160),
    )
    return fig


def build_dropoff_chart(results_data):
    """Two-panel: stage funnel bar + probability box plots per stage."""
    probs = results_data.get('probabilities', {})
    qf = list(probs.get('quarterfinalists', {}).values())
    sf = list(probs.get('semifinalists', {}).values())
    fi = list(probs.get('finalists', {}).values())
    ch = list(probs.get('champions', {}).values())
    if not ch:
        return None
    n = len(ch)
    stages = ['Rd. of 16', 'Quarterfinal', 'Semifinal', 'Final', 'Champion']
    counts = [n, sum(qf), sum(sf), sum(fi), sum(ch)]
    palette = ['#4a90e2', '#48a869', '#d4a76a', '#e85d5d', '#e8c896']
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=['Expected Teams per Round', 'Probability Spread by Stage'],
        horizontal_spacing=0.12,
    )
    fig.add_trace(go.Bar(
        x=stages,
        y=counts,
        marker_color=palette,
        text=[f"{c:.1f}" for c in counts],
        textposition='outside',
        textfont=dict(color='#cbd5e1', size=11),
        showlegend=False,
        cliponaxis=False,
    ), row=1, col=1)
    for stage_label, data, color in [
        ('QF', qf, '#48a869'),
        ('SF', sf, '#d4a76a'),
        ('Final', fi, '#4a90e2'),
        ('Champion', ch, '#e85d5d'),
    ]:
        fig.add_trace(go.Box(
            y=[p * 100 for p in data],
            name=stage_label,
            marker_color=color,
            line_color=color,
            boxmean='sd',
            showlegend=True,
        ), row=1, col=2)
    fig.update_layout(
        **_DARK_LAYOUT,
        height=440,
        margin=dict(l=55, r=30, t=70, b=60),
        yaxis=dict(title='Expected teams', gridcolor='#2d3a4a', linecolor='#2d3a4a'),
        yaxis2=dict(title='Probability %', gridcolor='#2d3a4a', linecolor='#2d3a4a'),
        xaxis=dict(linecolor='#2d3a4a'),
        xaxis2=dict(linecolor='#2d3a4a'),
        legend=dict(bgcolor='#161d26', bordercolor='#2d3a4a', x=1.01, y=1),
    )
    fig.update_annotations(font=dict(color='#94a3b8', size=12))
    return fig


def build_top_contenders_chart(results_data):
    """Grouped bar chart: top 8 teams × Semifinal / Final / Champion probabilities."""
    probs = results_data.get('probabilities', {})
    champions = probs.get('champions', {})
    if not champions:
        return None
    top_8 = [t for t, _ in sorted(champions.items(), key=lambda x: x[1], reverse=True)[:8]]
    stage_def = [
        ('Semifinal', 'semifinalists', '#4a90e2'),
        ('Final', 'finalists', '#d4a76a'),
        ('Champion', 'champions', '#e85d5d'),
    ]
    fig = go.Figure()
    for label, key, color in stage_def:
        stage_probs = probs.get(key, {})
        fig.add_trace(go.Bar(
            name=label,
            x=top_8,
            y=[stage_probs.get(t, 0) * 100 for t in top_8],
            marker_color=color,
            text=[f"{stage_probs.get(t, 0)*100:.1f}%" for t in top_8],
            textposition='outside',
            textfont=dict(size=9, color='#cbd5e1'),
            cliponaxis=False,
        ))
    fig.update_layout(
        **_DARK_LAYOUT,
        barmode='group',
        title=dict(text='Top 8 Contenders — Stage Probabilities', font=dict(size=14, color='#f8f9fa')),
        yaxis=dict(title='Probability %', gridcolor='#2d3a4a', linecolor='#2d3a4a'),
        xaxis=dict(tickangle=-25, linecolor='#2d3a4a'),
        height=440,
        margin=dict(l=55, r=30, t=55, b=100),
        legend=dict(bgcolor='#161d26', bordercolor='#2d3a4a'),
    )
    return fig


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
    highest_elo_team, highest_elo = get_highest_elo()
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

            # Clear data caches so the next render reads fresh simulation results.
            load_json_results.clear()
            load_features_data.clear()
            st.rerun()
        else:
            st.error("❌ Simulation failed. Please check the logs.")

st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ============================================================================
# INTERACTIVE VISUALIZATIONS (live Plotly charts from simulation JSON)
# ============================================================================

st.markdown('<div class="section-label">Visual Diagnostics</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "Championship odds",
    "Stage progression",
    "Elimination shape",
    "Leading contenders"
])

if results_data:
    with tab1:
        fig = build_championship_chart(results_data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ No championship data available — run a simulation first.")

    with tab2:
        fig = build_progression_heatmap(results_data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ No progression data available — run a simulation first.")

    with tab3:
        fig = build_dropoff_chart(results_data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ No drop-off data available — run a simulation first.")

    with tab4:
        fig = build_top_contenders_chart(results_data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ No top contenders data available — run a simulation first.")
else:
    with tab1:
        st.info("ℹ️ Run a simulation to generate interactive charts.")
    with tab2:
        st.info("ℹ️ Run a simulation to generate interactive charts.")
    with tab3:
        st.info("ℹ️ Run a simulation to generate interactive charts.")
    with tab4:
        st.info("ℹ️ Run a simulation to generate interactive charts.")

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
    # Dynamic simulation metadata
    if results_data:
        num_sims = results_data.get('num_simulations', 'N/A')
        st.markdown("### Last Simulation")
        st.markdown(
            f"**{num_sims:,} iterations**" if isinstance(num_sims, int) else f"**{num_sims} iterations**"
        )
        probs_sidebar = results_data.get('probabilities', {}).get('champions', {})
        if probs_sidebar:
            st.markdown("**Top 5 by P(Champion):**")
            top5 = sorted(probs_sidebar.items(), key=lambda x: x[1], reverse=True)[:5]
            for rank, (team, prob) in enumerate(top5, 1):
                st.markdown(f"{rank}. {team} — `{prob*100:.1f}%`")
        st.divider()

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
