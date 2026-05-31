"""
PyTest suite for API-Football data extractor.

Tests the Champions League fixture extraction pipeline including:
- League ID discovery
- Fixture retrieval and parsing
- Data mapping
- MongoDB insertion with duplicate prevention
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.extraction.api_extractor import (
    APIFootballExtractor,
    insert_matches_to_mongodb,
    extract_and_store
)


class TestAPIFootballExtractorInitialization:
    """Test APIFootballExtractor initialization."""

    def test_initialization_with_api_key_argument(self):
        """Test initialization with explicit API key."""
        extractor = APIFootballExtractor(api_key="test-key-12345")
        assert extractor.api_key == "test-key-12345"
        assert extractor.min_delay == 0.5
        assert extractor.session is not None

    def test_initialization_custom_delay(self):
        """Test initialization with custom delay."""
        extractor = APIFootballExtractor(api_key="test-key", min_delay=2.0)
        assert extractor.min_delay == 2.0

    def test_initialization_missing_api_key(self):
        """Test initialization fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="RAPIDAPI_KEY not found"):
                APIFootballExtractor(api_key=None)

    def test_headers_built_correctly(self):
        """Test that request headers are built with correct structure."""
        extractor = APIFootballExtractor(api_key="test-key")
        assert "x-rapidapi-host" in extractor.headers
        assert "x-rapidapi-key" in extractor.headers
        assert extractor.headers["x-rapidapi-key"] == "test-key"

    def test_context_manager_support(self):
        """Test that extractor works as context manager."""
        with APIFootballExtractor(api_key="test-key") as extractor:
            assert extractor.api_key == "test-key"


class TestAPIFootballExtractorRequests:
    """Test API request functionality."""

    @patch('requests.Session.get')
    def test_make_request_success(self, mock_get):
        """Test successful API request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"leagues": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        extractor = APIFootballExtractor(api_key="test-key")
        result = extractor._make_request("/leagues")

        assert result == {"leagues": []}
        mock_get.assert_called_once()

    @patch('time.sleep')
    @patch('requests.Session.get')
    def test_make_request_applies_delay(self, mock_get, mock_sleep):
        """Test that delay is applied before request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        extractor = APIFootballExtractor(api_key="test-key", min_delay=1.5)
        extractor._make_request("/leagues")

        mock_sleep.assert_called_once_with(1.5)

    @patch('requests.Session.get')
    def test_make_request_connection_error(self, mock_get):
        """Test handling of connection errors."""
        import requests
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        extractor = APIFootballExtractor(api_key="test-key")
        result = extractor._make_request("/leagues")

        assert result is None

    @patch('requests.Session.get')
    def test_make_request_timeout(self, mock_get):
        """Test handling of timeouts."""
        import requests
        mock_get.side_effect = requests.Timeout("Request timed out")

        extractor = APIFootballExtractor(api_key="test-key")
        result = extractor._make_request("/leagues")

        assert result is None


class TestLeagueIDDiscovery:
    """Test Champions League league ID discovery."""

    @patch('src.extraction.api_extractor.APIFootballExtractor._make_request')
    def test_get_league_id_success(self, mock_request):
        """Test successful league ID discovery."""
        mock_request.return_value = {
            "leagues": [
                {"id": 1, "name": "Premier League"},
                {"id": 39, "name": "UEFA Champions League"},
                {"id": 140, "name": "LaLiga"}
            ]
        }

        extractor = APIFootballExtractor(api_key="test-key")
        league_id = extractor.get_league_id()

        assert league_id == 39
        assert extractor.league_id == 39

    @patch('src.extraction.api_extractor.APIFootballExtractor._make_request')
    def test_get_league_id_caching(self, mock_request):
        """Test that league ID is cached after first call."""
        mock_request.return_value = {
            "leagues": [{"id": 39, "name": "UEFA Champions League"}]
        }

        extractor = APIFootballExtractor(api_key="test-key")
        league_id_1 = extractor.get_league_id()
        league_id_2 = extractor.get_league_id()

        assert league_id_1 == league_id_2 == 39
        # Should only call _make_request once due to caching
        assert mock_request.call_count == 1

    @patch('src.extraction.api_extractor.APIFootballExtractor._make_request')
    def test_get_league_id_not_found(self, mock_request):
        """Test when Champions League is not found."""
        mock_request.return_value = {
            "leagues": [
                {"id": 1, "name": "Premier League"},
                {"id": 140, "name": "LaLiga"}
            ]
        }

        extractor = APIFootballExtractor(api_key="test-key")
        league_id = extractor.get_league_id()

        assert league_id is None

    @patch('src.extraction.api_extractor.APIFootballExtractor._make_request')
    def test_get_league_id_invalid_response(self, mock_request):
        """Test handling of invalid API response."""
        mock_request.return_value = None

        extractor = APIFootballExtractor(api_key="test-key")
        league_id = extractor.get_league_id()

        assert league_id is None


