"""
PyTest suite for FBRef Champions League web scraper.

Tests web scraping functionality, data parsing, MongoDB insertion,
and error handling scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup

from src.extraction.scraper import (
    FBRefScraper,
    insert_matches_to_mongodb,
    scrape_and_store
)


class TestFBRefScraperInitialization:
    """Test FBRefScraper initialization and configuration."""

    def test_initialization_default_params(self):
        """Test scraper initialization with default parameters."""
        scraper = FBRefScraper()
        assert scraper.min_delay == 1.0
        assert scraper.max_delay == 5.0
        assert scraper.session is not None

    def test_initialization_custom_delays(self):
        """Test scraper initialization with custom delay parameters."""
        scraper = FBRefScraper(min_delay=2.0, max_delay=10.0)
        assert scraper.min_delay == 2.0
        assert scraper.max_delay == 10.0

    def test_headers_set(self):
        """Test that User-Agent header is properly set."""
        scraper = FBRefScraper()
        assert "User-Agent" in scraper.session.headers
        assert "Mozilla" in scraper.session.headers["User-Agent"]

    def test_fbref_seasons_mapping(self):
        """Test that FBREF_SEASONS mapping is correct."""
        assert 2023 in FBRefScraper.FBREF_SEASONS
        assert FBRefScraper.FBREF_SEASONS[2023] == "2023-2024"
        assert FBRefScraper.FBREF_SEASONS[2015] == "2015-2016"


class TestFBRefScraperDelays:
    """Test random delay functionality."""

    @patch('time.sleep')
    @patch('random.uniform')
    def test_apply_random_delay(self, mock_uniform, mock_sleep):
        """Test that random delay is applied correctly."""
        mock_uniform.return_value = 3.5
        scraper = FBRefScraper(min_delay=1.0, max_delay=5.0)
        
        scraper._apply_random_delay()
        
        mock_uniform.assert_called_once_with(1.0, 5.0)
        mock_sleep.assert_called_once_with(3.5)

    @patch('time.sleep')
    def test_delay_within_range(self, mock_sleep):
        """Test that delays are within specified range."""
        scraper = FBRefScraper(min_delay=2.0, max_delay=3.0)
        
        for _ in range(5):
            scraper._apply_random_delay()
        
        # Verify sleep was called 5 times
        assert mock_sleep.call_count == 5


class TestFBRefScraperFetching:
    """Test web page fetching functionality."""

    @patch('src.extraction.scraper.FBRefScraper._apply_random_delay')
    @patch('requests.Session.get')
    def test_fetch_page_success(self, mock_get, mock_delay):
        """Test successful page fetch."""
        mock_response = MagicMock()
        mock_response.text = "<html>Test content</html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        scraper = FBRefScraper()
        content = scraper._fetch_page("http://example.com")

        assert content == "<html>Test content</html>"
        mock_get.assert_called_once()
        mock_delay.assert_called_once()

    @patch('src.extraction.scraper.FBRefScraper._apply_random_delay')
    @patch('requests.Session.get')
    def test_fetch_page_failure_connection_error(self, mock_get, mock_delay):
        """Test page fetch with connection error."""
        import requests
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        scraper = FBRefScraper()
        content = scraper._fetch_page("http://example.com")

        assert content is None

    @patch('src.extraction.scraper.FBRefScraper._apply_random_delay')
    @patch('requests.Session.get')
    def test_fetch_page_timeout(self, mock_get, mock_delay):
        """Test page fetch with timeout."""
        import requests
        mock_get.side_effect = requests.Timeout("Request timed out")

        scraper = FBRefScraper()
        content = scraper._fetch_page("http://example.com")

        assert content is None


class TestFBRefScraperParsing:
    """Test HTML parsing and match data extraction."""

    def test_parse_match_data_valid_row(self):
        """Test parsing a valid match row."""
        scraper = FBRefScraper()
        
        # Create mock row with proper structure
        html = """
        <tr>
            <td>2024-01-15</td>
            <td></td>
            <td>Barcelona</td>
            <td>3–1</td>
            <td>Real Madrid</td>
        </tr>
        """
        row = BeautifulSoup(html, 'html.parser').find('tr')

        match_data = scraper._parse_match_data(row, "2023-2024")

        assert match_data is not None
        assert match_data["season"] == "2023-2024"
        assert match_data["home_team"] == "Barcelona"
        assert match_data["away_team"] == "Real Madrid"
        assert match_data["home_goals"] == 3
        assert match_data["away_goals"] == 1
        assert match_data["result"] == "H"  # Home win

    def test_parse_match_data_draw(self):
        """Test parsing a match that ends in a draw."""
        scraper = FBRefScraper()
        
        html = """
        <tr>
            <td>2024-01-15</td>
            <td></td>
            <td>Team A</td>
            <td>2–2</td>
            <td>Team B</td>
        </tr>
        """
        row = BeautifulSoup(html, 'html.parser').find('tr')

        match_data = scraper._parse_match_data(row, "2023-2024")

        assert match_data["result"] == "D"  # Draw
        assert match_data["home_goals"] == 2
        assert match_data["away_goals"] == 2

    def test_parse_match_data_away_win(self):
        """Test parsing a match with away team win."""
        scraper = FBRefScraper()
        
        html = """
        <tr>
            <td>2024-01-15</td>
            <td></td>
            <td>Team A</td>
            <td>1–3</td>
            <td>Team B</td>
        </tr>
        """
        row = BeautifulSoup(html, 'html.parser').find('tr')

        match_data = scraper._parse_match_data(row, "2023-2024")

        assert match_data["result"] == "A"  # Away win
        assert match_data["home_goals"] == 1
        assert match_data["away_goals"] == 3

    def test_parse_match_data_invalid_row(self):
        """Test parsing with insufficient cells."""
        scraper = FBRefScraper()
        
        # Only 3 cells - should fail (needs at least 5)
        html = "<tr><td>Cell 1</td><td>Cell 2</td><td>Cell 3</td></tr>"
        row = BeautifulSoup(html, 'html.parser').find('tr')

        match_data = scraper._parse_match_data(row, "2023-2024")

        assert match_data is None


class TestFBRefScraperScraping:
    """Test scraping functionality."""

    @patch('src.extraction.scraper.FBRefScraper._fetch_page')
    def test_scrape_season_success(self, mock_fetch):
        """Test scraping a single season."""
        # Mock HTML response
        html = """
        <html>
            <table>
                <tbody>
                    <tr>
                        <td>2024-01-15</td>
                        <td></td>
                        <td>Team A</td>
                        <td>2–1</td>
                        <td>Team B</td>
                    </tr>
                </tbody>
            </table>
        </html>
        """
        mock_fetch.return_value = html

        scraper = FBRefScraper()
        matches = scraper.scrape_season(2023)

        assert len(matches) > 0
        assert matches[0]["season"] == "2023-2024"
        assert matches[0]["home_team"] == "Team A"

    @patch('src.extraction.scraper.FBRefScraper._fetch_page')
    def test_scrape_season_fetch_failure(self, mock_fetch):
        """Test scraping when page fetch fails."""
        mock_fetch.return_value = None

        scraper = FBRefScraper()
        matches = scraper.scrape_season(2023)

        assert len(matches) == 0

    def test_scrape_unsupported_season(self):
        """Test scraping with unsupported season year."""
        scraper = FBRefScraper()
        matches = scraper.scrape_season(1990)

        assert len(matches) == 0

    @patch('src.extraction.scraper.FBRefScraper.scrape_season')
    def test_scrape_all_seasons(self, mock_scrape_season):
        """Test scraping multiple seasons."""
        mock_scrape_season.side_effect = [
            [{"season": "2023-2024", "home_team": "A", "away_team": "B"}],
            [{"season": "2022-2023", "home_team": "C", "away_team": "D"}],
        ]

        scraper = FBRefScraper()
        all_data = scraper.scrape_all_seasons([2023, 2022])

        assert len(all_data) == 2
        assert "2023-2024" in all_data
        assert "2022-2023" in all_data

    def test_close_session(self):
        """Test closing the session."""
        scraper = FBRefScraper()
        scraper.close()
        # Should not raise an error


class TestMongoDBInsertion:
    """Test MongoDB insertion functionality."""

    def test_insert_matches_to_mongodb_success(self):
        """Test successful match insertion."""
        mock_collection = MagicMock()
        mock_collection.update_one.return_value = MagicMock(
            upserted_id="test_id",
            modified_count=0
        )

        matches = [
            {
                "season": "2023-2024",
                "date": datetime(2024, 1, 15),
                "home_team": "Team A",
                "away_team": "Team B",
                "home_goals": 2,
                "away_goals": 1,
            }
        ]

        inserted, skipped = insert_matches_to_mongodb(matches, mock_collection)

        assert inserted == 1
        assert skipped == 0
        mock_collection.update_one.assert_called_once()

    def test_insert_matches_to_mongodb_duplicate(self):
        """Test insertion with duplicate match (should skip)."""
        mock_collection = MagicMock()
        mock_collection.update_one.return_value = MagicMock(
            upserted_id=None,
            modified_count=0
        )

        matches = [
            {
                "season": "2023-2024",
                "date": datetime(2024, 1, 15),
                "home_team": "Team A",
                "away_team": "Team B",
            }
        ]

        inserted, skipped = insert_matches_to_mongodb(matches, mock_collection)

        assert inserted == 0
        assert skipped == 1

    def test_insert_matches_to_mongodb_error(self):
        """Test insertion with error."""
        mock_collection = MagicMock()
        mock_collection.update_one.side_effect = Exception("DB error")

        matches = [
            {
                "season": "2023-2024",
                "date": datetime(2024, 1, 15),
                "home_team": "Team A",
                "away_team": "Team B",
            }
        ]

        inserted, skipped = insert_matches_to_mongodb(matches, mock_collection)

        assert inserted == 0
        assert skipped == 0


class TestScrapeAndStore:
    """Test the main scrape_and_store orchestration function."""

    @patch('src.extraction.scraper.insert_matches_to_mongodb')
    @patch('src.extraction.scraper.FBRefScraper.scrape_all_seasons')
    def test_scrape_and_store_success(self, mock_scrape_all, mock_insert):
        """Test successful scrape and store operation."""
        mock_scrape_all.return_value = {
            "2023-2024": [{"season": "2023-2024", "home_team": "A"}]
        }
        mock_insert.return_value = (1, 0)

        mock_collection = MagicMock()

        stats = scrape_and_store(mock_collection, seasons=[2023])

        assert stats["total_inserted"] == 1
        assert stats["total_skipped"] == 0
        assert stats["seasons_scraped"] == 1
        assert "timestamp" in stats


class TestDataValidation:
    """Test data validation in scraped matches."""

    def test_match_data_has_required_fields(self):
        """Test that parsed match data has all required fields."""
        scraper = FBRefScraper()
        
        html = """
        <tr>
            <td>2024-01-15</td>
            <td></td>
            <td>Team A</td>
            <td>2–1</td>
            <td>Team B</td>
        </tr>
        """
        row = BeautifulSoup(html, 'html.parser').find('tr')
        match_data = scraper._parse_match_data(row, "2023-2024")

        required_fields = [
            "season", "date", "home_team", "away_team",
            "home_goals", "away_goals", "result", "scraped_at", "source"
        ]

        for field in required_fields:
            assert field in match_data

    def test_match_data_types(self):
        """Test that parsed match data has correct types."""
        scraper = FBRefScraper()
        
        html = """
        <tr>
            <td>2024-01-15</td>
            <td></td>
            <td>Team A</td>
            <td>2–1</td>
            <td>Team B</td>
        </tr>
        """
        row = BeautifulSoup(html, 'html.parser').find('tr')
        match_data = scraper._parse_match_data(row, "2023-2024")

        assert isinstance(match_data["season"], str)
        assert isinstance(match_data["home_goals"], int)
        assert isinstance(match_data["away_goals"], int)
        assert isinstance(match_data["result"], str)
        assert match_data["result"] in ["H", "A", "D"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
