"""
Champions League Tournament Simulation (Monte Carlo)

Simulates 10,000 tournament iterations using dynamic Elo updates and rolling goals
after each match. Uses predict_proba() to sample outcomes based on model probabilities.

Author: Champions League Predictor
"""

import json
import logging
import os
import pickle
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChampionsLeagueTournamentSimulator:
    """
    Simulates Champions League knockout tournament 10,000 times using trained XGBoost model.
    Dynamically updates team stats (Elo, rolling goals) after each simulated match.
    """
    
    def __init__(self, model_dir: str = 'models', features_dir: str = 'data', num_simulations: int = 10000):
        """
        Initialize tournament simulator.
        
        Args:
            model_dir: Directory containing trained models and scaler
            features_dir: Directory containing processed features
            num_simulations: Number of tournament simulations to run
        """
        self.model_dir = Path(model_dir)
        self.features_dir = Path(features_dir)
        self.num_simulations = num_simulations
        
        logger.info(f"{'='*80}")
        logger.info(f"CHAMPIONS LEAGUE TOURNAMENT SIMULATION (MONTE CARLO)")
        logger.info(f"{'='*80}")
        
        # Load trained model
        logger.info("📥 Loading trained XGBoost model...")
        self.model = joblib.load(self.model_dir / 'best_model_xgboost.joblib')
        logger.info("✓ Model loaded")
        
        # Load scaler
        logger.info("📥 Loading feature scaler...")
        self.scaler = joblib.load(self.model_dir / 'scaler.joblib')
        logger.info("✓ Scaler loaded")
        
        # Load feature columns
        logger.info("📥 Loading feature columns...")
        with open(self.model_dir / 'feature_columns.json', 'r') as f:
            self.feature_columns = json.load(f)
        logger.info(f"✓ Features: {self.feature_columns}")
        
        # Load processed features to extract team stats
        logger.info("📥 Loading processed features...")
        self.df = pd.read_csv(self.features_dir / 'processed_features.csv')
        logger.info(f"✓ Loaded {len(self.df)} matches from processed data")
        
        # Initialize team registry (will extract latest stats for each team)
        self._initialize_team_registry()
        
        # Tournament results tracker
        self.champion_counter = defaultdict(int)
        self.runner_up_counter = defaultdict(int)
        self.finalist_counter = defaultdict(int)
        self.semifinalist_counter = defaultdict(int)
        self.quarterfinalist_counter = defaultdict(int)

        
        # Class mapping (critical for understanding predictions)
        self.class_map = {0: 'Draw', 1: 'Home Win', 2: 'Away Win'}
        self.reverse_class_map = {'Draw': 0, 'Home Win': 1, 'Away Win': 2}
    
    def _initialize_team_registry(self):
        """
        Extract the most recent stats for each team from the processed features.
        These will be the starting points for tournament simulation.
        """
        logger.info("🏢 Initializing team registry with latest statistics...")
        
        self.teams = {}
        
        # Get unique teams from both home and away columns
        home_teams = self.df['home_team'].unique()
        away_teams = self.df['away_team'].unique()
        all_teams = list(set(home_teams) | set(away_teams))
        
        logger.info(f"  Total unique teams: {len(all_teams)}")
        
        # For each team, get the most recent match to extract their stats
        for team in all_teams:
            # Get most recent match where this team played
            home_matches = self.df[self.df['home_team'] == team]
            away_matches = self.df[self.df['away_team'] == team]
            
            # Combine and sort by date
            team_matches = pd.concat([home_matches, away_matches], ignore_index=True)
            team_matches = team_matches.sort_values('date', ascending=False)
            
            if len(team_matches) == 0:
                logger.warning(f"  ⚠ No matches found for {team}, skipping")
                continue
            
            latest_match = team_matches.iloc[0]
            
            # Extract stats - determine if team was home or away in latest match
            if latest_match['home_team'] == team:
                # Team was home team
                elo_current = latest_match['Home_Elo_Pre']  # Pre-match Elo
                goals_scored_avg = latest_match['Home_Rolling_Goals_Scored']
                goals_conceded_avg = latest_match['Home_Rolling_Goals_Conceded']
            else:
                # Team was away team
                elo_current = latest_match['Away_Elo_Pre']
                goals_scored_avg = latest_match['Away_Rolling_Goals_Scored']
                goals_conceded_avg = latest_match['Away_Rolling_Goals_Conceded']
            
            self.teams[team] = {
                'name': team,
                'elo': elo_current,
                'rolling_goals_scored': goals_scored_avg,
                'rolling_goals_conceded': goals_conceded_avg,
                'matches_played': 0  # Will track simulated matches
            }
        
        # Filter to only 16 teams (those most likely to be in knockout stage)
        # Sort by Elo rating and take top 16
        teams_sorted = sorted(self.teams.items(), key=lambda x: x[1]['elo'], reverse=True)
        self.teams = {name: stats for name, stats in teams_sorted[:16]}
        
        logger.info(f"\n✓ Tournament teams initialized ({len(self.teams)} teams):")
        logger.info(f"{'Team':<25} {'Elo':<10} {'Goals Scored':<15} {'Goals Conceded':<15}")
        logger.info(f"{'-'*65}")
        for team_name, stats in sorted(self.teams.items(), key=lambda x: x[1]['elo'], reverse=True):
            logger.info(f"{team_name:<25} {stats['elo']:<10.1f} {stats['rolling_goals_scored']:<15.2f} {stats['rolling_goals_conceded']:<15.2f}")
    
    def _engineer_match_features(self, home_team: str, away_team: str) -> np.ndarray:
        """
        Engineer features for a simulated match between two teams.
        
        Args:
            home_team: Name of home team
            away_team: Name of away team
            
        Returns:
            Scaled feature vector for the match
        """
        home_stats = self.teams[home_team]
        away_stats = self.teams[away_team]
        
        # Create feature row
        features_dict = {
            'Home_Elo_Pre': home_stats['elo'],
            'Away_Elo_Pre': away_stats['elo'],
            'Home_Rolling_Goals_Scored': home_stats['rolling_goals_scored'],
            'Home_Rolling_Goals_Conceded': home_stats['rolling_goals_conceded'],
            'Away_Rolling_Goals_Scored': away_stats['rolling_goals_scored'],
            'Away_Rolling_Goals_Conceded': away_stats['rolling_goals_conceded']
        }
        
        # Create DataFrame with correct column order
        features_df = pd.DataFrame([features_dict])
        features_df = features_df[self.feature_columns]
        
        # Scale features (returns 2D array of shape (1, 6))
        features_scaled = self.scaler.transform(features_df)
        
        return features_scaled[0]  # Return 1D array of shape (6,)
    
    def _simulate_match(self, home_team: str, away_team: str) -> Tuple[str, int]:
        """
        Simulate a single match and update team stats based on outcome.
        
        Args:
            home_team: Name of home team
            away_team: Name of away team
            
        Returns:
            Tuple of (winner_name, match_result_class)
        """
        # Engineer features for this match
        features = self._engineer_match_features(home_team, away_team)
        
        # Get probability predictions (3 classes: Draw, Home Win, Away Win)
        # features is 1D array of shape (6,), need to reshape to (1, 6) for predict_proba
        probabilities = self.model.predict_proba(features.reshape(1, -1))[0]
        
        # Sample outcome based on probabilities
        outcome_class = np.random.choice([0, 1, 2], p=probabilities)
        
        # Determine winner
        if outcome_class == 0:  # Draw - need to resample (unlikely in knockout)
            # If draw is sampled, resample avoiding draw
            p_home_win = probabilities[1]
            p_away_win = probabilities[2]
            total_p = p_home_win + p_away_win
            
            # Normalize with safety for floating-point errors
            normalized_probs = np.array([p_home_win / total_p, p_away_win / total_p])
            normalized_probs = normalized_probs / normalized_probs.sum()
            
            outcome_class = np.random.choice([1, 2], p=normalized_probs)
        
        if outcome_class == 1:  # Home Win
            winner = home_team
            loser = away_team
        else:  # Away Win
            winner = away_team
            loser = home_team
        
        # Update team stats after match
        self._update_team_stats(winner, loser, probabilities, outcome_class)
        
        return winner, outcome_class
    
    def _update_team_stats(self, winner: str, loser: str, probabilities: np.ndarray, outcome_class: int):
        """
        Update team stats (Elo, rolling goals) after a simulated match.
        
        Args:
            winner: Name of winning team
            loser: Name of losing team
            probabilities: Model probability predictions [P(Draw), P(Home), P(Away)]
            outcome_class: Sampled outcome class (0=Draw, 1=Home, 2=Away)
        """
        # Elo rating update using standard chess-like system
        K = 32  # K-factor for Elo calculation
        
        winner_elo = self.teams[winner]['elo']
        loser_elo = self.teams[loser]['elo']
        
        # Expected score calculation
        expected_winner = 1 / (1 + 10**((loser_elo - winner_elo) / 400))
        expected_loser = 1 / (1 + 10**((winner_elo - loser_elo) / 400))
        
        # Update Elo (winner gets +K, loser gets -K/2 to reflect knockout advantage)
        self.teams[winner]['elo'] = winner_elo + K * (1 - expected_winner)
        self.teams[loser]['elo'] = loser_elo + K * (0 - expected_loser)
        
        # Update rolling goals based on match performance
        # Winner gets slight boost to rolling goals (confidence in attacking)
        # Loser gets slight reduction (momentum loss)
        
        # Use model probabilities to modulate goal updates
        # High confidence win → bigger goal boost for winner
        confidence = max(probabilities[1], probabilities[2])
        
        self.teams[winner]['rolling_goals_scored'] += 0.2 * (confidence - 0.5)
        self.teams[loser]['rolling_goals_conceded'] += 0.15 * (confidence - 0.5)
        
        # Clamp rolling goals to realistic ranges
        self.teams[winner]['rolling_goals_scored'] = np.clip(self.teams[winner]['rolling_goals_scored'], 0.5, 3.5)
        self.teams[loser]['rolling_goals_conceded'] = np.clip(self.teams[loser]['rolling_goals_conceded'], 0.5, 3.5)
        
        # Increment match counters
        self.teams[winner]['matches_played'] += 1
        self.teams[loser]['matches_played'] += 1
    
    def _simulate_tournament_iteration(self, iteration: int) -> str:
        """
        Simulate one complete tournament iteration (16 → 8 → 4 → 2 → 1).
        
        Args:
            iteration: Iteration number for logging
            
        Returns:
            Name of tournament champion
        """
        # Reset team stats for this iteration (fresh Elo state)
        # We'll make a copy of teams for this simulation
        simulation_teams = {}
        for team_name, stats in self.teams.items():
            simulation_teams[team_name] = stats.copy()
        
        # Get initial 16 teams
        remaining_teams = list(simulation_teams.keys())
        
        # Round of 16
        semifinalists = []
        for i in range(0, len(remaining_teams), 2):
            home_team = remaining_teams[i]
            away_team = remaining_teams[i + 1]
            winner, _ = self._simulate_match_with_temp_stats(home_team, away_team, simulation_teams)
            semifinalists.append(winner)
        
        # Quarterfinals (8 → 4)
        quarterfinalists = []
        for i in range(0, len(semifinalists), 2):
            home_team = semifinalists[i]
            away_team = semifinalists[i + 1]
            winner, _ = self._simulate_match_with_temp_stats(home_team, away_team, simulation_teams)
            quarterfinalists.append(winner)

        # Track quarterfinalists: after Round of 16, 8 teams advance.
        # In this code, `semifinalists` represents the 8 teams that advance from Round of 16.
        for team in semifinalists:
            self.quarterfinalist_counter[team] += 1

        # Track semifinalists: after quarterfinals, 4 teams remain.
        for team in quarterfinalists:
            self.semifinalist_counter[team] += 1

        
        # Semifinals (4 → 2)
        finalists = []
        for i in range(0, len(quarterfinalists), 2):
            home_team = quarterfinalists[i]
            away_team = quarterfinalists[i + 1]
            winner, _ = self._simulate_match_with_temp_stats(home_team, away_team, simulation_teams)
            finalists.append(winner)
        
        # Track finalists
        for team in finalists:
            self.finalist_counter[team] += 1
        
        # Final (2 → 1)
        champion, runner_up = finalists[0], finalists[1]
        winner, _ = self._simulate_match_with_temp_stats(champion, runner_up, simulation_teams)
        
        # Track results
        loser = runner_up if winner == champion else champion
        self.champion_counter[winner] += 1
        self.runner_up_counter[loser] += 1
        
        if iteration % 1000 == 0:
            logger.info(f"  Iteration {iteration:,d}: {winner} won the tournament")
        
        return winner
    
    def _simulate_match_with_temp_stats(self, home_team: str, away_team: str, 
                                        simulation_teams: Dict) -> Tuple[str, int]:
        """
        Simulate a match using temporary team stats (for single iteration).
        
        Args:
            home_team: Name of home team
            away_team: Name of away team
            simulation_teams: Temporary team stats for this iteration
            
        Returns:
            Tuple of (winner_name, match_result_class)
        """
        home_stats = simulation_teams[home_team]
        away_stats = simulation_teams[away_team]
        
        # Create feature row
        features_dict = {
            'Home_Elo_Pre': home_stats['elo'],
            'Away_Elo_Pre': away_stats['elo'],
            'Home_Rolling_Goals_Scored': home_stats['rolling_goals_scored'],
            'Home_Rolling_Goals_Conceded': home_stats['rolling_goals_conceded'],
            'Away_Rolling_Goals_Scored': away_stats['rolling_goals_scored'],
            'Away_Rolling_Goals_Conceded': away_stats['rolling_goals_conceded']
        }
        
        # Create DataFrame with correct column order
        features_df = pd.DataFrame([features_dict])
        features_df = features_df[self.feature_columns]
        
        # Scale features
        features_scaled = self.scaler.transform(features_df)
        
        # Get probability predictions (shape should be (1, 3) for 3 classes)
        probabilities = self.model.predict_proba(features_scaled)[0]
        
        # Sample outcome based on probabilities
        outcome_class = np.random.choice([0, 1, 2], p=probabilities)
        
        # Handle draw: resample to get winner
        if outcome_class == 0:
            # Normalize probabilities for home/away wins (exclude draw)
            p_home_win = probabilities[1]
            p_away_win = probabilities[2]
            total_p = p_home_win + p_away_win
            
            # Resample excluding draw (with safety normalization for floating-point errors)
            normalized_probs = np.array([p_home_win / total_p, p_away_win / total_p])
            normalized_probs = normalized_probs / normalized_probs.sum()  # Ensure sum to 1
            
            outcome_class = np.random.choice([1, 2], p=normalized_probs)
        
        if outcome_class == 1:  # Home Win
            winner = home_team
            loser = away_team
        else:  # Away Win
            winner = away_team
            loser = home_team
        
        # Update temporary stats
        K = 32
        winner_elo = simulation_teams[winner]['elo']
        loser_elo = simulation_teams[loser]['elo']
        
        expected_winner = 1 / (1 + 10**((loser_elo - winner_elo) / 400))
        expected_loser = 1 / (1 + 10**((winner_elo - loser_elo) / 400))
        
        simulation_teams[winner]['elo'] = winner_elo + K * (1 - expected_winner)
        simulation_teams[loser]['elo'] = loser_elo + K * (0 - expected_loser)
        
        confidence = max(probabilities[1], probabilities[2])
        simulation_teams[winner]['rolling_goals_scored'] += 0.2 * (confidence - 0.5)
        simulation_teams[loser]['rolling_goals_conceded'] += 0.15 * (confidence - 0.5)
        
        simulation_teams[winner]['rolling_goals_scored'] = np.clip(
            simulation_teams[winner]['rolling_goals_scored'], 0.5, 3.5)
        simulation_teams[loser]['rolling_goals_conceded'] = np.clip(
            simulation_teams[loser]['rolling_goals_conceded'], 0.5, 3.5)
        
        return winner, outcome_class
    
    def run_simulation(self):
        """
        Run 10,000 tournament simulations and collect statistics.
        """
        logger.info(f"\n🎮 Running {self.num_simulations:,d} tournament simulations...")
        logger.info(f"{'='*80}")
        
        for i in range(1, self.num_simulations + 1):
            self._simulate_tournament_iteration(i)
        
        logger.info(f"\n✅ SIMULATION COMPLETE")
        logger.info(f"{'='*80}")
    
    def generate_report(self):
        """
        Generate comprehensive tournament statistics report.
        """
        logger.info(f"\n📊 TOURNAMENT SIMULATION RESULTS ({self.num_simulations:,d} iterations)")
        logger.info(f"{'='*80}\n")
        
        # Champion statistics
        logger.info("🏆 CHAMPIONS (P(Win Tournament)):")
        logger.info(f"{'Team':<25} {'Wins':<10} {'Probability':<15}")
        logger.info(f"{'-'*50}")
        
        sorted_champions = sorted(self.champion_counter.items(), key=lambda x: x[1], reverse=True)
        for team, wins in sorted_champions:
            prob = wins / self.num_simulations
            bar = '█' * int(prob * 50)
            logger.info(f"{team:<25} {wins:<10} {prob:<15.4f} {bar}")
        
        # Runner-up statistics
        logger.info(f"\n🥈 RUNNER-UPS (P(Reach Final)):")
        logger.info(f"{'Team':<25} {'Times':<10} {'Probability':<15}")
        logger.info(f"{'-'*50}")
        
        sorted_runners = sorted(self.runner_up_counter.items(), key=lambda x: x[1], reverse=True)
        for team, times in sorted_runners[:10]:
            prob = times / self.num_simulations
            bar = '█' * int(prob * 50)
            logger.info(f"{team:<25} {times:<10} {prob:<15.4f} {bar}")
        
        # Finalist statistics
        logger.info(f"\n🥉 FINALISTS (P(Reach Final/Semifinal)):")
        logger.info(f"{'Team':<25} {'Times':<10} {'Probability':<15}")
        logger.info(f"{'-'*50}")
        
        sorted_finalists = sorted(self.finalist_counter.items(), key=lambda x: x[1], reverse=True)
        for team, times in sorted_finalists[:10]:
            prob = times / self.num_simulations
            bar = '█' * int(prob * 50)
            logger.info(f"{team:<25} {times:<10} {prob:<15.4f} {bar}")
        
        # Semifinalist statistics
        logger.info(f"\n📍 SEMIFINALISTS (P(Reach Semifinals)):")
        logger.info(f"{'Team':<25} {'Times':<10} {'Probability':<15}")
        logger.info(f"{'-'*50}")
        
        sorted_semis = sorted(self.semifinalist_counter.items(), key=lambda x: x[1], reverse=True)
        for team, times in sorted_semis[:10]:
            prob = times / self.num_simulations
            bar = '█' * int(prob * 50)
            logger.info(f"{team:<25} {times:<10} {prob:<15.4f} {bar}")
        
        # Summary statistics
        logger.info(f"\n{'='*80}")
        logger.info(f"📈 SUMMARY STATISTICS:")
        logger.info(f"{'='*80}")
        
        # Most likely champion
        most_likely_champion = sorted_champions[0]
        logger.info(f"\n🏅 Most Likely Champion: {most_likely_champion[0]}")
        logger.info(f"   P(Champion) = {most_likely_champion[1]/self.num_simulations:.4f}")
        
        # Top 3 favorites
        logger.info(f"\n🎯 Top 3 Favorites:")
        for rank, (team, wins) in enumerate(sorted_champions[:3], 1):
            logger.info(f"   {rank}. {team}: {wins/self.num_simulations:.4f}")
        
        # Average probability per team (entropy/uncertainty)
        logger.info(f"\n📊 Competition Metrics:")
        num_teams_with_wins = len(self.champion_counter)
        max_prob = max(self.champion_counter.values()) / self.num_simulations
        min_prob = min(self.champion_counter.values()) / self.num_simulations
        
        logger.info(f"   Teams with positive P(Champion): {num_teams_with_wins}")
        logger.info(f"   Favorite probability: {max_prob:.4f}")
        logger.info(f"   Underdog probability: {min_prob:.4f}")
        logger.info(f"   Probability ratio (Fav/Underdog): {max_prob/min_prob:.2f}x")
        
        # Herfindahl-Hirschman Index (concentration measure)
        hhi = sum((wins / self.num_simulations)**2 for wins in self.champion_counter.values())
        logger.info(f"   HHI (Concentration): {hhi:.4f} (lower = more competitive)")
        
        return {
            'champions': dict(sorted_champions),
            'runners_up': dict(sorted_runners),
            'finalists': dict(sorted_finalists),
            'semifinalists': dict(sorted_semis)
        }
    
    def save_results(self, output_file: str = 'results/tournament_simulation_results.json'):
        """
        Save simulation results to JSON file.
        
        Args:
            output_file: Path to save results
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        results = {
            'num_simulations': self.num_simulations,
            'champions': {team: wins for team, wins in self.champion_counter.items()},
            'runners_up': {team: times for team, times in self.runner_up_counter.items()},
            'finalists': {team: times for team, times in self.finalist_counter.items()},
            'semifinalists': {team: times for team, times in self.semifinalist_counter.items()},
            'quarterfinalists': {team: times for team, times in self.quarterfinalist_counter.items()},
            'probabilities': {
                'champions': {team: wins/self.num_simulations for team, wins in self.champion_counter.items()},
                'runners_up': {team: times/self.num_simulations for team, times in self.runner_up_counter.items()},
                'finalists': {team: times/self.num_simulations for team, times in self.finalist_counter.items()},
                'semifinalists': {team: times/self.num_simulations for team, times in self.semifinalist_counter.items()},
                'quarterfinalists': {team: times/self.num_simulations for team, times in self.quarterfinalist_counter.items()}
            }
        }

        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"\n💾 Results saved to {output_path}")


def main():
    """
    Main execution function for tournament simulation.
    """
    try:
        # Initialize simulator
        num_iterations = int(os.environ.get('NUM_ITERATIONS', 10000))

        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=num_iterations
        )

        
        # Run simulation
        simulator.run_simulation()
        
        # Generate report
        simulator.generate_report()
        
        # Save results
        simulator.save_results('results/tournament_simulation_results.json')
        
        logger.info(f"\n✅ TOURNAMENT SIMULATION PIPELINE COMPLETE")
        logger.info(f"{'='*80}\n")
        
    except Exception as e:
        logger.error(f"❌ Tournament simulation failed: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
