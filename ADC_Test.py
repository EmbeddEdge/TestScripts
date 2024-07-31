## @package pulseCount_Test
# Author:  Turyn Lim Banda
#
# Date: 23 April 2018
#
# Edited by: Turyn
#
# Date Last Modified: 08 May 2018
#
# Latest change: First Operating version of the script. Still needs cleaning up with passing parameters and variables. The script cannot reset the controller after each round of testing.
#                The controller needs to be manually reset. Controller FW needs update to fix this.
#
# Purpose: A script to validate a devices ability to accurately sample and measure a sine wave input
#
# Version : V1.0
#
#  More details.
#
#  This script sends commands to a controller board that generates a sinusoidal waveform at X amplitude and Y frequency.
#  That device then samples the waveform and returns 3 values, the average ADC count, the minimum, the maximum. 
#  The script then checks whether the returned values are accurate according to the input waveform.
#  This test runs continously through a specified amount of iterations.

import argparse
from argparse import RawTextHelpFormatter
from enum import Enum
import serial
import logging
import time
import math


MAJOR = 1
MINOR = 0

class Amplitudes(Enum):
    Max = 0.43
    Min = 0.0

class Frequencies(Enum):
    Max = 110
    Min = 1

#class ADCaverageLimits(Enum):
#    Max = What
#    Min = Waht


## Documentation for the InputParse class.
#
#  This class defines the methods used to provide modem functionality
class InputParse(object):
    
    ## The constructor.
    def __init__(self):
        print ("InputParse Initialised")

    ## Documentation for the GetInput method.
    #
    # This method aqcuires and parses all the user defined arguments
    def GetInput(self):

        global args 
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description="Validates the ADC measurements of the DUT device \n\n"
                                                     #"Each device under test (DUT) publishes three parameters (to a Frame in openHAB):\n"
                                                     #"  -Serial Number\n"
                                                     #"  -Test Status\n"
                                                     #"  -Pass Rate\n"
                                                     #"  -Test Counter\n\n"
                                                     #"Link to the sitemap:\n"
                                                     #"  http://192.168.2.32:8080/basicui/app?sitemap=sg102\n\n"
                                                     "The results are also logged in a text file formatted:\n"
                                                     #"  <Device#>_ModemTests_<serialnumber>_<TCP port>.log\n\n"
                                                     "  SamplingEngine_Results.log\n\n"
                                                     "An example command using all possible arguments looks as follows:\n"
                                                     "  python SamplingEngine_Test.py <arguments>\n\n"
                                                     "Remember to substitute the example values with those of the actual device under test\n\n"
                                                     #"Note: The device will ping every 5 mins indefinitely by default\n"
                                                     "      See the positional and optional argument descriptions for more usage information\n\n")
        parser.add_argument("dutCOM", type=str, help=           "COM port of the DUT e.g. 'COM7' or '/dev/ttyUSB0'")
        parser.add_argument("dutBaud", type=int, help=          "Baudrate of the DUT e.g. '115200'")
        parser.add_argument("uCOM", type=str, help=             "COM port of the Controller e.g. 'COM8' or '/dev/ttyUSB1'")
        parser.add_argument("uBaud", type=int, help=            "Baudrate of the Controller e.g. '9600'")
        parser.add_argument("Amplitude", type=float, help=        "Amplitude of sinewave from 0-0.5 e.g. '0.5'")
        parser.add_argument("Frequency", type=int, help=        "Frequency of the Sine wave e.g. '50'")
        parser.add_argument("-i", "--interval", type=int, help= "Interval between Tests")
        parser.add_argument("-m", "--maxtest", type=int, help=   "Maximum amount of tests to run")
    
        args = parser.parse_args()
        return args.dutCOM, args.dutBaud, args.uCOM, args.uBaud, args.Amplitude, args.Frequency

