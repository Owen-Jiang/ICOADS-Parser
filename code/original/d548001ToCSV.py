import os
import subprocess
import time
import pandas as pd
import csv
import glob
from datetime import datetime
from tqdm import tqdm
import re

def preamble():
    print("ICOADS d548001 Data Access V1.1")
    print("Please download the applicable .STD files that are located on the Research Data Archive at https://rda.ucar.edu/datasets/d548001/ and extract the .tar and .gz files.")

def fileLocations():
    path = input(
        "Path to STD files (due to FORTRAN limitations, this path cannot contain spaces or ~, "
        "also make sure there is nothing else in this folder) "
        "(also don't convert too many files at once, you may crash)\n: "
    )
    if not path.endswith(os.sep):
        path += os.sep
    return path

def STDtoTXT(path):
    command = (
        f'for file in "{path}"*.STD; do '
        f'base_name=$(basename "$file" .STD); '
        f'{{ csh rdmsg1_Cshell "$file"; echo "$1 $(date)" | ./a.out; }} '
        f'| tee "{path}${{base_name}}.txt"; '
        f'done'
    )

    start_time = time.perf_counter()
    process = subprocess.run(
        command, shell=True, capture_output=True, text=True, executable="/bin/bash"
    )
    end_time = time.perf_counter()

    if process.returncode == 0:
        print(f"STD to TXT executed successfully in {end_time - start_time} seconds:")
        print(process.stdout)
    else:
        print(f"STD to TXT failed with error code {process.returncode}:")
        print(process.stderr)

def deleteExtension(path, extension):
    command = f'rm -f "{path}"*.{extension}'
    subprocess.run(command, shell=True, capture_output=True, text=True, executable="/bin/bash")

def delimiter_fix(input_path, output_path):
    # Define the delimiters and the common delimiter
    delimiters = [' ', '|']
    common_delimiter = ','

    with open(input_path, newline='') as infile, open(output_path, 'w', newline='') as outfile:
        input_reader = csv.reader(infile)
        cleaning_writer = csv.writer(outfile)

        for row in input_reader:
            merged_row = []

            # Merge delimiters in the row
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

