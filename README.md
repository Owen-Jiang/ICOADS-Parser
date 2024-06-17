# ICOADS-Parser

This code is designed to pull data from the NOAA's International Comprehensive Ocean-Atmosphere Data Set (ICOADS) and pull the output from FORTRAN code to a better format. This would likely find itself useful for oceanographic researchers looking to analyze data using more modern formats.

Note: this code was tested first on Linux, please make adjustments to your system accordingly.

## Prerequisites
+ FORTRAN 77
+ Cshell
+ Python
  + pandas
  + csv
 
## How to Use
There are a few commands to run, and they require some setup. I've named folders in the text below for the sake of clarity, but feel free to change things to your preference.
+ First, download ``rdmsg1_Cshell`` and ``data_cleaner.py``. Place them both in a dedicated folder, which I will denote ``FOLDER`` for the rest of this document.
+ Next, download the data. There are two layers of extraction necessary, so after you've done that, move the bare .STD files that you wish to move to ``FOLDER``. I advise creating another subfolder (you can name it ``STDs``) inside ``FOLDER`` because of the data extraction process that needs to occur.
+ Then move into the ``FOLDER`` directory and run the following command: ``for file in STDs/*.STD; do { csh rdmsg1_Cshell "$file"; echo "$1 $(date)" | ./a.out;} | tee "${file}.txt"; done``
+ The terminal will proceed to read the terminal output into a .txt file and save it as a file in the same folder with the same name but with a .txt extension.
+ Once that's done, then, in that same folder, run ``python3 data_cleaner.py``. This will create a bunch of properly formatted csv files with the extracted data. This process usually takes a bit longer.
+ You now have all your data in the form of csvs!
+ If something isn't working in the Python code, you can enable verbosity in data_cleaner.py on Line 25 to display what's going on in the terminal.
