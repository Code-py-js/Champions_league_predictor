"""
Test suite for Champions League Visualization Reports

Tests data loading, DataFrame creation, plot generation, and file I/O.
"""

import pytest
import json
import tempfile
import os
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from visualization.reports import ChampionsLeagueReportGenerator


class TestReportGeneratorInitialization:
    """Test report generator initialization and data loading."""
    
    def test_generator_initializes(self):
        """Test that report generator initializes without errors."""
        generator = ChampionsLeagueReportGenerator(
            results_file='results/tournament_simulation_results.json',
            output_dir='results/plots'
        )
        assert generator is not None
    
    def test_results_loaded(self):
        """Test that simulation results are loaded correctly."""
        generator = ChampionsLeagueReportGenerator(
            results_file='results/tournament_simulation_results.json',
            output_dir='results/plots'
        )
        assert generator.results is not None
        assert 'probabilities' in generator.results
        assert 'champions' in generator.results['probabilities']
    
    def test_output_directory_created(self):
        """Test that output directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'test_plots')
            assert not os.path.exists(output_path)
            
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=output_path
            )
            
            assert os.path.exists(output_path)


class TestDataFrameCreation:
    """Test DataFrame creation from simulation results."""
    
    def test_dataframe_created(self):
        """Test that DataFrame is created from results."""
        generator = ChampionsLeagueReportGenerator(
            results_file='results/tournament_simulation_results.json',
            output_dir='results/plots'
        )
        assert generator.df is not None
        assert isinstance(generator.df, pd.DataFrame)
    
    def test_dataframe_has_required_columns(self):
        """Test that DataFrame has all required columns."""
        generator = ChampionsLeagueReportGenerator(
            results_file='results/tournament_simulation_results.json',
            output_dir='results/plots'
        )
        
        required_columns = ['Team', 'P(Champion)', 'P(Runner-Up)', 'P(Finalist)', 'P(Semifinalist)']
        for col in required_columns:
            assert col in generator.df.columns
    
    def test_dataframe_has_16_teams(self):
        """Test that DataFrame contains 16 teams."""
        generator = ChampionsLeagueReportGenerator(
            results_file='results/tournament_simulation_results.json',
            output_dir='results/plots'
        )
        assert len(generator.df) == 16
    
    def test_dataframe_sorted_by_championship_probability(self):
        """Test that DataFrame is sorted by championship probability (descending)."""
        generator = ChampionsLeagueReportGenerator(
            results_file='results/tournament_simulation_results.json',
            output_dir='results/plots'
        )
        
        probs = generator.df['P(Champion)'].values
        assert np.all(probs[:-1] >= probs[1:])  # Descending order
    
    def test_probabilities_are_valid(self):
        """Test that all probabilities are between 0 and 1."""
        generator = ChampionsLeagueReportGenerator(
            results_file='results/tournament_simulation_results.json',
            output_dir='results/plots'
        )
        
        probability_columns = ['P(Champion)', 'P(Runner-Up)', 'P(Finalist)', 'P(Semifinalist)']
        for col in probability_columns:
            assert np.all(generator.df[col] >= 0)
            assert np.all(generator.df[col] <= 1)


class TestChampionshipProbabilitiesPlot:
    """Test championship probabilities bar chart generation."""
    
    def test_plot_generates_without_error(self):
        """Test that plot generation completes without errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            output_path = generator.plot_championship_probabilities()
            assert output_path is not None
    
    def test_plot_file_created(self):
        """Test that plot file is created on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            output_path = generator.plot_championship_probabilities()
            assert os.path.exists(output_path)
    
    def test_plot_file_is_png(self):
        """Test that output file is PNG format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            output_path = generator.plot_championship_probabilities()
            assert output_path.endswith('.png')
    
    def test_plot_file_has_content(self):
        """Test that plot file has non-zero size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            output_path = generator.plot_championship_probabilities()
            file_size = os.path.getsize(output_path)
            assert file_size > 0


class TestProgressionHeatmapPlot:
    """Test tournament progression heatmap generation."""
    
    def test_heatmap_generates_without_error(self):
        """Test that heatmap generation completes without errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            output_path = generator.plot_progression_heatmap()
            assert output_path is not None
    
    def test_heatmap_file_created(self):
        """Test that heatmap file is created on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            output_path = generator.plot_progression_heatmap()
            assert os.path.exists(output_path)
    
    def test_heatmap_file_has_content(self):
        """Test that heatmap file has non-zero size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            output_path = generator.plot_progression_heatmap()
            file_size = os.path.getsize(output_path)
            assert file_size > 0


