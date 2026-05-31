"""
Data Extraction Script - Extract Champions League Data from API-Football.
Populates MongoDB with historical match data for seasons 2015-2024.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from extraction.api_extractor import APIFootballExtractor, extract_and_store
from database.mongo_client import get_mongo_client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main extraction orchestrator."""
    logger.info("=" * 80)
    logger.info("CHAMPIONS LEAGUE DATA EXTRACTION - Starting")
    logger.info("=" * 80)
    
    try:
        # Get API key
        api_key = os.getenv('RAPIDAPI_KEY')
        if not api_key:
            logger.error("❌ RAPIDAPI_KEY not found in environment variables")
            return False
        
        logger.info(f"✓ API Key loaded successfully")
        
        # Connect to MongoDB
        mongo_client = get_mongo_client()
        logger.info("✓ MongoDB connection established")
        
        # Get matches collection
        db = mongo_client.get_database()
        matches_collection = db['matches']
        logger.info("✓ Matches collection ready")
        
        # Define seasons to extract (2015-2024)
        seasons = [
            "2015-2016", "2016-2017", "2017-2018", "2018-2019", "2019-2020",
            "2020-2021", "2021-2022", "2022-2023", "2023-2024"
        ]
        
        logger.info(f"\n📊 Extracting data for {len(seasons)} seasons:")
        logger.info(f"   Seasons: {', '.join(seasons)}")
        
        # Run extraction and store to MongoDB
        result = extract_and_store(matches_collection, api_key, seasons)
        
        if result:
            # Verify data in MongoDB
            match_count = matches_collection.count_documents({})
            logger.info("\n" + "=" * 80)
            logger.info(f"✅ EXTRACTION COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Total matches in MongoDB: {match_count}")
            
            # Sample data from MongoDB
            if match_count > 0:
                sample = matches_collection.find_one()
                logger.info(f"\n📋 Sample match data:")
                logger.info(f"   Season: {sample.get('season')}")
                logger.info(f"   Date: {sample.get('date')}")
                logger.info(f"   Match: {sample.get('home_team')} vs {sample.get('away_team')}")
                logger.info(f"   Result: {sample.get('home_goals')}-{sample.get('away_goals')} ({sample.get('result')})")
            
            mongo_client.close()
            return True
        else:
            logger.error("❌ Extraction failed")
            mongo_client.close()
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
