import os
import pandas as pd
import re
from tqdm import tqdm

identifier_map = {
    "S1": "s1",
    "Median": "s3",
    "S5": "s5",
    "Mean": "m",
    "Observation number": "n",
    "Standard deviation": "s",
    "Mean day of the month": "d",
    "Fraction of daylight observations": "ht"
}

ordered_prefixes = [
    "S", "A", "Q", "R", "W", "U", "V", "P", "C", "X", "Y",
    "D", "E", "F", "G", "I", "J", "K", "L", "M", "N", "B1", "B2"
]

ordered_suffixes = ["s1", "s3", "s5", "m", "n", "s", "d", "ht"]

def extract_suffix(original):
    for long, short in identifier_map.items():
        if original.endswith(long):
            return short
    return None

def extract_prefix(col):
    if col.startswith("B1"):
        return "B1"
    if col.startswith("B2"):
        return "B2"
    return col[0]

def rename_column(col):
    prefix = extract_prefix(col)
    suffix = extract_suffix(col)
    if suffix is None:
        return None
    return f"{prefix}{suffix}"

def process_csv(path):
    df = pd.read_csv(path)

    df = df.drop(columns=[c for c in df.columns if c.lower() == "running month"], errors="ignore")
    cols_to_drop = [c for c in df.columns if c.startswith("R-") and c.endswith("_y")]
    df = df.drop(columns=cols_to_drop, errors="ignore")

    rename_map = {}
    for c in df.columns:
        if c.startswith("R-") and c.endswith("_x"):
            rename_map[c] = c[:-2]
    df = df.rename(columns=rename_map)

    preserved = ["Year", "Month", "Longitude", "Latitude"]
    new_columns = {}

    for col in df.columns:
        if col in preserved:
            new_columns[col] = col
            continue
        short = rename_column(col)
        if short is not None:
            new_columns[col] = short
        else:
            new_columns[col] = None

    drop_cols = [old for old,new in new_columns.items() if new is None]
    df = df.drop(columns=drop_cols)

    df = df.rename(columns={old:new for old,new in new_columns.items() if new is not None})

    def sort_key(col):
        if col in preserved:
            return (0, preserved.index(col), 0)

        prefix = extract_prefix(col)
        prefix_index = ordered_prefixes.index(prefix) if prefix in ordered_prefixes else 999
        suffix = col[len(prefix):]
        suffix_index = ordered_suffixes.index(suffix) if suffix in ordered_suffixes else 999

        return (1, prefix_index, suffix_index)

    df = df[sorted(df.columns, key=sort_key)]

    df.to_csv(path, index=False)

csv_files = []
for root, dirs, files in os.walk('./'):
    for f in files:
        if f.lower().endswith(".csv"):
            csv_files.append(os.path.join(root, f))

for csv_path in tqdm(csv_files, desc="Processing..."):
    process_csv(csv_path)
