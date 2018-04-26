## @package pulseCount_Test
# Author:  Turyn Lim Banda
#
# Date: 23 April 2018
#
# Edited by: 
#
# Date Last Modified: 26 April 2018
#
# Latest change: Framework set, Fleshing out Functions and working on Calculations
#
# Purpose: A script to validate a devices ability to accurately sample and measure a sine wave input
#
# Version : V0.2
#
#  More details.
#
#  This script sends commands to a controller board that generates a sinusoidal waveform at X amplitude and Y frequency.
#  That device then samples the waveform and returns 3 values, the average ADC count, the minimum, the maximum. 
#  The script then checks whether the returned values are accurate according to the input waveform.
#  This test runs continously through a specified amount of iterations.

import argparse
from argparse import RawTextHelpFormatter
import serial
import logging
import time
from enum import Enum

MAJOR = 0
MINOR = 2

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
        print "InputParse Initialised"

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
        parser.add_argument("Amplitude", type=str, help=        "Amplitude of sinewave from 0-0.5 e.g. '0.5'")
        parser.add_argument("Frequency", type=str, help=        "Frequency of the Sine wave e.g. '50'")
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
        print "SerialConnecter Initialised"

    ## Documentation for openSerialPortCON method.
    #  @param self The object pointer.
    def openSerialPortCON(self):
        self.ser1 = serial.Serial(uC_PORT, uC_BAUD, timeout=10)
        print "Controller Serial Port: Open" 

    ## Documentation for openSerialPortDUT method.
    #  @param self The object pointer.
    def openSerialPortDUT(self):
        self.ser2 = serial.Serial(DUT_PORT, DUT_BAUD, timeout=21)
        print "DUT Serial Port: Open" 

    ## Documentation for SendSerialCON method.
    #  @param self The object pointer.
    def SendSerialCON(self,command, getline=False):
        print "Controller Serial Port Tx: ", command
        self.ser1.write(command)
        data = ''
        if getline:
            data=self.ReadLine()
        return data

    ## Documentation for SendSerialDUT method.
    #  @param self The object pointer.
    def SendSerialDUT(self,command, getline=False):
        print "DUT Serial Port Tx: ", command
        self.ser2.write(command)
        data = ''
        if getline:
            data=self.ReadLine()
        return data    

    ## Documentation for ReadSerialPortLineCON method.
    #  @param self The object pointer.
    def ReadSerialPortLineCON(self):
        data = self.ser1.readline()
        print "Controller Serial Port Rx: ", data
        return data

    ## Documentation for ReadSerialPortLineDUT method.
    #  @param self The object pointer.
    def ReadSerialPortLineDUT(self):
        data = self.ser2.readline()
        print "DUT Serial Port Rx: ", data
        return data    

    ## Documentation for CloseSerialPortCON method.
    #  @param self The object pointer.
    def CloseSerialPortCON(self):
        self.ser1.close()
        print "Controller Serial Port: Closed"

    ## Documentation for CloseSerialPortDUT method.
    #  @param self The object pointer.
    def CloseSerialPortDUT(self):
        self.ser2.close()
        print "DUT Serial Port: Closed"

