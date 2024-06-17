# To run: python txtTocsv.py

# Helpful imports
import subprocess
import pandas as pd
import csv

def main():

	fileName = input("What is the name of the STD file you wish to parse? (Do not include the .STD at the end.) ")
	
	Verbosity = True

	# .txt and .csv locations
	txt_input = fileName + ".txt"
	csv_output = fileName + ".csv"
	cleaned_csv_output = "cleaned_" + fileName + ".csv"

	# Convert .txt to .csv
	df = pd.read_csv(txt_input)
	df.to_csv(csv_output, index = None)

	# The following is the fix the delimiting issue
	delimiter_fix(csv_output, cleaned_csv_output)

	# Read cleaned_csv_output
	infile = open(cleaned_csv_output, 'r')
	cleaning_reader = csv.reader(infile)
	cleaning_rows = list(cleaning_reader)

	# Delete metadata remnants from reading the terminal
	rowsToDelete = 0
	for row_index in range(len(cleaning_rows)):
		if cleaning_rows[row_index][0] == "1RDMSG.01D":
			rowsToDelete += 1

	for row_index in range(len(cleaning_rows) - rowsToDelete):
		if cleaning_rows[row_index][0] == "1RDMSG.01D":
			del cleaning_rows[row_index]

	writeToCSV(cleaned_csv_output, cleaning_rows)

	# Data cleaning process
	# Step 1: Bring down time and push second row with statistics right one cell
	print("Step 1/7: Time and Second Row Push, last row counter")
	for row_index in range(len(cleaning_rows)):
		# This row contains year, month, box size, longitude, latitude, standard or enhanced statistics, group, and checksum
		if row_index % 6 == 0:
			# Cell 0
			# Pull the time_string for the first cell of every 6th row
			time_string = cleaning_rows[row_index][0]
			# Remove periods in the year/month string
			time_string = time_string[0:time_string.find(".")] + time_string[time_string.find(".") + 1:-1]
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
	print("Step 2/7: Bring down first row variables")
	for row_index in range(len(cleaning_rows)):
		if row_index % 6 == 0:
			box_size = cleaning_rows[row_index][2]
			longitude = cleaning_rows[row_index][4]
			latitude = cleaning_rows[row_index][6]
			enhanced = cleaning_rows[row_index][8]
			group = cleaning_rows[row_index][10]
			checksum = cleaning_rows[row_index][12]
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
	print("Step 3/7: Remove extra rows")
	rowsToDelete = 0
	for row_index in range(len(cleaning_rows)):
		if cleaning_rows[row_index][1] == "":
			rowsToDelete += 1

	for row_index in range(len(cleaning_rows) - rowsToDelete):
		if cleaning_rows[row_index][1] == "":
			del cleaning_rows[row_index]

	if Verbosity:
		verbosity(cleaning_rows)

	writeToCSV(cleaned_csv_output, cleaning_rows)

	# Step 4: Rename headers to something nice
	print("Step 4/7: Header renaming")
	for row_index in range(len(cleaning_rows)):
		if row_index % 5 == 0:
			cleaning_rows[row_index] = ["Year/Month", "Box Size", "Longitude", "Latitude", "PID2: Standard/Enhanced", "Group", "Checksum", "Variable", "S1", "Median", "S5", "Mean", "Observation number", "Standard deviation", "Mean day of the month", "Fraction of daylight observations", "Mean Longitude", "Mean Latitude"]

	if Verbosity:
		verbosity(cleaning_rows)

	writeToCSV(cleaned_csv_output, cleaning_rows)

	# Step 5: Remove invalid measurements
	print("Step 5/7: Remove invalid measurements")
	invalid_data = ['-9999.', '-9999.0', '-9999.00']
	for row_index in range(len(cleaning_rows)):
		for col_index in range(len(cleaning_rows[row_index])):
			if cleaning_rows[row_index][col_index] in invalid_data:
				cleaning_rows[row_index][col_index] = "NA"

	if Verbosity:
		verbosity(cleaning_rows)

	writeToCSV(cleaned_csv_output, cleaning_rows)

	# Step 6: Remove trailing periods
	print("Step 6/7: Remove trailing dots (vestige of floating point)")
	for row_index in range(len(cleaning_rows)):
		for col_index in range(len(cleaning_rows[row_index])):
			if (cleaning_rows[row_index][col_index])[-1] == ".":
				(cleaning_rows[row_index][col_index]) = (cleaning_rows[row_index][col_index])[0:-1]
			if (cleaning_rows[row_index][col_index])[-1] == "°" and (cleaning_rows[row_index][col_index])[-2] == ".":
				(cleaning_rows[row_index][col_index]) = (cleaning_rows[row_index][col_index])[0:-2] + "°"

	if Verbosity:
		verbosity(cleaning_rows)

	writeToCSV(cleaned_csv_output, cleaning_rows)

	# Step 7: Remove all extra headers in the middle
	print("Step 7/7: Remove extra headers")

	rowsToDelete = 0
	for row_index in range(len(cleaning_rows)):
		if cleaning_rows[row_index][0] == "Year/Month" and row_index != 0:
			rowsToDelete += 1

	for row_index in range(len(cleaning_rows) - rowsToDelete):
		if cleaning_rows[row_index][0] == "Year/Month" and row_index != 0:
			del cleaning_rows[row_index]

	if Verbosity:
		verbosity(cleaning_rows)

	writeToCSV(cleaned_csv_output, cleaning_rows)

def delimiter_fix(input, output):
	# Define the delimiters and the common delimiter
	delimiters = [' ', '*']
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

main()
