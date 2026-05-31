"""
API-Football Data Extractor for Champions League Historical Match Data.

Uses the Free API Live Football Data via RapidAPI to fetch Champions League
match fixtures for seasons 2015-2024. Includes:
- Programmatic League ID discovery
- Season-by-season fixture retrieval
- Data mapping to MongoDB schema
- Duplicate prevention with upsert operations

Environment Variables Required:
- RAPIDAPI_KEY: Your RapidAPI key for API-Football

Refs:
- https://rapidapi.com/api-sports/api/api-football
"""

import os
import time
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

import requests
from dotenv import load_dotenv
from pymongo.collection import Collection

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class APIFootballExtractor:
    """Extractor for Champions League data from API-Football."""

    # API Configuration
    BASE_URL = "https://free-api-live-football-data.p.rapidapi.com"
    
    # Supported seasons
    SEASONS = list(range(2015, 2024))  # 2015 through 2023
    
    # Championship League identifier (may vary depending on API version)
    LEAGUE_NAMES = ["UEFA Champions League", "Champions League", "UCL"]

    def __init__(self, api_key: Optional[str] = None, min_delay: float = 0.5):
        """
        Initialize the API Football extractor.

        Args:
            api_key: RapidAPI key. If None, loads from RAPIDAPI_KEY env variable.
            min_delay: Minimum delay between API requests in seconds
        """
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            raise ValueError(
                "RAPIDAPI_KEY not found. Set it in .env file or pass as argument."
            )
        
        self.min_delay = min_delay
        self.session = requests.Session()
        self.headers = self._build_headers()
        self.league_id = None

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers for RapidAPI."""
        return {
            "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com",
            "x-rapidapi-key": self.api_key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko)"
        }

    def _apply_delay(self):
        """Apply delay between requests to respect API rate limits."""
        time.sleep(self.min_delay)

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Make an API request with error handling.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response as dictionary, or None if request fails
        """
        try:
            self._apply_delay()
            url = f"{self.BASE_URL}{endpoint}"
            logger.debug(f"Requesting: {url} with params {params}")
            
            response = self.session.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"✓ Response received from {endpoint}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Request failed for {endpoint}: {e}")
            return None
        except ValueError as e:
            logger.error(f"✗ Invalid JSON response: {e}")
            return None

    def get_league_id(self) -> Optional[int]:
        """
        Programmatically find the Champions League league ID.

        Returns:
            League ID (integer), or None if not found
        """
        if self.league_id:
            return self.league_id

        logger.info("🔍 Searching for Champions League league ID...")
        
        try:
            # Request leagues endpoint to find Champions League
            response = self._make_request("/leagues")
            
            if not response or "leagues" not in response:
                logger.error("✗ Invalid response from /leagues endpoint")
                return None
            
            leagues = response.get("leagues", [])
            logger.debug(f"Found {len(leagues)} leagues in response")
            
            # Search for Champions League by name
            for league in leagues:
                league_name = league.get("name", "").upper()
                for target_name in self.LEAGUE_NAMES:
                    if target_name.upper() in league_name:
                        self.league_id = league.get("id")
                        logger.info(f"✓ Found Champions League: ID={self.league_id} ({league.get('name')})")
                        return self.league_id
            
            logger.warning("✗ Champions League not found in leagues list")
            return None
            
        except Exception as e:
            logger.error(f"✗ Error fetching league ID: {e}")
            return None

    def fetch_fixtures_for_season(self, season: int) -> List[Dict]:
        """
        Fetch all fixtures for a Champions League season.

        Args:
            season: Season year (e.g., 2023 for 2023-24 season)

        Returns:
            List of fixture dictionaries
        """
        if not self.league_id:
            logger.error("✗ League ID not set. Call get_league_id() first.")
            return []

        logger.info(f"📅 Fetching fixtures for {season} season...")

        try:
            params = {
                "league_id": self.league_id,
                "season": season
            }
            
            response = self._make_request("/fixtures", params=params)
            
            if not response:
                logger.error(f"✗ No response for season {season}")
                return []
            
            fixtures = response.get("fixtures", [])
            logger.info(f"✓ Retrieved {len(fixtures)} fixtures for season {season}")
            
            return fixtures
            
        except Exception as e:
            logger.error(f"✗ Error fetching fixtures for season {season}: {e}")
            return []

    def parse_fixture(self, fixture: Dict, season: int) -> Optional[Dict]:
        """
        Parse a fixture response into our MongoDB schema.

        Args:
            fixture: Raw fixture dictionary from API
            season: Season year

        Returns:
            Parsed match dictionary, or None if parsing fails
        """
        try:
            # Extract fixture status - only process finished matches
            status = fixture.get("status", "").upper()
            if status != "FT" and status != "FINISHED":
                return None  # Skip non-finished matches

            # Extract date
            fixture_date = fixture.get("timestamp")
            if fixture_date:
                try:
                    match_date = datetime.fromtimestamp(fixture_date)
                except:
                    match_date = None
            else:
                match_date = None

            # Extract team information
            home_team_data = fixture.get("homeTeam", {})
            away_team_data = fixture.get("awayTeam", {})
            
            home_team = home_team_data.get("team_name")
            away_team = away_team_data.get("team_name")
            
            # Extract goals
            goals = fixture.get("goals", {})
            home_goals = goals.get("home")
            away_goals = goals.get("away")
            
            # Determine result
            result = None
            if home_goals is not None and away_goals is not None:
                if home_goals > away_goals:
                    result = "H"  # Home win
                elif away_goals > home_goals:
                    result = "A"  # Away win
                else:
                    result = "D"  # Draw

            # Extract additional information
            fixture_id = fixture.get("fixture_id")
            league_stage = fixture.get("league", {}).get("stage")
            
            # Build match data
            match_data = {
                "season": f"{season}-{season + 1}",
                "date": match_date,
                "fixture_id": fixture_id,
                "home_team": home_team,
                "away_team": away_team,
                "home_goals": home_goals,
                "away_goals": away_goals,
                "result": result,
                "stage": league_stage,
                "status": status,
                "extracted_at": datetime.now(),
                "source": "api-football"
            }
            
            return match_data
            
        except Exception as e:
            logger.warning(f"⚠ Failed to parse fixture: {e}")
            return None

    def fetch_all_seasons(self, seasons: Optional[List[int]] = None) -> Dict[str, List[Dict]]:
        """
        Fetch Champions League data for multiple seasons.

        Args:
            seasons: List of season years to fetch. If None, fetches all supported seasons.

        Returns:
            Dictionary mapping season names to lists of parsed match data
        """
        if seasons is None:
            seasons = self.SEASONS

        all_data = {}

        for season in sorted(seasons):
            fixtures = self.fetch_fixtures_for_season(season)
            
            parsed_matches = []
            for fixture in fixtures:
                match_data = self.parse_fixture(fixture, season)
                if match_data:
                    parsed_matches.append(match_data)
            
            season_key = f"{season}-{season + 1}"
            all_data[season_key] = parsed_matches
            
            logger.info(
                f"Season {season_key}: {len(parsed_matches)} finished matches "
                f"(from {len(fixtures)} total fixtures)"
            )

        return all_data

    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("✓ Session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def insert_matches_to_mongodb(
    matches: List[Dict],
    collection: Collection
) -> Tuple[int, int]:
    """
    Insert match data into MongoDB collection with duplicate prevention.

    Args:
        matches: List of match dictionaries
        collection: MongoDB collection object

    Returns:
        Tuple of (inserted_count, skipped_count)
    """
    inserted_count = 0
    skipped_count = 0

    try:
        for match in matches:
            # Create unique key to avoid duplicates
            match_key = {
                "fixture_id": match.get("fixture_id"),
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "date": match.get("date"),
            }

            # Use upsert to avoid duplicates
            result = collection.update_one(
                match_key,
                {"$set": match},
                upsert=True
            )

            if result.upserted_id:
                inserted_count += 1
            elif result.modified_count > 0:
                inserted_count += 1
            else:
                skipped_count += 1

    except Exception as e:
        logger.error(f"✗ Failed to insert matches: {e}")
        return inserted_count, skipped_count

    logger.info(f"✓ Inserted: {inserted_count}, Skipped: {skipped_count}")
    return inserted_count, skipped_count