class TestFixturesParsing:
    """Test fixture parsing and data mapping."""

    def test_parse_fixture_finished_home_win(self):
        """Test parsing a finished match with home win."""
        fixture = {
            "fixture_id": 12345,
            "timestamp": 1695148800,  # Sep 19, 2023
            "status": "FT",
            "homeTeam": {"team_name": "Real Madrid"},
            "awayTeam": {"team_name": "Manchester City"},
            "goals": {"home": 2, "away": 1},
            "league": {"stage": "Group Stage"}
        }

        extractor = APIFootballExtractor(api_key="test-key")
        parsed = extractor.parse_fixture(fixture, 2023)

        assert parsed is not None
        assert parsed["home_team"] == "Real Madrid"
        assert parsed["away_team"] == "Manchester City"
        assert parsed["home_goals"] == 2
        assert parsed["away_goals"] == 1
        assert parsed["result"] == "H"
        assert parsed["season"] == "2023-2024"

    def test_parse_fixture_draw(self):
        """Test parsing a draw."""
        fixture = {
            "fixture_id": 12346,
            "timestamp": 1695148800,
            "status": "FT",
            "homeTeam": {"team_name": "Bayern Munich"},
            "awayTeam": {"team_name": "Paris Saint-Germain"},
            "goals": {"home": 2, "away": 2},
            "league": {"stage": "Group Stage"}
        }

        extractor = APIFootballExtractor(api_key="test-key")
        parsed = extractor.parse_fixture(fixture, 2023)

        assert parsed["result"] == "D"

    def test_parse_fixture_away_win(self):
        """Test parsing an away win."""
        fixture = {
            "fixture_id": 12347,
            "timestamp": 1695148800,
            "status": "FT",
            "homeTeam": {"team_name": "Arsenal"},
            "awayTeam": {"team_name": "Barcelona"},
            "goals": {"home": 1, "away": 3},
            "league": {"stage": "Knockout Stage"}
        }

        extractor = APIFootballExtractor(api_key="test-key")
        parsed = extractor.parse_fixture(fixture, 2023)

        assert parsed["result"] == "A"

    def test_parse_fixture_not_finished(self):
        """Test that non-finished matches are skipped."""
        fixture = {
            "fixture_id": 12348,
            "timestamp": 1695148800,
            "status": "NS",  # Not started
            "homeTeam": {"team_name": "Team A"},
            "awayTeam": {"team_name": "Team B"},
            "goals": {"home": None, "away": None}
        }

        extractor = APIFootballExtractor(api_key="test-key")
        parsed = extractor.parse_fixture(fixture, 2023)

        assert parsed is None

    def test_parse_fixture_missing_fields(self):
        """Test parsing with missing fields gracefully returns None."""
        fixture = {
            "fixture_id": 12349,
            "status": "FT"
            # Missing teams and goals
        }

        extractor = APIFootballExtractor(api_key="test-key")
        parsed = extractor.parse_fixture(fixture, 2023)

        # Should handle gracefully and return None or minimal data
        assert parsed is None or parsed.get("home_team") is None


class TestFixturesFetching:
    """Test fixture fetching for seasons."""

    @patch('src.extraction.api_extractor.APIFootballExtractor._make_request')
    def test_fetch_fixtures_for_season_success(self, mock_request):
        """Test successful fixture fetching for a season."""
        mock_request.return_value = {
            "fixtures": [
                {
                    "fixture_id": 1,
                    "status": "FT",
                    "timestamp": 1695148800,
                    "homeTeam": {"team_name": "Real Madrid"},
                    "awayTeam": {"team_name": "Manchester City"},
                    "goals": {"home": 2, "away": 1}
                }
            ]
        }

        extractor = APIFootballExtractor(api_key="test-key")
        extractor.league_id = 39
        fixtures = extractor.fetch_fixtures_for_season(2023)

        assert len(fixtures) == 1
        assert fixtures[0]["fixture_id"] == 1

    @patch('src.extraction.api_extractor.APIFootballExtractor._make_request')
    def test_fetch_fixtures_without_league_id(self, mock_request):
        """Test that fetching fails without league ID."""
        extractor = APIFootballExtractor(api_key="test-key")
        # Don't set league_id
        fixtures = extractor.fetch_fixtures_for_season(2023)

        assert fixtures == []
        mock_request.assert_not_called()


