"""
Feature Engineering Pipeline for Champions League Prediction Model.

Loads raw match data, engineers predictive time-series features without data leakage,
and produces a cleaned dataset ready for ML model training.

Key Features:
- Chronological data sorting (critical for time-series)
- Elo rating engine with pre-match recording (preventing future look-ahead)
- Rolling 5-match momentum with .shift(1) (preventing data leakage)
- Comprehensive data quality checks
- MongoDB storage of processed features
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import pandas as pd
import numpy as np
from pymongo import MongoClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChampionsLeagueFeatureEngineer:
    """Feature engineering pipeline for Champions League prediction."""
    
    # Elo rating constants
    ELO_BASE_RATING = 1500
    ELO_K_FACTOR = 32
    ELO_SCALE = 400
    
    def __init__(self, data_source: str = "json"):
        """
        Initialize feature engineer.
        
        Args:
            data_source: "json" for local JSON files, "mongodb" for MongoDB
        """
        self.data_source = data_source
        self.df = None
        self.team_elos = {}
        self.mongo_client = None
        self.processed_features = None
    
    def load_data(self, json_file: str = None) -> pd.DataFrame:
        """
        Load match data from JSON or MongoDB.
        
        Args:
            json_file: Path to JSON file (if data_source='json')
            
        Returns:
            DataFrame with raw match data
        """
        logger.info("📥 Loading raw match data...")
        
        if self.data_source == "json":
            if not json_file:
                json_file = "data/champions_league_matches.json"
            
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            df = pd.DataFrame(data)
            logger.info(f"✓ Loaded {len(df)} matches from JSON")
            
        else:
            # MongoDB loading (backup for when auth is fixed)
            try:
                self.mongo_client = MongoClient('mongodb://localhost:27017/', 
                                               serverSelectionTimeoutMS=5000)
                db = self.mongo_client['champions_league']
                matches_collection = db['matches']
                
                data = list(matches_collection.find())
                df = pd.DataFrame(data)
                logger.info(f"✓ Loaded {len(df)} matches from MongoDB")
            except Exception as e:
                logger.error(f"✗ Failed to load from MongoDB: {e}")
                raise
        
        return df
    
    def sort_chronologically(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sort DataFrame chronologically by date (CRITICAL for time-series).
        
        Args:
            df: Input DataFrame with match data
            
        Returns:
            Chronologically sorted DataFrame
        """
        logger.info("🔄 Sorting data chronologically...")
        
        # Convert date to datetime if it's a string
        df['date'] = pd.to_datetime(df['date'])
        
        # Sort by date ascending
        df = df.sort_values('date', ascending=True).reset_index(drop=True)
        
        logger.info(f"✓ Data sorted chronologically from {df['date'].min()} to {df['date'].max()}")
        
        return df
    
    def initialize_elo_ratings(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Initialize Elo ratings for all unique teams.
        
        Args:
            df: DataFrame with match data
            
        Returns:
            Dictionary mapping team names to initial Elo ratings
        """
        logger.info("⚙️  Initializing Elo ratings for all teams...")
        
        unique_teams = set()
        unique_teams.update(df['home_team'].unique())
        unique_teams.update(df['away_team'].unique())
        
        team_elos = {team: self.ELO_BASE_RATING for team in unique_teams}
        
        logger.info(f"✓ Initialized {len(team_elos)} teams at base rating {self.ELO_BASE_RATING}")
        
        return team_elos
    
    def calculate_elo_change(self, current_rating: float, opponent_rating: float, 
                            result: float) -> float:
        """
        Calculate Elo rating change using standard Elo formula.
        
        Args:
            current_rating: Current Elo rating of the player
            opponent_rating: Elo rating of opponent
            result: Match result (1=win, 0.5=draw, 0=loss)
            
        Returns:
            Change in Elo rating
        """
        expected_score = 1 / (1 + 10 ** ((opponent_rating - current_rating) / self.ELO_SCALE))
        elo_change = self.ELO_K_FACTOR * (result - expected_score)
        return elo_change
    
    def engineer_elo_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer Elo rating features with pre-match recording.
        
        CRITICAL: Records Elo BEFORE updating to prevent data leakage.
        
        Args:
            df: Chronologically sorted DataFrame
            
        Returns:
            DataFrame with Home_Elo_Pre and Away_Elo_Pre columns
        """
        logger.info("🏆 Engineering Elo rating features (pre-match recording)...")
        
        # Initialize team Elos
        self.team_elos = self.initialize_elo_ratings(df)
        
        home_elo_pre = []
        away_elo_pre = []
        
        # Iterate chronologically through matches
        for idx, row in df.iterrows():
            home_team = row['home_team']
            away_team = row['away_team']
            home_goals = row['home_goals']
            away_goals = row['away_goals']
            
            # CRITICAL: Record pre-match ratings BEFORE updating
            home_elo_pre.append(self.team_elos[home_team])
            away_elo_pre.append(self.team_elos[away_team])
            
            # Determine result (1=win, 0.5=draw, 0=loss)
            if home_goals > away_goals:
                home_result = 1.0
                away_result = 0.0
            elif home_goals < away_goals:
                home_result = 0.0
                away_result = 1.0
            else:
                home_result = 0.5
                away_result = 0.5
            
            # Calculate Elo changes
            home_elo_change = self.calculate_elo_change(
                self.team_elos[home_team],
                self.team_elos[away_team],
                home_result
            )
            away_elo_change = self.calculate_elo_change(
                self.team_elos[away_team],
                self.team_elos[home_team],
                away_result
            )
            
            # Update team ratings AFTER recording
            self.team_elos[home_team] += home_elo_change
            self.team_elos[away_team] += away_elo_change
            
            if (idx + 1) % 100 == 0:
                logger.debug(f"  Processed {idx + 1}/{len(df)} matches for Elo ratings")
        
        df['Home_Elo_Pre'] = home_elo_pre
        df['Away_Elo_Pre'] = away_elo_pre
        
        logger.info(f"✓ Engineered Elo features for {len(df)} matches")
        logger.info(f"  Home Elo range: {df['Home_Elo_Pre'].min():.1f} - {df['Home_Elo_Pre'].max():.1f}")
        logger.info(f"  Away Elo range: {df['Away_Elo_Pre'].min():.1f} - {df['Away_Elo_Pre'].max():.1f}")
        
        return df
    
    def engineer_rolling_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer rolling 5-match momentum features with .shift(1) anti-leakage.
        
        CRITICAL: Uses .shift(1) to ensure Match N only sees data from matches N-5 to N-1.
        
        Args:
            df: DataFrame with Elo features
            
        Returns:
            DataFrame with rolling momentum features
        """
        logger.info("📊 Engineering rolling momentum features (with .shift(1) anti-leakage)...")
        
        # Initialize feature columns with NaN
        df['Home_Rolling_Goals_Scored'] = np.nan
        df['Home_Rolling_Goals_Conceded'] = np.nan
        df['Away_Rolling_Goals_Scored'] = np.nan
        df['Away_Rolling_Goals_Conceded'] = np.nan
        
        # Get unique teams
        unique_teams = set()
        unique_teams.update(df['home_team'].unique())
        unique_teams.update(df['away_team'].unique())
        
        logger.info(f"  Calculating rolling features for {len(unique_teams)} teams...")
        
        # For each team, calculate rolling averages
        for team in unique_teams:
            # Get all matches for this team (home or away)
            team_home_matches = df[df['home_team'] == team].copy()
            team_away_matches = df[df['away_team'] == team].copy()
            
            # Process home matches
            if len(team_home_matches) > 0:
                # Goals scored when home
                goals_scored = team_home_matches['home_goals'].values
                # Goals conceded when home
                goals_conceded = team_home_matches['away_goals'].values
                
                # Apply rolling window with shift to prevent leakage
                # CRITICAL: shift(1) means we look at the previous 5 matches, not the current one
                rolling_scored = pd.Series(goals_scored).rolling(window=5, min_periods=1).mean().shift(1).values
                rolling_conceded = pd.Series(goals_conceded).rolling(window=5, min_periods=1).mean().shift(1).values
                
                # Assign back to original DataFrame indices
                df.loc[team_home_matches.index, 'Home_Rolling_Goals_Scored'] = rolling_scored
                df.loc[team_home_matches.index, 'Home_Rolling_Goals_Conceded'] = rolling_conceded
            
            # Process away matches
            if len(team_away_matches) > 0:
                # Goals scored when away
                goals_scored = team_away_matches['away_goals'].values
                # Goals conceded when away
                goals_conceded = team_away_matches['home_goals'].values
                
                # Apply rolling window with shift to prevent leakage
                rolling_scored = pd.Series(goals_scored).rolling(window=5, min_periods=1).mean().shift(1).values
                rolling_conceded = pd.Series(goals_conceded).rolling(window=5, min_periods=1).mean().shift(1).values
                
                # Assign back to original DataFrame indices
                df.loc[team_away_matches.index, 'Away_Rolling_Goals_Scored'] = rolling_scored
                df.loc[team_away_matches.index, 'Away_Rolling_Goals_Conceded'] = rolling_conceded
        
        logger.info(f"✓ Engineered rolling momentum features")
        logger.info(f"  Home Rolling Goals Scored: mean={df['Home_Rolling_Goals_Scored'].mean():.2f} (before NaN removal)")
        logger.info(f"  Home Rolling Goals Conceded: mean={df['Home_Rolling_Goals_Conceded'].mean():.2f} (before NaN removal)")
        
        return df
    
    def engineer_target_variable(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create target variable for classification.
        
        Args:
            df: DataFrame with match results
            
        Returns:
            DataFrame with Target column (1=Home Win, 0=Draw, 2=Away Win)
        """
        logger.info("🎯 Engineering target variable...")
        
        def map_result(result: str) -> int:
            """Map result string to target value."""
            if result == 'H':
                return 1  # Home win
            elif result == 'D':
                return 0  # Draw
            else:  # 'A'
                return 2  # Away win
        
        df['Target'] = df['result'].apply(map_result)
        
        # Show distribution
        target_dist = df['Target'].value_counts().sort_index()
        logger.info(f"✓ Target variable created")
        logger.info(f"  Home Wins (1): {target_dist.get(1, 0)} ({target_dist.get(1, 0)/len(df)*100:.1f}%)")
        logger.info(f"  Draws (0): {target_dist.get(0, 0)} ({target_dist.get(0, 0)/len(df)*100:.1f}%)")
        logger.info(f"  Away Wins (2): {target_dist.get(2, 0)} ({target_dist.get(2, 0)/len(df)*100:.1f}%)")
        
        return df
    
    def clean_and_select_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove NaN values and select only predictive features.
        
        Args:
            df: DataFrame with engineered features
            
        Returns:
            Clean DataFrame ready for model training
        """
        logger.info("🧹 Cleaning data and selecting features...")
        
        initial_count = len(df)
        
        # Drop rows with NaN values in rolling window columns
        # (first ~5 matches per team won't have complete rolling history)
        df_clean = df.dropna(subset=[
            'Home_Rolling_Goals_Scored',
            'Home_Rolling_Goals_Conceded',
            'Away_Rolling_Goals_Scored',
            'Away_Rolling_Goals_Conceded'
        ])
        
        removed_count = initial_count - len(df_clean)
        logger.info(f"✓ Removed {removed_count} matches with NaN values ({removed_count/initial_count*100:.1f}%)")
        logger.info(f"  Remaining: {len(df_clean)} matches")
        
        # Select predictive features
        feature_columns = [
            'season',
            'date',
            'home_team',
            'away_team',
            'Home_Elo_Pre',
            'Away_Elo_Pre',
            'Home_Rolling_Goals_Scored',
            'Home_Rolling_Goals_Conceded',
            'Away_Rolling_Goals_Scored',
            'Away_Rolling_Goals_Conceded',
            'Target'
        ]
        
        df_processed = df_clean[feature_columns].copy()
        
        logger.info(f"✓ Selected {len(feature_columns)} features")
        logger.info(f"  Features: {', '.join(feature_columns[:5])}...")
        
        # Data quality check
        logger.info(f"\n📋 Data Quality Check:")
        logger.info(f"  Total matches: {len(df_processed)}")
        logger.info(f"  Seasons: {df_processed['season'].nunique()}")
        logger.info(f"  Teams: {len(set(df_processed['home_team'].unique()) | set(df_processed['away_team'].unique()))}")
        logger.info(f"  Date range: {df_processed['date'].min()} to {df_processed['date'].max()}")
        logger.info(f"  Missing values: {df_processed.isnull().sum().sum()}")
        logger.info(f"  Numeric columns range check:")
        
        numeric_cols = ['Home_Elo_Pre', 'Away_Elo_Pre', 
                       'Home_Rolling_Goals_Scored', 'Home_Rolling_Goals_Conceded',
                       'Away_Rolling_Goals_Scored', 'Away_Rolling_Goals_Conceded']
        
        for col in numeric_cols:
            logger.info(f"    {col}: {df_processed[col].min():.2f} - {df_processed[col].max():.2f} (mean={df_processed[col].mean():.2f})")
        
        return df_processed
    
    def save_to_mongodb(self, df: pd.DataFrame) -> bool:
        """
        Save processed features to MongoDB collection.
        
        Args:
            df: Processed features DataFrame
            
        Returns:
            True if successful
        """
        logger.info("💾 Saving processed features to MongoDB...")
        
        try:
            if not self.mongo_client:
                self.mongo_client = MongoClient('mongodb://localhost:27017/', 
                                               serverSelectionTimeoutMS=5000)
            
            db = self.mongo_client['champions_league']
            
            # Try to drop existing collection
            try:
                db['processed_features'].drop()
                logger.info("  Dropped existing processed_features collection")
            except:
                pass
            
            # Convert DataFrame to records
            records = df.to_dict('records')
            
            # Convert date to datetime objects for MongoDB
            for record in records:
                if isinstance(record['date'], str):
                    record['date'] = pd.to_datetime(record['date'])
            
            # Insert into MongoDB
            result = db['processed_features'].insert_many(records)
            
            logger.info(f"✓ Inserted {len(result.inserted_ids)} records into processed_features collection")
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠ Could not save to MongoDB: {e}")
            logger.info("  (Will save to CSV as fallback)")
            
            # Fallback to CSV
            csv_file = "data/processed_features.csv"
            df.to_csv(csv_file, index=False)
            logger.info(f"✓ Saved to {csv_file}")
            
            return True
    
    def run_pipeline(self, json_file: str = None) -> Optional[pd.DataFrame]:
        """
        Execute complete feature engineering pipeline.
        
        Args:
            json_file: Path to JSON input file
            
        Returns:
            Processed features DataFrame
        """
        logger.info("=" * 80)
        logger.info("CHAMPIONS LEAGUE FEATURE ENGINEERING PIPELINE - Starting")
        logger.info("=" * 80 + "\n")
        
        try:
            # Step 1: Load data
            df = self.load_data(json_file)
            
            # Step 2: Sort chronologically
            df = self.sort_chronologically(df)
            
            # Step 3: Engineer Elo features
            df = self.engineer_elo_features(df)
            
            # Step 4: Engineer rolling momentum features
            df = self.engineer_rolling_momentum_features(df)
            
            # Step 5: Engineer target variable
            df = self.engineer_target_variable(df)
            
            # Step 6: Clean and select features
            df_processed = self.clean_and_select_features(df)
            
            # Step 7: Save to MongoDB
            self.save_to_mongodb(df_processed)
            
            self.processed_features = df_processed
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ FEATURE ENGINEERING COMPLETE")
            logger.info("=" * 80)
            
            return df_processed
            
        except Exception as e:
            logger.error(f"\n❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        finally:
            if self.mongo_client:
                self.mongo_client.close()


def main():
    """Main entry point for feature engineering."""
    engineer = ChampionsLeagueFeatureEngineer(data_source="json")
    df = engineer.run_pipeline()
    
    if df is not None:
        logger.info(f"\n🎉 Pipeline produced {len(df)} processed matches")
        return True
    else:
        logger.error("\n❌ Pipeline failed to produce output")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
