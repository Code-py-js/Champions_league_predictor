"""
FBRef Web Scraper for Champions League Historical Data.

Scrapes Champions League match data from Football Reference (FBRef)
for seasons 2015-2024. Implements random delays to avoid IP bans
and inserts raw data into MongoDB.

Data sources:
- FBRef Champions League match results and statistics
- Seasons: 2015-16 through 2023-24
"""

import requests
import time
import random
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
from pymongo.collection import Collection
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FBRefScraper:
    """Scraper for Champions League data from Football Reference."""

    # FBRef base URLs for Champions League
    FBREF_BASE_URL = "https://fbref.com/en/comps/8/"
    FBREF_SEASONS = {
        2015: "2015-2016",
        2016: "2016-2017",
        2017: "2017-2018",
        2018: "2018-2019",
        2019: "2019-2020",
        2020: "2020-2021",
        2021: "2021-2022",
        2022: "2022-2023",
        2023: "2023-2024",
    }

    # User-Agent to avoid blocking
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/91.0.4472.124 Safari/537.36"
    }

    def __init__(self, min_delay: float = 1.0, max_delay: float = 5.0):
        """
        Initialize the FBRef scraper.

        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _apply_random_delay(self):
        """Apply random delay to prevent IP bans."""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.info(f"⏱ Applying delay: {delay:.2f}s")
        time.sleep(delay)

    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a web page with error handling.

        Args:
            url: URL to fetch

        Returns:
            Page content as string, or None if fetch fails
        """
        try:
            self._apply_random_delay()
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            logger.debug(f"✓ Fetched: {url}")
            return response.text
        except Exception as e:
            logger.error(f"✗ Failed to fetch {url}: {e}")
            return None

    def _parse_match_data(
        self,
        row: BeautifulSoup,
        season: str
    ) -> Optional[Dict]:
        """
        Parse a match row from FBRef HTML.

        Args:
            row: BeautifulSoup table row element
            season: Season identifier (e.g., "2023-2024")

        Returns:
            Dictionary with parsed match data, or None if parsing fails
        """
        try:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 5:
                return None

            # Extract date (first cell)
            date_cell = cells[0].get_text(strip=True)
            try:
                match_date = pd.to_datetime(date_cell)
            except:
                match_date = None

            # Extract teams - flexible indexing
            home_team = None
            away_team = None
            score_text = None
            
            # Try to find score and teams by looking for the score pattern
            # Skip first cell (usually date) when searching for score
            for i, cell in enumerate(cells[1:], start=1):
                cell_text = cell.get_text(strip=True)
                # Score should be numeric-dash-numeric pattern
                if ('–' in cell_text or '-' in cell_text) and any(c.isdigit() for c in cell_text):
                    # Found score
                    score_text = cell_text
                    if i > 1:
                        home_team = cells[i-1].get_text(strip=True)
                    if i < len(cells) - 1:
                        away_team = cells[i+1].get_text(strip=True)
                    break
            
            # If score not found by pattern, use fixed indices
            if score_text is None and len(cells) >= 5:
                home_team = cells[2].get_text(strip=True) if not home_team else home_team
                score_text = cells[3].get_text(strip=True)
                away_team = cells[4].get_text(strip=True) if not away_team else away_team

            # Parse score
            home_goals = None
            away_goals = None
            if score_text:
                try:
                    # Try both dash types
                    if '–' in score_text:
                        score_parts = score_text.split('–')
                    else:
                        score_parts = score_text.split('-')
                    home_goals = int(score_parts[0].strip())
                    away_goals = int(score_parts[1].strip())
                except:
                    home_goals = None
                    away_goals = None

            # Determine result
            result = None
            if home_goals is not None and away_goals is not None:
                if home_goals > away_goals:
                    result = "H"  # Home win
                elif away_goals > home_goals:
                    result = "A"  # Away win
                else:
                    result = "D"  # Draw

            # Extract competition stage (if available)
            stage = None
            for cell in cells:
                cell_text = cell.get_text(strip=True)
                if any(stage_name in cell_text for stage_name in 
                       ['Group', 'Qualifying', 'Round of 16', 'Quarterfinals', 'Semifinals', 'Final']):
                    stage = cell_text
                    break

            match_data = {
                "season": season,
                "date": match_date,
                "home_team": home_team,
                "away_team": away_team,
                "home_goals": home_goals,
                "away_goals": away_goals,
                "result": result,
                "stage": stage,
                "scraped_at": datetime.now(),
                "source": "fbref.com"
            }

            return match_data

        except Exception as e:
            logger.warning(f"⚠ Failed to parse match row: {e}")
            return None

    def scrape_season(self, season_year: int) -> List[Dict]:
        """
        Scrape all Champions League matches for a specific season.

        Args:
            season_year: Year of season start (e.g., 2023 for 2023-24 season)

        Returns:
            List of match dictionaries
        """
        if season_year not in self.FBREF_SEASONS:
            logger.error(f"Season {season_year} not supported")
            return []

        season_name = self.FBREF_SEASONS[season_year]
        logger.info(f"🔍 Starting scrape for season {season_name}")

        # Construct URL
        season_url = f"{self.FBREF_BASE_URL}{season_year}-{season_year + 1}/schedule/"

        # Fetch page
        page_content = self._fetch_page(season_url)
        if not page_content:
            return []

        # Parse HTML
        try:
            soup = BeautifulSoup(page_content, 'html.parser')
            matches = []

            # Find all match rows in tables
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables on page")

            for table in tables:
                tbody = table.find('tbody')
                if not tbody:
                    continue

                rows = tbody.find_all('tr')
                logger.info(f"Processing {len(rows)} rows from table")

                for row in rows:
                    match_data = self._parse_match_data(row, season_name)
                    if match_data:
                        matches.append(match_data)

            logger.info(f"✓ Scraped {len(matches)} matches for season {season_name}")
            return matches

        except Exception as e:
            logger.error(f"✗ Failed to parse page for season {season_name}: {e}")
            return []

    def scrape_all_seasons(self, seasons: Optional[List[int]] = None) -> Dict[str, List[Dict]]:
        """
        Scrape Champions League data for multiple seasons.

        Args:
            seasons: List of season years to scrape. If None, scrapes all available.

        Returns:
            Dictionary mapping season names to lists of match data
        """
        if seasons is None:
            seasons = list(self.FBREF_SEASONS.keys())

        all_data = {}

        for season_year in sorted(seasons):
            season_name = self.FBREF_SEASONS.get(season_year)
            if not season_name:
                logger.warning(f"⚠ Skipping unsupported season: {season_year}")
                continue

            matches = self.scrape_season(season_year)
            all_data[season_name] = matches
            logger.info(f"Season {season_name}: {len(matches)} matches")

        return all_data

    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("✓ Session closed")


