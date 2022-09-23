# exec_sc.py
#
#   Runs batch short circuit analysis on a group of savecases/buses and
#   outputs to csv.
#
#   Syntax:
#   python exec_sc.py
#
#   Instructions:
#   Ensure the list of savecases (arrCases) and buses (arrBuses) are populated.
#   Settings for the fault calculation are further down in iecs_4()
#
#
#   Revisions:
#   2022/08/28  PVH
#   First release.
#

# ---- Start of imports -------------------------------------------------------
# System imports start here
import os, sys      # For system calls
import re           # Regex
import math
import glob         # Parsing CWD

# ---- Initialize program settings for PSSE run outside of GUI ----------------
PSSE_LOCATION   = "C:\Program Files (x86)\PTI\PSSE34\PSSBIN"

sys.path.append(PSSE_LOCATION)
os.environ["PATH"] = os.environ["PATH"] + ";" + PSSE_LOCATION

# ---- Resuming imports -------------------------------------------------------
import psse34
import psspy
import redirect

redirect.psse2py()
psspy.throwPsseExceptions = True
# ---- End of   imports -------------------------------------------------------


# ---- Start of global definitions --------------------------------------------

# List of sc cases to process
arrCases  = [   "ir652_max.sav",
                "ir652_min.sav"
                ]   # End of arrCases

# List of buses to process (18 max)
arrBuses    = [ 2024,
                2028,
                2034,
                2035,
                2042
                ]   # End of arrBuses

# Output csv headers
arrCsvHeaders   = [ "case",
                    "bus",
                    "name",
                    "MVA",
                    "amps",
                    "impedance",
                    "X/R"
                    ]   # End of arrCsvHeaders

# Short circuit report prefix. Used for both the report output files and
# search pattern when parsing to csv.
strReports      = "sc_report_-_"
strProg         = "sc_prog_-_"                  # This one is just there for conformity

csvDelim        = ","
csvEOL          = "\n"

dictExt         = { "ext_csv"   : ".csv",
                    "ext_txt"   : ".txt"
                    }

# Regex strings, expecting each bus entry to have this line precede data:
# X------------ BUS ------------X          MVA        AMP      DEG       AMP       AMP       AMP       AMP       AMP
#   2024     [MyBusName   100.00] 3PH    2573.54   14858.3   -88.07   40041.5   39580.3        0.0   13702.0   13702.0
# THEVENIN IMPEDANCE, X/R  (OHM)    Z+:/4.274/88.066, 29.60898
#
reHeaderLine    = "X------------ BUS ------------X"
reBus           = "\d{1,}"                                      # Bus numbers with at least 1 digit
reName          = "\[(.+?)\]"
reMVA           = "3PH[\s]*([\d]*\.[\d]*)"
reAmps          = "3PH[\s]*[\d]*\.[\d]*[\s]*([\d]*\.[\d]*)"
reImp           = "THEVENIN IMPEDANCE.*Z\+\:(.*)\,"
reXR            = "THEVENIN IMPEDANCE.*\, ([\d]*\.[\d]*)"

# ---- End of   global definitions --------------------------------------------


