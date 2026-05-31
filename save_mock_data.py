"""
Generate and save mock Champions League data to JSON files.
Works around MongoDB authentication by storing data locally.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from random import randint, choice

# Sample teams
TEAMS = [
    "Manchester City", "Real Madrid", "Barcelona", "Bayern Munich",
    "Liverpool", "Paris Saint-Germain", "Chelsea", "Juventus",
    "Manchester United", "Inter Milan", "AC Milan", "Napoli",
    "Atlético Madrid", "Borussia Dortmund", "Ajax", "Porto"
]

SEASONS = [
    "2015-2016", "2016-2017", "2017-2018", "2018-2019", "2019-2020",
    "2020-2021", "2021-2022", "2022-2023", "2023-2024"
]


def json_serializer(obj):
    """Serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def generate_mock_data():
    """Generate mock Champions League match data."""
    matches_list = []
    match_id = 1
    
    for season in SEASONS:
        season_count = randint(50, 60)
        start_year = int(season.split('-')[0])
        start_date = datetime(start_year, 8, 1)
        
        for i in range(season_count):
            match_date = start_date + timedelta(days=randint(0, 270))
            
            home_team = choice(TEAMS)
            away_teams = [t for t in TEAMS if t != home_team]
            away_team = choice(away_teams)
            
            home_goals = randint(0, 4)
            away_goals = randint(0, 4)
            
            if home_goals > away_goals:
                result = "H"
            elif away_goals > home_goals:
                result = "A"
            else:
                result = "D"
            
            match = {
                "_id": match_id,
                "fixture_id": int(f"{start_year}{i:04d}"),
                "season": season,
                "date": match_date.isoformat(),
                "home_team": home_team,
                "away_team": away_team,
                "home_goals": home_goals,
                "away_goals": away_goals,
                "result": result,
                "stage": choice(["Group Stage", "Round of 16", "Quarter-finals", "Semi-finals", "Final"]),
                "status": "FT",
                "source": "mock",
                "extracted_at": datetime.now().isoformat(),
                "home_xG": round(randint(5, 25) / 10.0, 2),
                "away_xG": round(randint(5, 25) / 10.0, 2),
            }
            matches_list.append(match)
            match_id += 1
    
    return matches_list


def main():
    """Generate and save mock data."""
    print("=" * 80)
    print("MOCK DATA GENERATION & SAVING - Starting")
    print("=" * 80)
    
    try:
        # Create data directory
        data_dir = "data"
        os.makedirs(data_dir, exist_ok=True)
        
        # Generate mock data
        print("\n📊 Generating mock Champions League match data...")
        matches = generate_mock_data()
        print(f"✓ Generated {len(matches)} matches")
        
        # Save to JSON
        json_file = os.path.join(data_dir, "champions_league_matches.json")
        print(f"\n💾 Saving to {json_file}...")
        
        with open(json_file, 'w') as f:
            json.dump(matches, f, indent=2, default=json_serializer)
        
        print(f"✓ Saved {len(matches)} matches to JSON")
        
        # Verify file
        file_size = os.path.getsize(json_file)
        print(f"   File size: {file_size / 1024:.2f} KB")
        
        # Summary by season
        print("\n📊 Data Summary:")
        season_counts = {}
        for match in matches:
            season = match['season']
            season_counts[season] = season_counts.get(season, 0) + 1
        
        for season in SEASONS:
            count = season_counts.get(season, 0)
            print(f"   {season}: {count} matches")
        
        print(f"   Total: {len(matches)} matches")
        
        # Show sample
        if matches:
            sample = matches[0]
            print(f"\n📋 Sample Match:")
            print(f"   ID: {sample['_id']}")
            print(f"   Season: {sample['season']}")
            print(f"   Date: {sample['date']}")
            print(f"   Match: {sample['home_team']} {sample['home_goals']}-{sample['away_goals']} {sample['away_team']}")
            print(f"   Result: {sample['result']}")
            print(f"   Home xG: {sample['home_xG']}, Away xG: {sample['away_xG']}")
        
        print("\n" + "=" * 80)
        print("✅ MOCK DATA SAVED SUCCESSFULLY")
        print("=" * 80)
        print(f"\nNext steps:")
        print(f"1. This data will be used for feature engineering in Task 3")
        print(f"2. Data is stored at: {os.path.abspath(json_file)}")
        print(f"3. Ready to proceed to data cleaning & feature engineering\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
