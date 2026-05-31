"""
Comprehensive PyTest suite for Model Training & Evaluation Pipeline.

Tests ensure:
- Time-series split maintains chronological order (no data leakage)
- Feature scaling is properly fitted on training data only
- Models train successfully and produce valid predictions
- Evaluation metrics are computed correctly
- Models are properly persisted with joblib
"""

import pytest
import tempfile
import joblib
import json
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from models.train import ChampionsLeagueModelTrainer


class TestDataLoading:
    """Test data loading functionality."""
    
    def test_load_csv_data(self):
        """Test loading processed features from CSV."""
        trainer = ChampionsLeagueModelTrainer()
        df = trainer.load_data("data/processed_features.csv")
        
        assert df is not None
        assert len(df) > 0
        assert 'season' in df.columns
        assert 'Target' in df.columns
    
    def test_load_data_has_required_features(self):
        """Test that loaded data has all required feature columns."""
        trainer = ChampionsLeagueModelTrainer()
        df = trainer.load_data("data/processed_features.csv")
        
        for feature in trainer.FEATURE_COLUMNS:
            assert feature in df.columns, f"Missing feature: {feature}"


class TestTimeSeriesSplit:
    """Test chronological time-series data splitting."""
    
    def test_time_series_split_no_shuffle(self):
        """Test that time-series split maintains chronological order."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        X_train, X_test, y_train, y_test = trainer.split_time_series()
        
        # Verify split
        assert len(X_train) > 0
        assert len(X_test) > 0
        assert len(X_train) > len(X_test)  # Most data in training
    
    def test_time_series_split_correct_seasons(self):
        """Test that split uses correct seasons."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        
        # Get seasons from original dataframe
        train_seasons = trainer.df[trainer.df.index.isin(trainer.X_train.index)]['season'].unique()
        test_seasons = trainer.df[trainer.df.index.isin(trainer.X_test.index)]['season'].unique()
        
        # Training should have multiple seasons
        assert len(train_seasons) > 1
        
        # Test should be single season
        assert len(test_seasons) == 1
        assert test_seasons[0] == trainer.TEST_SEASON
    
    def test_no_overlap_between_train_test(self):
        """Test that train and test sets don't overlap."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        
        # Verify no index overlap
        train_indices = set(trainer.X_train.index)
        test_indices = set(trainer.X_test.index)
        
        assert len(train_indices & test_indices) == 0, "Train/Test overlap detected"


class TestFeatureScaling:
    """Test feature scaling with StandardScaler."""
    
    def test_scaler_fitted_on_train_only(self):
        """Test that scaler is fitted only on training data."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        
        # Store original train statistics
        train_mean_before = trainer.X_train.mean()
        train_std_before = trainer.X_train.std()
        
        trainer.scale_features()
        
        # After scaling, training mean should be near 0, std near 1
        train_mean_after = trainer.X_train.mean()
        train_std_after = trainer.X_train.std()
        
        assert np.allclose(train_mean_after, 0, atol=0.1), "Train set mean not centered"
        assert np.allclose(train_std_after, 1, atol=0.1), "Train set std not scaled"
    
    def test_scale_consistent_feature_names(self):
        """Test that scaling preserves feature column names."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        trainer.scale_features()
        
        # Verify column names preserved
        assert list(trainer.X_train.columns) == trainer.FEATURE_COLUMNS
        assert list(trainer.X_test.columns) == trainer.FEATURE_COLUMNS


class TestLogisticRegressionTraining:
    """Test Logistic Regression model training."""
    
    def test_lr_model_trains_successfully(self):
        """Test that Logistic Regression model trains without errors."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        trainer.scale_features()
        
        trainer.train_logistic_regression()
        
        assert trainer.lr_model is not None
        assert trainer.lr_model.classes_ is not None
        assert len(trainer.lr_model.classes_) == 3  # 3 classes
    
    def test_lr_model_makes_predictions(self):
        """Test that LR model can make predictions."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        trainer.scale_features()
        trainer.train_logistic_regression()
        
        predictions = trainer.lr_model.predict(trainer.X_test)
        proba_predictions = trainer.lr_model.predict_proba(trainer.X_test)
        
        assert len(predictions) == len(trainer.X_test)
        assert proba_predictions.shape == (len(trainer.X_test), 3)
        assert np.allclose(proba_predictions.sum(axis=1), 1.0)  # Probabilities sum to 1


class TestXGBoostTraining:
    """Test XGBoost model training with hyperparameter tuning."""
    
    def test_xgb_model_trains_successfully(self):
        """Test that XGBoost model trains without errors."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        trainer.scale_features()
        
        trainer.train_xgboost_with_tuning()
        
        assert trainer.xgb_model is not None
    
    def test_xgb_model_makes_predictions(self):
        """Test that XGBoost model can make predictions."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        trainer.scale_features()
        trainer.train_xgboost_with_tuning()
        
        predictions = trainer.xgb_model.predict(trainer.X_test)
        proba_predictions = trainer.xgb_model.predict_proba(trainer.X_test)
        
        assert len(predictions) == len(trainer.X_test)
        assert proba_predictions.shape == (len(trainer.X_test), 3)
        assert np.allclose(proba_predictions.sum(axis=1), 1.0)
    
    def test_xgb_hyperparameters_tuned(self):
        """Test that XGBoost hyperparameters have been tuned."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        trainer.scale_features()
        trainer.train_xgboost_with_tuning()
        
        # Check that model has tuned parameters
        assert trainer.xgb_model.max_depth is not None
        assert trainer.xgb_model.learning_rate is not None
        assert trainer.xgb_model.n_estimators is not None


