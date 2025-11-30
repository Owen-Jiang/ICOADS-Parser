# ICOADS-Parser

This code is designed to pull data from the NOAA's International Comprehensive Ocean-Atmosphere Data Set (ICOADS) and pull the output from FORTRAN code to a better format. This would likely find itself useful for oceanographic researchers looking to analyze data using more modern formats.

Note: this code was tested first on Linux, please make adjustments to your system accordingly.

Most recent data from: 2025-07

ICOADS last updated: 2025-08-12

This file last updated: 2025-11-29

**NEWS**: I have elected to bring the column names in line with current standards (see https://osdata.gdex.ucar.edu/web/datasets/d548001/docs/msg). This should have the added bonus of reducing the file sizes by a small amount but primarily is meant to help shorten the length of column names.

## Prerequisites
+ FORTRAN 77
+ Cshell
+ Python
  + pandas
  + csv

## How to Use the Extractor
There are a few commands to run, and they require some setup. I've named folders in the text below for the sake of clarity, but feel free to change things to your preference.
+ First, download the two files ``rdmsg1_Cshell`` and ``d548001ToCSV.py`` contained in the ``code`` folder. Place them together in the same folder.
+ Next, download the data. There are two layers of extraction necessary, so after you've done that, you have various .STD files. Choose a folder to dedicate for this purpose.
+ Open your terminal and while in the folder with the ``code`` folder, run the Python program with ``python3 d548001ToCSV.py``. Follow the necessary prompts. Please note that the path that you enter into the system is either relative or absolute but your file path cannot contain any directories with spaces. This is a FORTRAN limitation.
+ The terminal will read the terminal outputs and save every STD file as a TXT file before converting it to a proper CSV. The program is slow. Please note that if your system RAM is not sufficiently large the program will likely crash after conversion to TXT, in which case you have to open up the Python program and comment out the ``STDToCSV`` method and run it again.
+ Note that the program will remove all extraneous files produced in the process, but that it only does so after all processes have finished. Ensure you have enough memory for this before you begin.

## How to Use the CSVs
The ``csv`` folder contains 1-degree (post-1960) (12.6 GB) and 2-degree (post-1800) (7.2 GB) data, split into decade folders and each CSV containing a year and month. Columns in each CSV include Year, Month, the Running Month (Year * 12 + Month), Longitude, Latitude, and the first sextile (S1), median, fifth sextile (S5), mean, number of observations, standard deviation, mean day of the month of observance, and fraction of daylight observations for all sixteen variables in the dataset.

## Troubleshooting
+ If something isn't working in the Python code, you can enable verbosity within ``d548001ToCSV.py`` to see what's going on.
+ Email ``projecthandsondeck (at) gmail (dot) com`` if there's something wrong with something in this repository here.

## Citations
+ Research Data Archive/Computational and Information Systems Laboratory/National Center for Atmospheric Research/University Corporation for Atmospheric Research, Physical Sciences Laboratory/Earth System Research Laboratory/OAR/NOAA/U.S. Department of Commerce, Cooperative Institute for Research in Environmental Sciences/University of Colorado, National Oceanography Centre/University of Southampton, Met Office/Ministry of Defence/United Kingdom, Deutscher Wetterdienst (German Meteorological Service)/Germany, Department of Atmospheric Science/University of Washington, Center for Ocean-Atmospheric Prediction Studies/Florida State University, and National Centers for Environmental Information/NESDIS/NOAA/U.S. Department of Commerce. 2016, updated monthly. _International Comprehensive Ocean-Atmosphere Data Set (ICOADS) Release 3, Monthly Summaries_. Research Data Archive at the National Center for Atmospheric Research, Computational and Information Systems Laboratory. https://doi.org/10.5065/D6V40SFD.
+ Comprehensive Ocean-Atmosphere Data Set (COADS): Software
  Program name.level: RDMSG.01D
  19 February 1997
  Function: Read and print: Monthly Summary Groups (MSG.1)
  Author: S.Lubker
