import pandas as pd

# Check V1 features
v1 = pd.read_csv('data/features_output/features_v1.csv')
print("=" * 80)
print("V1 UNIFIED FILE (features_v1.csv)")
print("=" * 80)
print(f"Rows: {len(v1):,}")
print(f"Columns: {v1.shape[1]}")
print(f"\nColumn names:\n{list(v1.columns)}")
print(f"\nFirst 2 rows:")
print(v1.head(2))

# Check V2 features
v2 = pd.read_csv('data/features_output/features_v2.csv')
print("\n" + "=" * 80)
print("V2 ADVANCED FILE (features_v2.csv)")
print("=" * 80)
print(f"Rows: {len(v2):,}")
print(f"Columns: {v2.shape[1]}")
print(f"\nColumn names:\n{list(v2.columns)}")
print(f"\nFirst 2 rows:")
print(v2.head(2))