## Documentation for the SerialConnecter class.
#
#  This class defines the methods used to provide modem functionality
class SerialConnecter(object):
    
    ## The constructor.
    def __init__(self):
        print ("SerialConnecter Initialised")

    ## Documentation for openSerialPortCON method.
    #  @param self The object pointer.
    def openSerialPortCON(self):
        self.ser1 = serial.Serial(uC_PORT, uC_BAUD, timeout=10)
        print ("Controller Serial Port: Open") 

    ## Documentation for openSerialPortDUT method.
    #  @param self The object pointer.
    def openSerialPortDUT(self):
        self.ser2 = serial.Serial(DUT_PORT, DUT_BAUD, timeout=10)
        print ("DUT Serial Port: Open") 

    ## Documentation for SendSerialCON method.
    #  @param self The object pointer.
    def SendSerialCON(self,command, getline=False):
        print ("Controller Serial Port Tx: ", command)
        self.ser1.write(command)
        data = ''
        if getline:
            data=self.ReadLine()
        return data

    ## Documentation for SendSerialDUT method.
    #  @param self The object pointer.
    def SendSerialDUT(self,command, getline=False):
        print ("DUT Serial Port Tx: ", command)
        self.ser2.write(command)
        data = ''
        if getline:
            data=self.ReadLine()
        return data    

    ## Documentation for ReadSerialPortLineCON method.
    #  @param self The object pointer.
    def ReadSerialPortLineCON(self):
        data = self.ser1.readline()
        print ("Controller Serial Port Rx: ", data)
        return data

    ## Documentation for ReadSerialPortLineDUT method.
    #  @param self The object pointer.
    def ReadSerialPortLineDUT(self):
        data = self.ser2.readline()
        print ("DUT Serial Port Rx: ", data)
        return data    

    ## Documentation for CloseSerialPortCON method.
    #  @param self The object pointer.
    def CloseSerialPortCON(self):
        self.ser1.close()
        print ("Controller Serial Port: Closed")

    ## Documentation for CloseSerialPortDUT method.
    #  @param self The object pointer.
    def CloseSerialPortDUT(self):
        self.ser2.close()
        print ("DUT Serial Port: Closed")