def TXTtoCSV(path, fileNames):
    for fileName in tqdm(fileNames, desc="Converting TXTs to CSVs"):
        print("Working on " + fileName)
        Verbosity = False  # Set True if you want verbose debug output

        txt_input = path + fileName
        csv_output = path + "undelimited_" + fileName.replace(".txt", ".csv")
        cleaned_csv_output = path + fileName.replace(".txt", ".csv")

        # Convert .txt to .csv
        df = pd.read_csv(txt_input)
        df.to_csv(csv_output, index=None)

        # Fix delimiters
        delimiter_fix(csv_output, cleaned_csv_output)

        undelimited_removal = f'rm -f "{path}"undelimited_*.csv'
        subprocess.run(undelimited_removal, shell=True, capture_output=True, text=True, executable="/bin/bash")

        # Read cleaned_csv_output
        with open(cleaned_csv_output, 'r') as infile:
            cleaning_reader = csv.reader(infile)
            cleaning_rows = list(cleaning_reader)

        # Delete metadata remnants from reading the terminal
        cleaning_rows = [row for row in cleaning_rows if row[0] != "1RDMSG.01D"]

        # Months 1-9 have an extra space that needs to be removed
        for row_index in range(len(cleaning_rows)):
            if row_index % 6 == 0 and len(cleaning_rows[row_index][1]) == 2:
                cleaning_rows[row_index][0] = cleaning_rows[row_index][0] + cleaning_rows[row_index][1]
                del cleaning_rows[row_index][1]

        writeToCSV(cleaned_csv_output, cleaning_rows)

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

        if Verbosity:
            verbosity(cleaning_rows)
        writeToCSV(cleaned_csv_output, cleaning_rows)

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

        if Verbosity:
            verbosity(cleaning_rows)
        writeToCSV(cleaned_csv_output, cleaning_rows)

        # Step 3: Remove all extra % 6 == 1 rows
        if Verbosity:
            print("Step 3/14: Remove extra rows")
        cleaning_rows = [row for row in cleaning_rows if row[1] != ""]

        if Verbosity:
            verbosity(cleaning_rows)
        writeToCSV(cleaned_csv_output, cleaning_rows)

        # Step 4: Rename headers to something nice
        if Verbosity:
            print("Step 4/14: Header renaming")
        for row_index in range(len(cleaning_rows)):
            if row_index % 5 == 0:
                cleaning_rows[row_index] = [
                    "Year/Month", "Box Size", "Longitude", "Latitude",
                    "PID2: Standard/Enhanced", "Group", "Checksum",
                    "Variable", "S1", "Median", "S5", "Mean",
                    "Observation number", "Standard deviation",
                    "Mean day of the month", "Fraction of daylight observations",
                    "Mean Longitude", "Mean Latitude"
                ]

        if Verbosity:
            verbosity(cleaning_rows)
        writeToCSV(cleaned_csv_output, cleaning_rows)

        # Step 5: Remove invalid measurements
        if Verbosity:
            print("Step 5/14: Remove invalid measurements")
        invalid_data = {'-9999.', '-9999.0', '-9999.00'}
        for row_index, row in enumerate(cleaning_rows):
            cleaning_rows[row_index] = ["NA" if val in invalid_data else val for val in row]

        if Verbosity:
            verbosity(cleaning_rows)
        writeToCSV(cleaned_csv_output, cleaning_rows)

        # Step 6: Remove trailing periods
        if Verbosity:
            print("Step 6/14: Remove trailing dots (vestige of floating point)")
        for row_index, row in enumerate(cleaning_rows):
            for col_index, val in enumerate(row):
                if val.endswith('.'):
                    val = val[:-1]
                if val.endswith('.°'):
                    val = val[:-2] + '°'
                cleaning_rows[row_index][col_index] = val

        if Verbosity:
            verbosity(cleaning_rows)
        writeToCSV(cleaned_csv_output, cleaning_rows)

        # Step 7: Remove extra headers in the middle
        if Verbosity:
            print("Step 7/14: Remove extra headers")
        cleaning_rows = [row for i, row in enumerate(cleaning_rows) if not (row[0] == "Year/Month" and i != 0)]

        if Verbosity:
            verbosity(cleaning_rows)
        writeToCSV(cleaned_csv_output, cleaning_rows)

        # Step 8: Remove degree signs
        if Verbosity:
            print("Step 8/14: Remove degree signs")
        for row_index, row in enumerate(cleaning_rows):
            for col_index, val in enumerate(row):
                if val.endswith("°"):
                    cleaning_rows[row_index][col_index] = val.rstrip("°")

        if Verbosity:
            verbosity(cleaning_rows)
        writeToCSV(cleaned_csv_output, cleaning_rows)

        # Step 9: Pivot the table
        if Verbosity:
            print("Step 9/14: Pivot the table")
        variableArray = (cleaning_rows[1][7], cleaning_rows[2][7], cleaning_rows[3][7], cleaning_rows[4][7])

        columns_to_transform = [
            'S1', 'Median', 'S5', 'Mean', 'Observation number',
            'Standard deviation', 'Mean day of the month',
            'Fraction of daylight observations', 'Mean Longitude', 'Mean Latitude'
        ]

        index = 8
        for variableName in variableArray:
            for stat in columns_to_transform:
                cleaning_rows[0].insert(index, variableName + "-" + stat)
                index += 1
        for stat in columns_to_transform:
            cleaning_rows[0].remove(stat)

        for row_index in range(len(cleaning_rows)):
            mod = (row_index - 1) % 4
            if row_index != 0 and mod != 0:
                for col_index in range(10):
                    cleaning_rows[row_index - mod].insert(
                        col_index + 8 + 10 * mod,
                        cleaning_rows[row_index][col_index + 8]
                    )

        new_cleaning_rows = [row for row in cleaning_rows if row[7] not in variableArray[1:]]

        # Removes Variable column
        for row in cleaning_rows:
            del row[7]

        if Verbosity:
            verbosity(new_cleaning_rows)
        writeToCSV(cleaned_csv_output, new_cleaning_rows)

        # Step 10: Remove rows with NA
        if Verbosity:
            print("Step 10/14: Remove rows with NA")
        new_cleaning_rows = [row for row in new_cleaning_rows if 'NA' not in row]

        if Verbosity:
            verbosity(new_cleaning_rows)
        writeToCSV(cleaned_csv_output, new_cleaning_rows)

        # Step 11: Year/Month splitting
        if Verbosity:
            print("Step 11/14: Year/Month splitting")
        headers = new_cleaning_rows[0]
        data_rows = new_cleaning_rows[1:]

        ym_index = headers.index("Year/Month")
        headers.extend(["Year", "Month", "Running Month"])

        for row in data_rows:
            try:
                dt = datetime.strptime(row[ym_index], "%Y/%m")
                year = dt.year
                month = dt.month
                running_month = year * 12 + month
            except ValueError:
                year = month = running_month = "NA"
            row.extend([str(year), str(month), str(running_month)])

        new_cleaning_rows = [headers] + data_rows
        writeToCSV(cleaned_csv_output, new_cleaning_rows)

        # Step 12: Drop extra columns
        columns_to_remove = ['Year/Month', 'Box Size', 'PID2: Standard/Enhanced', 'Group', 'Checksum']

        for col in columns_to_remove:
            if col in headers:
                idx = headers.index(col)
                headers.pop(idx)
                for row in data_rows:
                    row.pop(idx)

        new_cleaning_rows = [headers] + data_rows
        writeToCSV(cleaned_csv_output, new_cleaning_rows)

        # Step 13: Convert -Mean Longitude and -Mean Latitude into x and y stats
        for i, h in enumerate(headers):
            if h.endswith("-Mean Longitude"):
                headers[i] = h.replace("-Mean Longitude", "-x")
            elif h.endswith("-Mean Latitude"):
                headers[i] = h.replace("-Mean Latitude", "-y")

        new_cleaning_rows = [headers] + data_rows
        writeToCSV(cleaned_csv_output, new_cleaning_rows)

        # Step 14: Reorder columns (Year, Month, Running Month to front)
        if Verbosity:
            print("Step 14/14: Reorder columns")

        columns_to_move = ["Year", "Month", "Running Month"]
        remaining_headers = [col for col in headers if col not in columns_to_move]
        new_header_order = columns_to_move + remaining_headers

        header_idx_map = {col: idx for idx, col in enumerate(headers)}
        data_rows = [[row[header_idx_map[col]] for col in new_header_order] for row in data_rows]
        headers = new_header_order

        new_cleaning_rows = [headers] + data_rows
        writeToCSV(cleaned_csv_output, new_cleaning_rows)

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
                merged_df = pd.merge(
                    merged_df, df,
                    on=['Year', 'Month', 'Running Month', 'Longitude', 'Latitude'],
                    how='outer'
                )
        if merged_df is None:
            continue
        output_file = f"{prefix}.csv"
        merged_df = merged_df.drop(columns=[col for col in merged_df.columns if col.endswith("_y")])
        merged_df.rename(
            columns={col: col.rstrip('_x') for col in merged_df.columns if col.endswith('_x')},
            inplace=True
        )
        merged_df.to_csv(output_file, index=False)
        stem_removal = f'rm -f "{prefix}".*.csv'
        subprocess.run(stem_removal, shell=True, capture_output=True, text=True, executable="/bin/bash")
        print(f"Merged {prefix}.")

def removeUnderscores(path):
    command = f'for f in "{path}"*.csv; do mv "$f" "$(echo "$f" | sed s/_/./)"; done'
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

    # Drop "Running Month" if present
    df = df.drop(columns=[c for c in df.columns if c.lower() == "running month"], errors="ignore")

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

    txtList = [
        f for f in os.listdir(path)
        if os.path.isfile(os.path.join(path, f)) and f.endswith(".txt")
    ]

    TXTtoCSV(path, txtList)
    deleteExtension(path, "txt")

    mergeGroups(path)
    removeUnderscores(path)

    # New: apply final renaming/ordering to all CSVs under this path
    postprocess_all_csvs(path)

if __name__ == "__main__":
    main()
