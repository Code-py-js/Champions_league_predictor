"""
PyTest suite for MongoDB client module.

Tests connection handling, database creation, and error scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from src.database.mongo_client import MongoDBClient, get_mongo_client


class TestMongoDBClient:
    """Test suite for MongoDBClient class."""

    def test_initialization(self):
        """Test MongoDB client initialization with default parameters."""
        client = MongoDBClient()
        assert client.host == "localhost"
        assert client.port == 27017
        assert client.database_name == "champions_league"
        assert client.timeout == 5000
        assert client.client is None
        assert client.db is None

    def test_initialization_custom_params(self):
        """Test MongoDB client initialization with custom parameters."""
        client = MongoDBClient(
            host="192.168.1.100",
            port=27018,
            database_name="test_db",
            timeout=10000
        )
        assert client.host == "192.168.1.100"
        assert client.port == 27018
        assert client.database_name == "test_db"
        assert client.timeout == 10000

    @patch('src.database.mongo_client.MongoClient')
    def test_connect_success(self, mock_mongo_client):
        """Test successful MongoDB connection."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {"ok": 1}

        # Create and connect client
        client = MongoDBClient()
        result = client.connect()

        # Assertions
        assert result is True
        assert client.client is not None
        assert client.db is not None
        mock_mongo_client.assert_called_once()

    @patch('src.database.mongo_client.MongoClient')
    def test_connect_failure_server_timeout(self, mock_mongo_client):
        """Test connection failure due to server timeout."""
        # Setup mock to raise ServerSelectionTimeoutError
        mock_mongo_client.side_effect = ServerSelectionTimeoutError("No servers found")

        # Create and attempt to connect
        client = MongoDBClient()
        with pytest.raises(ConnectionFailure):
            client.connect()

    @patch('src.database.mongo_client.MongoClient')
    def test_connect_failure_connection_error(self, mock_mongo_client):
        """Test connection failure due to connection error."""
        # Setup mock to raise ConnectionFailure
        mock_mongo_client.side_effect = ConnectionFailure("Connection refused")

        # Create and attempt to connect
        client = MongoDBClient()
        with pytest.raises(ConnectionFailure):
            client.connect()

    @patch('src.database.mongo_client.MongoClient')
    def test_get_database_success(self, mock_mongo_client):
        """Test getting database object after successful connection."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {"ok": 1}

        # Connect and get database
        client = MongoDBClient()
        client.connect()
        db = client.get_database()

        # Assertions
        assert db is not None

    def test_get_database_not_connected(self):
        """Test getting database object without connection raises error."""
        client = MongoDBClient()
        with pytest.raises(RuntimeError, match="Not connected to MongoDB"):
            client.get_database()

    @patch('src.database.mongo_client.MongoClient')
    def test_create_collections_success(self, mock_mongo_client):
        """Test successful collection creation."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {"ok": 1}
        
        # Setup mock database
        mock_db = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_db.list_collection_names.return_value = []

        # Connect and create collections
        client = MongoDBClient()
        client.connect()
        result = client.create_collections(["matches", "teams", "predictions"])

        # Assertions
        assert result is True

    @patch('src.database.mongo_client.MongoClient')
    def test_create_collections_not_connected(self, mock_mongo_client):
        """Test creating collections without connection raises error."""
        client = MongoDBClient()
        with pytest.raises(RuntimeError, match="Not connected to MongoDB"):
            client.create_collections(["matches"])

    @patch('src.database.mongo_client.MongoClient')
    def test_close_connection(self, mock_mongo_client):
        """Test closing MongoDB connection."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {"ok": 1}

        # Connect and close
        client = MongoDBClient()
        client.connect()
        client.close()

        # Assertions
        mock_client_instance.close.assert_called_once()

    @patch('src.database.mongo_client.MongoClient')
    def test_context_manager(self, mock_mongo_client):
        """Test using MongoDBClient as context manager."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {"ok": 1}

        # Use as context manager
        with MongoDBClient() as client:
            assert client.client is not None
            assert client.db is not None

        # Verify close was called
        mock_client_instance.close.assert_called_once()

    @patch('src.database.mongo_client.MongoClient')
    def test_get_mongo_client_factory(self, mock_mongo_client):
        """Test get_mongo_client factory function."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {"ok": 1}

        # Create client using factory
        client = get_mongo_client(
            host="localhost",
            port=27017,
            database_name="champions_league"
        )

        # Assertions
        assert isinstance(client, MongoDBClient)
        assert client.client is not None
        assert client.db is not None

    @patch('src.database.mongo_client.MongoClient')
    def test_connection_string_format(self, mock_mongo_client):
        """Test that correct connection string is used."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {"ok": 1}

        # Connect with custom host and port
        client = MongoDBClient(host="192.168.1.1", port=27018)
        client.connect()

        # Verify MongoClient was called with correct connection string
        call_args = mock_mongo_client.call_args
        assert "mongodb://192.168.1.1:27018/" in str(call_args)


class TestMongoDBIntegration:
    """Integration tests for MongoDB (requires running MongoDB instance)."""

    @pytest.mark.skip(reason="Requires running MongoDB instance")
    def test_real_mongodb_connection(self):
        """Test actual connection to MongoDB (skipped by default)."""
        try:
            client = MongoDBClient()
            result = client.connect()
            assert result is True
            client.close()
        except ConnectionFailure:
            pytest.skip("MongoDB not running")

    @pytest.mark.skip(reason="Requires running MongoDB instance")
    def test_real_collection_creation(self):
        """Test actual collection creation in MongoDB (skipped by default)."""
        try:
            client = MongoDBClient()
            client.connect()
            client.create_collections(["test_matches", "test_teams"])
            
            collections = client.db.list_collection_names()
            assert "test_matches" in collections
            assert "test_teams" in collections
            
            # Cleanup
            client.db.drop_collection("test_matches")
            client.db.drop_collection("test_teams")
            client.close()
        except ConnectionFailure:
            pytest.skip("MongoDB not running")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
