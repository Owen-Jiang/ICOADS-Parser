import os
import subprocess
import time
import pandas as pd
import csv
import glob
from datetime import datetime
from tqdm import tqdm

def preamble():
    print("ICOADS d548001 Data Access V1.0")
    print("Please download the applicable .STD files that are located on the Research Data Archive at https://rda.ucar.edu/datasets/d548001/ and extract the .tar and .gz files.")
    # print(r"for file in PATH/*.STD; do stem=$(stem "$file" .STD); { csh rdmsg1_Cshell "$file"; echo "$1 $(date)" | ./a.out; } | tee "PATH/${stem}.txt"; done")

def fileLocations():
    path = input("Path to STD files (due to FORTRAN limitations, this path cannot contain spaces or ~, also make sure there is nothing else in this folder) (also don't convert too many files at once, you may crash)\n: ")

    return path

def STDtoTXT(path):
    command = (
        f'for file in "{path}"/*.STD; do '
        f'base_name=$(basename "$file" .STD); '
        f'{{ csh rdmsg1_Cshell "$file"; echo "$1 $(date)" | ./a.out; }} '
        f'| tee "{path}/${{base_name}}.txt"; '
        f'done'
    )

    start_time = time.perf_counter()
    process = subprocess.run(command, shell=True, capture_output=True, text=True, executable="/bin/bash")
    end_time = time.perf_counter()

    if process.returncode == 0:
        print(f"STD to TXT executed successfully in {end_time - start_time} seconds:")
        print(process.stdout)
    else:
        print(f"STD to TXT failed with error code {process.returncode}:")
        print(process.stderr)

def deleteExtension(path, extension):
    command = (f'rm -f "{path}"/*.{extension}')
    process = subprocess.run(command, shell=True, capture_output=True, text=True, executable="/bin/bash")