def extract_and_store(
    collection: Collection,
    api_key: Optional[str] = None,
    seasons: Optional[List[int]] = None
) -> Dict[str, int]:
    """
    Main function to extract Champions League data and store in MongoDB.

    Args:
        collection: MongoDB collection to insert data into
        api_key: RapidAPI key (uses RAPIDAPI_KEY env var if not provided)
        seasons: List of seasons to extract

    Returns:
        Dictionary with statistics
    """
    try:
        extractor = APIFootballExtractor(api_key=api_key)
        
        # Find league ID
        league_id = extractor.get_league_id()
        if not league_id:
            raise RuntimeError("Failed to find Champions League league ID")
        
        # Fetch all seasons
        all_data = extractor.fetch_all_seasons(seasons)
        
        total_inserted = 0
        total_skipped = 0
        
        # Insert data for each season
        for season_name, matches in all_data.items():
            inserted, skipped = insert_matches_to_mongodb(matches, collection)
            total_inserted += inserted
            total_skipped += skipped
        
        stats = {
            "total_inserted": total_inserted,
            "total_skipped": total_skipped,
            "seasons_extracted": len(all_data),
            "timestamp": datetime.now()
        }
        
        logger.info(f"📊 Extraction complete: {stats}")
        extractor.close()
        
        return stats
        
    except Exception as e:
        logger.error(f"✗ Extraction failed: {e}")
        raise
