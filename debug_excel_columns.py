"""Debug what columns are in the Leaderboard dataframe"""

# The issue is that after RUI processing, the dataframe might have different columns
# than what's expected

expected_cols = [
    'Global Rank', 'Email', 'Adjusted Consistency (%)', 'Overall Recency', 
    'Total Tools Used', 'Avg Tools / Report', 'Adoption Velocity', 
    'Tool Expansion Rate', 'Days Since License', 'Usage Trend', 'Engagement Score'
]

print("Expected columns for Leaderboard:")
for i, col in enumerate(expected_cols, 1):
    print(f"  {i}. {col}")

print("\nPossible issues:")
print("1. 'Total Tools Used' might not exist - it's renamed from 'Usage Complexity'")
print("2. After RUI processing, new columns are added that might interfere")
print("3. Some columns might be missing entirely after the RUI calculation")

print("\nThe fix needed:")
print("- Ensure 'Usage Complexity' is properly renamed to 'Total Tools Used'")
print("- Make sure all expected columns exist in the dataframe")
print("- Handle missing columns gracefully")