# ---- Start of main() --------------------------------------------------------
if __name__ == "__main__":

    # Setup csv output file
    fCsv    = open( "sc_results" + dictExt["ext_csv"],
                    "w"
                    )

    # Write headers
    for index, indCol in enumerate(arrCsvHeaders):
        fCsv.write(indCol)
        
        if(index < (len(arrCsvHeaders) - 1)):
            fCsv.write(csvDelim)
    fCsv.write(csvEOL)

    # Start PSS/e
    iErr = psspy.psseinit()
    
    # Loop through short circuit basecases
    for basecase in arrCases:
        # Get case name (full name w/o extension)
        nameCase = os.path.splitext(basecase)[0]
        
        # Load basecase
        iErr = psspy.case(basecase)
        
        # Set up SC reporting options
        psspy.short_circuit_units(          ival    = 1)            # physical units
        psspy.short_circuit_z_units(        ival    = 1)            # physical units
        psspy.short_circuit_coordinates(    ival    = 1)            # polar coordinates
        psspy.short_circuit_z_coordinates(  ival    = 0)            # polar coordinates
        
        # Set report file
        psspy.lines_per_page_one_device(    device  = 1,
                                            ival    = 60)
        psspy.report_output(    islct       = 2,
                                filarg      = strReports + nameCase + dictExt["ext_txt"],
                                options1    = 0
                                )
        psspy.progress_output(  islct       = 2,
                                filarg      = strProg + nameCase + dictExt["ext_txt"],
                                options     = 0
                                )
    
        # Set up for SC
        iErr = psspy.flat_2(    options1    = 1,        # classical fault analysis conditions option
                                options2    = 0,        # tap ratios unchanged
                                options3    = 0,        # leave line charging unchanged
                                options4    = 0,        # leave fixed bus shunts unchanged
                                options5    = 0,        # switched shunts unchanged
                                options6    = 0,        # line shunts unchanged
                                options7    = 0,        # transformer magnetizing unchanged
                                options8    = 3         # loads constant, power, and admittance set to 0.0 in all sequence networks
                            )
        
        # Set up bus subsystem
        mySid = 1
        psspy.bsys(     sid         = mySid,
                        numbus      = len(arrBuses),
                        buses       = arrBuses
                        )

        # Run fault calculation
        psspy.iecs_4(   sid         = mySid,
                        all         = 0,                # process only buses in subsystem SID
                        status1     = 1,                # include 3ph faults
                        status2     = 0,                # no lg faults
                        status3     = 0,                # no llg faults
                        status4     = 0,                # no ll faults
                        status5     = 1,                # report total fault currents (mva, amps, impedance, and x/r)
                        status6     = 0,                # number of levels back
                        status7     = 0,                # fault at network bus
                        status8     = 0,                # no line out faults
                        status9     = 0,                # no line end faults
                        status10    = 2,                # set tap raiots and phase shift angles to 0 in all seq
                        status11    = 2,                # set line charging to 0 in all seq
                        status12    = 2,                # set line, fixed, and switched shunts, and magnetizing admittance to 0 in all seq
                        status13    = 0,                # DC line and FACTS blocked
                        status14    = 0,                # ignore zero seq transformer impedance
                        status15    = 0,                # voltage factor C for max fault currents
                        status16    = 2,                # set loads to 0 in all seq
                        status17    = 1                 # use transient reactance
                        )

        # End of loop: for sFile in fileList
        
    # Parse report to csv
    fReportList = glob.glob(strReports + "*" + dictExt["ext_txt"])
    
    for sFile in fReportList:
        print("Working on [" + sFile + "]")
        
        # Strip extension for output filenames
        sCaseName = sFile.rsplit(".", 1)[0]
        
        # Open input file, read lines, and close
        hFileIn     = open(sFile, "r")
        bufLines    = hFileIn.readlines()
        hFileIn.close()
        
        # Cycle through each line and process if we find a match, starting with
        # bus number
        ctrLines    = 0
        iLen        = len(bufLines)
        while(ctrLines < iLen):
            result = re.match(reHeaderLine, bufLines[ctrLines])

            # If bus number is found, process
            if(result):
                # Advance to the next line to grab the data
                ctrLines = ctrLines + 1
                
                # Get bus
                subResult   = re.findall(reBus, bufLines[ctrLines])
                strBus      = subResult[0]
                
                # Get name
                subResult   = re.findall(reName, bufLines[ctrLines])
                strName     = subResult[0]

                # Get SC MVA
                subResult   = re.findall(reMVA, bufLines[ctrLines])
                strMVA      = subResult[0]

                # Get SC amps
                subResult   = re.findall(reAmps, bufLines[ctrLines])
                strAmps      = subResult[0]
                
                # Get impedance
                subResult   = re.findall(reImp, bufLines[ctrLines + 1])
                strImp      = subResult[0]
                
                # Get X/R (next line)
                subResult   = re.findall(reXR, bufLines[ctrLines + 1])
                strXR       = subResult[0]
                
                print(sCaseName + ":   " + strBus + ": " + strName + ", " + strMVA + ", " + strAmps + ", " + strImp + ", " + strXR)

                # Write to output file
                fCsv.write(sCaseName + csvDelim)
                fCsv.write(strBus + csvDelim)
                fCsv.write(strName + csvDelim)
                fCsv.write(strMVA + csvDelim)
                fCsv.write(strAmps + csvDelim)
                fCsv.write(strXR + csvEOL)

            ctrLines = ctrLines + 1
        # End of while(ctrLines < iLen)

    # Cleanup
    fCsv.close()

# ---- End   of main() --------------------------------------------------------