class TestDropoffAnalysisPlot:
    """Test drop-off analysis chart generation."""
    
    def test_dropoff_plot_generates_without_error(self):
        """Test that drop-off plot generation completes without errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            output_path = generator.plot_dropoff_analysis()
            assert output_path is not None
    
    def test_dropoff_plot_file_created(self):
        """Test that drop-off plot file is created on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            output_path = generator.plot_dropoff_analysis()
            assert os.path.exists(output_path)


class TestTopContendersPlot:
    """Test top contenders comparison chart generation."""
    
    def test_top_contenders_plot_generates_without_error(self):
        """Test that top contenders plot generation completes without errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            output_path = generator.plot_top_contenders()
            assert output_path is not None
    
    def test_top_contenders_plot_file_created(self):
        """Test that top contenders plot file is created on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            output_path = generator.plot_top_contenders()
            assert os.path.exists(output_path)


class TestAllReportGeneration:
    """Test full report generation pipeline."""
    
    def test_generate_all_reports(self):
        """Test that all reports generate without errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            reports = generator.generate_all_reports()
            assert reports is not None
            assert len(reports) == 4
    
    def test_all_report_files_created(self):
        """Test that all report files are created on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            reports = generator.generate_all_reports()
            
            for report_name, file_path in reports.items():
                assert os.path.exists(file_path), f"{report_name} file not created"
    
    def test_all_report_files_are_png(self):
        """Test that all report files are PNG format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            reports = generator.generate_all_reports()
            
            for report_name, file_path in reports.items():
                assert file_path.endswith('.png'), f"{report_name} is not PNG"
    
    def test_all_report_files_have_content(self):
        """Test that all report files have content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            reports = generator.generate_all_reports()
            
            for report_name, file_path in reports.items():
                file_size = os.path.getsize(file_path)
                assert file_size > 0, f"{report_name} file is empty"


class TestSummaryStatistics:
    """Test summary statistics generation."""
    
    def test_summary_statistics_generated(self):
        """Test that summary statistics are generated."""
        generator = ChampionsLeagueReportGenerator(
            results_file='results/tournament_simulation_results.json',
            output_dir='results/plots'
        )
        
        summary = generator.generate_summary_statistics()
        assert summary is not None
        assert isinstance(summary, dict)
    
    def test_summary_has_required_keys(self):
        """Test that summary has all required keys."""
        generator = ChampionsLeagueReportGenerator(
            results_file='results/tournament_simulation_results.json',
            output_dir='results/plots'
        )
        
        summary = generator.generate_summary_statistics()
        required_keys = ['Total Teams', 'Favorite (Highest P(Champion))', 'Average P(Championship)']
        
        for key in required_keys:
            assert key in summary


class TestProductionReportGeneration:
    """Test production-grade report generation with specified output."""
    
    def test_championship_probabilities_png_created(self):
        """Test that championship_probabilities.png is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            generator.plot_championship_probabilities()
            
            expected_file = os.path.join(tmpdir, 'championship_probabilities.png')
            assert os.path.exists(expected_file)
    
    def test_progression_heatmap_png_created(self):
        """Test that progression_heatmap.png is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChampionsLeagueReportGenerator(
                results_file='results/tournament_simulation_results.json',
                output_dir=tmpdir
            )
            
            generator.plot_progression_heatmap()
            
            expected_file = os.path.join(tmpdir, 'progression_heatmap.png')
            assert os.path.exists(expected_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
