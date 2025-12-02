import os
import subprocess
import time
import pandas as pd
import csv
import glob
from datetime import datetime
from tqdm import tqdm
import re
import shutil
import uuid
from multiprocessing import Pool, cpu_count, set_start_method

# RUN python d548001ToCSVParallel.py FROM the directory that contains rdmsg1_Cshell, PLEASE
# p.f MUST BE A SEPARATE FILE IN THE SAME FOLDER AS THE Csh FILE!

SCRIPT_DIR = os.getcwd()

def preamble():
    print("ICOADS d548001 Data Access V1.1")
    print("Please download the applicable .STD files that are located on the Research Data Archive at https://rda.ucar.edu/datasets/d548001/ and extract the .tar and .gz files.")

def fileLocations():
    path = input("Path to STD files (due to FORTRAN limitations, this path cannot contain spaces or ~, also make sure there is nothing else in this folder) (also don't convert too many files at once, you may crash)\n: ").strip()
    return os.path.abspath(path)

def execute_fortran():
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(SCRIPT_DIR, "a.out")

    if os.path.exists(exe_path):
        return exe_path

    p_path = os.path.join(SCRIPT_DIR, "p.f")
    if not os.path.exists(p_path):
        raise FileNotFoundError(f"p.f not found in {SCRIPT_DIR}")

    print("Compiling Fortran code (once)...")

    result = subprocess.run(["f77", "-o", exe_path, p_path])

    return exe_path

def STDtoTXT_Worker(args):
    path, std_file, exe_path = args  # exe_path is the PRECOMPILED a.out

    cubicle = os.path.join(path, f"_cubicle_{uuid.uuid4().hex}")
    os.makedirs(cubicle, exist_ok=True)

    try:
        # Copy precompiled a.out into cubicle
        exe_local = os.path.join(cubicle, "a.out")
        shutil.copy(exe_path, exe_local)
        os.chmod(exe_local, 0o755)

        # Copy STD as fort.1
        abs_std = os.path.abspath(os.path.join(path, std_file))
        shutil.copy(abs_std, os.path.join(cubicle, "fort.1"))

        # TXT output path
        base = os.path.splitext(std_file)[0]
        out_txt = os.path.join(path, base + ".txt")

        # FORTRAN still expects PATH via stdin
        stdin_line = f"{abs_std}\n"

        with open(out_txt, "w") as outf:
            subprocess.run([exe_local], input=stdin_line, text=True, stdout=outf, cwd=cubicle)

    finally:
        shutil.rmtree(cubicle, ignore_errors=True)

    return std_file

def STDtoTXT(path):
    path = os.path.abspath(path)

    std_files = [f for f in os.listdir(path) if f.endswith(".STD") and os.path.isfile(os.path.join(path, f))]

    # PRECOMPILE a.out
    exe_path = execute_fortran()

    workers = max(cpu_count() - 1, 1) # I don't want to crash
    print(f"Converting {len(std_files)} STD files to TXT using {workers} workers...")

    from multiprocessing import Pool
    from tqdm import tqdm

    args = [(path, f, exe_path) for f in std_files]

    with Pool(workers) as pool:
        for _ in tqdm(pool.imap(STDtoTXT_Worker, args), total=len(args), desc="STD -> TXT"):
            pass

def deleteExtension(path, extension):
    command = f'rm -f "{path}"/*.{extension}'
    subprocess.run(command, shell=True, capture_output=True, text=True, executable="/bin/bash")

def delimiter_fix(input_path, output_path):
    delimiters = [' ', '|']
    common_delimiter = ','

    with open(input_path, newline='') as infile, open(output_path, 'w', newline='') as outfile:
        input_reader = csv.reader(infile)
        cleaning_writer = csv.writer(outfile)

        for row in input_reader:
            merged_row = []

            for delimiter in delimiters:
                row[0] = row[0].replace(delimiter, common_delimiter)

            split_row = row[0].split(common_delimiter)
            split_row = [element for element in split_row if element]
            merged_row.extend(split_row)

            cleaning_writer.writerow(merged_row)