def TXTtoCSV(path, fileNames):
    for fileName in tqdm(fileNames, desc="Converting TXTs to CSVs"):
        print("Working on " + fileName)
        # If you want to see the printed rows
        Verbosity = False

        # .txt and .csv locations
        txt_input = path + fileName

        csv_output = path + "undelimited_" + fileName.replace(".txt", ".csv")
        cleaned_csv_output = path + fileName.replace(".txt", ".csv")

        # Convert .txt to .csv
        df = pd.read_csv(txt_input)
        df.to_csv(csv_output, index = None)

        # The following is the fix the delimiting issue
        delimiter_fix(csv_output, cleaned_csv_output)

        undelimited_removal = (f'rm -f "{path}"/undelimited_*.csv')
        subprocess.run(undelimited_removal, shell=True, capture_output=True, text=True, executable="/bin/bash")

        # Read cleaned_csv_output
        infile = open(cleaned_csv_output, 'r')
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

        # Data cleaning process
        # Step 1: Bring down time and push second row with statistics right one cell
        if Verbosity:
            print("Step 1/14: Time and Second Row Push, last row counter")
        for row_index in range(len(cleaning_rows)):
        	# This row contains year, month, box size, longitude, latitude, standard or enhanced statistics, group, and checksum
        	if row_index % 6 == 0:
        		# Cell 0
        		# Pull the time_string for the first cell of every 6th row
        		time_string = cleaning_rows[row_index][0]
        		# Remove periods in the year/month string
        		time_string = time_string[0:time_string.find(".")] + time_string[(time_string.find(".") + 1):-1]
        		# Replace the first cell of every 6 rows with a time descriptor
        		cleaning_rows[row_index][0] = "Year/Month"

        	else:	# Other rows contained need to have time added to the first column
        		cleaning_rows[row_index].insert(0, time_string)
        		# If the row is the statistics row that begins with & (placed there for delimiting purposes), remove the & and replace it with ''
        		if row_index % 6 == 1:
        			cleaning_rows[row_index][1] = ""
        		# Remove the last row that shows the counter
        	if row_index == len(cleaning_rows) - 1:
        		del cleaning_rows[row_index]

        # Verbose output for seeing data cleaning in action
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
        		# Empty the previous positions
        		for cell in range(6):
        			del cleaning_rows[row_index][cell + 2] # Don't change this, calculation of the change in row size has already been made
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
        		cleaning_rows[row_index] = ["Year/Month", "Box Size", "Longitude", "Latitude", "PID2: Standard/Enhanced", "Group", "Checksum", "Variable", "S1", "Median", "S5", "Mean", "Observation number", "Standard deviation", "Mean day of the month", "Fraction of daylight observations", "Mean Longitude", "Mean Latitude"]

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

        # Step 7: Remove all extra headers in the middle
        if Verbosity:
            print("Step 7/14: Remove extra headers")
        cleaning_rows = [row for i, row in enumerate(cleaning_rows) if not (row[0] == "Year/Month" and i != 0)]

        if Verbosity:
        	verbosity(cleaning_rows)

        writeToCSV(cleaned_csv_output, cleaning_rows)

        if Verbosity:
            print("Step 8/14: Remove degree signs")
        for row_index, row in enumerate(cleaning_rows):
            for col_index, val in enumerate(row):
                if val.endswith("°"):
                    cleaning_rows[row_index][col_index] = val.rstrip("°")

        if Verbosity:
        	verbosity(cleaning_rows)

        writeToCSV(cleaned_csv_output, cleaning_rows)

        if Verbosity:
            print("Step 9/14: Pivot the table")
        variableArray = (cleaning_rows[1][7], cleaning_rows[2][7], cleaning_rows[3][7], cleaning_rows[4][7])

        columns_to_transform = ['S1', 'Median', 'S5', 'Mean', 'Observation number',
        			            'Standard deviation', 'Mean day of the month',
        			            'Fraction of daylight observations', 'Mean Longitude', 'Mean Latitude']

        # Adds additional columns
        index = 8
        for variableName in variableArray:
        	for stat in columns_to_transform:
        		cleaning_rows[0].insert(index, variableName + "-" + stat)
        		index += 1
        for stat in columns_to_transform:
        	cleaning_rows[0].remove(stat)

        # Moves cells below to the row of the first variable
        for row_index in range(len(cleaning_rows)):
        	mod = (row_index - 1) % 4
        	if row_index != 0 and mod != 0:
        		for col_index in range(10):
        			cleaning_rows[row_index - mod].insert(col_index + 8 + 10 * mod, cleaning_rows[row_index][col_index + 8])

        # Removes extra three rows
        new_cleaning_rows = [row for row in cleaning_rows if row[7] not in variableArray[1:]]

        # Removes Variable column
        for row in cleaning_rows:
        	del row[7]

        if Verbosity:
        	verbosity(new_cleaning_rows)

        writeToCSV(cleaned_csv_output, new_cleaning_rows)

        if Verbosity:
            print("Step 10/14: Remove rows with NA")
        new_cleaning_rows = [row for row in new_cleaning_rows if 'NA' not in row]

        if Verbosity:
        	verbosity(new_cleaning_rows)

        writeToCSV(cleaned_csv_output, new_cleaning_rows)

        if Verbosity:
            print("Step 11/14: Year/Month splitting")
        # Extract headers and data
        headers = new_cleaning_rows[0]
        data_rows = new_cleaning_rows[1:]

        # Find the index of the 'Year/Month' column
        ym_index = headers.index("Year/Month")

        # Add new headers
        headers.extend(["Year", "Month", "Running Month"])

        # Add new columns to each row
        for row in data_rows:
            try:
                dt = datetime.strptime(row[ym_index], "%Y/%m")
                year = dt.year
                month = dt.month
                running_month = year * 12 + month
            except ValueError:
                # Handle invalid date format gracefully
                year = month = running_month = "NA"

            row.extend([str(year), str(month), str(running_month)])

        # Recombine header and data
        new_cleaning_rows = [headers] + data_rows

        if Verbosity:
            verbosity(new_cleaning_rows)

        # Write to CSV
        writeToCSV(cleaned_csv_output, new_cleaning_rows)

        if Verbosity:
            print("Step 12/14: Spatial increments")

        # Get headers and data
        headers = new_cleaning_rows[0]
        data_rows = new_cleaning_rows[1:]

        # Get index positions for the relevant columns
        lon_idx = headers.index('Longitude')
        lat_idx = headers.index('Latitude')
        smean_lon_idx = next(i for i, h in enumerate(headers) if h.endswith('-Mean Longitude'))
        smean_lat_idx = next(i for i, h in enumerate(headers) if h.endswith('-Mean Latitude'))

        # Process rows
        for row in data_rows:
            try:
                # Convert string values to float
                lon = float(row[lon_idx]) + float(row[smean_lon_idx])
                lat = float(row[lat_idx]) + float(row[smean_lat_idx])

                # Wrap-around correction
                if lon > 180:
                    lon -= 360

                # Update values in-place
                row[lon_idx] = str(lon)
                row[lat_idx] = str(lat)

            except ValueError:
                # If conversion fails, keep original or replace with "NA"
                row[lon_idx] = row[lat_idx] = "NA"

        # Recombine header and data
        new_cleaning_rows = [headers] + data_rows

        if Verbosity:
            verbosity(new_cleaning_rows)

        # Write to CSV
        writeToCSV(cleaned_csv_output, new_cleaning_rows)

        if Verbosity:
            print("Step 13/14: Drop extra columns")

        columns_to_remove = [header for header in headers if header.endswith("-Mean Longitude") or header.endswith("-Mean Latitude")] + ['Year/Month', 'Box Size', 'PID2: Standard/Enhanced', 'Group', 'Checksum']

        # Remove optional columns
        for col in columns_to_remove:
            if col in headers:
                idx = headers.index(col)
                headers.pop(idx)
                for row in data_rows:
                    row.pop(idx)

        # Recombine header and data
        new_cleaning_rows = [headers] + data_rows

        if Verbosity:
            verbosity(new_cleaning_rows)

        # Write to CSV
        writeToCSV(cleaned_csv_output, new_cleaning_rows)

        if Verbosity:
            print("Step 14/14: Reorder columns")

        # Columns you want to move to the front
        columns_to_move = ["Year", "Month", "Running Month"]

        # Build a new header order
        remaining_headers = [col for col in headers if col not in columns_to_move]
        new_header_order = columns_to_move + remaining_headers

        # Create a mapping from old header to index
        header_idx_map = {col: idx for idx, col in enumerate(headers)}

        # Reorder each row according to new header order
        data_rows = [[row[header_idx_map[col]] for col in new_header_order] for row in data_rows]
        headers = new_header_order

        new_cleaning_rows = [headers] + data_rows

        if Verbosity:
            verbosity(new_cleaning_rows)

        writeToCSV(cleaned_csv_output, new_cleaning_rows)

