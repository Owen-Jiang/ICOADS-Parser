# ICOADS-Parser

This code is designed to pull data from the NOAA's International Comprehensive Ocean-Atmosphere Data Set (ICOADS) and pull the output from FORTRAN code to a better format. This would likely find itself useful for oceanographic researchers looking to analyze data using more modern formats.

Note: this code was tested first on Linux, please make adjustments to your system accordingly.
Note: the code is different for different kinds of datasets. Please use the releases page or the branch navigator to get to the right place. The main branch serves only as a landing page.

## Prerequisites
+ FORTRAN 77 (90 works for ds548.0)
+ Cshell
+ Python (ideally above 3.7)
  + pandas
  + csv
