"""
Main orchestration script for Champions League Predictor.

This is the entry point for the entire ML pipeline that:
1. Extracts historical Champions League data
2. Cleans and engineers features
3. Trains predictive models
4. Simulates tournament outcomes

Usage:
    python main.py [--mode {extract,clean,train,simulate,full}]
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.mongo_client import get_mongo_client


def main():
    """Main orchestration function."""
    parser = argparse.ArgumentParser(
        description="Champions League Predictor - ML Pipeline"
    )
    parser.add_argument(
        "--mode",
        choices=["extract", "clean", "train", "simulate", "full"],
        default="full",
        help="Pipeline mode to execute"
    )
    parser.add_argument(
        "--db-host",
        default="localhost",
        help="MongoDB host address"
    )
    parser.add_argument(
        "--db-port",
        type=int,
        default=27017,
        help="MongoDB port"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Champions League Predictor - ML Pipeline")
    print("=" * 80)
    
    # Initialize MongoDB connection
    try:
        mongo_client = get_mongo_client(
            host=args.db_host,
            port=args.db_port
        )
        print(f"✓ Database initialized: {mongo_client.database_name}")
        
        # Create collections
        collections = ["matches", "teams", "predictions"]
        mongo_client.create_collections(collections)
        print(f"✓ Collections initialized: {', '.join(collections)}")
        
        mongo_client.close()
        
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")
        sys.exit(1)
    
    print("\n✓ Pipeline initialized successfully")
    print(f"✓ Mode: {args.mode}")
    print("\nNext: Run Task 2 - Data Extraction Pipeline")


if __name__ == "__main__":
    main()