def writeToCSV(csvFile, rows):
    with open(csvFile, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(rows)

def verbosity(cleaning_rows):
    for row in cleaning_rows:
        print(row)

def worker_txt_to_csv(args):
    path, fileName = args  # path is ABSOLUTE directory, fileName is *.txt
    Verbosity = False  # Set True for debugging

    tempdir = os.path.join(path, f"_tmp_{uuid.uuid4().hex}")
    os.makedirs(tempdir, exist_ok=True)

    try:
        txt_input = os.path.join(path, fileName)
        csv_output = os.path.join(tempdir, "undelimited_" + fileName.replace(".txt", ".csv"))
        cleaned_csv_output = os.path.join(tempdir, fileName.replace(".txt", ".csv"))

        # Convert .txt to .csv
        df_tmp = pd.read_csv(txt_input)
        df_tmp.to_csv(csv_output, index=None)

        # Fix delimiters
        delimiter_fix(csv_output, cleaned_csv_output)

        with open(cleaned_csv_output, 'r') as infile:
            cleaning_reader = csv.reader(infile)
            cleaning_rows = list(cleaning_reader)

        # Delete metadata remnants from reading the terminal
        cleaning_rows = [row for row in cleaning_rows if row and row[0] != "1RDMSG.01D"]

        # Months 1-9 have an extra space that needs to be removed
        for row_index in range(len(cleaning_rows)):
            if row_index % 6 == 0 and len(cleaning_rows[row_index]) > 1 and len(cleaning_rows[row_index][1]) == 2:
                cleaning_rows[row_index][0] = cleaning_rows[row_index][0] + cleaning_rows[row_index][1]
                del cleaning_rows[row_index][1]

        # Step 1: Bring down time and push second row with statistics right one cell
        if Verbosity:
            print("Step 1/14: Time and Second Row Push, last row counter")
        for row_index in range(len(cleaning_rows)):
            if row_index % 6 == 0:
                time_string = cleaning_rows[row_index][0]
                time_string = time_string[0:time_string.find(".")] + time_string[(time_string.find(".") + 1):-1]
                cleaning_rows[row_index][0] = "Year/Month"
            else:
                cleaning_rows[row_index].insert(0, time_string)
                if row_index % 6 == 1:
                    cleaning_rows[row_index][1] = ""
            if row_index == len(cleaning_rows) - 1:
                del cleaning_rows[row_index]

        # Step 2: Bring down first row variables
        if Verbosity:
            print("Step 2/14: Bring down first row variables")
        for row_index in range(len(cleaning_rows)):
            if row_index % 6 == 0:
                box_size = cleaning_rows[row_index][2]
                longitude = cleaning_rows[row_index][4]
                latitude = cleaning_rows[row_index][6]
                enhanced = cleaning_rows[row_index][9]
                group = cleaning_rows[row_index][11]
                checksum = cleaning_rows[row_index][13]
                for cell in range(6):
                    del cleaning_rows[row_index][cell + 2]
                for stat in ('S1', 'Med', 'S5', 'Mean', 'Obs.', 'σ', 'Day', 'Light%', '+x', '+y'):
                    cleaning_rows[row_index].append(stat)
            if row_index % 6 not in (0, 1):
                cleaning_rows[row_index].insert(1, box_size)
                cleaning_rows[row_index].insert(2, longitude)
                cleaning_rows[row_index].insert(3, latitude)
                cleaning_rows[row_index].insert(4, enhanced)
                cleaning_rows[row_index].insert(5, group)
                cleaning_rows[row_index].insert(6, checksum)

        # Step 3: Remove all extra % 6 == 1 rows
        if Verbosity:
            print("Step 3/14: Remove extra rows")
        cleaning_rows = [row for row in cleaning_rows if len(row) > 1 and row[1] != ""]

        # Step 4: Rename headers to something nice
        if Verbosity:
            print("Step 4/14: Header renaming")
        for row_index in range(len(cleaning_rows)):
            if row_index % 5 == 0:
                cleaning_rows[row_index] = ["Year/Month", "Box Size", "Longitude", "Latitude", "PID2: Standard/Enhanced", "Group", "Checksum", "Variable", "S1", "Median", "S5", "Mean", "Observation number", "Standard deviation", "Mean day of the month", "Fraction of daylight observations", "Mean Longitude", "Mean Latitude"]

        # Step 5: Remove invalid measurements
        if Verbosity:
            print("Step 5/14: Remove invalid measurements")
        invalid_data = {'-9999.', '-9999.0', '-9999.00'}
        for row_index, row in enumerate(cleaning_rows):
            cleaning_rows[row_index] = ["NA" if val in invalid_data else val for val in row]

        # Step 6: Remove trailing periods
        if Verbosity:
            print("Step 6/14: Remove trailing dots (vestige of floating point)")
        for row_index, row in enumerate(cleaning_rows):
            for col_index, val in enumerate(row):
                if isinstance(val, str):
                    if val.endswith('.'):
                        val = val[:-1]
                    if val.endswith('.°'):
                        val = val[:-2] + '°'
                    cleaning_rows[row_index][col_index] = val

        # Step 7: Remove extra headers in the middle
        if Verbosity:
            print("Step 7/14: Remove extra headers")
        cleaning_rows = [row for i, row in enumerate(cleaning_rows) if not (row[0] == "Year/Month" and i != 0)]

        # Step 8: Remove degree signs
        if Verbosity:
            print("Step 8/14: Remove degree signs")
        for row_index, row in enumerate(cleaning_rows):
            for col_index, val in enumerate(row):
                if isinstance(val, str) and val.endswith("°"):
                    cleaning_rows[row_index][col_index] = val.rstrip("°")

        # Build DataFrame from rows after step 8
        headers = cleaning_rows[0]
        data_rows = cleaning_rows[1:]
        df = pd.DataFrame(data_rows, columns=headers)

        # Normalize stat column names
        df = df.rename(columns={
            "Med": "Median",
            "Obs.": "Observation number",
            "σ": "Standard deviation",
            "Day": "Mean day of the month",
            "Light%": "Fraction of daylight observations"
        })

        stat_cols = ['S1', 'Median', 'S5', 'Mean', 'Observation number', 'Standard deviation', 'Mean day of the month', 'Fraction of daylight observations', 'Mean Longitude', 'Mean Latitude']

        id_vars = ["Year/Month", "Box Size", "Longitude", "Latitude", "PID2: Standard/Enhanced", "Group", "Checksum", "Variable"]

        # Melt to long form: one row per (cell, variable, stat)
        df_long = df.melt(id_vars=id_vars, value_vars=stat_cols, var_name="Stat", value_name="Value")

        # Pivot to wide
        df_wide = df_long.pivot_table(index=["Year/Month", "Box Size", "Longitude", "Latitude", "PID2: Standard/Enhanced", "Group", "Checksum"], columns=["Variable", "Stat"], values="Value", aggfunc="first")

        # Flatten MultiIndex columns
        df_wide.columns = [f"{var}-{stat}" for var, stat in df_wide.columns]
        df_wide = df_wide.reset_index()

        # Step 10: remove any rows with "NA"
        mask_na_row = df_wide.eq("NA").any(axis=1)
        df_wide = df_wide.loc[~mask_na_row].copy()

        # Step 11: Year/Month splitting
        if Verbosity:
            print("Step 11/14: Year/Month splitting")

        dt = pd.to_datetime(df_wide["Year/Month"], format="%Y/%m", errors="coerce")
        df_wide["Year"] = dt.dt.year.astype("Int64")
        df_wide["Month"] = dt.dt.month.astype("Int64")

        df_wide["Year"] = df_wide["Year"].astype(object).where(df_wide["Year"].notna(), "NA")
        df_wide["Month"] = df_wide["Month"].astype(object).where(df_wide["Month"].notna(), "NA")

        # Step 12: Drop metadata columns but KEEP mean lon/lat columns (now stats)
        if Verbosity:
            print("Step 12/14: Drop metadata columns only")
        metadata_cols = ['Year/Month', 'Box Size', 'PID2: Standard/Enhanced', 'Group', 'Checksum']
        df_wide = df_wide.drop(columns=[c for c in metadata_cols if c in df_wide.columns])

        # Step 13: Convert -Mean Longitude / -Mean Latitude into -x / -y stats
        if Verbosity:
            print("Step 13/14: Rename Mean Lon/Lat stat columns to x/y")

        def rename_mean_lon_lat(col):
            if col.endswith("-Mean Longitude"):
                return col.replace("-Mean Longitude", "-x")
            if col.endswith("-Mean Latitude"):
                return col.replace("-Mean Latitude", "-y")
            return col

        df_wide.columns = [rename_mean_lon_lat(c) for c in df_wide.columns]

        # Step 14: Reorder columns (Year, Month to front)
        if Verbosity:
            print("Step 14/14: Reorder columns")
        cols = list(df_wide.columns)
        front = ["Year", "Month"]
        front_existing = [c for c in front if c in cols]
        remaining = [c for c in cols if c not in front_existing]
        df_wide = df_wide[front_existing + remaining]

        df_wide.to_csv(cleaned_csv_output, index=False)
        final_output = os.path.join(path, fileName.replace(".txt", ".csv"))
        shutil.move(cleaned_csv_output, final_output)

    finally:
        shutil.rmtree(tempdir, ignore_errors=True)

    return fileName

def TXTtoCSV(path, fileNames):
    if not fileNames:
        print("No .txt files found for TXT->CSV.")
        return

    workers = max(cpu_count() - 1, 1)
    print(f"Converting {len(fileNames)} TXT files to CSV using {workers} workers...")

    start_time = time.perf_counter()
    with Pool(workers) as pool:
        for _ in tqdm(pool.imap(worker_txt_to_csv, [(path, f) for f in fileNames]), total=len(fileNames), desc="TXT -> CSV"):
            pass
    end_time = time.perf_counter()
    print(f"TXT to CSV (parallel) completed in {end_time - start_time:.2f} seconds.")

def mergeGroups(path):
    all_files = glob.glob(os.path.join(path, "*.csv"))
    all_files = [f for f in all_files if f.endswith(tuple(f".{i}.csv" for i in range(3, 10)))]
    prefixes = list(set([f[:-6] for f in all_files if f.endswith('.csv')]))
    for prefix in tqdm(prefixes, desc="Merging CSVs"):
        files = glob.glob(os.path.join(f"{prefix}*.csv"))
        merged_df = None
        for file in files:
            df = pd.read_csv(file)
            if merged_df is None:
                merged_df = df
            else:
                merged_df = pd.merge(merged_df, df, on=['Year', 'Month', 'Longitude', 'Latitude'], how='outer')
        if merged_df is None:
            continue
        output_file = f"{prefix}.csv"
        merged_df = merged_df.drop(columns=[col for col in merged_df.columns if col.endswith("_y")])
        merged_df.rename(columns={col: col.rstrip('_x') for col in merged_df.columns if col.endswith('_x')}, inplace=True)
        merged_df.to_csv(output_file, index=False)
        stem_removal = f'rm -f "{prefix}".*.csv'
        subprocess.run(stem_removal, shell=True, capture_output=True, text=True, executable="/bin/bash")
        print(f"Merged {prefix}.")

def removeUnderscores(path):
    command = f'for f in "{path}"/*.csv; do mv "$f" "$(echo "$f" | sed s/_/./)"; done'
    subprocess.run(command, shell=True, capture_output=True, text=True, executable="/bin/bash")

identifier_map = {
    "S1": "s1",
    "Median": "s3",
    "S5": "s5",
    "Mean": "m",
    "Observation number": "n",
    "Standard deviation": "s",
    "Mean day of the month": "d",
    "Fraction of daylight observations": "ht",
    "x": "x",
    "y": "y"
}

ordered_prefixes = [
    "S", "A", "Q", "R", "W", "U", "V", "P", "C", "X", "Y",
    "D", "E", "F", "G", "I", "J", "K", "L", "M", "N", "B1", "B2"
]

ordered_suffixes = ["s1", "s3", "s5", "m", "n", "s", "d", "ht", "x", "y"]

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

    # Drop duplicate R-* columns ending with _y
    cols_to_drop = [c for c in df.columns if c.startswith("R-") and c.endswith("_y")]
    df = df.drop(columns=cols_to_drop, errors="ignore")

    # Remove _x from remaining R-* columns
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

    drop_cols = [old for old, new in new_columns.items() if new is None]
    df = df.drop(columns=drop_cols)

    df = df.rename(columns={old: new for old, new in new_columns.items() if new is not None})

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

def postprocess_all_csvs(base_path):
    csv_files = []
    for root, dirs, files in os.walk(base_path):
        for f in files:
            if f.lower().endswith(".csv"):
                csv_files.append(os.path.join(root, f))

    for csv_path in tqdm(csv_files, desc="Final CSV processing"):
        process_csv(csv_path)

def main():
    preamble()
    path = fileLocations()

    STDtoTXT(path)
    deleteExtension(path, "STD")

    txtList = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f.endswith(".txt")]
    TXTtoCSV(path, txtList)
    deleteExtension(path, "txt")

    mergeGroups(path)

    removeUnderscores(path)

    postprocess_all_csvs(path)


if __name__ == "__main__":
    # Careful multiprocessing initiation
    try:
        set_start_method("spawn")
    except RuntimeError:
        pass
    main()