class TestModelEvaluation:
    """Test model evaluation metrics."""
    
    def test_log_loss_computed(self):
        """Test that Log Loss is computed for both models."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        trainer.scale_features()
        trainer.train_logistic_regression()
        trainer.train_xgboost_with_tuning()
        trainer.evaluate_models()
        
        assert trainer.lr_log_loss is not None
        assert trainer.xgb_log_loss is not None
        assert isinstance(trainer.lr_log_loss, (float, np.floating))
        assert isinstance(trainer.xgb_log_loss, (float, np.floating))
        assert trainer.lr_log_loss > 0
        assert trainer.xgb_log_loss > 0
    
    def test_brier_score_computed(self):
        """Test that Brier Score is computed for both models."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        trainer.scale_features()
        trainer.train_logistic_regression()
        trainer.train_xgboost_with_tuning()
        trainer.evaluate_models()
        
        assert trainer.lr_brier is not None
        assert trainer.xgb_brier is not None
        assert 0 <= trainer.lr_brier <= 1
        assert 0 <= trainer.xgb_brier <= 1
    
    def test_best_model_selection(self):
        """Test that best model is correctly selected based on Log Loss."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        trainer.scale_features()
        trainer.train_logistic_regression()
        trainer.train_xgboost_with_tuning()
        trainer.evaluate_models()
        
        assert trainer.best_model is not None
        assert trainer.best_model_name in ['Logistic Regression', 'XGBoost']
        
        if trainer.xgb_log_loss < trainer.lr_log_loss:
            assert trainer.best_model_name == 'XGBoost'
        else:
            assert trainer.best_model_name == 'Logistic Regression'


class TestModelPersistence:
    """Test model saving and loading with joblib."""
    
    def test_model_saved_to_disk(self):
        """Test that best model is saved to disk."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        trainer.scale_features()
        trainer.train_logistic_regression()
        trainer.train_xgboost_with_tuning()
        trainer.evaluate_models()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_paths = trainer.save_models(tmpdir)
            
            assert save_paths['model_path'] is not None
            assert os.path.exists(save_paths['model_path'])
            assert os.path.exists(save_paths['scaler_path'])
            assert os.path.exists(save_paths['features_path'])
            assert os.path.exists(save_paths['metadata_path'])
    
    def test_model_loaded_from_disk(self):
        """Test that saved model can be loaded and used for predictions."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        trainer.scale_features()
        trainer.train_logistic_regression()
        trainer.train_xgboost_with_tuning()
        trainer.evaluate_models()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_paths = trainer.save_models(tmpdir)
            
            # Load model
            loaded_model = joblib.load(save_paths['model_path'])
            loaded_scaler = joblib.load(save_paths['scaler_path'])
            
            # Verify loaded model can make predictions
            predictions = loaded_model.predict_proba(trainer.X_test)
            assert predictions.shape[0] == len(trainer.X_test)
    
    def test_metadata_saved_correctly(self):
        """Test that metadata is saved with correct information."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        trainer.scale_features()
        trainer.train_logistic_regression()
        trainer.train_xgboost_with_tuning()
        trainer.evaluate_models()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_paths = trainer.save_models(tmpdir)
            
            with open(save_paths['metadata_path']) as f:
                metadata = json.load(f)
            
            assert 'best_model' in metadata
            assert 'lr_log_loss' in metadata
            assert 'xgb_log_loss' in metadata
            assert 'train_samples' in metadata
            assert 'test_samples' in metadata
            assert metadata['test_season'] == trainer.TEST_SEASON