class TestMongoDBInsertion:
    """Test MongoDB insertion functionality."""

    def test_insert_matches_success(self):
        """Test successful match insertion."""
        mock_collection = MagicMock()
        mock_collection.update_one.return_value = MagicMock(
            upserted_id="test_id",
            modified_count=0
        )

        matches = [
            {
                "fixture_id": 123,
                "season": "2023-2024",
                "date": datetime(2023, 9, 19),
                "home_team": "Real Madrid",
                "away_team": "Manchester City",
                "home_goals": 2,
                "away_goals": 1,
                "result": "H"
            }
        ]

        inserted, skipped = insert_matches_to_mongodb(matches, mock_collection)

        assert inserted == 1
        assert skipped == 0
        mock_collection.update_one.assert_called_once()

    def test_insert_matches_duplicate_prevention(self):
        """Test that duplicates are skipped."""
        mock_collection = MagicMock()
        mock_collection.update_one.return_value = MagicMock(
            upserted_id=None,
            modified_count=0
        )

        matches = [
            {
                "fixture_id": 123,
                "home_team": "Real Madrid",
                "away_team": "Manchester City",
                "date": datetime(2023, 9, 19)
            }
        ]

        inserted, skipped = insert_matches_to_mongodb(matches, mock_collection)

        assert inserted == 0
        assert skipped == 1

    def test_insert_matches_error_handling(self):
        """Test error handling during insertion."""
        mock_collection = MagicMock()
        mock_collection.update_one.side_effect = Exception("DB error")

        matches = [{"fixture_id": 123, "home_team": "Team A"}]

        inserted, skipped = insert_matches_to_mongodb(matches, mock_collection)

        assert inserted == 0
        assert skipped == 0


class TestExtractAndStore:
    """Test the main extraction and storage orchestration."""

    @patch('src.extraction.api_extractor.insert_matches_to_mongodb')
    @patch('src.extraction.api_extractor.APIFootballExtractor.fetch_all_seasons')
    @patch('src.extraction.api_extractor.APIFootballExtractor.get_league_id')
    def test_extract_and_store_success(self, mock_league_id, mock_fetch_all, mock_insert):
        """Test successful extraction and storage."""
        mock_league_id.return_value = 39
        mock_fetch_all.return_value = {
            "2023-2024": [
                {
                    "fixture_id": 1,
                    "home_team": "Real Madrid",
                    "away_team": "Manchester City"
                }
            ]
        }
        mock_insert.return_value = (1, 0)

        mock_collection = MagicMock()

        stats = extract_and_store(
            mock_collection,
            api_key="test-key",
            seasons=[2023]
        )

        assert stats["total_inserted"] == 1
        assert stats["total_skipped"] == 0
        assert stats["seasons_extracted"] == 1
        assert "timestamp" in stats

    @patch('src.extraction.api_extractor.APIFootballExtractor.get_league_id')
    def test_extract_and_store_league_id_not_found(self, mock_league_id):
        """Test extraction fails when league ID not found."""
        mock_league_id.return_value = None

        mock_collection = MagicMock()

        with pytest.raises(RuntimeError, match="Failed to find Champions League league ID"):
            extract_and_store(mock_collection, api_key="test-key")


class TestDataIntegrity:
    """Test data integrity and schema validation."""

    def test_match_data_schema(self):
        """Test that parsed match data has correct schema."""
        fixture = {
            "fixture_id": 123,
            "timestamp": 1695148800,
            "status": "FT",
            "homeTeam": {"team_name": "Real Madrid"},
            "awayTeam": {"team_name": "Manchester City"},
            "goals": {"home": 2, "away": 1},
            "league": {"stage": "Group Stage"}
        }

        extractor = APIFootballExtractor(api_key="test-key")
        parsed = extractor.parse_fixture(fixture, 2023)

        required_fields = [
            "season", "date", "fixture_id", "home_team", "away_team",
            "home_goals", "away_goals", "result", "source"
        ]

        for field in required_fields:
            assert field in parsed, f"Missing required field: {field}"

    def test_match_data_types(self):
        """Test that parsed match data has correct types."""
        fixture = {
            "fixture_id": 123,
            "timestamp": 1695148800,
            "status": "FT",
            "homeTeam": {"team_name": "Real Madrid"},
            "awayTeam": {"team_name": "Manchester City"},
            "goals": {"home": 2, "away": 1},
            "league": {"stage": "Group Stage"}
        }

        extractor = APIFootballExtractor(api_key="test-key")
        parsed = extractor.parse_fixture(fixture, 2023)

        assert isinstance(parsed["season"], str)
        assert isinstance(parsed["home_goals"], int)
        assert isinstance(parsed["away_goals"], int)
        assert isinstance(parsed["result"], str)
        assert parsed["result"] in ["H", "A", "D"]
        assert isinstance(parsed["home_team"], str)
        assert isinstance(parsed["away_team"], str)


class TestSeasonMapping:
    """Test season mapping and formatting."""

    def test_season_string_format(self):
        """Test that season strings are formatted correctly."""
        fixture = {
            "fixture_id": 123,
            "timestamp": 1695148800,
            "status": "FT",
            "homeTeam": {"team_name": "Team A"},
            "awayTeam": {"team_name": "Team B"},
            "goals": {"home": 1, "away": 0},
            "league": {}
        }

        extractor = APIFootballExtractor(api_key="test-key")
        
        for year in [2015, 2019, 2023]:
            parsed = extractor.parse_fixture(fixture, year)
            expected = f"{year}-{year + 1}"
            assert parsed["season"] == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