## Documentation for the SamplingTest class.
#
#  This class defines the methods used to provide modem functionality
class SamplingTest(object):

    ## The constructor.
    def __init__(self):
        print ("SamplingTest Initialised")

    ## Documentation for RunTest method.
    #
    # This method perfoms the Sampling Engine test.
    # It opens a serial port to the controller, sends a command to generate a sine wave, verifies the command ran
    # It then opens a serial port to the DUT and reads the returned values.
    # It calculates the expected DUT values from the input parameters passed to the controller.
    # The returned values are then evaluated against expected results.
    # if the values returned are as expected then the test is a success, if any values fall outside of tolerance then the test is a fail 
    #  @param self The object pointer.
    def RunTest(self):

        #Local Variables------------------------------------------------------------------------
        #DUT ADC Configuration
        fGain       = 0.17    #Gain value of the ADC = 1/6
        BitRes      = 0.59    #Bit resolution of the DUT ADC in mV = 0.59  
        #Controller DAC Configuration
        fVrefDAC    = 3300    #Voltage reference used in the controller DAC in mV
        fOffsetDC   = 0.43    #DC offset value in terms of Controller DAC output
        iSampleDAC  = 1       #Current sample used in DAC
        iMaxSamples = 100     #Number of samples used by DAC
        fDacVal     = 0.0     #DAC Voltage
        #Measurement Variables     
        fVoltMean   = 0.0     #Represent the mean voltage of the input wave in mV
        fVoltPkMax  = 0.0     #Represent the maximum peak woltage of the input wave in mV
        fVoltPkMin  = 0.0     #Represent the maximum peak woltage of the input wave in mV
        fDACValSum  = 0       #Summation of DAC values used to calculate the mean
        iADCmean    = 0       #Expected Mean Value for ADC 
        iADCpeakMin = 0       #Expected Maximum peak Value for ADC
        iADCpeakMax = 0       #Expected Maximum peak Value for ADC 
        #flags
        
        
        #-----------------------------------------------------------------------------------------
        
        #Define Tolerance dictionaries--------
        ADCMeanLimits = {
            'Max': iADCmean + 20,
            'Min': iADCmean - 20
        }

        ADCMinLimits = {
            'Max': iADCpeakMin + 20,
            'Min': iADCpeakMin - 20
        }

        ADCMaxLimits = {
            'Max': iADCpeakMax + 20,
            'Min': iADCpeakMax - 20
        }
        #------------------------------------

        #Extract readings from the DUT Serial port------------------------------------- 
        #Read DUT data
        print ("Wait for DUT result")
        received_data = myConnector.ReadSerialPortLineDUT().rstrip()
        Header1,ADC_Channel1,ADC_Mean1,ADC_Min1,ADC_Max1=received_data.split(",")
        ADC_Max1 = ADC_Max1.rstrip()
        #time.sleep(1)
        received_data = myConnector.ReadSerialPortLineDUT()
        Header2,ADC_Channel2,ADC_Mean2,ADC_Min2,ADC_Max2=received_data.split(",")
        ADC_Max2 = ADC_Max2.rstrip()
        #Debug Trace---------------------------------------------
        #print "Header = " + str(Header1)
        #print "ADC Channel = " + str(ADC_Channel1)
        #print "ADC Average Count = " + str(ADC_Mean1)
        #print "ADC Minimum Count = " + str(ADC_Min1)
        #print "ADC Maximum Count = " + str(ADC_Max1)
        #print "Header = " + str(Header2)
        #print "ADC Channel = " + str(ADC_Channel2)
        #print "ADC Average Count = " + str(ADC_Mean2)
        #print "ADC Minimum Count = " + str(ADC_Min2)
        #print "ADC Maximum Count = " + str(ADC_Max2)
        #-------------------------------------------------------
        #----------------------------------------------------------------------------

        #Convert input fAmp to Comparable ADC Values

        #Calculate the expected Mean ADC Value----------------------------------------------------------------------------------------------    
        for iSampleDAC in range(1, iMaxSamples):
            fDacVal = fAMP*math.sin(iSampleDAC*((2*math.pi)/iMaxSamples)) + fOffsetDC
            fDACValSum += fDacVal
        
        fDACValMean = fDACValSum/iMaxSamples                #Quotient of the sum of DAC samples in DAC units and the number of samples
        fVoltMean = fDACValMean*fVrefDAC                    #Convert DAC values to voltage in mV  
        iADCmean  = fVoltMean*fGain/BitRes                  #Convert the mean value in voltage to DUT comparable ADC value
        iADCmean  = int(iADCmean)                           #Should be an int
    
        #Debug Trace-------------------------------------------------------------
        #print "Average Value from DAC:                      " + str(fDACValMean)    
        #print "Average mV Value from DAC:                   " + str(fVoltMean) 
        #print "Expected Average Voltage Value from DUT ADC: " + str(iADCmean)
        #------------------------------------------------------------------------

        #-----------------------------------------------------------------------------------------------------------------------------------

        #Calculate the expected Min ADC Value---------------------------------------------------------------------------------------------- 
        fDacVal = fAMP*math.sin(75*((2*math.pi)/iMaxSamples)) + fOffsetDC   #The lowest value from the DAC in DAC units
        fVoltPkMin = fDacVal*fVrefDAC                                       #Convert DAC values to voltage in mV 
        iADCpeakMin  = fVoltPkMin*fGain/BitRes                              #Convert the mean value in voltage to DUT comparable ADC value
        iADCpeakMin  = int(iADCpeakMin)                                     #Convert to an int  

        #Debug Trace-------------------------------------------------
        #print "Min Value from DAC:   " + str(fDacVal)
        #print "Min Value in mV:      " + str(fVoltPkMin)
        #print "Expected Min Value in ADC Val: " + str(iADCpeakMin)
        #-------------------------------------------------------------
        #----------------------------------------------------------------------------------------------------------------------------------

        #Calculate the expected Max ADC Value---------------------------------------------------------------------------------------------- 
        fDacVal = fAMP*math.sin(25*((2*math.pi)/iMaxSamples)) + fOffsetDC   #The highest value from the DAC in DAC units
        fVoltPkMax = fDacVal*fVrefDAC                                       #Convert DAC values to voltage in mV
        iADCpeakMax  = fVoltPkMax*fGain/BitRes                               #Convert the mean value in voltage to DUT comparable ADC value
        iADCpeakMax  = int(iADCpeakMax)                                     #Convert to an int
  
        #Debug Trace--------------------------------------
        #print "Max Value from DAC:   " + str(fDacVal)
        #print "Max Value in mV:      " + str(fVoltPkMax)
        #print "Expected Max Value in ADC Val: " + str(iADCpeakMax)
        #-------------------------------------------------
        #-----------------------------------------------------------------------------------------------------------------------------------

        #Set the pass/fail tolerances from the expected values---------------------------------
        #limits for the average ADC Value
        ADCMeanLimits['Max'] = iADCmean + 20
        ADCMeanLimits['Min'] = iADCmean - 20

        #limits for the minimum ADC Value
        ADCMinLimits['Max'] = iADCpeakMin + 20
        ADCMinLimits['Min'] = iADCpeakMin - 20

        #limits for the maximum ADC Value
        ADCMaxLimits['Max'] = iADCpeakMax + 20
        ADCMaxLimits['Min'] = iADCpeakMax - 20
        #--------------------------------------------------------------------------------------


        #Evaluate the values from readings against the expected values-----------
        #Check pass/fail for all 6 parameters
        #Channel 1
        #Channel1 Mean
        if int(ADC_Mean1) <=  ADCMeanLimits['Max'] and int(ADC_Mean1) >= ADCMeanLimits['Min']:
            passADC1mean = True
            
        else:
            passADC1mean = False
        #Channel1 Min
        if int(ADC_Min1) <=  ADCMinLimits['Max'] and int(ADC_Min1) >= ADCMinLimits['Min']:
            passADC1min = True
            
        else:
            passADC1min = False
        #Channel1 Max
        if int(ADC_Max1) <=  ADCMaxLimits['Max'] and int(ADC_Max1) >= ADCMaxLimits['Min']:
            passADC1max = True
            
        else:
            passADC1max = False
        #Channel 2
        #Channel2 Mean
        if int(ADC_Mean2) <=  ADCMeanLimits['Max'] and int(ADC_Mean2) >= ADCMeanLimits['Min']:
            passADC2mean = True
            
        else:
            passADC2mean = False
        #Channel2 Min
        if int(ADC_Min2) <=  ADCMinLimits['Max'] and int(ADC_Min2) >= ADCMinLimits['Min']:
            passADC2min = True
            
        else:
            passADC2min = False
        #Channel2 Max
        if int(ADC_Max2) <=  ADCMaxLimits['Max'] and int(ADC_Max2) >= ADCMaxLimits['Min']:
            passADC2max = True
            
        else:
            passADC2max = False

        #Check overall pass for each channel, channels need all 3 parameters to pass-
        #Channel 1
        if passADC1mean == True and passADC1min == True and passADC1max == True:
            passChannel1 = True
        else:
            passChannel1 = False
        #Channel 2 
        if passADC2mean == True and passADC2min == True and passADC2max == True:
            passChannel2 = True
        else:
            passChannel2 = False
        #-----------------------------------------------------------------------------

        ADCChannelsResults = [passChannel1,passChannel2]

        #Debug Trace----------------------------------------------------
        #print "Channel 1 mean value pass state: " + str(passADC1mean)
        #print "Channel 1 min value pass state:  " + str(passADC1min)
        #print "Channel 1 max value pass state:  " + str(passADC1max)
        #print "Channel 2 mean value pass state: " + str(passADC2mean)
        #print "Channel 2 min value pass state:  " + str(passADC2min)
        #print "Channel 2 max value pass state:  " + str(passADC2max)
        #print "Channel 1 pass state:            " + str(passChannel1)
        #print "Channel 2 pass state:            " + str(passChannel2)
        #print ADCChannelsResults
        #--------------------------------------------------------------
        #------------------------------------------------------------------------
        
        #Return the results
        return ADCChannelsResults

        #myConnector.CloseSerialPortCON()
        #myConnector.CloseSerialPortDUT()

    ## Documentation for CalculateMean method.
    #  @param self The object pointer.
    def CalculateMean(self):
        if args.interval > 0:
            waitInterval = args.interval
        else:
            #default wait period in seconds
            waitInterval = 1
        return waitInterval

    ## Documentation for CheckMaxTests method.
    #  @param self The object pointer.
    def CheckMaxTests(self):
        if args.maxtest > 0:
            maximumTests = args.maxtest
        else:
            maximumTests = 20
        return maximumTests

    ## Documentation for CheckInterval method.
    #  @param self The object pointer.
    def CheckInterval(self):
        if args.interval > 0:
            waitInterval = args.interval
        else:
            #default wait period in seconds
            waitInterval = 1
        return waitInterval

