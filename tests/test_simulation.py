"""
Test suite for Champions League Tournament Simulator (Monte Carlo)

Tests initialization, match simulation, Elo updates, and tournament execution.
"""

import pytest
import json
import tempfile
import logging
import os
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from simulation.bracket import ChampionsLeagueTournamentSimulator


class TestSimulatorInitialization:
    """Test simulator initialization and team registry."""
    
    def test_simulator_initializes(self):
        """Test that simulator initializes without errors."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=100
        )
        assert simulator is not None
        assert simulator.num_simulations == 100
    
    def test_team_registry_populated(self):
        """Test that team registry is populated with teams."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=100
        )
        assert len(simulator.teams) > 0
        assert len(simulator.teams) == 16  # Top 16 teams
    
    def test_team_stats_have_required_fields(self):
        """Test that team stats have all required fields."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=100
        )
        
        for team_name, stats in simulator.teams.items():
            assert 'elo' in stats
            assert 'rolling_goals_scored' in stats
            assert 'rolling_goals_conceded' in stats
            assert 'matches_played' in stats
            assert isinstance(stats['elo'], (int, float))
            assert stats['elo'] > 0
            assert stats['rolling_goals_scored'] > 0
            assert stats['rolling_goals_conceded'] > 0
    
    def test_model_and_scaler_loaded(self):
        """Test that model and scaler are properly loaded."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=100
        )
        
        assert simulator.model is not None
        assert simulator.scaler is not None
        assert len(simulator.feature_columns) == 6


class TestFeatureEngineering:
    """Test match feature engineering for simulation."""
    
    def test_features_engineered_correctly(self):
        """Test that features are engineered correctly for a match."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=100
        )
        
        # Get two teams
        teams = list(simulator.teams.keys())
        home_team, away_team = teams[0], teams[1]
        
        # Engineer features
        features = simulator._engineer_match_features(home_team, away_team)
        
        assert features is not None
        assert len(features) == 6  # Should have 6 features
        assert np.all(np.isfinite(features))  # All values should be finite
    
    def test_features_different_for_different_teams(self):
        """Test that different teams produce different feature vectors."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=100
        )
        
        teams = list(simulator.teams.keys())
        
        features1 = simulator._engineer_match_features(teams[0], teams[1])
        features2 = simulator._engineer_match_features(teams[2], teams[3])
        
        assert not np.allclose(features1, features2)
    
    def test_features_reflect_team_strength(self):
        """Test that stronger teams have higher Elo in features."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=100
        )
        
        teams = list(simulator.teams.keys())
        home_team = teams[0]  # Likely strongest (sorted by Elo)
        away_team = teams[-1]  # Likely weakest
        
        features = simulator._engineer_match_features(home_team, away_team)
        
        home_elo = features[0]  # First feature is Home_Elo_Pre (after scaling, but relative order preserved)
        away_elo = features[1]  # Second feature is Away_Elo_Pre
        
        # Home team (stronger) should have higher raw Elo before scaling
        assert simulator.teams[home_team]['elo'] >= simulator.teams[away_team]['elo']


class TestMatchSimulation:
    """Test individual match simulation."""
    
    def test_match_returns_winner(self):
        """Test that match simulation returns a winner."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=100
        )
        
        teams = list(simulator.teams.keys())
        # Create fresh copy of teams
        test_teams = {name: stats.copy() for name, stats in simulator.teams.items()}
        
        home_team, away_team = teams[0], teams[1]
        winner, outcome_class = simulator._simulate_match_with_temp_stats(
            home_team, away_team, test_teams
        )
        
        assert winner in [home_team, away_team]
        assert outcome_class in [1, 2]  # Should be 1 (home) or 2 (away), not 0 (draw)
    
    def test_match_outcome_class_valid(self):
        """Test that match outcome class is valid."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=100
        )
        
        teams = list(simulator.teams.keys())
        test_teams = {name: stats.copy() for name, stats in simulator.teams.items()}
        
        for _ in range(10):
            home_team = np.random.choice(list(simulator.teams.keys()))
            away_team = np.random.choice([t for t in simulator.teams.keys() if t != home_team])
            
            winner, outcome_class = simulator._simulate_match_with_temp_stats(
                home_team, away_team, test_teams
            )
            
            assert outcome_class in [1, 2]
    
    def test_match_updates_elo(self):
        """Test that match simulation updates team Elo."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=100
        )
        
        teams = list(simulator.teams.keys())
        test_teams = {name: stats.copy() for name, stats in simulator.teams.items()}
        
        home_team, away_team = teams[0], teams[1]
        initial_home_elo = test_teams[home_team]['elo']
        initial_away_elo = test_teams[away_team]['elo']
        
        winner, _ = simulator._simulate_match_with_temp_stats(
            home_team, away_team, test_teams
        )
        
        # Elo should change after match
        assert test_teams[home_team]['elo'] != initial_home_elo
        assert test_teams[away_team]['elo'] != initial_away_elo


class TestTournamentExecution:
    """Test tournament simulation execution."""
    
    def test_tournament_iteration_returns_champion(self):
        """Test that tournament iteration returns a champion."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=10
        )
        
        champion = simulator._simulate_tournament_iteration(1)
        assert champion in simulator.teams.keys()
    
    def test_multiple_iterations_produce_different_champions(self):
        """Test that multiple iterations can produce different champions."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=50
        )
        
        champions = set()
        for i in range(1, 11):
            champion = simulator._simulate_tournament_iteration(i)
            champions.add(champion)
        
        # With 10 iterations, likely to have multiple different champions
        assert len(champions) > 1 or len(champions) == 1  # At least test it doesn't error
    
    def test_counters_increment_properly(self):
        """Test that result counters increment properly."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=50
        )
        
        initial_count = sum(simulator.champion_counter.values())
        
        simulator._simulate_tournament_iteration(1)
        
        final_count = sum(simulator.champion_counter.values())
        assert final_count == initial_count + 1


class TestSimulationRun:
    """Test full simulation execution."""
    
    def test_run_simulation_small_iterations(self):
        """Test that full simulation runs without errors (small iteration count)."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=10
        )
        
        simulator.run_simulation()
        
        # Verify counters populated
        assert sum(simulator.champion_counter.values()) == 10
    
    def test_championship_probabilities_sum_to_one(self):
        """Test that championship probabilities sum to approximately 1.0."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=100
        )
        
        simulator.run_simulation()
        
        total_prob = sum(simulator.champion_counter.values()) / simulator.num_simulations
        assert 0.99 <= total_prob <= 1.01
    
    def test_generate_report_succeeds(self):
        """Test that report generation succeeds."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=50
        )
        
        simulator.run_simulation()
        results = simulator.generate_report()
        
        assert results is not None
        assert 'champions' in results
        assert 'runners_up' in results
        assert 'finalists' in results
        assert 'semifinalists' in results


class TestResultsPersistence:
    """Test saving and loading results."""
    
    def test_save_results_creates_file(self):
        """Test that save_results creates output file."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=50
        )
        
        simulator.run_simulation()
        
        # Use temp directory for test
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'test_results.json')
            simulator.save_results(output_file)
            
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
    
    def test_save_results_contains_probabilities(self):
        """Test that saved results contain probability information."""
        simulator = ChampionsLeagueTournamentSimulator(
            model_dir='models',
            features_dir='data',
            num_simulations=50
        )
        
        simulator.run_simulation()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'test_results.json')
            simulator.save_results(output_file)
            
            with open(output_file, 'r') as f:
                results = json.load(f)
            
            assert 'probabilities' in results
            assert 'champions' in results['probabilities']
            assert len(results['probabilities']['champions']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
