"""Debug what's happening with Leaderboard columns"""

print("Expected columns for Leaderboard after renaming:")
expected = [
    'Global Rank', 'Email', 'Adjusted Consistency (%)', 'Overall Recency', 
    'Total Tools Used',  # This should be renamed from 'Usage Complexity'
    'Avg Tools / Report', 'Adoption Velocity', 
    'Tool Expansion Rate', 'Days Since License', 'Usage Trend', 'Engagement Score'
]

print("\nColumn mapping:")
print("  'Usage Complexity' -> 'Total Tools Used'")

print("\nPotential issues:")
print("1. If 'Usage Complexity' doesn't exist in the dataframe, the rename won't happen")
print("2. If 'Overall Recency' doesn't exist, it will be filled with NaN")
print("3. The disclaimer row insertion might be corrupting the data")

print("\nColumns that might be missing:")
print("- Usage Complexity (gets renamed to Total Tools Used)")
print("- Overall Recency") 
print("- These are calculated earlier in the pipeline")

print("\nThe fix:")
print("1. Ensure 'Usage Complexity' and 'Overall Recency' exist in all_df")
print("2. Don't create NaN columns - fail loudly if required columns are missing")
print("3. Consider moving the disclaimer to a cell comment instead of a row")