"""Verify processed features dataset."""
import pandas as pd

# Load the processed features
df = pd.read_csv('data/processed_features.csv')

print("=" * 80)
print("PROCESSED FEATURES DATASET VERIFICATION")
print("=" * 80)

print(f"\n✓ Loaded {len(df)} processed matches")
print(f"\n📊 Dataset Shape: {df.shape}")

print(f"\n📋 Columns ({len(df.columns)}):")
for col in df.columns:
    print(f"   - {col}")

print(f"\n🔍 Data Types:")
print(df.dtypes)

print(f"\n🎯 Target Distribution:")
target_dist = df['Target'].value_counts().sort_index()
for target, count in target_dist.items():
    target_name = {0: 'Draw', 1: 'Home Win', 2: 'Away Win'}.get(target, 'Unknown')
    pct = count / len(df) * 100
    print(f"   {target_name} ({target}): {count} ({pct:.1f}%)")

print(f"\n📈 Feature Statistics:")
numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
for col in numeric_cols:
    if col not in ['Target']:
        print(f"   {col}:")
        print(f"      Min: {df[col].min():.2f}, Max: {df[col].max():.2f}, Mean: {df[col].mean():.2f}")

print(f"\n🏟️  Teams:")
teams = set(df['home_team'].unique()) | set(df['away_team'].unique())
print(f"   Total teams: {len(teams)}")
for team in sorted(teams):
    print(f"      - {team}")

print(f"\n📅 Seasons:")
for season in sorted(df['season'].unique()):
    count = len(df[df['season'] == season])
    print(f"   {season}: {count} matches")

print(f"\n✅ Data Quality Check:")
print(f"   Missing values: {df.isnull().sum().sum()}")
print(f"   Duplicate rows: {df.duplicated().sum()}")
print(f"   Date range: {df['date'].min()} to {df['date'].max()}")

print("\n" + "=" * 80)
print("✅ DATASET VERIFICATION COMPLETE")
print("=" * 80)
