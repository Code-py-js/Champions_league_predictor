"""
Model Training & Evaluation Pipeline for Champions League Prediction.

Trains baseline Logistic Regression and advanced XGBoost classifiers using
time-series split to predict Champions League match outcomes (Home Win/Draw/Away Win).

Key Features:
- Chronological time-series data split (prevents future data leakage)
- Logistic Regression baseline with scaling
- XGBoost with hyperparameter tuning (GridSearchCV with TimeSeriesSplit)
- Evaluation using Log Loss and Brier Score
- Model persistence with joblib
"""

import os
import json
import logging
from datetime import datetime
from typing import Tuple, Dict, Optional, List

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import log_loss, brier_score_loss, classification_report
from xgboost import XGBClassifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChampionsLeagueModelTrainer:
    """Model training and evaluation pipeline for Champions League prediction."""
    
    # Feature columns (must match engineer.py output)
    FEATURE_COLUMNS = [
        'Home_Elo_Pre',
        'Away_Elo_Pre',
        'Home_Rolling_Goals_Scored',
        'Home_Rolling_Goals_Conceded',
        'Away_Rolling_Goals_Scored',
        'Away_Rolling_Goals_Conceded'
    ]
    
    # Target column
    TARGET_COLUMN = 'Target'
    
    # Time-series split parameters
    TRAIN_SEASONS = ['2015-2016', '2016-2017', '2017-2018', '2018-2019', 
                    '2019-2020', '2020-2021', '2021-2022', '2022-2023']
    TEST_SEASON = '2023-2024'
    
    def __init__(self):
        """Initialize trainer."""
        self.df = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        
        self.scaler = None
        self.lr_model = None
        self.xgb_model = None
        self.best_model = None
        self.best_model_name = None
        
        self.lr_predictions = None
        self.xgb_predictions = None
        
        self.lr_log_loss = None
        self.xgb_log_loss = None
        self.lr_brier = None
        self.xgb_brier = None
    
    def load_data(self, csv_file: str = None, mongodb: bool = False) -> pd.DataFrame:
        """
        Load processed features data.
        
        Args:
            csv_file: Path to CSV file
            mongodb: If True, load from MongoDB
            
        Returns:
            DataFrame with processed features
        """
        logger.info("📥 Loading processed features data...")
        
        if mongodb:
            try:
                from pymongo import MongoClient
                client = MongoClient('mongodb://localhost:27017/', 
                                   serverSelectionTimeoutMS=5000)
                db = client['champions_league']
                data = list(db['processed_features'].find())
                df = pd.DataFrame(data)
                logger.info(f"✓ Loaded {len(df)} matches from MongoDB")
            except Exception as e:
                logger.warning(f"⚠ MongoDB load failed: {e}, falling back to CSV")
                csv_file = csv_file or "data/processed_features.csv"
                df = pd.read_csv(csv_file)
                logger.info(f"✓ Loaded {len(df)} matches from CSV")
        else:
            csv_file = csv_file or "data/processed_features.csv"
            df = pd.read_csv(csv_file)
            logger.info(f"✓ Loaded {len(df)} matches from CSV")
        
        self.df = df
        return df
    
    def split_time_series(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Split data chronologically by season (CRITICAL for time-series).
        
        Returns:
            X_train, X_test, y_train, y_test
        """
        logger.info("⏰ Performing chronological time-series split...")
        
        # Verify season column
        if 'season' not in self.df.columns:
            raise ValueError("Dataset missing 'season' column")
        
        # Split by season
        train_mask = self.df['season'].isin(self.TRAIN_SEASONS)
        test_mask = self.df['season'] == self.TEST_SEASON
        
        df_train = self.df[train_mask]
        df_test = self.df[test_mask]
        
        logger.info(f"✓ Time-series split complete:")
        logger.info(f"  Training seasons: {', '.join(self.TRAIN_SEASONS)}")
        logger.info(f"  Training set: {len(df_train)} matches ({len(df_train)/len(self.df)*100:.1f}%)")
        logger.info(f"  Test season: {self.TEST_SEASON}")
        logger.info(f"  Test set: {len(df_test)} matches ({len(df_test)/len(self.df)*100:.1f}%)")
        
        # Extract features and target
        X_train = df_train[self.FEATURE_COLUMNS].copy()
        X_test = df_test[self.FEATURE_COLUMNS].copy()
        y_train = df_train[self.TARGET_COLUMN].copy()
        y_test = df_test[self.TARGET_COLUMN].copy()
        
        # Verify no NaN values
        assert X_train.notna().all().all(), "NaN values in training features"
        assert X_test.notna().all().all(), "NaN values in test features"
        
        self.X_train = X_train
        self.X_test = X_test
        self.y_train = y_train
        self.y_test = y_test
        
        logger.info(f"✓ Features extracted: {len(self.FEATURE_COLUMNS)} columns")
        logger.info(f"✓ Target variable verified: {len(np.unique(y_train))} classes")
        
        return X_train, X_test, y_train, y_test
    
    def scale_features(self):
        """
        Scale features using StandardScaler.
        
        CRITICAL: Fit scaler ONLY on training data, then transform both train and test.
        """
        logger.info("📏 Scaling features with StandardScaler...")
        
        self.scaler = StandardScaler()
        
        # Fit on training data only (prevent data leakage)
        X_train_scaled = self.scaler.fit_transform(self.X_train)
        
        # Transform test data using training statistics
        X_test_scaled = self.scaler.transform(self.X_test)
        
        self.X_train = pd.DataFrame(X_train_scaled, columns=self.FEATURE_COLUMNS)
        self.X_test = pd.DataFrame(X_test_scaled, columns=self.FEATURE_COLUMNS)
        
        logger.info(f"✓ Features scaled")
        logger.info(f"  Training set - Mean: {X_train_scaled.mean():.4f}, Std: {X_train_scaled.std():.4f}")
        logger.info(f"  Test set - Mean: {X_test_scaled.mean():.4f}, Std: {X_test_scaled.std():.4f}")
    
    def train_logistic_regression(self):
        """
        Train baseline Logistic Regression model.
        """
        logger.info("🎯 Training Logistic Regression (Baseline)...")
        
        self.lr_model = LogisticRegression(
            solver='lbfgs',
            max_iter=500,
            random_state=42
        )
        
        self.lr_model.fit(self.X_train, self.y_train)
        
        logger.info(f"✓ Logistic Regression trained")
        logger.info(f"  Coefficients shape: {self.lr_model.coef_.shape}")
        logger.info(f"  Classes: {self.lr_model.classes_}")
    
    def train_xgboost_with_tuning(self):
        """
        Train XGBoost model with hyperparameter tuning using TimeSeriesSplit.
        
        CRITICAL: Uses TimeSeriesSplit for cross-validation to maintain chronological order.
        """
        logger.info("🚀 Training XGBoost with hyperparameter tuning...")
        logger.info("  Using TimeSeriesSplit for cross-validation...")
        
        # Base XGBoost model
        xgb_base = XGBClassifier(
            objective='multi:softprob',
            num_class=3,
            random_state=42,
            verbosity=0
        )
        
        # Hyperparameter grid
        param_grid = {
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.1, 0.2],
            'n_estimators': [50, 100, 150]
        }
        
        # TimeSeriesSplit for cross-validation (preserves chronological order)
        tscv = TimeSeriesSplit(n_splits=3)
        
        # GridSearchCV
        grid_search = GridSearchCV(
            xgb_base,
            param_grid,
            cv=tscv,
            scoring='neg_log_loss',
            n_jobs=-1,
            verbose=1
        )
        
        logger.info(f"  Grid search parameters: {len(param_grid['max_depth']) * len(param_grid['learning_rate']) * len(param_grid['n_estimators'])} combinations")
        
        grid_search.fit(self.X_train, self.y_train)
        
        self.xgb_model = grid_search.best_estimator_
        
        logger.info(f"✓ XGBoost hyperparameter tuning complete")
        logger.info(f"  Best parameters: {grid_search.best_params_}")
        logger.info(f"  Best CV score (neg_log_loss): {grid_search.best_score_:.4f}")
    
    def evaluate_models(self):
        """
        Evaluate both models on test set using Log Loss and Brier Score.
        """
        logger.info("📊 Evaluating models on test set...")
        
        # Get probability predictions
        self.lr_predictions = self.lr_model.predict_proba(self.X_test)
        self.xgb_predictions = self.xgb_model.predict_proba(self.X_test)
        
        # Calculate Log Loss (primary metric for multi-class classification)
        self.lr_log_loss = log_loss(self.y_test, self.lr_predictions)
        self.xgb_log_loss = log_loss(self.y_test, self.xgb_predictions)
        
        logger.info(f"\n🎯 EVALUATION RESULTS:")
        logger.info(f"{'='*70}")
        logger.info(f"{'Model':<25} {'Log Loss':<20} {'Status':<20}")
        logger.info(f"{'-'*70}")
        logger.info(f"{'Logistic Regression':<25} {self.lr_log_loss:<20.4f} {'Baseline':<20}")
        logger.info(f"{'XGBoost':<25} {self.xgb_log_loss:<20.4f} {'Optimized':<20}")
        logger.info(f"{'-'*70}")
        
        # Calculate Brier Score for multiclass (mean squared error between probabilities and one-hot encoding)
        # Convert y_test to one-hot encoding
        y_test_onehot = np.eye(3)[self.y_test.values]
        
        self.lr_brier = np.mean((self.lr_predictions - y_test_onehot) ** 2)
        self.xgb_brier = np.mean((self.xgb_predictions - y_test_onehot) ** 2)
        
        logger.info(f"\nBrier Score (multiclass mean squared error):")
        logger.info(f"  Logistic Regression: {self.lr_brier:.4f}")
        logger.info(f"  XGBoost: {self.xgb_brier:.4f}")
        
        # Determine best model
        if self.xgb_log_loss < self.lr_log_loss:
            self.best_model = self.xgb_model
            self.best_model_name = "XGBoost"
            improvement = (self.lr_log_loss - self.xgb_log_loss) / self.lr_log_loss * 100
            logger.info(f"\n🏆 BEST MODEL: XGBoost")
            logger.info(f"  Improvement over baseline: {improvement:.2f}%")
        else:
            self.best_model = self.lr_model
            self.best_model_name = "Logistic Regression"
            logger.info(f"\n🏆 BEST MODEL: Logistic Regression (XGBoost shows no improvement)")
    
    def print_classification_reports(self):
        """
        Print detailed classification reports for both models.
        """
        logger.info(f"\n{'='*70}")
        logger.info("CLASSIFICATION REPORTS")
        logger.info(f"{'='*70}")
        
        # Logistic Regression predictions
        lr_pred_classes = self.lr_model.predict(self.X_test)
        logger.info(f"\n📋 LOGISTIC REGRESSION:")
        logger.info(classification_report(self.y_test, lr_pred_classes, 
                                         target_names=['Draw', 'Home Win', 'Away Win'],
                                         digits=4))
        
        # XGBoost predictions
        xgb_pred_classes = self.xgb_model.predict(self.X_test)
        logger.info(f"📋 XGBOOST:")
        logger.info(classification_report(self.y_test, xgb_pred_classes,
                                         target_names=['Draw', 'Home Win', 'Away Win'],
                                         digits=4))
    
    def save_models(self, output_dir: str = "models"):
        """
        Save best model, scaler, and feature columns to disk using joblib.
        
        Args:
            output_dir: Directory to save models
        """
        logger.info(f"💾 Saving models to {output_dir}...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Save best model
        model_path = os.path.join(output_dir, f"best_model_{self.best_model_name.lower().replace(' ', '_')}.joblib")
        joblib.dump(self.best_model, model_path)
        logger.info(f"✓ Best model saved: {model_path}")
        
        # Save scaler
        scaler_path = os.path.join(output_dir, "scaler.joblib")
        joblib.dump(self.scaler, scaler_path)
        logger.info(f"✓ Scaler saved: {scaler_path}")
        
        # Save feature columns
        features_path = os.path.join(output_dir, "feature_columns.json")
        with open(features_path, 'w') as f:
            json.dump(self.FEATURE_COLUMNS, f, indent=2)
        logger.info(f"✓ Feature columns saved: {features_path}")
        
        # Save metadata
        metadata = {
            'best_model': self.best_model_name,
            'lr_log_loss': float(self.lr_log_loss),
            'xgb_log_loss': float(self.xgb_log_loss),
            'lr_brier': float(self.lr_brier),
            'xgb_brier': float(self.xgb_brier),
            'train_seasons': self.TRAIN_SEASONS,
            'test_season': self.TEST_SEASON,
            'train_samples': len(self.X_train),
            'test_samples': len(self.X_test),
            'created_at': datetime.now().isoformat(),
            'features': self.FEATURE_COLUMNS
        }
        
        metadata_path = os.path.join(output_dir, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"✓ Metadata saved: {metadata_path}")
        
        return {
            'model_path': model_path,
            'scaler_path': scaler_path,
            'features_path': features_path,
            'metadata_path': metadata_path
        }
    
    def run_pipeline(self, csv_file: str = None) -> Dict:
        """
        Execute complete model training and evaluation pipeline.
        
        Args:
            csv_file: Path to processed features CSV
            
        Returns:
            Dictionary with evaluation results
        """
        logger.info("=" * 80)
        logger.info("CHAMPIONS LEAGUE MODEL TRAINING & EVALUATION - Starting")
        logger.info("=" * 80 + "\n")
        
        try:
            # Load data
            self.load_data(csv_file)
            
            # Time-series split
            self.split_time_series()
            
            # Scale features
            self.scale_features()
            
            # Train models
            self.train_logistic_regression()
            self.train_xgboost_with_tuning()
            
            # Evaluate
            self.evaluate_models()
            
            # Print reports
            self.print_classification_reports()
            
            # Save models
            save_paths = self.save_models()
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ MODEL TRAINING & EVALUATION COMPLETE")
            logger.info("=" * 80)
            
            # Return summary
            return {
                'status': 'success',
                'best_model': self.best_model_name,
                'lr_log_loss': float(self.lr_log_loss),
                'xgb_log_loss': float(self.xgb_log_loss),
                'improvement': (self.lr_log_loss - self.xgb_log_loss) / self.lr_log_loss * 100 
                              if self.xgb_log_loss < self.lr_log_loss else 0,
                'save_paths': save_paths,
                'train_size': len(self.X_train),
                'test_size': len(self.X_test)
            }
            
        except Exception as e:
            logger.error(f"\n❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return {'status': 'failed', 'error': str(e)}


def main():
    """Main entry point for model training."""
    trainer = ChampionsLeagueModelTrainer()
    results = trainer.run_pipeline()
    
    return results['status'] == 'success'


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