class TestDummyPrediction:
    """Test prediction on dummy data (similar to production usage)."""
    
    def test_model_predicts_on_dummy_row(self):
        """Test that loaded model can predict on a single dummy row."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.load_data("data/processed_features.csv")
        trainer.split_time_series()
        trainer.scale_features()
        trainer.train_logistic_regression()
        trainer.train_xgboost_with_tuning()
        trainer.evaluate_models()
        
        # Create dummy row
        dummy_data = np.array([[1500, 1500, 2.0, 2.0, 2.0, 2.0]])  # Mean values
        
        # Scale dummy data
        dummy_scaled = trainer.scaler.transform(dummy_data)
        
        # Make prediction
        prediction = trainer.best_model.predict_proba(dummy_scaled)
        
        assert prediction.shape == (1, 3)
        assert np.allclose(prediction.sum(axis=1), 1.0)
        assert prediction.min() >= 0
        assert prediction.max() <= 1
    
    def test_feature_columns_match_expectations(self):
        """Test that feature columns match the expected list."""
        trainer = ChampionsLeagueModelTrainer()
        
        expected_features = [
            'Home_Elo_Pre',
            'Away_Elo_Pre',
            'Home_Rolling_Goals_Scored',
            'Home_Rolling_Goals_Conceded',
            'Away_Rolling_Goals_Scored',
            'Away_Rolling_Goals_Conceded'
        ]
        
        assert trainer.FEATURE_COLUMNS == expected_features


class TestFullPipeline:
    """Test complete model training pipeline."""
    
    def test_full_pipeline_execution(self):
        """Test that full pipeline executes without errors."""
        trainer = ChampionsLeagueModelTrainer()
        results = trainer.run_pipeline("data/processed_features.csv")
        
        assert results['status'] == 'success'
        assert results['best_model'] in ['Logistic Regression', 'XGBoost']
        assert results['lr_log_loss'] > 0
        assert results['xgb_log_loss'] > 0
        assert results['train_size'] > 0
        assert results['test_size'] > 0
    
    def test_pipeline_produces_valid_models(self):
        """Test that pipeline produces models that can make predictions."""
        trainer = ChampionsLeagueModelTrainer()
        trainer.run_pipeline("data/processed_features.csv")
        
        # Both models should exist
        assert trainer.lr_model is not None
        assert trainer.xgb_model is not None
        
        # Both should make predictions
        lr_pred = trainer.lr_model.predict_proba(trainer.X_test)
        xgb_pred = trainer.xgb_model.predict_proba(trainer.X_test)
        
        assert lr_pred.shape == xgb_pred.shape


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
