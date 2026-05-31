"""
Champions League Tournament Visualization & Reporting

Generates publication-ready static plots analyzing Monte Carlo simulation results.
Creates bar charts and heatmaps showing tournament progression probabilities.

Author: Champions League Predictor
"""

import json
import logging
import os
import numpy as np
import pandas as pd

# Use non-interactive backend for matplotlib (no display required)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from pathlib import Path
from typing import Dict, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set style for publication-ready plots
sns.set_style("whitegrid")
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = '#f8f9fa'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10


class ChampionsLeagueReportGenerator:
    """
    Generates comprehensive visualization reports from Monte Carlo simulation results.
    """
    
    def __init__(self, results_file: str = 'results/tournament_simulation_results.json',
                 output_dir: str = 'results/plots'):
        """
        Initialize report generator.
        
        Args:
            results_file: Path to JSON simulation results
            output_dir: Directory for plot output
        """
        self.results_file = Path(results_file)
        self.output_dir = Path(output_dir)
        
        logger.info(f"{'='*80}")
        logger.info(f"CHAMPIONS LEAGUE VISUALIZATION & REPORTING")
        logger.info(f"{'='*80}")
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Output directory: {self.output_dir.absolute()}")
        
        # Load simulation results
        logger.info(f"\n📥 Loading simulation results from {self.results_file}...")
        self.results = self._load_results()
        logger.info(f"✓ Results loaded successfully")
        
        # Create DataFrame from results
        logger.info(f"\n📊 Creating data structures...")
        self.df = self._create_dataframe()
        logger.info(f"✓ DataFrame created: {self.df.shape[0]} teams, {self.df.shape[1]} columns")
    
    def _load_results(self) -> Dict:
        """Load JSON simulation results."""
        with open(self.results_file, 'r') as f:
            return json.load(f)
    
    def _create_dataframe(self) -> pd.DataFrame:
        """
        Create DataFrame from simulation results with tournament progression data.
        
        Returns:
            DataFrame with teams and their tournament probabilities at each stage
        """
        probs = self.results['probabilities']
        
        # Extract data for all teams
        data = []
        for team in probs['champions'].keys():
            data.append({
                'Team': team,
                'P(Champion)': probs['champions'].get(team, 0),
                'P(Runner-Up)': probs['runners_up'].get(team, 0),
                'P(Finalist)': probs['finalists'].get(team, 0),
                'P(Semifinalist)': probs['semifinalists'].get(team, 0),
                # Calculate intermediate stages
                'P(Final)': probs['finalists'].get(team, 0),  # Reached final
                'P(Semifinal)': probs['semifinalists'].get(team, 0),  # Reached semifinal
            })
        
        df = pd.DataFrame(data)
        
        # Sort by championship probability (descending)
        df = df.sort_values('P(Champion)', ascending=False).reset_index(drop=True)
        
        return df
    
    def plot_championship_probabilities(self) -> str:
        """
        Generate horizontal bar chart of championship probabilities.
        Highlights top quartile (top 4 teams) with distinct color.
        
        Returns:
            Path to saved figure
        """
        logger.info("\n📈 Generating Championship Probability Bar Chart...")
        
        # Prepare data
        df_sorted = self.df.sort_values('P(Champion)', ascending=True)
        teams = df_sorted['Team'].values
        probs = df_sorted['P(Champion)'].values
        
        # Create color palette - highlight top quartile
        colors = []
        top_quartile_threshold = self.df['P(Champion)'].quantile(0.75)
        
        for prob in probs:
            if prob >= top_quartile_threshold:
                colors.append('#d62728')  # Red for top quartile
            else:
                colors.append('#1f77b4')  # Blue for others
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 10), dpi=100)
        
        # Create bars
        bars = ax.barh(teams, probs, color=colors, edgecolor='black', linewidth=1.2)
        
        # Annotate bars with exact percentages
        for i, (team, prob) in enumerate(zip(teams, probs)):
            ax.text(prob + 0.001, i, f'{prob:.2%}', 
                   va='center', ha='left', fontsize=9, fontweight='bold')
        
        # Customize plot
        ax.set_xlabel('Probability of Winning Tournament', fontsize=12, fontweight='bold')
        ax.set_ylabel('Team', fontsize=12, fontweight='bold')
        ax.set_title('Champions League Tournament: Championship Probability Distribution\n(10,000 Monte Carlo Simulations)', 
                    fontsize=14, fontweight='bold', pad=20)
        
        # Set x-axis limits with padding
        ax.set_xlim(0, probs.max() * 1.15)
        
        # Add gridlines
        ax.grid(True, axis='x', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#d62728', edgecolor='black', label='Top Quartile (Q1)'),
            Patch(facecolor='#1f77b4', edgecolor='black', label='Other Teams')
        ]
        ax.legend(handles=legend_elements, loc='lower right', fontsize=10)
        
        # Tight layout
        plt.tight_layout()
        
        # Save figure
        output_path = self.output_dir / 'championship_probabilities.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"✓ Saved: {output_path}")
        
        plt.close()
        
        return str(output_path)
    
    def plot_progression_heatmap(self) -> str:
        """
        Generate tournament progression heatmap showing team drop-off rates.
        Y-axis sorted by championship probability (descending).
        Stages: Quarterfinal → Semifinal → Final → Champion
        
        Returns:
            Path to saved figure
        """
        logger.info("\n📊 Generating Tournament Progression Heatmap...")
        
        # Prepare data for heatmap
        # Tournament stages: Semifinal, Final, Champion (Quarterfinal is everyone)
        stages = ['P(Semifinal)', 'P(Final)', 'P(Champion)']
        stage_labels = ['Semifinal', 'Final', 'Champion']
        
        # Create data matrix (teams × stages)
        heatmap_data = self.df[['Team'] + stages].copy()
        heatmap_data = heatmap_data.set_index('Team')
        heatmap_data.columns = stage_labels
        
        # Sort by championship probability (descending) - already done in __init__
        heatmap_data = heatmap_data.iloc[::-1]  # Reverse for top-to-bottom display
        
        # Convert to percentages for display
        heatmap_display = heatmap_data * 100
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 12), dpi=100)
        
        # Create heatmap
        sns.heatmap(heatmap_display, 
                   annot=True, 
                   fmt='.2f',
                   cmap='RdYlGn',
                   cbar_kws={'label': 'Probability (%)'},
                   linewidths=0.5,
                   linecolor='gray',
                   vmin=0,
                   vmax=35,
                   ax=ax,
                   annot_kws={'fontsize': 9, 'fontweight': 'bold'})
        
        # Customize plot
        ax.set_title('Tournament Progression: Team Advancement Probabilities\nby Stage (10,000 Iterations)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Tournament Stage', fontsize=12, fontweight='bold')
        ax.set_ylabel('Team (Sorted by Championship Probability)', fontsize=12, fontweight='bold')
        
        # Rotate labels
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
        
        # Tight layout
        plt.tight_layout()
        
        # Save figure
        output_path = self.output_dir / 'progression_heatmap.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"✓ Saved: {output_path}")
        
        plt.close()
        
        return str(output_path)
    
    def plot_dropoff_analysis(self) -> str:
        """
        Generate drop-off rate analysis showing elimination at each stage.
        Shows how many teams are eliminated at each round.
        
        Returns:
            Path to saved figure
        """
        logger.info("\n📉 Generating Drop-off Analysis Chart...")
        
        # Calculate statistics
        total_teams = len(self.df)
        avg_semifinal = self.df['P(Semifinal)'].mean() * 100
        avg_final = self.df['P(Final)'].mean() * 100
        avg_champion = self.df['P(Champion)'].mean() * 100
        
        # Calculate team counts at each stage (expected value out of 16)
        stages_data = {
            'Round 1\n(16 teams)': 16,
            'Quarterfinal\n(8 teams)': avg_semifinal / 100 * 16 * 2,  # 8 survive QF
            'Semifinal\n(4 teams)': avg_final / 100 * 16 * 4,  # 4 survive to SF
            'Final\n(2 teams)': avg_champion / 100 * 16 * 8,  # 2 survive to Final
            'Champion\n(1 team)': avg_champion / 100 * 16 * 16,  # 1 wins
        }
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=100)
        
        # Left plot: Team advancement
        stages_list = list(stages_data.keys())
        teams_count = list(stages_data.values())
        
        bars = ax1.bar(range(len(stages_list)), teams_count, 
                      color=['#2ca02c', '#1f77b4', '#ff7f0e', '#d62728', '#9467bd'],
                      edgecolor='black', linewidth=1.2)
        
        # Annotate
        for i, (stage, count) in enumerate(zip(stages_list, teams_count)):
            ax1.text(i, count + 0.2, f'{count:.1f}', 
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax1.set_ylabel('Expected Number of Teams', fontsize=11, fontweight='bold')
        ax1.set_title('Average Team Advancement Through Tournament', fontsize=12, fontweight='bold')
        ax1.set_xticks(range(len(stages_list)))
        ax1.set_xticklabels(stages_list, fontsize=9)
        ax1.grid(True, axis='y', alpha=0.3)
        ax1.set_ylim(0, max(teams_count) * 1.15)
        
        # Right plot: Distribution of probabilities at each stage
        box_data = [
            self.df['P(Semifinal)'] * 100,
            self.df['P(Final)'] * 100,
            self.df['P(Champion)'] * 100
        ]
        
        bp = ax2.boxplot(box_data, labels=['Semifinal', 'Final', 'Champion'],
                        patch_artist=True, widths=0.6)
        
        # Color boxes
        colors_box = ['#1f77b4', '#ff7f0e', '#d62728']
        for patch, color in zip(bp['boxes'], colors_box):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax2.set_ylabel('Probability (%)', fontsize=11, fontweight='bold')
        ax2.set_title('Probability Distribution by Tournament Stage', fontsize=12, fontweight='bold')
        ax2.grid(True, axis='y', alpha=0.3)
        
        # Main title
        fig.suptitle('Tournament Drop-off Analysis: Team Elimination Through Rounds', 
                    fontsize=14, fontweight='bold', y=1.00)
        
        plt.tight_layout()
        
        # Save figure
        output_path = self.output_dir / 'dropoff_analysis.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"✓ Saved: {output_path}")
        
        plt.close()
        
        return str(output_path)
    
    def plot_top_contenders(self) -> str:
        """
        Generate comparison chart for top contenders at different stages.
        Shows how top teams' probabilities change across stages.
        
        Returns:
            Path to saved figure
        """
        logger.info("\n🏆 Generating Top Contenders Comparison Chart...")
        
        # Get top 8 teams
        top_teams = self.df.head(8)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 7), dpi=100)
        
        # Prepare data
        x = np.arange(len(top_teams))
        width = 0.2
        
        # Plot bars for each stage
        stage_data = [
            ('P(Semifinal)', 'Semifinal', '#1f77b4', 0),
            ('P(Final)', 'Final', '#ff7f0e', 1),
            ('P(Champion)', 'Champion', '#d62728', 2)
        ]
        
        for col_name, stage_name, color, offset in stage_data:
            values = top_teams[col_name].values * 100
            ax.bar(x + offset * width, values, width, label=stage_name, 
                  color=color, edgecolor='black', linewidth=0.8)
        
        # Customize plot
        ax.set_ylabel('Probability (%)', fontsize=12, fontweight='bold')
        ax.set_xlabel('Team', fontsize=12, fontweight='bold')
        ax.set_title('Top Contenders: Tournament Stage Probabilities\n(Top 8 Teams by Championship Odds)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x + width)
        ax.set_xticklabels(top_teams['Team'].values, rotation=45, ha='right')
        ax.legend(loc='upper right', fontsize=11)
        ax.grid(True, axis='y', alpha=0.3)
        ax.set_ylim(0, 35)
        
        # Tight layout
        plt.tight_layout()
        
        # Save figure
        output_path = self.output_dir / 'top_contenders.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"✓ Saved: {output_path}")
        
        plt.close()
        
        return str(output_path)
    
    def generate_all_reports(self) -> Dict[str, str]:
        """
        Generate all visualization reports.
        
        Returns:
            Dictionary mapping report names to file paths
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"GENERATING ALL VISUALIZATION REPORTS...")
        logger.info(f"{'='*80}")
        
        reports = {
            'Championship Probabilities': self.plot_championship_probabilities(),
            'Tournament Progression Heatmap': self.plot_progression_heatmap(),
            'Drop-off Analysis': self.plot_dropoff_analysis(),
            'Top Contenders': self.plot_top_contenders(),
        }
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ ALL REPORTS GENERATED SUCCESSFULLY")
        logger.info(f"{'='*80}\n")
        
        return reports
    
    def generate_summary_statistics(self) -> Dict:
        """
        Generate summary statistics from simulation data.
        
        Returns:
            Dictionary with summary metrics
        """
        logger.info("\n📊 Generating Summary Statistics...")
        
        summary = {
            'Total Teams': len(self.df),
            'Favorite (Highest P(Champion))': f"{self.df.iloc[0]['Team']} ({self.df.iloc[0]['P(Champion)']:.2%})",
            'Underdog (Lowest P(Champion))': f"{self.df.iloc[-1]['Team']} ({self.df.iloc[-1]['P(Champion)']:.2%})",
            'Average P(Championship)': f"{self.df['P(Champion)'].mean():.2%}",
            'Average P(Final)': f"{self.df['P(Final)'].mean():.2%}",
            'Average P(Semifinal)': f"{self.df['P(Semifinal)'].mean():.2%}",
            'Probability Range': f"{self.df['P(Champion)'].min():.2%} - {self.df['P(Champion)'].max():.2%}",
        }
        
        logger.info("\n📈 Summary Statistics:")
        for key, value in summary.items():
            logger.info(f"  {key}: {value}")
        
        return summary


def main():
    """Main execution function for report generation."""
    try:
        # Initialize report generator
        generator = ChampionsLeagueReportGenerator(
            results_file='results/tournament_simulation_results.json',
            output_dir='results/plots'
        )
        
        # Generate all reports
        reports = generator.generate_all_reports()
        
        # Generate summary statistics
        summary = generator.generate_summary_statistics()
        
        # Log completion
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ VISUALIZATION PIPELINE COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"\n📁 Generated Reports:")
        for report_name, file_path in reports.items():
            logger.info(f"  ✓ {report_name}: {file_path}")
        
        logger.info(f"\n📊 Output Directory: {generator.output_dir.absolute()}")
        logger.info(f"{'='*80}\n")
        
        return reports, summary
        
    except Exception as e:
        logger.error(f"❌ Report generation failed: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