def delimiter_fix(input, output):
	# Define the delimiters and the common delimiter
	delimiters = [' ', '|']
	common_delimiter = ','

	# Open the input CSV file for reading and the output CSV file for writing
	with open(input, newline = '') as infile, open(output, 'w', newline = '') as outfile:
		# Create a CSV reader object
		input_reader = csv.reader(infile)

		# Create a CSV writer object
		cleaning_writer = csv.writer(outfile)

		# Iterate over each row in the input CSV file
		for row in input_reader:
			# Initialize a list to store merged elements
			merged_row = []

			# Merge delimiters in the row
			for delimiter in delimiters:
				row[0] = row[0].replace(delimiter, common_delimiter)

			# Split the row using the common delimiter
			split_row = row[0].split(common_delimiter)

			# Remove empty strings from the split row
			split_row = [element for element in split_row if element]

			# Add the split elements to the merged row
			merged_row.extend(split_row)

			# Write the parsed row to the output CSV file
			cleaning_writer.writerow(merged_row)

def writeToCSV(csvFile, rows):
	with open(csvFile, 'w', newline = '') as file:
		writer = csv.writer(file)
		writer.writerows(rows)

def verbosity(cleaning_rows):
	for row_index in range(len(cleaning_rows)):
		print(cleaning_rows[row_index])

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
                merged_df = pd.merge(merged_df, df, on=['Year', 'Month', 'Running Month', 'Longitude', 'Latitude'], how='outer')
        output_file = f"{prefix}.csv"
        merged_df = merged_df.drop(columns=[col for col in df if col.endswith("_y")])
        merged_df.rename(columns={col: col.rstrip('_x') for col in df.columns if col.endswith('_x')}, inplace=True)
        merged_df.to_csv(output_file, index=False)
        stem_removal = (f'rm -f "{prefix}".*.csv')
        process = subprocess.run(stem_removal, shell=True, capture_output=True, text=True, executable="/bin/bash")
        print(f"Merged {prefix}.")

def removeUnderscores(path):
    command = (f'for f in "{path}"/*.csv; do mv "$f" "$(echo "$f" | sed s/_/./)"; done')
    process = subprocess.run(command, shell=True, capture_output=True, text=True, executable="/bin/bash")

def main():
    preamble()
    path = fileLocations()
    # STDtoTXT(path)
    deleteExtension(path, "STD")

    txtList = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f.endswith("txt")]

    TXTtoCSV(path, txtList)

    deleteExtension(path, "txt")

    mergeGroups(path)

    removeUnderscores(path)

main()