## Documentation for the SamplingTest class.
#
#  This class defines the methods used to provide modem functionality
class SamplingTest(object):

    ## The constructor.
    def __init__(self):
        print "SamplingTest Initialised"

    ## Documentation for RunTest method.
    #
    # This method perfoms the Sampling Engine test.
    # It opens a serial port to the controller, sends a command to generate a sine wave, verifies the command ran
    # It then opens a serial port to the DUT and reads the returned values.
    # The returned values are then evaluated against expected results.
    # if the values returned are as expected then the test is a success, if any values fall outside of tolerance then the test is a fail 
    #  @param self The object pointer.
    def RunTest(self):

        #Local Variables
        fVoltMean   = 0.0     #Represent the mean woltage of the input wave in mV
        fVoltPkMax  = 0.0     #Represent the maximum peak woltage of the input wave in mV
        fVoltPkMin  = 0.0     #Represent the maximum peak woltage of the input wave in mV
        iADCpeakMax = 0       #Expected Maximum peak Value for ADC 
        iADCpeakMin = 0       #Expected Maximum peak Value for ADC
        iSampleDAC  = 1       #Samples used in DAC
        iMaxSamples = 100     #Number of samples used by DAC
        fDacVal = 0.0         #DAC Voltage
        

        #Wait for DUT
        time.sleep(1)
        received_data = myConnector.ReadSerialPortLineDUT()
        print "DUT OK"
        #time.sleep(1)
        
        #Send the command to the controller and check that the command ran
        #time.sleep(10)
        myConnector.SendSerialCON(MESSAGE_PING)
        #time.sleep(2)
        myConnector.ReadSerialPortLineCON()

        #Take an actual reading from the DUT Serial port 
        #Read DUT data
        print "Wait for DUT result"
        received_data = myConnector.ReadSerialPortLineDUT()
        Header1,ADC_Channel1,ADC_Average1,ADC_Min1,ADC_Max1=received_data.split(",")
        ADC_Max1 = ADC_Max1.rstrip()
        #time.sleep(1)
        received_data = myConnector.ReadSerialPortLineDUT()
        Header2,ADC_Channel2,ADC_Average2,ADC_Min2,ADC_Max2=received_data.split(",")
        ADC_Max2 = ADC_Max2.rstrip()
        #Debug Trace---------------------------------------------
        #print "ADC Channel = " + str(ADC_Channel)
        #print "ADC Average Count = " + str(ADC_Average)
        #print "ADC Minimum Count = " + str(ADC_Min)
        #print "ADC Maximum Count = " + str(ADC_Max)
        #-------------------------------------------------------

        #Convert input fAmp to Comparable ADC Values
        #Expected Mean ADC Value
        #Calculate the average voltage from the DAC

        #for iSampleDAC in range(1, iMaxSamples):
        #    fDacVal = fAMP*
        #    print "Test Number :",testCounter
        #    MESSAGE_PING = '1,' + str(AMP) + ',' + str(FREQ) + '\r'

        #    EngineResults = [False,False]
        #    EngineResults = SamplingTest.RunTest()
        #    print "pulseResults = " + str(EngineResults)
        #    Channel1result = EngineResults[0]
        #    Channel2result = EngineResults[1]
        #    if Channel1result == True :
        #        PassCounterChannel1 += 1
        #        SuccessStatChannel1 = 100.0 * PassCounterChannel1 / testCounter
        #        print "Expected response received. P1 Test Passed: ", SuccessStatChannel1
        #        logging.info('Test %d,Passed,%d', testCounter, SuccessStatChannel1)
        #    else:
        #        SuccessStatChannel1 = 100.0 * PassCounterChannel1 / testCounter
        #        print"Expected response Not received. P1 Test Failed: ", SuccessStatChannel1
        #        logging.info('Test %d, Failed,%d', testCounter, SuccessStatChannel1)
        #    if Channel2result == True :
        #        PassCounterChannel2 += 1
        #        SuccessStatChannel2 = 100.0 * PassCounterChannel2 / testCounter
        #        print "Expected response received. P2 Test Passed: ", SuccessStatChannel2
        #        logging.info('Test %d,Passed,%d', testCounter, SuccessStatChannel2)
        #    else:
        #        SuccessStatChannel2 = 100.0 * PassCounterChannel2 / testCounter
        #        print"Expected response Not received. P2 Test Failed: ", SuccessStatChannel2
        #        logging.info('Test %d, Failed,%d', testCounter, SuccessStatChannel2)
        
        #    time.sleep(TEST_WAIT_PERIOD_SECONDS)

        fVoltMean = 1500                                #Quotient of the sum of DAC samples and the number of samples
        iADCMean  = 1500/BitRes                         #

        #Expected Maximum ADC Value
        fVoltPkMax = (fAMP*fVrefCON)+(0.43*fVrefCON)    #0.43 is the offset for the sine wave to a midpoint of 1.5V
        fVoltPkMax = fVoltPeak*1000                     #convert to mV
        iADCPkMax  = fVoltPk/BitRes                     #Convert to an actual ADC Value

        #Expected Minimum ADC Value
        iADCPkMin  = 





        #Evaluate the values from readings against the expected values

        #Channel 1

        #Check ADC Average

        #Check pass/fail for all 6 parameters

        #Check Pulse counter 1 Pass/Fail
        if PulseCounter1_Val == NUM_PULSES:
            passP1 = True
        else:
            passP1 = False

        #Check Pulse counter 2 Pass/Fail
        if PulseCounter2_Val == NUM_PULSES:
            passP2 = True
        else:
            passP2 = False

        #Check Pulse counter 3 Pass/Fail
        if PulseCounter3_Val == NUM_PULSES:
            passP3 = True
        else:
            passP3 = False

        pulseCounterResults = [passP1,passP2,passP3]
        #print pulseCounterResults

        return pulseCounterResults

        #Return the results


        myConnector.CloseSerialPortCON()
        myConnector.CloseSerialPortDUT()

        bPingTest = False
        if received_data == MESSAGE_PING:
            bPingTest = True
        else:
            print "Serial Port: Failed to Read"

        myModem.SendSerial(MESSAGE_PONG, False)
        time.sleep(1)
        data = myModem.ReadTcpPorttLine()

        bPongTest = False
        if data == MESSAGE_PONG:
            bPongTest = True

        if bPingTest == True and bPongTest == True:
            return True
        else:
            return False

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

    testCounter = 1
    PassCounter = [0,0]
    SuccessStat = [0,0]
    PassCounterChannel1 = 0
    PassCounterChannel2 = 0
    SuccessStatChannel1 = 0
    SuccessStatChannel2 = 0

    LOGFILENAME = 'SamplingEngine_Results.log'
    logging.basicConfig(filename=LOGFILENAME,level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')
    logging.info('Tests Started - Device COM port %s', DUT_PORT)

    TEST_WAIT_PERIOD_SECONDS = SamplingTest.CheckInterval()
    MAX_TEST = SamplingTest.CheckMaxTests()

    myConnector.openSerialPortCON()
    myConnector.openSerialPortDUT()

    for testCounter in range(1, MAX_TEST+1):
        print "Test Number :",testCounter
        MESSAGE_PING = '1,' + str(AMP) + ',' + str(FREQ) + '\r'

        EngineResults = [False,False]
        EngineResults = SamplingTest.RunTest()
        print "pulseResults = " + str(EngineResults)
        Channel1result = EngineResults[0]
        Channel2result = EngineResults[1]
        if Channel1result == True :
            PassCounterChannel1 += 1
            SuccessStatChannel1 = 100.0 * PassCounterChannel1 / testCounter
            print "Expected response received. P1 Test Passed: ", SuccessStatChannel1
            logging.info('Test %d,Passed,%d', testCounter, SuccessStatChannel1)
        else:
            SuccessStatChannel1 = 100.0 * PassCounterChannel1 / testCounter
            print"Expected response Not received. P1 Test Failed: ", SuccessStatChannel1
            logging.info('Test %d, Failed,%d', testCounter, SuccessStatChannel1)
        if Channel2result == True :
            PassCounterChannel2 += 1
            SuccessStatChannel2 = 100.0 * PassCounterChannel2 / testCounter
            print "Expected response received. P2 Test Passed: ", SuccessStatChannel2
            logging.info('Test %d,Passed,%d', testCounter, SuccessStatChannel2)
        else:
            SuccessStatChannel2 = 100.0 * PassCounterChannel2 / testCounter
            print"Expected response Not received. P2 Test Failed: ", SuccessStatChannel2
            logging.info('Test %d, Failed,%d', testCounter, SuccessStatChannel2)
        
        time.sleep(TEST_WAIT_PERIOD_SECONDS)
        
    #Close Serial Ports
    myConnector.CloseSerialPortCON()
    myConnector.CloseSerialPortDUT()
    logging.info('Finished')

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
    global fAMP             #peak Amplitude of the Sine wave 
    global fVrefCON = 3.5   #Reference voltage for the DAC on the controller
    global BitRes = 0.59    #Bit resolution of the DUT ADC in mV
    global FREQ             #Frequency of the input wave in Hz
    #global NUM_PULSES
    global myInputs         #Name for instance of InputParse object
    global myConnector      #Name for instance of SerialConnecter object
    global mySamplingTest   #Name for instance of SamplingTest object
    global MESSAGE_PING     #String Command to be sent to the controller


    #Create the needed class instances
    myInputs = InputParse()
    myConnector = SerialConnecter()
    mySamplingTest = SamplingTest()

    #Initialize variables from input parameters
    [DUT_PORT, DUT_BAUD, uC_PORT, uC_BAUD, fAMP, FREQ] = myInputs.GetInput()

    print "\nDUT Sampling Engine Test"
    print 'DUT'+' Serial Port '+str(DUT_PORT)
    print 'Controller'+' Serial Port '+str(uC_PORT)
    print "Sampling Engine Test version: V" + str(MAJOR) + '.' + str(MINOR)
    
    #LoopAndLog()
    #Debug and Trace Section-------------
    myConnector.openSerialPortDUT()

    #------------------------------------


    print "All Tests completed!"

if __name__ == "__main__":
    main()
