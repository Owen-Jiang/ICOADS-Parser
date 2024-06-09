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
+ ```bash | tee MSG2.[year].[month].[day].txt```
+ ```csh rdmsg1_Cshell MSG2.[year].[month].[day].STD```
+ ```echo "$1 `date`" | ./a.out```
+ ```exit```
+ ```python3 data_cleaner.py```