def insert_matches_to_mongodb(
    matches: List[Dict],
    collection: Collection
) -> Tuple[int, int]:
    """
    Insert match data into MongoDB collection.

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
                "season": match.get("season"),
                "date": match.get("date"),
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
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


def scrape_and_store(
    collection: Collection,
    seasons: Optional[List[int]] = None,
    min_delay: float = 1.0,
    max_delay: float = 5.0
) -> Dict[str, int]:
    """
    Main function to scrape and store Champions League data.

    Args:
        collection: MongoDB collection to insert data into
        seasons: List of seasons to scrape
        min_delay: Minimum delay between requests
        max_delay: Maximum delay between requests

    Returns:
        Dictionary with statistics
    """
    scraper = FBRefScraper(min_delay=min_delay, max_delay=max_delay)

    try:
        all_data = scraper.scrape_all_seasons(seasons)
        
        total_inserted = 0
        total_skipped = 0

        for season_name, matches in all_data.items():
            inserted, skipped = insert_matches_to_mongodb(matches, collection)
            total_inserted += inserted
            total_skipped += skipped

        stats = {
            "total_inserted": total_inserted,
            "total_skipped": total_skipped,
            "seasons_scraped": len(all_data),
            "timestamp": datetime.now()
        }

        logger.info(f"📊 Scraping complete: {stats}")
        return stats

    finally:
        scraper.close()