## Documentation for a function.
#
# Runs the tests in a continous loop for a definite or indefinite amount of iterations and logs the results
#Note: Change the function to accept input parameters for Message Ping 
def LoopAndLog():

    #Local Variables
    testCounter = 1
    PassCounter = [0,0]
    SuccessStat = [0,0]
    PassCounterChannel1 = 0
    PassCounterChannel2 = 0
    SuccessStatChannel1 = 0
    SuccessStatChannel2 = 0
    #Flags
    TestBegin = True

    #Create and configure the log file-----------------------------------------------------------------------------------------------
    LOGFILENAME = 'SamplingEngine_Results.log'
    logging.basicConfig(filename=LOGFILENAME,level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')
    logging.info('Tests Started - Device COM port %s', DUT_PORT)
    #--------------------------------------------------------------------------------------------------------------------------------

    #Configure the time interval between tests and the maximum amount of tests to run-
    TEST_WAIT_PERIOD_SECONDS = mySamplingTest.CheckInterval()
    MAX_TEST = mySamplingTest.CheckMaxTests()
    #---------------------------------------------------------------------------------

    #Open the serial ports----------
    myConnector.openSerialPortCON()
    myConnector.openSerialPortDUT()
    #-------------------------------

    #Continously run through tests until max number of tests have been reached-----------------------------
    for testCounter in range(1, MAX_TEST+1):
        print ("Test Number :",testCounter)
        MESSAGE_PING = '2,' + str(fAMP) + ',' + str(FREQ) + '\r'

        #Wait for DUT and then trigger the controller------------------------------------------------- 
        #It send 2 lines of data, one for each channel---
        #Only runs on first iteration
        #time.sleep(1)
        if TestBegin == True:
            received_data = myConnector.ReadSerialPortLineDUT()
            received_data = myConnector.ReadSerialPortLineDUT() #run twice for both incoming lines
            print ("The DUT is Ready")
            myConnector.SendSerialCON(MESSAGE_PING)
            myConnector.ReadSerialPortLineCON()            #Check that the command ran
            TestBegin = False
        #time.sleep(1)
        #--------------------------------------------------------------------------------------------

        EngineResults = [False,False]
        EngineResults = mySamplingTest.RunTest()
        #print "Sampling Engine Results = " + str(EngineResults)
        Channel1result = EngineResults[0]
        Channel2result = EngineResults[1]
        if Channel1result == True :
            PassCounterChannel1 += 1
            SuccessStatChannel1 = 100.0 * PassCounterChannel1 / testCounter
            print ("Expected response received. Channel 1 Test Passed: ", SuccessStatChannel1)
            logging.info('Test %d,Passed,%d', testCounter, SuccessStatChannel1)
        else:
            SuccessStatChannel1 = 100.0 * PassCounterChannel1 / testCounter
            print("Expected response Not received. Channel 1 Test Failed: ", SuccessStatChannel1)
            logging.info('Test %d, Failed,%d', testCounter, SuccessStatChannel1)
        if Channel2result == True :
            PassCounterChannel2 += 1
            SuccessStatChannel2 = 100.0 * PassCounterChannel2 / testCounter
            print ("Expected response received. Channel 2 Test Passed: ", SuccessStatChannel2)
            logging.info('Test %d,Passed,%d', testCounter, SuccessStatChannel2)
        else:
            SuccessStatChannel2 = 100.0 * PassCounterChannel2 / testCounter
            print("Expected response Not received. Channel 2 Test Failed: ", SuccessStatChannel2)
            logging.info('Test %d, Failed,%d', testCounter, SuccessStatChannel2)
        
        time.sleep(TEST_WAIT_PERIOD_SECONDS)
    #--------------------------------------------------------------------------------------------------------    
    
    #Close Serial Ports and end-------
    myConnector.CloseSerialPortCON()
    myConnector.CloseSerialPortDUT()
    logging.info('Finished')
    #--------------------------------

## Documentation for a function.
#
# The main function parses the arguments input by the user, creates a modem object, opens the serial port, opens the TCP port
# and then runs the modem test. The results are posted to OpenHAB and recorded in a log file
def main():

    #Setup global variables for the whole script
    global DUT_PORT         #COM Port for the DUT board     
    global DUT_BAUD         #Baudrate for the DUT board
    global uC_PORT          #Com Port for the Controller board
    global uC_BAUD          #Baudrate for the controller board
    global fAMP             #peak Amplitude of the Sine wave in terms of controller DAC output
    global fVrefCON         #Reference voltage for the DAC on the controller = 3.5
    global BitRes           #Bit resolution of the DUT ADC in mV = 0.59
    global FREQ             #Frequency of the input wave in Hz
    global myInputs         #Name for instance of InputParse object
    global myConnector      #Name for instance of SerialConnecter object
    global mySamplingTest   #Name for instance of SamplingTest object
    global MESSAGE_PING     #String Command to be sent to the controller

    #Temp variables

    #Create the needed class instances
    myInputs = InputParse()
    myConnector = SerialConnecter()
    mySamplingTest = SamplingTest()

    #Initialize variables from input parameters
    [DUT_PORT, DUT_BAUD, uC_PORT, uC_BAUD, fAMP, FREQ] = myInputs.GetInput()

    print ("\nDUT Sampling Engine Test")
    print 'DUT'+' Serial Port '+str(DUT_PORT)
    print 'Controller'+' Serial Port '+str(uC_PORT)
    print "Sampling Engine Test version: V" + str(MAJOR) + '.' + str(MINOR)
    
    LoopAndLog()
    #Debug and Trace Section-------------
    #------------------------------------


    print "All Tests completed!"

if __name__ == "__main__":
    main()
