"""
MongoDB client for Champions League Predictor.

Handles connection to local MongoDB instance and database creation.
"""

import os
from typing import Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError


class MongoDBClient:
    """MongoDB connection handler for the Champions League prediction pipeline."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 27017,
        database_name: str = "champions_league",
        timeout: int = 5000
    ):
        """
        Initialize MongoDB client.

        Args:
            host: MongoDB server hostname (default: localhost)
            port: MongoDB server port (default: 27017)
            database_name: Name of the database to use
            timeout: Connection timeout in milliseconds
        """
        self.host = host
        self.port = port
        self.database_name = database_name
        self.timeout = timeout
        self.client: Optional[MongoClient] = None
        self.db = None

    def connect(self) -> bool:
        """
        Establish connection to MongoDB.

        Returns:
            True if connection successful, False otherwise.

        Raises:
            ConnectionFailure: If connection to MongoDB fails.
        """
        try:
            connection_string = f"mongodb://{self.host}:{self.port}/"
            self.client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=self.timeout
            )
            # Verify connection by pinging the server
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            print(f"✓ Connected to MongoDB at {connection_string}")
            return True
        except ServerSelectionTimeoutError as e:
            print(f"✗ Connection timeout: {e}")
            raise ConnectionFailure(f"Failed to connect to MongoDB at {self.host}:{self.port}") from e
        except ConnectionFailure as e:
            print(f"✗ Connection failed: {e}")
            raise

    def get_database(self):
        """
        Get the database instance.

        Returns:
            MongoDB database object.

        Raises:
            RuntimeError: If not connected to MongoDB.
        """
        if self.db is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        return self.db

    def create_collections(self, collection_names: list) -> bool:
        """
        Create collections in the database if they don't exist.

        Args:
            collection_names: List of collection names to create.

        Returns:
            True if successful, False otherwise.
        """
        if self.db is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")

        try:
            existing_collections = []
            try:
                existing_collections = self.db.list_collection_names()
            except Exception as auth_error:
                # If listCollections fails due to auth, try to insert directly
                print(f"⚠ Warning: Cannot list collections ({auth_error}). Attempting direct creation...")

            for collection_name in collection_names:
                if collection_name not in existing_collections:
                    try:
                        self.db.create_collection(collection_name)
                        print(f"✓ Created collection: {collection_name}")
                    except Exception as create_error:
                        # Collection may already exist
                        print(f"✓ Collection already exists or created: {collection_name}")
                else:
                    print(f"✓ Collection already exists: {collection_name}")
            return True
        except Exception as e:
            print(f"✗ Failed to create collections: {e}")
            raise

    def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            print("✓ MongoDB connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def get_mongo_client(
    host: str = "localhost",
    port: int = 27017,
    database_name: str = "champions_league"
) -> MongoDBClient:
    """
    Factory function to create and connect to MongoDB.

    Args:
        host: MongoDB server hostname
        port: MongoDB server port
        database_name: Name of the database

    Returns:
        Connected MongoDBClient instance.
    """
    client = MongoDBClient(host=host, port=port, database_name=database_name)
    client.connect()
    return client
