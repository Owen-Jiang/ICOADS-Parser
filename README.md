# ICOADS-Parser

This code is designed to pull data from the NOAA's International Comprehensive Ocean-Atmosphere Data Set (ICOADS) and pull the output from FORTRAN code to a better format. This would likely find itself useful for oceanographic researchers looking to analyze data using more modern formats.

## About ds548.0
This dataset contains individual observations from the ICOADS dataset, and there is already a Python program on the website located [here](https://rda.ucar.edu/OS/web/datasets/d548000/software/ICOADS_IMMA12NetCDF_python.zip), though there are some indentation problems with it.

## Terminal Output

### Prerequisites
+ Cshell
+ FORTRAN 90

If you want to display the code directly in the terminal, you will need rwimma1 (there is a mistake in the file on the website, so please download the one attached here instead). Extract the file from the .gz (like IMMA1_R3.1.0_2014-11 for example), then run the following command:

```csh rwimma1 < [name of the file here]```

## Python to netCDF4 (see link above)

Credit goes to Zhankun Wang for writing the vast majority of the code. Several things to note: If you are using Python 3, Line 337 in the file named IMMA2nc1.py needs to be rewritten as ```print(var, type(data.data[var][index[0]]))``` due to changes in how Python 3+ handles print statements. Additionally (and this is not limited to any version of Python), please replace all occurrences of ```\t``` in all these Python files with 8 spaces (```        ```) so the indentation works out.
