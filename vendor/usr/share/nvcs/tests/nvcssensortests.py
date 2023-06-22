# Copyright (c) 2012-2020 NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#

from __future__ import division
from __future__ import print_function

import stat
from nvcstestcore import *
import nvcstestutils
import nvcstestsystem
import random

def isRangeCorrect(numExposures, index, Range):
    #
    # Range values have the following format
    #        0             1          2         numExpsures-1
    #  0   min (0,0)    min (0,1)   min (0,2)   min (0, numExposures-1)
    #  1   max (1,0)    max (1,1)   max (1,2)   max (1, numExposures-1)
    #
    # index is -1 if all exposures in range 0 to numExposures need to be checked
    # index is > 0 if only the specific index needs to be checked
    #
    # we do not check Range[0][index] for 0, as the value could be 0 for ET
    # short exposures
    #
    # max should be more than or equal to min, while comparing.
    # Exposure time could be in nanoseconds. We multiply by 10 power 9 to get a larger
    # number while comparing. numpy library is the best for comparing floats, but
    # installation/licensing becomes an issue
    #
    # if (long(Range[0][index] * float(1000 * 1000 * 1000)) == long(Range[1][index] * float(1000 * 1000 * 1000))):
    #    print "###### Comparison returns equal %10.10f  %10.10f" % (Range[0][index] * 1000 * 1000 * 1000, Range[1][index] * 1000 * 1000 * 1000)
    #else:
    #    print "##### Comparison returns non-equal %10.15f  %10.15f" % (Range[0][index] * 1000 * 1000 * 1000, Range[1][index] * 1000 * 1000 * 1000)

    if (index == -1):
        for i in range(num):
            if (int(Range[0][i]) == -1 or int(Range[1][i]) == -1 or \
                int(Range[0][i] * float(1000000000)) > int(Range[1][i] * float(1000000000))):
                return NvCSTestResult.ERROR
            elif (int(Range[0][i] * float(1000000000)) == int(Range[1][i] * float(1000000000))):
                return NvCSTestResult.SKIPPED
    else:
        if (int(Range[0][index]) == -1 or int(Range[1][index]) == -1 or \
               int(Range[0][index] * float(1000000000)) > int(Range[1][index] * float(1000000000))):
            return NvCSTestResult.ERROR
        elif (int(Range[0][index] * float(1000000000)) == int(Range[1][index] * float(1000000000))):
            return NvCSTestResult.SKIPPED
    return NvCSTestResult.SUCCESS

def isSensorInList(sensorList, sensorName):
    for sensor in sensorList:
        if (sensorName.lower().find(sensor.lower()) is not -1):
            return True
    return False

class bcolors(object):
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class NvCSGainTest(NvCSTestBase):
    "Gain test"

    startGainVal = 0.0
    stopGainVal = 0.0
    step = 0.0
    errPercent = 10.0
    iterations = 11

    def __init__(self, options, logger, sensorSetting):
        NvCSTestBase.__init__(self, options, logger, "Gain", sensorSetting)
        self.options = options
        self.sensorSetting = sensorSetting

    def setupGraph(self):
        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.sensorSetting.imager_id, self.sensorSetting.imager_name)
        self.obGraph.setGraphType(GraphType.RAW)

        return NvCSTestResult.SUCCESS

    def runTest(self, args):
        self.failIfAohdrEnabled()

        # get the gain range
        self.obCamera.startPreview()

        gainRange = self.obCamera.getAttr(nvcamera.attr_gainrange)
        exposureTimeRange = self.obCamera.getAttr(nvcamera.attr_exposuretimerange)

        bMultiExpos = nvcstestsystem.isMultipleExposuresSupported()

        (ret, numExposures, numGains, \
            supportedMode, currentMode, bHdrChangeable) = self.obGraph.getHDRInfo()

        #
        # Check if the command line options are specified correctly
        # Get the index of the exposure that we need to use.
        #
        index, exposureMode = nvcstestsystem.getSingleExposureIndex(numExposures, False, self.options, self.logger)
        if (index == -1):
            self.logger.error("getSingleExposureIndex: Command line options error")
            return NvCSTestResult.ERROR

        if (bMultiExpos):
            self.logger.info("Number of exposures %d Number of gains %d index used %d " % (numExposures, numGains, index))
            self.logger.info("Index     ETMin         ETMax         GainMin  GainMax")
            for i in range(0, numExposures, 1):
                self.logger.info("  %d   %2.10f   %2.10f      %2.2f     %2.2f " % \
                                (i, exposureTimeRange[0][i], exposureTimeRange[1][i], \
                                 gainRange[0][i], gainRange[1][i]))

            for i in range(0, numExposures, 1):
                if (gainRange[1][i] > 16):
                    self.logger.warning("Max Sensor Gain Higher than 16 [%d] for exposure %d" % \
                                        (gainRange[1][i], i))

        elif (bMultiExpos == False and gainRange[1] > 16):
            self.logger.warning("Max Sensor Gain Higher than 16 [%d]" % (gainRange[1]))

        capExposure = None
        if (bMultiExpos):
            self.logger.info("Gain test: camera queried gain range (%2.2f, %2.2f)" % \
                            (gainRange[0][index], gainRange[1][index]))

            rangeValidity = isRangeCorrect(numExposures, index, gainRange)
            if rangeValidity == NvCSTestResult.SKIPPED:
                self.logger.warning("gain range min [{0}] == gain range max [{1}];"
                    "please check your driver and make sure this is correct behavior.".format(gainRange[0][index], gainRange[1][index]))
            elif rangeValidity == NvCSTestResult.ERROR:
                self.logger.error("Invalid Gain range returned by the driver")
                return NvCSTestResult.ERROR

            self.startGainVal = gainRange[0][index]
            self.stopGainVal = gainRange[1][index]
            capExposure = exposureTimeRange[1][index]
        else:
            self.logger.info("Gain test: camera queried gain range (%2.2f, %2.2f)" % \
                            (gainRange[0], gainRange[1]))

            if(gainRange[0] < 0 or gainRange[1] < 0):
                self.logger.error("gain range is invalid")
                return NvCSTestResult.ERROR
            if (gainRange[0] == gainRange[1]):
                self.logger.warning("gain range min [{0}] == gain range max [{1}];"
                    "please check your driver and make sure this is correct behavior.".format(gainRange[0], gainRange[1]))

            self.startGainVal = gainRange[0]
            self.stopGainVal = gainRange[1]
            capExposure = exposureTimeRange[1]

        if (self.stopGainVal < self.startGainVal):
            self.logger.error("invalid gain range from returned from sensor driver: max[{0}] < min[{1}]".format(index, self.stopGainVal, self.startGainVal))
            return ConformanceTestResult.ERROR

        if(self.options.numTimes > 1):
            self.iterations = self.options.numTimes
        elif(self.options.numTimes == 1):
            self.logger.warning("User entered invalid number of samples (1)."
                        "  Using default (%d)" % self.iterations)

        self.step = (self.stopGainVal - self.startGainVal) if (self.iterations == 1.0) else \
            (self.stopGainVal - self.startGainVal)/(self.iterations - 1.0)

        if self.step == 0.0:
            self.step = 1.0
            self.iterations = 1

        self.logger.info("Gain test: start %2.2f end %2.2f step %2.2f iterations %d " % \
                        (self.startGainVal, self.stopGainVal, self.step, self.iterations))

         # in case of special sensor; the gain can only be alternated when exposure is set to cap value

        if self.options.cappedExposure:
            if (bMultiExpos):
                exp_time_list = [-1 for i in range(0, nvcamera.HDR_MAX_EXPOSURES, 1)]
                exp_time_list[index] = capExposure
                self.obCamera.setAttr(nvcamera.attr_exposuretime, exp_time_list)
            else:
                self.obCamera.setAttr(nvcamera.attr_exposuretime, capExposure)

        while(self.startGainVal <= self.stopGainVal):
            if (bMultiExpos):
                gain_list = [-1 for i in range(0, nvcamera.HDR_MAX_EXPOSURES, 1)]
                gain_list[index] = self.startGainVal
                self.obCamera.setAttr(nvcamera.attr_bayergains, gain_list)
            else:
                self.obCamera.setAttr(nvcamera.attr_bayergains, self.startGainVal)

            # Construct filename
            fileName = "%s_test_e%d_%2.6f" % (self.testID, index, self.startGainVal)
            rawFilePath = os.path.join(self.testDir, fileName + ".nvraw")
            self.logger.info("capturing raw image with gains set to %2.2f..." % self.startGainVal)

            # capture raw image
            try:
                self.obCamera.captureRAWImage(rawFilePath, False)
            except nvcamera.NvCameraException as err:
                if (err.value == nvcamera.NvError_NotSupported):
                    self.logger.info("raw capture is not supported")
                    return NvCSTestResult.SKIPPED
                else:
                    raise

            if not self.nvrf.readFile(rawFilePath):
                self.logger.error("couldn't open the file: %s" % rawFilePath)
                return NvCSTestResult.ERROR

            #
            # As we support single gain for this test, we can assume that the exposure time is
            # always present in th Capture chunk. We do not use HDR chunk in this case.
            #
            if (abs(self.nvrf.getSensorGain() -  self.startGainVal) \
                    > ((self.errPercent * self.startGainVal) / 100.0)):
                self.logger.error("SensorGains value of %2.4f is not correct in the raw header " \
                        "Diff should be less than %2.4f percent. Applied value was %2.4f" \
                        % (self.nvrf.getSensorGain(), self.errPercent, self.startGainVal))
                return NvCSTestResult.ERROR

            self.startGainVal = self.startGainVal + self.step

            # Check no values over 2**dynamicPixelBitDepth
            if (self.nvrf.getMaxPixelValue() > self.nvrf.getPeakPixelValue()):
                self.logger.error("pixel value is over %d." % self.nvrf.getPeakPixelValue())
                return NvCSTestResult.ERROR

        self.obCamera.stopPreview()

        return NvCSTestResult.SUCCESS

class NvCSExposureTimeTest(NvCSTestBase):
    "Exposure Time Test"

    errPercent = 10.0
    iterations = 5

    def __init__(self, options, logger, sensorSetting):
        NvCSTestBase.__init__(self, options, logger, "Exposure_Time", sensorSetting)
        self.options = options

    def setupGraph(self):
        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.sensorSetting.imager_id, self.sensorSetting.imager_name)
        self.obGraph.setGraphType(GraphType.RAW)

        return NvCSTestResult.SUCCESS

    def runTest(self, args):
        self.failIfAohdrEnabled()
        if (args != None):
            self.exposureTimeValues = args

        bMultiExpos = nvcstestsystem.isMultipleExposuresSupported()

        #
        # Get HDR info.
        #
        (ret, numExposures, numGains, \
            supportedMode, currentMode, bHdrChangeable) = self.obGraph.getHDRInfo()

        if (ret != NvCSTestResult.SUCCESS):
            self.logger.error("Error: getHDRInfo() returned error")
            return NvCSTestResult.ERROR
        #
        # Check if the command line options are specified correctly
        # Get the index of the exposure that we need to use.
        #
        index, exposureMode = nvcstestsystem.getSingleExposureIndex(numExposures, False, self.options, self.logger)
        if (index == -1):
            self.logger.error("getSingleExposureIndex: Command line options error")
            return NvCSTestResult.ERROR

        # query and print exposuretime range
        # we need to start preview to get correct exposure time range
        self.obCamera.startPreview()
        exposureTimeRange = self.obCamera.getAttr(nvcamera.attr_exposuretimerange)
        gainRange = self.obCamera.getAttr(nvcamera.attr_gainrange)

        if (bMultiExpos):
            self.logger.info("Number of exposures %d Number of gains %d index used %d " % (numExposures, numGains, index))
            self.logger.info("Index     ETMin         ETMax         GainMin  GainMax")
            for i in range(0, numExposures, 1):
                self.logger.info("  %d   %2.10f   %2.10f      %2.2f     %2.2f " % \
                                (i, exposureTimeRange[0][i], exposureTimeRange[1][i], \
                                 gainRange[0][i], gainRange[1][i]))

            rangeValidity = isRangeCorrect(numExposures, index, exposureTimeRange)
            if rangeValidity == NvCSTestResult.SKIPPED:
                self.logger.warning("Exposure Time range min [{0}] == Exposure Time range max [{1}];"
                    "please check your driver and make sure this is correct behavior."\
                    .format(exposureTimeRange[0][index], exposureTimeRange[1][index]))
            elif rangeValidity == NvCSTestResult.ERROR:
                self.logger.info("Camera queried Exposure Time range (%2.10f, %2.10f)" % \
                    (exposureTimeRange[0][index], exposureTimeRange[1][index]))
                self.logger.error("Invalid Exposure time range returned by the driver")
                return NvCSTestResult.ERROR
        else:
            self.logger.info("exposuretime range: [%2.9f sec, %2.9f sec]" %  \
                            (exposureTimeRange[0], (exposureTimeRange[1])))
            if(exposureTimeRange[0] <= 0 or exposureTimeRange[1] <= 0):
                self.logger.error("exposuretime range is invalid")
                return NvCSTestResult.ERROR
            if (exposureTimeRange[0] == exposureTimeRange[1]):
                self.logger.warning("Exposure Time range min [{0}] == Exposure Time range max [{1}];"
                "please check your driver and make sure this is correct behavior."\
                .format(exposureTimeRange[0][index], exposureTimeRange[1][index]))

        retVal = NvCSTestResult.SUCCESS

        if (bMultiExpos):
            startExpTimeValue = exposureTimeRange[0][index]
            stopExpTimeValue = exposureTimeRange[1][index]
        else:
            startExpTimeValue = exposureTimeRange[0]
            stopExpTimeValue = exposureTimeRange[1]

        if (stopExpTimeValue < startExpTimeValue):
            self.logger.error("invalid exposure time range from returned from sensor driver: max[{0}] < min[{1}]".format(index, self.stopExpTimeValue, self.startExpTimeValue))
            return ConformanceTestResult.ERROR

        if(self.options.numTimes > 1):
            self.iterations = self.options.numTimes
        elif(self.options.numTimes == 1):
            self.logger.warning("User entered invalid number of samples (1).  "
                                "Using default (%d)" % self.iterations)

        step = (stopExpTimeValue - startExpTimeValue) if (self.iterations == 1.0) else \
            (stopExpTimeValue - startExpTimeValue)/(self.iterations - 1.0)

        if step == 0.0:
            step = 1.0
            self.iterations = 1

        while startExpTimeValue <= stopExpTimeValue:
            # take an image specified exposure time
            self.logger.info("capturing raw image with exposure time set to %fs..." % \
                            startExpTimeValue)


            if (bMultiExpos):
                exp_time_list = [-1 for i in range(0, nvcamera.HDR_MAX_EXPOSURES, 1)]
                exp_time_list[index] = startExpTimeValue
                self.obCamera.setAttr(nvcamera.attr_exposuretime, exp_time_list)
            else:
                self.obCamera.setAttr(nvcamera.attr_exposuretime, startExpTimeValue)

            fileName = "%s_test_e%d_%2.6f" % (self.testID, index, startExpTimeValue)
            rawFilePath = os.path.join(self.testDir, fileName + ".nvraw")

            # capture raw image
            try:
                self.obCamera.captureRAWImage(rawFilePath, False)
            except nvcamera.NvCameraException as err:
                if (err.value == nvcamera.NvError_NotSupported):
                    self.logger.info("raw capture is not supported")
                    return NvCSTestResult.SKIPPED
                else:
                    raise

            if not self.nvrf.readFile(rawFilePath):
                self.logger.error("couldn't open the file: %s" % rawFilePath)
                retVal = NvCSTestResult.ERROR
                break

            # Check no values over 2**dynamicPixelBitDepth
            if (self.nvrf.getMaxPixelValue() > self.nvrf.getPeakPixelValue()):
                self.logger.error("pixel value is over %d." % self.nvrf.getPeakPixelValue())
                retVal = NvCSTestResult.ERROR
                break

            #
            # As we support single exposure for this test, we can assume that the exposure time is
            # always present in th Capture chunk. We do not use HDR chunk in this case.
            #
            exposureTimeFromFile = self.nvrf.getExposureTime()

            minExpectedExpTime = startExpTimeValue - ((startExpTimeValue * self.errPercent) / 100.0)
            maxExpectedExpTime = startExpTimeValue + ((startExpTimeValue * self.errPercent) / 100.0)

            # check SensorExposure value
            if (exposureTimeFromFile < minExpectedExpTime or
                exposureTimeFromFile > maxExpectedExpTime):
                self.logger.error( "exposuretime is not correct in the raw header: %.6f" %
                                    exposureTimeFromFile)
                self.logger.error( "exposuretime should be between %.6f and %.6f" %
                                    (minExpectedExpTime, maxExpectedExpTime))
                retVal = NvCSTestResult.ERROR
                break

            expTime = self.obCamera.getAttr(nvcamera.attr_exposuretime)
            if (bMultiExpos and (expTime[index] < minExpectedExpTime or expTime[index] > maxExpectedExpTime)):
                self.logger.error("exposuretime is not set in the driver...")
                self.logger.error( "exposure value %.6f should be between %.6f and %.6f" %
                                    (expTime[0], minExpectedExpTime, maxExpectedExpTime))
                retVal = NvCSTestResult.ERROR
                break
            elif (bMultiExpos == False and (expTime < minExpectedExpTime or expTime > maxExpectedExpTime)):
                self.logger.error("exposuretime is not set in the driver...")
                self.logger.error( "exposure value %.6f should be between %.6f and %.6f" %
                                    (expTime, minExpectedExpTime, maxExpectedExpTime))
                retVal = NvCSTestResult.ERROR
                break

            startExpTimeValue = startExpTimeValue + step

        self.obCamera.stopPreview()

        return retVal

class NvCSLinearityRawTest(NvCSTestBase):
    "Linearity Raw Image Test"

    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    # Environment Check results
    GainStartVal = 0.0
    GainStopVal = 0.0
    GainExpo = 0.0
    GainStep = 0.0
    ExpTimeStart = 0.0
    ExpTimeStop = 0.0
    ExpTimeGain = 0.0
    ExpTimeStep = 0.0

    # Environment Check constants
    TestSensorGainRange = 1.00             # 100%
    ValidETRangePercentageThreshold = 0.50 # 50%
    ETPrecisionThreshold = 0.004           # 4ms

    qMaxExpTime = 0.0
    qMinExpTime = 0.0
    qMaxGain = 0.0
    qMinGain = 0.0
    qMaxPixelValue = 0

    defFocusPos = 450
    qMinFocusPos = 0
    qMaxFocusPos = 0
    NumImages = 6.0
    noShuffle = False
    TestSensorRangeMax = 0.95
    BayerPhaseConfirmed = True
    MaxPixelVal = 0
    maxGainInDb = 0.0
    minGainInDb = 0.0
    gainStepsInDb = 0
    gainGranularityInDb = 0.3
    manualGainStep = None
    maxPixelValue = 0.0
    LinearityEnum = {'EXPOSURE':0, 'GAIN':1, 'EP':2, 'numLinearityEnum':3, 'ALL':4 }
    ReverseLinearityEnum =  {LinearityEnum['EXPOSURE']:'EXPOSURE', LinearityEnum['GAIN']:'GAIN', LinearityEnum['EP']:'EP', LinearityEnum['numLinearityEnum']:'numLinearityEnum', LinearityEnum['ALL']:'ALL'}
    linearityOnOffLUT = None
    def __init__(self, options, logger, sensorSetting):
        NvCSTestBase.__init__(self, options, logger, "Linearity", sensorSetting)
        self.options = options
        self.sensorSetting = sensorSetting
        if self.options.gainGranularity is not None:
            self.gainGranularityInDb = self.options.gainGranularity
        self.linearityOnOffLUT = dict([('GAIN',True), ('EXPOSURE_TIME',True) , ('EP',True)])
    def needTestSetup(self):
        return True

    def getSetupString(self):
        return "\n\nThis test must be run with a controlled, uniformly lit scene.  Cover the sensor with the light source on its lowest setting.\n\n"

    def setupGraph(self):
        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.sensorSetting.imager_id, self.sensorSetting.imager_name)
        self.obGraph.setGraphType(GraphType.RAW)

        return NvCSTestResult.SUCCESS

    def getBlackLevel(self, expRangeList):
        import types
        longExpRange = []
        if type(expRangeList[0]) is list :
            longExpRange.append(expRangeList[0][0])
            longExpRange.append(expRangeList[1][0])
        else :
            longExpRange = expRangeList

        # Test BlackLevel using minimum settings reported
        # Also test a smaller exposure as the driver should be limiting the config
        BLList = []
        blackLevelExpList = []

        if (2 > len(longExpRange)) :
            print("nvcssensortests.py: len(longExpRange)[%d] is less than 2; cannot find the min/max ET range\n"%(len(longExpRange)));
            return NvCSTestResult.ERROR
        if (self.qMinExpTime < longExpRange[0]) :
            print("nvcssensortests.py: minExpTime [%f] is smaller than min. exp time from sensor[%f]\n"%(self.qMinExpTime, longExpRange[0]));
            return NvCSTestResult.ERROR

        # we will test with a lower exposure time if the 1/10 of the qMinExpTime is valid.
        # Otherwise, we will set to the median of range.
        if ((self.qMinExpTime * 0.1) >= longExpRange[0]) :
            blackLevelExpList.append(self.qMinExpTime * 0.1)
            blackLevelExpList.append(self.qMinExpTime)
        else :
            blackLevelExpList.append(longExpRange[0])
            blackLevelExpList.append((longExpRange[0] + longExpRange[1]) / 2)

        for blackLevelExp in blackLevelExpList :
            BLList.append(NvCSTestConfiguration(
                "BlackLevel", "BL_%.5f_%.2f" % (blackLevelExp, self.qMinGain),
                blackLevelExp, self.qMinGain))

        self.logger.info("\n\nThe test will now take captures for black levels.\n\n")
        if (NvCSTestResult.ERROR == NvCSTestConfiguration.runConfigList(self, BLList, False)):
            self.logger.error("nvcssensortests.py::NvCSLinearityRawTest::getBlackLevel: not able to capture image for black level.")
            return NvCSTestResult.ERROR

        self.MaxPixelVal = self.nvrf.getPeakPixelValue()

        # Setting initial black levels to be overwritten
        BlackLevel = [self.MaxPixelVal, self.MaxPixelVal, self.MaxPixelVal]

        for imageStat in BLList:
            # Leaving in a sanity check of the blacklevel configuration
            if (imageStat.testing == "BlackLevel"):
                if(BlackLevel[0] > imageStat.Avg["Color"][0]):
                    BlackLevel[0] = imageStat.Avg["Color"][0]
                if(BlackLevel[1] > imageStat.Avg["Color"][1]):
                    BlackLevel[1] = imageStat.Avg["Color"][1]
                if(BlackLevel[2] > imageStat.Avg["Color"][2]):
                    BlackLevel[2] = imageStat.Avg["Color"][2]
            else:
                self.logger.info("\nIT SHOULD NOT HAVE REACHED THIS CODE. IT RAN INTO NON BLACKLEVEL CONFIG\n")

        self.logger.info("\nPerceived Black Level:  R:%.1f, G:%.1f, B:%.1f\tMax Possible Pixel Value: %d\n" %
            (BlackLevel[0], BlackLevel[1], BlackLevel[2], self.MaxPixelVal))

        return BlackLevel

    def runLinearity(self, configList, testName, bias):
        MIN_RSQUARED_ERROR = self.options.rsquaredmin
        MIN_RSQUARED_ERROR_LOWER_BOUND = 0.5 # half of max of 1.0
        MIN_SLOPE = 10.0
        Linearity = True
        OverExposed = True
        UnderExposed = True
        logStr = ""
        rSquared = [0.0, 0.0, 0.0] # Correlation Coefficient
        a = [0.0, 0.0, 0.0] # Slope
        b = [0.0, 0.0, 0.0] # Y-intercept

        if(MIN_RSQUARED_ERROR < MIN_RSQUARED_ERROR_LOWER_BOUND):
            self.logger.error("Minimum squared error for R^2 is quite wrong.")
            return NvCSTestResult.ERROR

        if (NvCSTestResult.ERROR == NvCSTestConfiguration.runConfigList(self, configList, False)):
            self.logger.error("nvcssensortests.py::NvCSLinearityRawTest::runLinearity:not able to capture image linearity test.")
            return NvCSTestResult.ERROR

        # Assign Capture Order & Sort
        captureCounter = 1
        for imageStat in configList:
            imageStat.attr_order = captureCounter
            captureCounter += 1
        configList = sorted(configList, key=lambda entry: entry.attr_gain)
        configList = sorted(configList, key=lambda entry: entry.attr_expo)
        logStr, rSquared, a, b, OverExposed, UnderExposed, csvStr = NvCSTestConfiguration.processLinearityStats(testName, configList, bias)

        # Dump CSV String to File
        filePath = os.path.join(self.testDir, testName + ".csv")
        f = open(filePath, 'w')
        f.write(csvStr)
        f.close()

        # These two conditions should not be reached because of earlier environment check
        if (OverExposed):
            logStr += ("\n\nAt least one image is overexposed (at least one average pixel value is too high)\n")
            logStr += ("Please make sure you are using the light panel to keep a controlled uniform lighting\n")
            Linearity = False
        if (UnderExposed):
            logStr += ("\n\nAt least one image is underexposed (at least one average pixel value is too low)\n")
            logStr += ("Please make sure you are using the light panel to keep a controlled uniform lighting\n")
            Linearity = False

        for j in range(0, 3):
            if (rSquared[j] < MIN_RSQUARED_ERROR):
                Linearity = False
                logStr += ("\n\n%s FAILED, minimum R^2 value is %f, minimum slope value is %f\n" % (testName, MIN_RSQUARED_ERROR, MIN_SLOPE))
                logStr += ("The minimum R^2 (correlation coefficient) value has not been met. (%f vs %f)\n" % (rSquared[j], MIN_RSQUARED_ERROR))
            if (a[j] < MIN_SLOPE):
                Linearity = False
                logStr += ("%s FAILED, minimum R^2 value is %f, minimum slope value is %f\n" % (testName, MIN_RSQUARED_ERROR, MIN_SLOPE))
                logStr += ("The minimum slope value has not been met. (%f vs %f)\n" % (a[j], MIN_SLOPE))

        return Linearity, logStr

    def runSNR(self, configList, testName, bias=[0.0, 0.0, 0.0], allowedVariation = 3.16):
        # 3.16% coefficient of variation is equivalent to the old 30dB SNR figure.
        MIN_VARIATION_PERCENT = allowedVariation
        Linearity = True
        Variation = [float("inf"), float("inf"), float("inf")]
        MaxTracker = -1.0
        MinTracker = -1.0
        AvgTracker = -1.0
        logStr = ""
        csvStr = ""
        maxPixelVal = None

        maxPixelVal = self.nvrf.getPeakPixelValue()

        if (NvCSTestResult.ERROR == NvCSTestConfiguration.runConfigList(self, configList)):
            self.logger.error("nvcssensortests.py::NvCSLinearityRawTest::runSNR:not able to capture image for SNR.")
            return NvCSTestResult.ERROR
        # Assign Capture Order & Sort
        captureCounter = 1
        for imageState in configList:
            imageState.attr_order = captureCounter
            captureCounter += 1
        configList = sorted(configList, key=lambda entry: entry.attr_gain)
        configList = sorted(configList, key=lambda entry: entry.attr_expo)
        logStr, Variation, MaxTracker, MinTracker, AvgTracker, csvStr, bPixelValueLow = NvCSTestConfiguration.processVariationStats(testName, configList, "Color", maxPixelVal, bias)

        # Dump CSV String to File
        filePath = os.path.join(self.testDir, testName + ".csv")
        f = open(filePath, 'w')
        f.write(csvStr)
        f.close()

        for j in range(0, 3):
            if(Variation[j] > MIN_VARIATION_PERCENT):
                Linearity = False

        # If the pixel values are too low (less than 30% of max value), fail the test
        # in Embedded linux only
        if ( nvcsUtil.isEmbeddedOS() and \
            (bPixelValueLow == True)):
            Linearity = False

        return Linearity, logStr, bPixelValueLow

    def runEnvCheckForEPAndGainLinearity(self):
        # skip the environment test and linearity if min and max of sensor gain is the same
        if (self.qMinGain == self.qMaxGain):
            self.logger.warning ("minimum gain [{0}] == maximum gain[{1}]; please check the gain range of sensor driver\n"
            .format(self.qMinGain, self.qMaxGain))
            self.linearityOnOffLUT['GAIN'] = False
            self.linearityOnOffLUT['EP'] = False
            return NvCSTestResult.SKIPPED
        if (self.qMinGain > self.qMaxGain):
            self.logger.error ("minimum gain [{0}] > maximum gain[{1}]; please check the gain range of sensor driver\n"
            .format(self.qMinGain, self.qMaxGain))
            return NvCSTestResult.ERROR

        # Find maximum ET that doesn't overexpose
        # special sensors can only adjust the gain when exposure is capped.
        HighestValidETForGainLinearity = self.qMaxExpTime
        OverExposureThreshold = NvCSTestConfiguration.OverExposureThreshold

        if self.options.cappedExposure:
            self.logger.info("\n\nValid Exposure time for Gain linearity is: %2.6f sec\n\n" % HighestValidETForGainLinearity)

            # check for overexposure when using max ET and max gain
            config = NvCSTestConfiguration("TestHalfMaxExposure",
                "envCheck_%.5f_%.2f_test" % (self.qMaxExpTime, self.qMaxGain),
                self.qMaxExpTime, self.qMaxGain)
            NvCSTestConfiguration.runConfig(self, config, False)

            if (max(config.Avg["Color"][0], config.Avg["Color"][1], config.Avg["Color"][2]) >= self.maxPixelValue * OverExposureThreshold * 0.99):
                self.logger.info("Environment Check Failed: light source is too bright.")
                self.logger.info("Average Values: R %3.4f G %3.4f B %3.4f " % (config.Avg["Color"][0], config.Avg["Color"][1], config.Avg["Color"][2]))
                self.logger.info("maxPixelValue %3.4f OverExposureThreshold %3.4f " % (self.maxPixelValue, OverExposureThreshold))
                return NvCSTestResult.ERROR
        else:
            self.logger.info("\n\nENVIRONMENT CHECK: Finding valid exposuer time for gain linearity.\n\n")
            HighestValidETForGainLinearity = self.FindHighestValidET(self.qMinExpTime, self.qMaxExpTime,
                self.maxPixelValue * OverExposureThreshold * 0.99, self.qMaxGain)
            self.logger.info("\n\nValid Exposure time for Gain and EP linearity is: %2.6f sec\n\n" % HighestValidETForGainLinearity)

        # Save the relevant data
        self.GainStartVal = self.qMinGain
        self.GainStopVal = self.qMaxGain * self.TestSensorGainRange
        self.GainStep = (self.GainStopVal-self.GainStartVal)/self.NumImages
        self.GainExpo = HighestValidETForGainLinearity
        self.maxGainInDb = math.log10(self.qMaxGain) * 20.0
        self.minGainInDb = math.log10(self.qMinGain) * 20.0
        self.gainStepsInDb = int(math.ceil((self.maxGainInDb - self.minGainInDb) / (self.gainGranularityInDb * self.NumImages))) * self.gainGranularityInDb

        return NvCSTestResult.SUCCESS

    def runEnvCheckForETLinearity(self, BlackLevel):
        # skip the environment test and linearity if min and max of sensor exposure time is the same
        if (self.qMinExpTime == self.qMaxExpTime):
            self.logger.warning ("minimum exposure time [{0}] == maximum exposure time [{1}]; please check the exposure time range of sensor driver\n"
            .format(self.qMinExpTime, self.qMaxExpTime))
            self.linearityOnOffLUT['EXPOSURE_TIME'] = False
            self.linearityOnOffLUT['EP'] = False
            return NvCSTestResult.SKIPPED
        ValidETRangePercentageThreshold = self.ValidETRangePercentageThreshold
        BlackLevelPadding = NvCSTestConfiguration.BlackLevelPadding
        OverExposureThreshold = NvCSTestConfiguration.OverExposureThreshold

        # Find minimum ET that doesn't underexpose
        self.logger.info("\n\nENVIRONMENT CHECK: Finding minimum exposuretime that doesn't underexpose at gain %2.6f.\n\n" % self.qMinGain)
        LowestValidET = self.FindLowestValidET(self.qMinExpTime, self.qMaxExpTime,
            min(BlackLevel) + BlackLevelPadding*4, self.qMinGain)
        # Find maximum ET that doesn't overexpose
        self.logger.info("\n\nENVIRONMENT CHECK: Finding maximum exposuretime that doesn't overexpose at gain %2.6f.\n\n" % self.qMinGain)
        HighestValidET = self.FindHighestValidET(self.qMinExpTime, self.qMaxExpTime,
            self.maxPixelValue * OverExposureThreshold * 0.99, self.qMinGain)

        self.logger.info("\n\nValid Exposure Range for ET linearity is: %.5f-%.5f sec\n\n" % (LowestValidET, HighestValidET))

        # Check that a high enough percentage of ET range is valid
        if((HighestValidET-LowestValidET)/(self.qMaxExpTime-self.qMinExpTime)
        < ValidETRangePercentageThreshold):
            # Check if light is too bright or too dark (valid range tends high or low)
            if((HighestValidET+LowestValidET) < (self.qMaxExpTime+self.qMinExpTime)):
                self.logger.error("Environment Check Failed: light source is too bright.")
            else:
                self.logger.error("Environment Check Failed: light source is too dark.")
            self.logger.info("HighestValidET %3.4f LowestValidET %3.4f " % (HighestValidET, LowestValidET))
            self.logger.info("self.qMaxExpTime %3.4f self.qMinExpTime %3.4f " % (self.qMaxExpTime, self.qMinExpTime))
            return NvCSTestResult.ERROR

        # Save the relevant data
        self.ExpTimeStart = LowestValidET
        self.ExpTimeStop = HighestValidET
        self.ExpTimeStep = (HighestValidET - LowestValidET)/self.NumImages
        self.ExpTimeGain = self.qMinGain

        return NvCSTestResult.SUCCESS

    def testIfLightIsOff(self, BlackLevel):
        BlackLevelPadding = NvCSTestConfiguration.BlackLevelPadding
        GainStopVal = self.qMaxGain * self.TestSensorGainRange

        # Test Upper Bound
        # (To check if the light is off)
        config = NvCSTestConfiguration("TestHalfMaxExposure",
            "envCheck_%.5f_%.2f_test" % (self.qMaxExpTime/2.0, self.qMinGain),
            self.qMaxExpTime/2.0, self.qMinGain)
        NvCSTestConfiguration.runConfig(self, config, False)

        self.maxPixelValue = self.nvrf.getPeakPixelValue()

        self.logger.info("Determining exposure to run in gain linearity.  Checking Gain %f [%.2f, %.2f, %.2f] MaxPixelValue %f" %
            (GainStopVal, config.Avg["Color"][0], config.Avg["Color"][1], config.Avg["Color"][2], self.maxPixelValue))

        if ((config.Avg["Color"][0] < (BlackLevel[0]+BlackLevelPadding))
        or (config.Avg["Color"][1] < (BlackLevel[1]+BlackLevelPadding))
        or (config.Avg["Color"][2] < (BlackLevel[2]+BlackLevelPadding))):
            self.logger.error("Environment Check Failed: light source is too dark (is it turned on?)")
            return NvCSTestResult.ERROR
        return NvCSTestResult.SUCCESS

    def runEnvCheck(self, BlackLevel):
        if(self.options.useClassicRanges == True):
            self.logger.info("A command line option flag was used to run the classic hard coded ranges for the test.")
            self.logger.warning("Classic hard coded ranges are no longer supported.  Environment check will continue as usual.")

        self.BayerPhaseConfirmed = True

        # check if the light is off
        err = self.testIfLightIsOff(BlackLevel)
        if (err != NvCSTestResult.SUCCESS):
            return err

        for mode in self.options.linearityMode :
            if (("ALL" == mode) or \
                ("EP" == mode) or \
                ("GAIN" == mode)):
                # get max exposure time for Gain and EP linearity
                err = self.runEnvCheckForEPAndGainLinearity()
                if ((err != NvCSTestResult.SUCCESS) and (err != NvCSTestResult.SKIPPED)):
                    return err

        # run environment check for ET linearity.
        # if the sensor is one of the special sensors then we don't need to run
        # environment check for exposure time linearity test because we are running
        # it separately before running the test.
        for mode in self.options.linearityMode:
            if ((not self.options.cappedExposure) and \
                (("ALL" == mode) or \
                ("EP" == mode) or \
                ("EXPOSURE" == mode))):
                if ("EP" == mode) and (False == self.linearityOnOffLUT['EP']):
                    err = NvCSTestResult.SKIPPED
                elif ("ALL" == mode) and ((False == self.linearityOnOffLUT['EXPOSURE_TIME']) and \
                                          (False == self.linearityOnOffLUT['EP'])):
                    err = NvCSTestResult.SKIPPED
                else:
                    err = self.runEnvCheckForETLinearity(BlackLevel)
                if ((err != NvCSTestResult.SUCCESS) and (err != NvCSTestResult.SKIPPED)):
                    return err


        return NvCSTestResult.SUCCESS

    def FindLowestValidET(self, left, right, threshold, gain):
        ''' Find lowest valid exposure for the given gain which should
            produce channel values more than the specified threshold
        '''
        # check base case
        if(right-left <= self.ETPrecisionThreshold):
            return right
        # test the center brightness
        CenterET = (right+left)/2
        config = NvCSTestConfiguration("FindLowestValidET",
            "envCheck_%.5f_%.2f_test" %
            (CenterET, gain),
            CenterET, gain)
        NvCSTestConfiguration.runConfig(self, config, False)

        self.logger.info("ET: %fs - Average RGB pixel values: [%.2f, %.2f, %.2f]" %
            (CenterET, config.Avg["Color"][0], config.Avg["Color"][1], config.Avg["Color"][2]))

        if (min(config.Avg["Color"][0], config.Avg["Color"][1], config.Avg["Color"][2]) <= threshold):
            return self.FindLowestValidET(CenterET, right, threshold, gain)
        else:
            return self.FindLowestValidET(left, CenterET, threshold, gain)

    def FindHighestValidET(self, left, right, threshold, gain):
        ''' Find highest valid et for a given gain which should
            produce channel values less than specified threhold
        '''
        # check base case
        if(right-left <= self.ETPrecisionThreshold):
            if (right <= self.ETPrecisionThreshold):
                return right
            else:
                return left
        # test the center brightness
        CenterET = (right+left)/2.0
        config = NvCSTestConfiguration("FindHighestValidET",
            "envCheck_%.5f_%.2f_test" %
            (CenterET, gain),
            CenterET, gain)
        NvCSTestConfiguration.runConfig(self, config, False)

        self.logger.info("ET: %fs - Average RGB pixel values: [%.2f, %.2f, %.2f]" %
            (CenterET, config.Avg["Color"][0], config.Avg["Color"][1], config.Avg["Color"][2]))

        if (max(config.Avg["Color"][0], config.Avg["Color"][1], config.Avg["Color"][2]) >= threshold):
            return self.FindHighestValidET(left, CenterET, threshold, gain)
        else:
            return self.FindHighestValidET(CenterET, right, threshold, gain)

    def runGainLinearity(self, BlackLevel=[0.0, 0.0, 0.0]):
        testGainLinearityList = []

        # Create the list of capture configurations
        # Make sure to include the max gain

        if self.gainStepsInDb == 0.0 :
            return False, "gainSteps is 0; check the min sensor gain [{0}] and the max sensor gain [{1}]\n".format(self.qMinGain, self.qMaxGain);
        GainStep = int(math.ceil((self.maxGainInDb - self.minGainInDb) / self.gainStepsInDb));
        if self.manualGainStep is not None :
            GainStep = self.manualGainStep
        else :
            GainStep = 5 if GainStep < 5 else GainStep
        self.logger.info("Gain Linearity : GainStep: %2.6f" % GainStep)
        self.logger.info("Gain Linearity : Gain Start Value: %2.6f" % self.minGainInDb)

        # recalculate the gainStepsInDb
        self.gainStepsInDb = (self.maxGainInDb - self.minGainInDb)/GainStep
        if (self.options.gainGranularity is not None):
            if (self.gainStepsInDb > self.options.gainGranularity):
                self.gainStepsInDb -= (self.gainStepsInDb % self.options.gainGranularity)
            else:
                self.gainStepsInDb = self.options.gainGranularity
        tempGainTestPoints = set()
        gainTestPoints = []
        for i in range(GainStep):
            if (self.options.gainGranularity is not None):
                self.gainStepsInDb -= (self.gainStepsInDb % self.options.gainGranularity)
            calculatedGain = math.pow(10, (self.minGainInDb + i * self.gainStepsInDb)/20.0)
            if calculatedGain <= self.qMaxGain and calculatedGain >= self.qMinGain:
                self.logger.info("dbStep: %2.6f gain value: %2.6f\n" % ((i * self.gainStepsInDb), calculatedGain))
                tempGainTestPoints.add(calculatedGain)
        gainTestPoints = list(tempGainTestPoints)
        # Make sure to include the max gain
        if len(gainTestPoints) is not 0 :
            if (self.GainStopVal - gainTestPoints[-1] > math.pow(10, self.gainStepsInDb / 20.0)):
                self.logger.info("last gain step (%2.6f) is lower than the max gain; adding one more gain step" \
                    " with the max gain value (%2.6f)"%(gainTestPoints[-1], self.GainStopVal))
                if self.options.gainGranularity is not None:
                    self.maxGainInDb -= (self.maxGainInDb % self.options.gainGranularity)
                    self.logger.info("round the max gain to {0} by granularity = {1:2.8}".format(\
                        self.maxGainInDb, self.options.gainGranularity))
                    self.GainStopVal -= (self.GainStopVal % math.pow(10, self.gainStepsInDb / 20.0))
                self.logger.info("dbStep: %2.6f gain value: %2.6f\n" % (self.maxGainInDb, self.GainStopVal))
                gainTestPoints.append(self.GainStopVal)
                GainStep = len(gainTestPoints)
                self.logger.info("new Gain Linearity : GainStep: %2.6f"%len(gainTestPoints))
        else :
            gainTestPoints.append(self.GainStartVal)
            gainTestPoints.append(self.GainStopVal)

        # assemble the test configuration
        for gainVal in gainTestPoints:
            testGainLinearityList.append(NvCSTestConfiguration(
                "GainLinearity",
                "G_%.3f_%.2f" % (self.GainExpo, gainVal),
                self.GainExpo,
                gainVal,
                self.qMinFocusPos))

        # Shuffle the configuration list to catch any buffered configuration cases (Bug 752686)
        if(self.noShuffle == False):
            random.shuffle(testGainLinearityList)

        GainIsLinear, GainLog = self.runLinearity(testGainLinearityList, "Gain Linearity", BlackLevel)

        return GainIsLinear, GainLog

    def runExposureLinearity(self, BlackLevel=[0.0, 0.0, 0.0]):
        testExposureLinearityList = []

        # Create the list of capture configurations
        # Using  a *1000 trick to utilize range()
        ExpTimeStart = self.ExpTimeStart*100
        ExpTimeStop = self.ExpTimeStop*100

        ExpTimeInterval = (ExpTimeStop - ExpTimeStart) + 1
        # Arbitrarily setting steps to be log_2(interval) + 4
        ExpTimeTestSteps = int(math.log(ExpTimeInterval, 2)) + 4
        if(ExpTimeTestSteps < self.NumImages):
            ExpTimeTestSteps = self.NumImages

        startExpTimePower = math.log(ExpTimeStart, 2)
        stopExpTimePower = math.log(ExpTimeStop, 2)

        ExpTimePowerStep = (stopExpTimePower - startExpTimePower)/(ExpTimeTestSteps-1)

        if (ExpTimeTestSteps - 1) == 0.0:
            return False, "Error: ExpTimeTestSteps step is 0.0"
        if ExpTimePowerStep == 0.0:
            return False, "Error: ExpTimePowerStep step is 0.0; please check your starting exposure time [{0}] and ending exposure time [{1}]".format(startExpTimePower, stopExpTimePower)
        ExpTimePowerPoints = list(range(int(startExpTimePower*1000000), int(stopExpTimePower*1000000), int(ExpTimePowerStep*1000000)))

        # Make sure to include the max exposure time
        ExpTimeTestPoints = []
        for expoVal in ExpTimePowerPoints:
            ExpTimeTestPoints.append(math.pow(2, expoVal/1000000.0)/100)
        if ExpTimeTestPoints[-1] != self.ExpTimeStop:
            ExpTimeTestPoints[-1] = self.ExpTimeStop

        # assemble the test configuration
        for expoVal in ExpTimeTestPoints:
            testExposureLinearityList.append(NvCSTestConfiguration(
                "ExposureLinearity",
                "E_%.3f_%.2f" % (expoVal, self.ExpTimeGain),
                expoVal,
                self.ExpTimeGain,
                self.qMinFocusPos))

        # Shuffle the configuration list to catch any buffered configuration cases (Bug 752686)
        if(self.noShuffle == False):
            random.shuffle(testExposureLinearityList)

        ExpoIsLinear, ExpoLog = self.runLinearity(testExposureLinearityList, "ExposureTime Linearity", BlackLevel)

        return ExpoIsLinear, ExpoLog

    def runEPLinearity(self, BlackLevel):
        testEPSnrList = []

        # Intialize EP and GainStartValue
        EP = self.GainExpo * self.qMaxGain

        if self.qMaxGain <= 4.0:
             # Limit the maximum EP to the product of mid gain setting and max exposure time
            MaxEP = self.ExpTimeStop * (self.qMinGain + self.qMaxGain) / 2.0

            if EP > MaxEP:
                self.logger.info(("nvcssensortests.py::runEPLinearity: EP test will use a reduced EP " \
                    "constant of {0:.4f} due to the dimness of the light source.").format(MaxEP))
                EP = MaxEP

        MinExposureTime = EP / self.qMaxGain
        GainStartVal = EP / self.ExpTimeStop

        if GainStartVal < self.qMinGain :
            self.logger.warning("nvcssensortests.py::runEPLinearity: GainStartVal(%2.6f) is lower than sensor minimum gain " \
                                "(%2.6f); setting the starting gain to the sensor minimum gain value "% (GainStartVal, self.qMinGain));
            GainStartVal = self.qMinGain
        if GainStartVal > self.qMaxGain :
            self.logger.error("nvcssensortests.py::runEPLinearity: GainStartVal(%2.6f) is greater than sensor maximum gain " \
                    "(%2.6f); check your gain/exp setting"% (GainStartVal, self.qMaxGain));
            return False, "GainStartVal is greater than sensor maximum gain.", False

        # use GainStartVal as the minGainInDb
        minStartGainInDb = math.log10(GainStartVal) * 20
        GainStep = int(math.ceil((self.maxGainInDb - minStartGainInDb) / self.gainStepsInDb));
        if self.manualGainStep is not None :
            GainStep = self.manualGainStep
        else :
            GainStep = 5 if GainStep < 5 else GainStep
        self.logger.info("Exposure Product Linearity :GainStep: %2.6f" % GainStep)
        self.logger.info("Exposure Product Linearity :Gain Start Value: %2.6f" % GainStartVal)
        # recalculate the gainStepsInDb
        self.gainStepsInDb = (self.maxGainInDb - minStartGainInDb)/GainStep
        if (self.options.gainGranularity is not None):
            if (self.gainStepsInDb > self.options.gainGranularity):
                self.gainStepsInDb -= (self.gainStepsInDb % self.options.gainGranularity)
            else:
                self.gainStepsInDb = self.options.gainGranularity

        EPGainTestPoints = []
        for i in range(GainStep):
            calculatedGain = math.pow(10, (minStartGainInDb + i * self.gainStepsInDb)/20.0)
            if (calculatedGain < self.qMaxGain and calculatedGain > GainStartVal):
                self.logger.info("dbStep: %2.6f gain value: %2.6f\n" % ((i * self.gainStepsInDb), calculatedGain))
                EPGainTestPoints.append(calculatedGain)

        # Make sure to include the max gain
        if len(EPGainTestPoints) is not 0 :
            if self.options.gainGranularity is not None:
                self.GainStopVal -= (self.GainStopVal % math.pow(10, self.gainStepsInDb / 20.0))
                self.logger.info("round the GainStop to {0} by granularity = {1:2.8}".format\
                    (self.GainStopVal, self.options.gainGranularity))
            if (self.GainStopVal - EPGainTestPoints[-1] > math.pow(10, self.gainStepsInDb / 20.0)):
                self.logger.info("last gain step (%2.6f) is lower than the max gain; adding one more gain step" \
                                 " with the max gain value (%2.6f)"%(EPGainTestPoints[-1], self.GainStopVal))
                if self.options.gainGranularity is not None:
                    self.maxGainInDb -= (self.maxGainInDb % self.options.gainGranularity)
                    self.logger.info("round the max gain to {0} by granularity = {1:2.8}".format(\
                        self.maxGainInDb, self.options.gainGranularity))
                    self.GainStopVal -= (self.GainStopVal % math.pow(10, self.gainStepsInDb / 20.0))
                self.logger.info("dbStep: %2.6f gain value: %2.6f\n" % (self.maxGainInDb, self.qMaxGain))
                EPGainTestPoints.append(self.GainStopVal)
                self.logger.info("new exposure product Linearity : GainStep: %2.6f"%len(EPGainTestPoints))
        else :
            EPGainTestPoints.append(self.GainStartVal)
            EPGainTestPoints.append(self.GainStopVal)

        GainStartVal = EPGainTestPoints[0]
        GainStopVal  = EPGainTestPoints[-1]

        if GainStartVal == GainStopVal :
            GainStartVal = self.qMinGain # set to minimum value
        gainStepDelta = GainStep - len(EPGainTestPoints) + 1
        gainMaxMinDelta = abs(EPGainTestPoints[0] - EPGainTestPoints[-1])
        for i in range(1, gainStepDelta):
           EPGainTestPoints.append(EPGainTestPoints[0] + (i * (gainMaxMinDelta/gainStepDelta)))
        EPGainTestPoints.sort()
        # recalculate EP based on valid exposure from gain linearity
        EP = MinExposureTime * GainStopVal

        expStart = EP / max(EPGainTestPoints)
        expStop = EP / min(EPGainTestPoints)

        if expStop > self.qMaxExpTime:
            return False, "The light source is too dark for EP Linearity test.", False
        elif expStart < self.qMinExpTime:
            return False, "The light source is too bright for EP Linearity test.", False

        for gainVal in EPGainTestPoints:
            expoVal = EP/gainVal

            testEPSnrList.append(NvCSTestConfiguration(
                "ExposureProductLinearity",
                "EP_%.3f_%.2f" % (expoVal, gainVal),
                expoVal,
                gainVal,
                self.qMinFocusPos))

        # Shuffle the configuration list to catch any buffered configuration cases (Bug 752686)
        if(self.noShuffle == False):
            random.shuffle(testEPSnrList)

        EPIsLinear, EPLog, bPixelValueLow = self.runSNR(testEPSnrList, "Exposure Product Linearity", BlackLevel, allowedVariation=5.0)

        return EPIsLinear, EPLog, bPixelValueLow

    def runTest(self, args):
        self.logger.info("NVCS Linearity Test v2.1")
        GainLog = None
        ExpoLog = None
        EPLog   = None
        segmentGainRange = []
        # parse the advanced option if exist
        if self.options.advanced is not None :
           if self.options.gainsteps is not None :
               if self.options.gainsteps <= 0:
                   self.logger.error("NvCSLinearityRawTest::runTest: Invalid use of the --gainsteps option; value must greater than 0")
                   return NvCSTestResult.ERROR
               else :
                   self.logger.debug("NvCSLinearityRawTest::runTest: advanced option maunual step [%d] is used" % (self.options.gainsteps))
                   self.manualGainStep = self.options.gainsteps
           if self.options.linearitySegment is not None:
            # parse the linearitySegment string; none digit input is not allowed;
            # must present at least two arguments in ascending order
            segmentGainRange = self.options.linearitySegment.split(",")
            if (len(segmentGainRange) < 2) :
                self.logger.error("NvCSLinearityRawTest::runTest: Invalid use of the --segment option;less than 2 arguments.")
                return NvCSTestResult.ERROR
            else :
                tmp = 0.0
                for value in segmentGainRange :
                    if not value.isdigit() :
                        self.logger.error("Invalid use of the --segment option; argument must be digit")
                        return NvCSTestResult.ERROR
                    else :
                        # validate whether it's in ascending order
                        if tmp >= float(value) :
                            self.logger.error("Invalid use of the --segment option; argument must grater than 0, must be unique, and in ascending order")
                            return NvCSTestResult.ERROR
                        else :
                            tmp = float(value)

        self.failIfAohdrEnabled()

        bMultiExpos = nvcstestsystem.isMultipleExposuresSupported()

        (ret, numExposures, numGains, supportedMode, currentMode, bHdrChangeable) = self.obGraph.getHDRInfo()

        if (ret != NvCSTestResult.SUCCESS):
            self.logger.error("Error: getHDRInfo() returned error. Return value %d, numExposures %d numGains %d" % \
                              (ret, numExposures, numGains))
            return NvCSTestResult.ERROR

        #
        # Check if the comand line options are specified correctly
        # Get the index of the exposure that we need to use.
        #
        index, exposureMode = nvcstestsystem.getSingleExposureIndex(numExposures, False, self.options, self.logger)
        if (index == -1):
            self.logger.error("getSingleExposureIndex: Command line options error")
            return NvCSTestResult.ERROR

        if(self.options.numTimes > 1):
            self.NumImages = self.options.numTimes
        elif(self.options.numTimes == 1):
            self.logger.warning("User entered invalid number of samples (1).  Using default (%d)" % self.NumImages)

        self.noShuffle = self.options.noShuffle

        # Query exposure, gain, and focuser range
        self.obCamera.startPreview()
        gainRange = self.obCamera.getAttr(nvcamera.attr_gainrange)
        exposureTimeRange = self.obCamera.getAttr(nvcamera.attr_exposuretimerange)

        if (self.obCamera.isFocuserSupported()):
            focusRange = self.obCamera.getAttr(nvcamera.attr_focuspositionphysicalrange)
        self.obCamera.stopPreview()

        if(bMultiExpos):
            self.logger.info("Number of exposures %d Number of gains %d index used %d " % (numExposures, numGains, index))
            self.logger.info("Index     ETMin         ETMax         GainMin  GainMax")
            for i in range(0, numExposures, 1):
                self.logger.info("  %d   %2.10f   %2.10f      %2.2f     %2.2f " % (i, exposureTimeRange[0][i], exposureTimeRange[1][i], gainRange[0][i], gainRange[1][i]))

            if (isRangeCorrect(numExposures, index, exposureTimeRange) == NvCSTestResult.ERROR or \
                isRangeCorrect(numExposures, index, gainRange) == NvCSTestResult.ERROR):
                self.logger.info("")
                self.logger.info("")
                self.logger.error("TEST FAILED TO QUERY GAIN AND EXPOSURETIME RANGE!")
                self.logger.error("Make sure your driver supports range/limit queries like "
                                  "your reference driver")
                self.logger.info(" index %d  ETRange [%2.9f   %2.9f]  GainRange [%2.2f   %2.2f] " % \
                                (index, exposureTimeRange[0][index], exposureTimeRange[1][index], \
                                 gainRange[0][index], gainRange[1][index]))
                self.logger.info("")
                self.logger.info("")
                return NvCSTestResult.ERROR

            self.logger.info("Gain Range: [%f, %f]" % (gainRange[0][index], \
                             gainRange[1][index]))
            self.logger.info("ExposureTime Range: [%f sec, %f sec]" % \
                             (exposureTimeRange[0][index], \
                              exposureTimeRange[1][index]))
            if(gainRange[1][index] > 16):
                self.logger.warning("Max Sensor Gain Higher than 16 [%d]" % \
                                    (gainRange[1][index]))
                if (nvcsUtil.isEmbeddedOS()):
                    maxGainRangeRatio = 0.75
                    gainRange[1][index] = 16  if ((gainRange[1][index] * maxGainRangeRatio) < 16) else (gainRange[1][index] * maxGainRangeRatio)
                    self.logger.warning("EmbeddedOS: set Max Sensor Gain to %f" % gainRange[1][index])
                    if self.options.gainGranularity is not None:
                        gainGranLinear = math.pow(10, (self.options.gainGranularity/20.0))
                        origMaxGain = gainRange[1][index]
                        gainRange[1][index] += (gainGranLinear - (gainRange[1][index] % gainGranLinear))
                        self.logger.warning("EmbeddedOS: round Max Sensor Gain to %fdB granulairty from %f to %f "%(self.options.gainGranularity, origMaxGain, gainRange[1][index]))

            self.qMinGain = gainRange[0][index]
            self.qMaxGain = gainRange[1][index]
            self.qMinExpTime = exposureTimeRange[0][index]
            self.qMaxExpTime = exposureTimeRange[1][index]

        else:
            if ((gainRange[1] == 0) or (exposureTimeRange[1] == 0)):
                self.logger.info("")
                self.logger.info("")
                self.logger.error("TEST FAILED TO QUERY GAIN AND EXPOSURETIME RANGE!")
                self.logger.error("Make sure your driver supports range/limit queries "
                                  "like your reference driver")
                self.logger.info("")
                self.logger.info("")
                return NvCSTestResult.ERROR

            self.logger.info("Gain Range: [%f, %f]" % (gainRange[0], gainRange[1]))
            self.logger.info("ExposureTime Range: [%f sec, %f sec]" % \
                            (exposureTimeRange[0], exposureTimeRange[1]))
            if(gainRange[1] > 16):
                self.logger.warning("Max Sensor Gain Higher than 16 [%d]" % (gainRange[1]))

            self.qMinGain = gainRange[0]
            self.qMaxGain = gainRange[1]
            self.qMinExpTime = exposureTimeRange[0]
            self.qMaxExpTime = exposureTimeRange[1]

        gainRangeList = []
        # add gain range set from minimum valid gain range to maximum valid gain range
        # range set is created by the segment value
        # I.E. segment = 1, 10, 72
        # set = [1,10], [10,72]

        gainMin = 0.0
        for index in range(len(segmentGainRange)) :
            segGainValdB = float(segmentGainRange[index])
            segGainVal = math.pow(10, (segGainValdB/20.0))

            if index is 0 :
                if (segGainVal < self.qMinGain) :
                   self.logger.error("The argument for --segment is invalid; value smaller than sensor minimum gain")
                   return NvCSTestResult.ERROR
                else :
                    gainMin = segGainVal
            elif index > 0 :
                # because there might have a minor variance when converting dB to voltage
                # we will set the segGainVal to the maximum value returned from the driver if and only if
                # the calculated value is in 1% of difference
                if segGainVal > self.qMaxGain :
                    if (((segGainVal - self.qMaxGain)/self.qMaxGain) > 0.01):
                        self.logger.error("The argument for --segment is invalid; value %d(%2.4f) greater than sensor maximum gain %ddB(%2.4f)"\
                                      % (segGainValdB,segGainVal,round(math.log10(self.qMaxGain) * 20), self.qMaxGain))
                        return NvCSTestResult.ERROR
                    else:
                        self.logger.warning("calculated voltage gain [%2.4f] is greater than the max gain returned from driver [%2.4f]; " \
                            "set the segmented gain to the maximum gain allowed by driver" \
                            %(segGainVal, self.qMaxGain))
                        gainRangeList.append([gainMin, self.qMaxGain])
                else :
                    gainRangeList.append([gainMin, segGainVal])
                    gainMin = segGainVal
        if (nvcsUtil.isEmbeddedOS() and \
            not self.options.cappedExposure and \
            ((self.options.advanced is None) or (len(segmentGainRange) is 0))) :
            # We are scaling the minimum gain to 4.0 instead of the minimum gain from
            # the sensor attribute. The reason is that we are trying to cover wider pixel data
            # value for exposure linearity test.
            # This adjust is only true when minimum gain is smaller than 4.0 and smaller than the maximum gain
            gainMin = 4.0
            if (self.qMinGain < gainMin) and (self.qMaxGain > gainMin) :
                print("set the minimum gain value to %2.4f instead of %2.4f"%(gainMin, self.qMinGain))
                self.qMinGain = gainMin
                gainRangeList = [[self.qMinGain, self.qMaxGain]]

        if (self.obCamera.isFocuserSupported()):
            self.qMinFocusPos = focusRange[0]
            self.qMaxFocusPos = focusRange[1]

        if len(gainRangeList) > 0 :
            self.logger.info ("The linearity test will be performed in %d time(s):" % len(gainRangeList))
        else :
            self.logger.info ("The linearity test will be performed in 1 time:")
            gainRangeList.append([self.qMinGain, self.qMaxGain])
        count = 0
        passFail = [NvCSTestResult.SKIPPED] * self.LinearityEnum["numLinearityEnum"]

        for gainRange in gainRangeList:
            count += 1
            self.qMinGain = gainRange[0]
            self.qMaxGain = gainRange[1]

            if (self.qMinExpTime == self.qMaxExpTime) and (self.qMinGain == self.qMaxGain):
                self.logger.warning ("min exposure time [{0}] == max exposure time [{1}] and "
                "min gain [{2}] == max gain [{3}]; SKIP all linearity tests".format(self.qMinExpTime, self.qMaxExpTime, self.qMinGain, self.qMaxGain))
                passFail = [NvCSTestResult.SKIPPED] * self.LinearityEnum["numLinearityEnum"]
                continue

            self.logger.info ("Running set(%d) of linearity with gain range of %f to %f" % (count, gainRange[0], gainRange[1]))
            self.confirmPrompt("\n\nThe test took its black level captures. Please TURN THE LIGHT OFF.\n\n")
            # Take captures to reference as black level
            BlackLevel = self.getBlackLevel(exposureTimeRange)

            if NvCSTestResult.ERROR == BlackLevel :
                self.logger.error("not able to retrieve black level; check you sensor driver")
                return BlackLevel

            # Process the test conditions
            if (self.options.cappedExposure):
                self.confirmPrompt("\n\nPlease TURN THE LIGHT ON for Gain linearity test.\n\n")
                self.logger.info("\nRunning environment check for Gain linearity test.\n")
            else:
                self.confirmPrompt("\n\n Please TURN THE LIGHT ON.\n\n")

            goodEnv = self.runEnvCheck(BlackLevel)
            if(goodEnv == NvCSTestResult.ERROR):
                self.logger.info("")
                self.logger.info("")
                self.logger.info("It is possible that an auto feature may also be on, preventing the test from calibrating correctly.")
                self.logger.info("All auto features (ie AGC, AWB, AEC) should be turned off.")
                self.logger.info("")
                self.logger.info("It is possible that the driver is incorrect and unusable to take valid measurements.")
                self.logger.info("Look back at the log and see if the [R:#, G:#, B:#] values make sense relative to the other capture settings.")
                self.logger.info("There was a line specifying the BlackLevel reference being used, is it a valid estimate?")
                self.logger.info("Are the captures with the lowest exposure and gain settings the smallest of the 3 captures?")
                self.logger.info("If not, validate the requested camera settings from NVCS are reaching your driver correctly.")
                self.logger.info("")
                self.logger.info("To help the debugging efforts, try removing the capture shuffling order by adding the flags --nv --noshuffle")
                self.logger.info("To help the debugging efforts, try a different number of captures by adding the flags --nv -n <# of captures>")
                self.logger.info("")
                passFail = [NvCSTestResult.ERROR] * self.LinearityEnum["numLinearityEnum"]
                continue

            # Run the Gain Linearity Experiment
            if (self.linearityOnOffLUT['GAIN'] == False):
                passFail[self.LinearityEnum["GAIN"]] = NvCSTestResult.SKIPPED
                GainLog = "Gain Linearity Test is skipped"
            else:
                for mode in self.options.linearityMode:
                    if mode == "ALL" or mode == "GAIN":
                        self.logger.info("")
                        self.logger.info("")
                        self.logger.info("Starting Gain Linearity Test.")
                        self.logger.info("")
                        self.logger.info("")
                        GainIsLinear, GainLog = self.runGainLinearity(BlackLevel)

                        if (not GainIsLinear):
                            passFail[self.LinearityEnum["GAIN"]] = NvCSTestResult.ERROR
                            if (GainLog is not None) :
                                self.logger.info("%s" % GainLog)
                            self.logger.info("")
                            self.logger.info("")
                            self.logger.error("Gain Linearity Test failed.")
                            self.logger.info("--Check if values are being written to the proper camera registers")
                            self.logger.info("--Check if values are being translated correctly from floating-point values to register values")
                            self.logger.info("--Ensure all sensor auto-exposure features are turned off. The test requires manual control of sensor settings.")
                            self.logger.info("--Check if test configuration gain values are set in the sensor driver correctly:")
                            self.logger.info("\t-Add a print to confirm gain floating point values that are translated in the sensor driver")
                            self.logger.info("\t-Compare printed floating point values from the sensor driver to the test configurations listed in the table")
                            self.logger.info("\tIf the values are different, there is an issue outside of your sensor driver.")
                            self.logger.info("")
                            self.logger.info("Still not fixed?  Look at the data results to see what values don't make sense")
                            self.logger.info("\t-A higher gain value should result in higher intensity values")
                            self.logger.info("\t-Ensure you have not hit any boundary limitations of the sensor or another dependent register")
                            self.logger.info("")
                            self.logger.info("To help the debugging efforts, try removing the capture shuffling order by adding the flags --nv --noshuffle")
                            self.logger.info("To help the debugging efforts, try a different number of captures by adding the flags --nv -n <# of captures>")
                            self.logger.info("")
                            self.logger.info("")
                            continue
                        passFail[self.LinearityEnum["GAIN"]] = NvCSTestResult.SUCCESS
                        self.logger.info("")
                        self.logger.info("")
                        self.logger.info("Gain Linearity Test Passed.")
                        self.logger.info("")
                        self.logger.info("")
                        break

            # This is needed because for these special sensors the gain
            # linearity uses maximum ET and sweeps gain, while the exposure
            # linearity uses the minimum gain and sweeps ET.
            # This causes the pixel values to be quite low for exposure
            # linearity producing a line fit which doesn't meet minimum slope requirement.
            if (self.linearityOnOffLUT['EXPOSURE_TIME'] == False):
                passFail[self.LinearityEnum["EXPOSURE"]] = NvCSTestResult.SKIPPED
                GainLog = "Exposure Linearity Test is skipped"
            else:
                for mode in self.options.linearityMode:
                    if mode == "ALL" or mode == "EXPOSURE" or mode == "EP":
                        if (self.options.cappedExposure):
                            self.confirmPrompt("\n\nIncrease the target brightness before running Exposure Linearity test.\n\n")

                            # Process the test conditions
                            self.logger.info("\nRunning environment check before running Exposure linearity test.\n")
                            goodEnv = self.runEnvCheckForETLinearity(BlackLevel)
                            if(goodEnv == NvCSTestResult.ERROR):
                                passFail[self.LinearityEnum['EXPOSURE']] = NvCSTestResult.ERROR
                                continue
                            break

            # Run the Exposure Linearity Experiment
            for mode in self.options.linearityMode:
                if mode == "ALL" or mode == "EXPOSURE":
                    if (self.linearityOnOffLUT['EXPOSURE_TIME'] == False):
                        passFail[self.LinearityEnum['EXPOSURE']] = NvCSTestResult.SKIPPED
                        ExpoLog = "Exposure Time Linearity Test is skipped"
                    else:
                        self.logger.info("")
                        self.logger.info("")
                        self.logger.info("Starting Exposure Linearity Test.")
                        self.logger.info("")
                        self.logger.info("")

                        ExpoIsLinear, ExpoLog = self.runExposureLinearity(BlackLevel)
                        if (not ExpoIsLinear):
                            passFail[self.LinearityEnum["EXPOSURE"]] = NvCSTestResult.ERROR
                            if GainLog is not None:
                                self.logger.info("%s" % GainLog)
                            if ExpoLog is not None:
                                self.logger.info("%s" % ExpoLog)
                            self.logger.info("")
                            self.logger.info("")
                            self.logger.error("Exposure Linearity Test failed.")
                            self.logger.info("--Check if values are being written to the proper camera registers")
                            self.logger.info("--Ensure all sensor auto-exposure features are turned off. The test requires manual control of sensor settings.")
                            self.logger.info("--Check if test configuration exposure settings are reaching sensor driver correctly:")
                            self.logger.info("\t-Add a print to confirm exposure time floating point values that are translated in the sensor driver")
                            self.logger.info("\t-Compare printed floating point values from the sensor driver to the test configurations listed in the table")
                            self.logger.info("\tIf the values are different, there is an issue outside of your sensor driver.")
                            self.logger.info("")
                            self.logger.info("Still not fixed?  Look at the data results to see what values don't make sense")
                            self.logger.info("\t-A higher exposure product should result in higher intensity values")
                            self.logger.info("\t-Ensure you have not hit any boundary limitations of the sensor or another dependent register")
                            self.logger.info("\t\t-A common boundary is a margin of padding between the framelength (VTS) and coarse time (exposure)")
                            self.logger.info("")
                            self.logger.info("To help the debugging efforts, try removing the capture shuffling order by adding the flags --nv --noshuffle")
                            self.logger.info("To help the debugging efforts, try a different number of captures by adding the flags --nv -n <# of captures>")
                            self.logger.info("")
                            self.logger.info("")
                            continue

                        self.logger.info("")
                        self.logger.info("")
                        passFail[self.LinearityEnum["EXPOSURE"]] = NvCSTestResult.SUCCESS
                        self.logger.info("Exposure Linearity Test Passed.")
                        self.logger.info("")
                        self.logger.info("")
                        break

            if self.options.cappedExposure :
                #in case of one of the special sensor, we will skip the exposure product linearity test
                if (self.linearityOnOffLUT['EP'] == False):
                    passFail[self.LinearityEnum["EP"]] = NvCSTestResult.SKIPPED
                    EPLog = "EP Linearity Test is skipped"
                else:
                    passFail[self.LinearityEnum["EP"]] = NvCSTestResult.SUCCESS
            else:
                for mode in self.options.linearityMode:
                    if mode == "ALL" or mode == "EP":
                        if (self.linearityOnOffLUT['EP'] == False):
                            passFail[self.LinearityEnum["EP"]] = NvCSTestResult.SKIPPED
                            EPLog = "EP Linearity Test is skipped"
                        else:
                            # Run the ExposureProduct Linearity Experiment
                            self.logger.info("")
                            self.logger.info("")
                            self.logger.info("Starting Exposure Product Linearity Test.")
                            self.logger.info("")
                            self.logger.info("")
                            EPIsLinear, EPLog, bPixelValueLow = self.runEPLinearity(BlackLevel)

                            if (not EPIsLinear):
                                passFail[self.LinearityEnum["EP"]] = NvCSTestResult.ERROR
                                if GainLog is not None:
                                    self.logger.info("%s" % GainLog)
                                if ExpoLog is not None:
                                    self.logger.info("%s" % ExpoLog)
                                if  EPLog is not None:
                                    self.logger.info("%s" % EPLog)
                                self.logger.info("")
                                self.logger.info("")
                                self.logger.error("Exposure Product Linearity Test failed.")
                                if (bPixelValueLow == True):
                                    self.logger.info("Average pixel values are too low - less than 30 percentof the maximum value")
                                else:
                                    self.logger.info("The pixel channel values (R,G,B) values here should have remained constant throughout the test")
                                self.logger.info("--Check if test configuration exposure and gain settings are reaching sensor driver correctly:")
                                self.logger.info("--Double Check gain values are translated correctly")
                                self.logger.info("--Do you think the test is requesting too high of a resolution of your sensor?")
                                self.logger.info("\t\tNote: The sensor does not have to match the exact resolution of the test to pass")
                                self.logger.info("--If it passed the previous Gain and Exposure Linearity tests, try increasing brightness")
                                self.logger.info("  to reduce possible low level noises")
                                self.logger.info("")
                                self.logger.info("To help the debugging efforts, try removing the capture shuffling order by adding the flags --nv --noshuffle")
                                self.logger.info("To help the debugging efforts, try a different number of captures by adding the flags --nv -n <# of captures>")
                                self.logger.info("")
                                self.logger.info("")
                                continue

                            self.logger.info("")
                            self.logger.info("")
                            passFail[self.LinearityEnum["EP"]] = NvCSTestResult.SUCCESS
                            self.logger.info("Exposure Product Linearity Test Passed.")
                            self.logger.info("")
                            self.logger.info("")
                            break

            self.logger.info("Test Data Results:")
            if GainLog is not None:
                self.logger.info("Gain Linearity Result:\n%s" % GainLog)
            if ExpoLog is not None:
                self.logger.info("Exposure Time Linearity Result:\n%s" % ExpoLog)
            if not (self.options.cappedExposure) and (EPLog is not None):
                #in case of one of the special sensor, we will skip the exposure product linearity test
                self.logger.info("%s" % EPLog)

            if(self.BayerPhaseConfirmed == False):
                self.logger.info("")
                self.logger.info("")
                self.logger.info("**The Bayer Phase could not automatically be validated in this test.")
                self.logger.info("**Please confirm the bayer phase is correct in the ODM driver.")
                self.logger.info("**You have passed linearity, but there is a phase discrepancy.")
                self.logger.info("")
                self.logger.info("")

        status = NvCSTestResult.SUCCESS
        skipped = 0
        if "ALL" in self.options.linearityMode:
            for idx in range(len(passFail)) :
                msg = "Linearity Test [%s] in range of [%2.6f ~ %2.6f] : " % \
                                      (self.ReverseLinearityEnum[idx],gainRangeList[0][0],gainRangeList[0][1])
                if (passFail[idx] == NvCSTestResult.ERROR) :
                    status = NvCSTestResult.ERROR
                    msg += "FAILED"
                    self.logger.error("%s" % msg)
                elif (passFail[idx] == NvCSTestResult.SKIPPED) :
                    skipped +=1
                    msg += "SKIPPED"
                    self.logger.info ("%s" % msg)
                else :
                    msg += "SUCCESS"
                    self.logger.info("%s" % msg)
        else:
            for mode in self.options.linearityMode:
                msg = "Linearity Test [%s] in range of [%2.6f ~ %2.6f] : " % \
                                      (mode,gainRangeList[0][0],gainRangeList[0][1])
                if (passFail[self.LinearityEnum[mode]] == NvCSTestResult.ERROR) :
                    status = NvCSTestResult.ERROR
                    msg += "FAILED"
                    self.logger.error("%s" % msg)
                elif (passFail[self.LinearityEnum[mode]] == NvCSTestResult.SKIPPED) :
                    skipped +=1
                    msg += "SKIPPED"
                    self.logger.info ("%s" % msg )
                else :
                    msg += "SUCCESS"
                    self.logger.info("%s" % msg)
        if skipped == len(self.linearityOnOffLUT):
            status = NvCSTestResult.SKIPPED
        return status

class NvCSBlackLevelRawTest(NvCSTestBase):
    "Black Level Raw Image Test"

    defNumImages = 15
    defMaxTemporalDiff = 1
    MaxTemporalDiff = 0.0
    MIN_SNR_dB = 30.0

    def __init__(self, options, logger, sensorSetting):
        NvCSTestBase.__init__(self, options, logger, "BlackLevel", sensorSetting)
        self.options = options
        self.sensorSetting = sensorSetting

    def needTestSetup(self):
        return True

    def getSetupString(self):
        return "This test requires the camera to be covered for darkest capture possible"

    def setupGraph(self):
        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.sensorSetting.imager_id, self.sensorSetting.imager_name)
        self.obGraph.setGraphType(GraphType.RAW)

        return NvCSTestResult.SUCCESS

    def runSNR(self, configList, testName):
        # 3.16% coefficient of variation is equivalent to the old 30dB SNR figure.
        MAX_VARIATION_PERCENT = 3.16
        Linearity = True
        Variation = [float("inf"), float("inf"), float("inf")]
        MaxTracker = -1
        MinTracker = -1
        AvgTracker = -1
        logStr = ""
        csvStr = ""
        maxPixelVal = None

        if (NvCSTestResult.ERROR == NvCSTestConfiguration.runConfigList(self, configList, False)):
            self.logger.error("nvcssensortests.py::NvCSBlackLevelRawTest::runSNR: not able to capture image for SNR.")
            return NvCSTestResult.ERROR

        maxPixelVal = self.nvrf.getPeakPixelValue()

        if maxPixelVal is None:
            Linearity = False
            if (self.nvrf.nvrawV3):
                logStr = "[ERROR]: maxPixelVal is none, invalid nvrf.dynamicPixelBitDepth[%d]\n" % self.nvrf._planeHeaderReader.getDynamicPixelBitDepth()
            else:
                logStr = "[ERROR]: maxPixelVal is none, invalid nvrf.outputFormat[%d]\n" % self.nvrf._outputDataFormat
            return Linearity, logStr

        logStr, Variation, MaxTracker, MinTracker, AvgTracker, csvStr, bPixelValueLow = NvCSTestConfiguration.processVariationStats(testName, configList, "Region", maxPixelVal)

        # If the user has not specified any command line options, we will set the difference tolerance to 1%.
        # The difference tolenrace is basically the fluctuation of blacklevel between the maximum and minimum
        # blacklevel value. The tolerance level is set to 6% of 10 bit image or 1% for any image greater than
        # 10 bits. We consider the blacklevel fluctuated greatly when he difference between max and min
        # is larger than the tolenrance level

        if (self.options.threshold == 0):
            # 6% for image with small output bit
            # 1% for image with large output bit
            # 6% is selected because original blacklevel test was based on the delta(1) between
            # min and max. In case of low output bit sensor, the pixel value is small, so the
            # % tolerance will be higher.
            if (self.nvrf.nvrawV3):
                if (self.nvrf.getDynamicBitDepth() == 10):
                    self.MaxTemporalDiff = 6
                else:
                    self.MaxTemporalDiff = 1
            else:
                if (self.nvrf._outputDataFormat == nvcamera.NvCameraToolsOutputDataFormat_10BitLinear):
                    self.MaxTemporalDiff = 6
                else:
                    self.MaxTemporalDiff = 1
        else:
            self.MaxTemporalDiff = float(self.options.threshold)

        if self.nvrf._sensorModeType == nvraw_v3.SENSOR_MODE_TYPE_WDR_PWL:
            self.MaxTemporalDiff *= 2

        for j in range(len(Variation)):
            if(Variation[j] > MAX_VARIATION_PERCENT):
                logStr += ("\n\nBlack Levels are fluctuating too greatly!\n\n")
                logStr += ("\n\nMaximum Coefficient of Variation has been exceeded! Found: %f%%, Maximum: %f%%\n\n" %
                    (Variation[j], MAX_VARIATION_PERCENT))
                Linearity = False
        spreadDiff = (MaxTracker - MinTracker)
        avgTolerance = (AvgTracker*self.MaxTemporalDiff/100)
        if(spreadDiff > avgTolerance):
            logStr += ("\n\nBlack Levels are fluctuating too greatly!\n\n")
            logStr += ("\n\nSpread of averages(%.2f) is greater than %.2f%%(%.2f) within an average of %.2f (%.2f to %.2f)!!!!!\n\n" %
                (spreadDiff,self.MaxTemporalDiff, avgTolerance, AvgTracker, MinTracker, MaxTracker))
            Linearity = False
        else:
            logStr += ("\n\nSpread of averages(%.2f) is within the specification of %.2f%%(%.2f)with an average of %.2f (%.2f to %.2f)\n\n" %
                (spreadDiff,self.MaxTemporalDiff, avgTolerance, AvgTracker, MinTracker, MaxTracker))

        return Linearity, logStr

    def runTest(self, args):
        self.logger.info("Black Level Test v2.0")
        self.failIfAohdrEnabled()

        bMultiExpos = nvcstestsystem.isMultipleExposuresSupported()

        #
        # Get HDR info.
        #
        (ret, numExposures, numGains, \
            supportedMode, currentMode, bHdrChangeable) = self.obGraph.getHDRInfo()

        if (ret != NvCSTestResult.SUCCESS):
            self.logger.error("Error: getHDRInfo() returned error. Return value %d, numExposures %d numGains %d" % \
                              (ret, numExposures, numGains))
            return NvCSTestResult.ERROR

        #
        # Check if the comand line options are specified correctly
        # Get the index of the exposure that we need to use.
        #
        index, exposureMode = nvcstestsystem.getSingleExposureIndex(numExposures, False, self.options, self.logger)
        if (index == -1):
            self.logger.error("getSingleExposureIndex: Command line options error")
            return NvCSTestResult.ERROR


        numImages = self.defNumImages
        if(self.options.numTimes > 1):
            numImages = self.options.numTimes
        elif(self.options.numTimes == 1):
            self.logger.warning("User entered invalid number of samples (1).  Using default (%d)" % numImages)

        if(self.options.threshold != 0):
            self.MaxTemporalDiff = self.options.threshold
        else:
            self.MaxTemporalDiff = self.defMaxTemporalDiff

        # Query ranges to use minimum configuration settings
        self.obCamera.startPreview()
        gainRange = self.obCamera.getAttr(nvcamera.attr_gainrange)
        exposureTimeRange = self.obCamera.getAttr(nvcamera.attr_exposuretimerange)
        self.obCamera.stopPreview()

        if (bMultiExpos):
            self.logger.info("Number of exposures %d Number of gains %d index used %d " % (numExposures, numGains, index))
            self.logger.info("Index   ETMin      ETMax      GainMin  GainMax")
            for i in range(0, numExposures, 1):
                self.logger.info("  %d   %2.6f   %2.6f      %2.2f     %2.2f " % (i, exposureTimeRange[0][i], exposureTimeRange[1][i], gainRange[0][i], gainRange[1][i]))

            qMinGain = gainRange[0][index]
            qMaxExpTime = exposureTimeRange[1][index]
        else:
            qMinGain = gainRange[0]
            qMaxExpTime = exposureTimeRange[1]

        gain = qMinGain
        expTime = qMaxExpTime
        self.logger.info("Max ET: %.5fs" % qMaxExpTime)

        # Create the configuration list
        testBlackLevelList = []
        for index in range(0, numImages):
            testBlackLevelList.append(NvCSTestConfiguration("Testing_BlackLevel",
                "BL_%.5f_%.2f_test" % (expTime, gain), expTime, gain))

        # Run the experiment with allowed variation of 3.16%
        TestPASS, BLLog = self.runSNR(testBlackLevelList, "Black Level Test")

        self.logger.info("%s" % BLLog)

        if(TestPASS == True):
            return NvCSTestResult.SUCCESS

        return NvCSTestResult.ERROR

class NvCSBayerPhaseTest(NvCSTestBase):
    "Bayer Phase Test"

    def __init__(self, options, logger, sensorSetting):
        NvCSTestBase.__init__(self, options, logger, "BayerPhase")
        self.options = options
        self.sensorSetting = sensorSetting

    def needTestSetup(self):
        return True

    def getSetupString(self):
        return "This test requires camera to be covered with the LED light panel turned on. Be careful not to overexpose or underexpose the scene."

    def setupGraph(self):
        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.sensorSetting.imager_id, self.sensorSetting.imager_name)
        self.obGraph.setGraphType(GraphType.RAW)

        return NvCSTestResult.SUCCESS

    def runTest(self, args):
        self.logger.info("Bayer Phase Test v1.1")

        # Exposue and Gain value acquired through general testing
        # These values may need to be changed
        Expo = 0.050
        Gain = 2.00
        config = NvCSTestConfiguration("Testing_BayerPhase",
                "BP_%.5f_%.2f_test" % (Expo, Gain), Expo, Gain)


        NvCSTestConfiguration.runConfig(self, config)

        # Calculating conditions of failure
        percErr = (abs(config.AvgPhaseGR - config.AvgPhaseGB)/max(config.AvgPhaseGR, config.AvgPhaseGB))
        if(percErr > 1.0):
            self.logger.error("Average GR (%f) & Average GB (%f) should be approximately equal." %
                (config.AvgPhaseGR, config.AvgPhaseGB))
            self.logger.error("Average GR (%f) & Average GB (%f) have a %f%% error (1%% is Passing)." %
                (config.AvgPhaseGR, config.AvgPhaseGB, percErr))
            return NvCSTestResult.ERROR
        if(config.AvgPhaseB < config.AvgPhaseR):
            self.logger.error("Average B (%f) should be GREATER than R (%f)." %
                (config.AvgPhaseB, config.AvgPhaseR))
            return NvCSTestResult.ERROR

        self.logger.info("\n\nConditions PASS for R(%.2f) GR(%.2f) GB(%.2f) B(%.2f)\n\n" % (config.AvgPhaseR, config.AvgPhaseGR, config.AvgPhaseGB, config.AvgPhaseB))
        return NvCSTestResult.SUCCESS

class NvCSFuseIDTest(NvCSTestBase):
    "Fuse ID test"

    FuseIDData = 0
    FuseID = []
    FuseIDSize = 0

    # Maximum length in bytes permitted for a fuse ID.  This should hold the same value as the maximum space allowed in the
    #   raw header.
    FuseIDMaxLength = 16

    # Table of values the Fuse ID should NOT hold.  A warning will be issued if the fuse ID matches any of these values.
    # Each entry is composed of the following fields:
    #   The first field per entry is the fuse ID byte value. If the length of this array is less than the maximum allowable size
    #       (the third field per entry), then the test will continue checking the last byte in the array.  This functionality
    #       is intended to serve two purposes:
    #           1. Checking for fuse IDs consisting of single repeated bytes.
    #           2. Accounting for the possibility of zero-padding after specific undesired fuse IDs.
    #   The second field per entry is the minimum size in bytes the fuse ID must be to be considered a match for this "bad value".
    #   The third field per entry is the maximum size in bytes the fuse ID must be to be considered a match for this "bad value".
    #   The fourth field per entry is a flag indicating if the fuse ID may still be equivalent to this "bad value"
    #       Set to "False" to disable checking for the corresponding "bad value".  Else set to "True".
    #   The final field per entry is a warning string to print if the fuse ID matches the bad value.
    BadValues = [
                  # Bits are all 0.  permitted size is 0-FuseIDMaxLength, so any size fuse id is valid.
                  [ [0x00],
                    0, FuseIDMaxLength, True,
                    "All Fuse ID bits are 0.  There is likely a problem with the driver, as it is very unlikely that a sensor will not have any data programmed to its OTP memory."],
                  # Bits are all 1.  permitted size is 0-FuseIDMaxLength, so any size fuse id is valid.
                  [ [0xff],
                    0, FuseIDMaxLength, True,
                    "All Fuse ID bits are 1.  There is likely a problem with the driver, as it is very unlikely that a sensor will have all of its OTP data written to 1."],
                  # Bytes spell out "DEADBEEF" in hex.  This is a common default value and usually will indicate an error.
                  # Must be at least 4 bytes long to be considered a match, but may be longer if following bytes are 0 (zero-padding).
                  [ [0xde, 0xad, 0xbe, 0xef, 0x00],
                    4, FuseIDMaxLength, True,
                    "The Fuse ID spells out \"DEADBEEF\" in hexadecimal.  This is a common default value, and hence means there is likely a problem with the driver."],
                  # This is a known default value.  A fuse ID return of this value will indicate there is probably a problem.
                  # Must be exactly 16 bytes long to be considered a match.
                  [ [0xff, 0xff, 0xff, 0xff, 0x67, 0x45, 0x23, 0x01, 0xf0, 0xde, 0xbc, 0x8a, 0xaa, 0xaa, 0xaa, 0xaa],
                    16, 16, True,
                    "The fuse ID has the value 0xffffffff67452301f0debc8aaaaaaaaa, which is a known default value.  Hence, there is likely a problem with the driver."]
                ]

    def __init__(self, options, logger, sensorSetting):
        NvCSTestBase.__init__(self, options, logger, "FuseID", sensorSetting)
        self.options = options
        self.sensorSetting = sensorSetting

    def setupGraph(self):
        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.sensorSetting.imager_id, self.sensorSetting.imager_name)
        self.obGraph.setGraphType(GraphType.RAW)

        return NvCSTestResult.SUCCESS

    def runTest(self, args):
        self.failIfAohdrEnabled()
        self.obCamera.startPreview()
        # get the fuse id
        try:
            self.FuseIDData = self.obCamera.getAttr(nvcamera.attr_fuseid)
        except nvcamera.NvCameraException as err:
            self.obCamera.stopPreview()
            if (err.value == nvcamera.NvError_NotSupported):
                self.logger.info("Fuse ID is not supported")
                return NvCSTestResult.SKIPPED
            else:
                self.logger.error("Fuse ID read failed.\nIs fuse ID read supported in the sensor driver?\n")
                return NvCSTestResult.ERROR

        if (0 < len(self.FuseIDData)):
            self.FuseIDSize = self.FuseIDData[0]
        else:
            self.logger.warning("no valid FuseID data; verify the sensor driver implementation")
            return NvCSTestResult.SKIPPED
        fileName = "header_test" + "_i%d_m%d"%(self.sensorSetting.imager_id, self.sensorSetting.sensor_mode) + ".nvraw"
        rawFilePath = os.path.join(self.testDir, fileName)

        # capture image to check against header
        try:
            self.obCamera.captureRAWImage(rawFilePath, False)
        except nvcamera.NvCameraException as err:
            if (err.value == nvcamera.NvError_NotSupported):
                self.logger.info("raw capture is not supported")
                return NvCSTestResult.SKIPPED
            else:
                raise

        self.obCamera.stopPreview()

        if not self.nvrf.readFile(rawFilePath):
            self.logger.error("couldn't open the file: %s" % rawFilePath)
            return NvCSTestResult.ERROR

        match = True
        # compare header fuse id with driver fuse id
        for index in range(self.FuseIDSize):
            val = int(self.nvrf._fuseId[(index * 2):(index * 2 + 2)], 16)
            if(val != self.FuseIDData[1][index]):
                match = False
                break

        if(match == False):
            fusestring = ""
            for index in range(self.FuseIDSize):
                fusestring += "{0:02x}".format(self.FuseIDData[1][index])

            self.logger.error("Header FuseID did not match Driver FuseID")
            self.logger.error("Header FuseID = 0x%s" % (self.nvrf._fuseId[:(self.FuseIDSize*2)]))
            self.logger.error("Driver FuseID = 0x%s" % (fusestring[:(self.FuseIDSize*2)]))
            return NvCSTestResult.ERROR

        self.logger.info("")
        self.logger.info("Fuse ID Size:\t%d" % self.FuseIDSize)
        if(self.FuseIDSize < 5):
            self.logger.error("Fuse ID Size (%d) should be at least 5.\n" % self.FuseIDSize)
            return NvCSTestResult.ERROR
        if(self.FuseIDSize > self.FuseIDMaxLength):
            self.logger.error("Fuse ID Size (%d) should be less than %d.\n" % (self.FuseIDSize, self.FuseIDMaxLength))
            self.logger.error("This larger size will not fit in the raw header.")
            return NvCSTestResult.ERROR
        # eliminate BadValue possible matches that have the wrong size range.
        for j in range(len(self.BadValues)):
            if(self.FuseIDSize < self.BadValues[j][1] or
               self.FuseIDSize > self.BadValues[j][2]):
                self.BadValues[j][3] = False;

        self.logger.info("")
        self.logger.info(" __Fuse ID:_______________ ")
        self.logger.info("| Byte #\t| Byte value\t|")
        self.logger.info("|_________|_______________|")
        for i in range(self.FuseIDSize):
            self.FuseID.append(self.FuseIDData[1][i])
            self.logger.info("| %d\t| 0x%x\t\t|" % (i, self.FuseID[i]))
            if(self.FuseID[i] > 0xff or self.FuseID[i] < 0):
                # this should never really happen, as the pipeline stores the values as single bytes throughout
                self.logger.error("Fuse ID byte is %d, which is not a valid single-byte value.  Values should fall between 0x00 and 0xff.")
                return NvCSTestResult.ERROR
            # check for undesirable values
            for j in range(len(self.BadValues)):
                if(self.BadValues[j][3] == True):
                    # repeat last array entry if needed
                    arrayindex = i if i < len(self.BadValues[j][0]) else len(self.BadValues[j][0])-1
                    if(self.BadValues[j][0][arrayindex] != self.FuseID[i]):
                        self.BadValues[j][3] = False
        self.logger.info("|_________|_______________|")
        self.logger.info("")

        for j in range(len(self.BadValues)):
            if(self.BadValues[j][3] == True):
                self.logger.info("*************************************************")
                self.logger.info("WARNING: %s" %(self.BadValues[j][4]))
                self.logger.info("*************************************************")

        return NvCSTestResult.SUCCESS

class NvCSAutoExposureTest(NvCSTestBase):
    "Auto Exposure Stability Test"

    testSettings = [[200, "High"],[100, "Med"],[50, "Low"]]

    settingsBase = """ap15Function.lensShading = FALSE;
    ae.MeanAlg.SmartTarget = FALSE;
    ae.MeanAlg.ConvergeSpeed = 0.9000;
    ae.MaxFstopDeltaNeg = 0.9000;
    ae.MaxFstopDeltaPos = 0.9000;
    ae.MaxSearchFrameCount = 50;\n"""

    overridesTarget = None

    qMinGain = 0.0
    qMinExpTime = 0.0

    def __init__(self, options, logger, sensorSetting):
        if (nvcsUtil.isL4T()):
            if os.getuid() != 0:
                print("You need to have root privileges to run ae_stability!\n")
                sys.exit(1)
        NvCSTestBase.__init__(self, options, logger, "AE_Stability")
        self.options = options
        self.sensorSetting = sensorSetting

    def needTestSetup(self):
        return True

    def getSetupString(self):
        return ("\n\nThis test must be run with a controlled, uniformly lit scene.  Cover the sensor with the light source on its middle setting.\n\n")

    def setupGraph(self):

        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.sensorSetting.imager_id, self.sensorSetting.imager_name)
        # parameters are width, height and modeNumber
        # modeNumber 0 will select highest res mode
        self.obGraph.setPreviewParams(self.sensorSetting.width, self.sensorSetting.height, self.sensorSetting.sensor_mode)
        self.obGraph.setStillParams(self.sensorSetting.width, self.sensorSetting.height, self.sensorSetting.sensor_mode)

        self.obGraph.setGraphType(GraphType.RAW)

        return NvCSTestResult.SUCCESS

    def aeCapture(self, config):
        rawFilePath = os.path.join(self.testDir, config.filename + ("_i%d_m%d.nvraw"%(self.sensorSetting.imager_id, self.sensorSetting.sensor_mode)))
        try:
            self.obCamera.captureRAWImage(rawFilePath, True)
        except nvcamera.NvCameraException as err:
            if (err.value == nvcamera.NvError_NotSupported):
                self.logger.info("raw capture is not supported")
                return NvCSTestResult.SKIPPED
            else:
                raise
        if not self.nvrf.readFile(rawFilePath):
            self.logger.error("couldn't open the file: %s" % rawFilePath)
            return NvCSTestResult.ERROR
        config.processRawAvgs(self.nvrf)

    def applySettings(self, settings):
        # Set Overrides
        try:
            f = open(self.overridesTarget, 'w')
            f.write(settings)
            f.close()

            # Set permission to 0664 here
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH
            if (nvcsUtil.setFileMode(self.overridesTarget, mode) != True):
                raise ValueError("Error: Setting file %s with mode to %o" % (self.overridesTarget, mode))

        except IOError:
            self.logger.error("Unable to set Overrides: [" + self.overridesTarget + "]")
            NvCSTestResult.ERROR

    def wipeSettings(self):
        # Delete Overrides
        os.remove(self.overridesTarget)

    def runTest(self, args):
        self.failIfAohdrEnabled()

        finishedTestData = []
        invGammaList = []
        avgBrightnessList = []
        imageCount = 0

        self.obCamera.startPreview()
        # Get the overrides location
        if (self.options.overridesPath != ""):
            self.overridesTarget = self.options.overridesPath
            self.obCamera.stopPreview()
        else:
            try:
                OverrideLocations = self.obCamera.getAttr(nvcamera.attr_overridelocations)
            except nvcamera.NvCameraException as err:
                self.logger.error("Failed to query override locations from the sensor")
                self.obCamera.stopPreview()
                return NvCSTestResult.ERROR
            self.obCamera.stopPreview()

            # Iterate through type 1 (".isp") files and find the first that is writeable.
            # NvCT only reports writeable paths, but in case of mixed permissions, we will double check.
            for path in OverrideLocations:
                if(path[0] == 1):
                    try:
                        dummyfile = open(path[1], 'wb')
                    except IOError:
                        self.logger.info(path[1] + " is not writeable.")
                    else:
                        dummyfile.close()
                        self.overridesTarget = path[1]
                        break
            if (self.overridesTarget is None):
                self.logger.error("No writeable override location available")
                return NvCSTestResult.ERROR
        self.logger.info("Camera Overrides Target: [%s]" % self.overridesTarget)

        for setting in self.testSettings:
            runSettings = self.settingsBase + "ae.MeanAlg.TargetBrightness = " + str(setting[0]) + ";\n"
            result = self.applySettings(runSettings)

            if(result == NvCSTestResult.ERROR):
                return NvCSTestResult.ERROR

            # Reload graph to force overrides
            self.obGraph.stopAndDeleteGraph()
            self.obGraph.createAndRunGraph()

            self.obCamera.startPreview()
            config = NvCSTestConfiguration("", "aeCheck_%d_test" % (setting[0]), -1, -1)
            self.aeCapture(config)
            self.obCamera.stopPreview()

            invGamma = (float(setting[0]) / 255) ** 2.2

            data = self.CaptureData("Test%sExpo" % (setting[1]), setting[0], invGamma,
                config.Avg["Color"][0], config.Avg["Color"][1], config.Avg["Color"][2])

            finishedTestData.append(data)

        self.wipeSettings()

        linearity = [False, False, False, False]
        rSquared = NvCSTestConfiguration.calculateRSquared(finishedTestData, "X", "Y", 4)

        self.rSquaredMin = self.options.rsquaredmin
        MIN_RSQUARED_ERROR_LOWER_BOUND = 0.5 # half of max of 1.0
        if (self.rSquaredMin < MIN_RSQUARED_ERROR_LOWER_BOUND):
            self.logger.error("Minimum squared error for R^2 is quite wrong.")
            return NvCSTestResult.ERROR

        fail = False
        for index in range(0, 4):
            linearity[index] = True if (rSquared[index] >= self.rSquaredMin) else False
            if(linearity[index] == False):
                fail = True

        self.logger.info("")
        self.logger.info("Camera Overrides Target [%s]" % self.overridesTarget)
        self.logger.info("")
        self.logger.info("___Auto_Exposure_Stability_________________________________")
        self.logger.info("|                 |TARGET |RED    |GREEN  |BLUE   |AVERAGE|")
        self.logger.info("|_________________|_______|_______|_______|_______|_______|")
        for i in range(0, len(finishedTestData)):
            t = finishedTestData[i]
            self.logger.info("|%16s |%7d|%7.2f|%7.2f|%7.2f|%7.2f|" %
                (t.ConfigName, t.Target, t.getR(), t.getG(),
                t.getB(), t.getAvg()))
        self.logger.info("|_________________|_______|_______|_______|_______|_______|")
        self.logger.info("| R^2             |       |%7.4f|%7.4f|%7.4f|%7.4f|" %
            (rSquared[0], rSquared[1], rSquared[2], rSquared[3]))
        self.logger.info("|_________________|_______|_______|_______|_______|_______|")
        self.logger.info("| RESULT          |       |%6s |%6s |%6s |%6s |" %
            ("PASS" if linearity[0] else "FAIL", "PASS" if linearity[1] else "FAIL",
            "PASS" if linearity[2] else "FAIL", "PASS" if linearity[3] else "FAIL"))
        self.logger.info("|_________________|_______|_______|_______|_______|_______|")
        self.logger.info("")

        # verify target 200 > 2 * target 50
        for i in range(len(finishedTestData[0].Y)):
            y1 = finishedTestData[0].Y[i] # y val for first data point (200)
            y2 = finishedTestData[-1].Y[i] # y val for last data point (50)
            if (y1 < (2 * y2)):
                fail = True
                self.logger.error("Brightness Target %d [%f] was not greater than 2 * Brightness Target %d [%f]"
                    % (finishedTestData[0].Target, finishedTestData[0].Y[i],
                       finishedTestData[-1].Target, finishedTestData[-1].Y[i]))

        return NvCSTestResult.ERROR if fail else NvCSTestResult.SUCCESS

    class CaptureData(object):
        def __init__(self, ConfigName, Target, X, R, G, B):
            self.ConfigName = ConfigName
            self.Target = Target
            self.X = X
            self.Y = [R, G, B, float(R + G + B) / 3]

        def getName(self):
            return self.ConfigName
        def getTarget(self):
            return self.Target
        def getR(self):
            return self.Y[0]
        def getG(self):
            return self.Y[1]
        def getB(self):
            return self.Y[2]
        def getAvg(self):
            return self.Y[3]


# This hardcoded test checks if max ET stored in driver is larger than 33ms.
# User can bypass this test by adding "-d constant_condition" in command line
# Any Future hardcoded check will be performed under this test.
class NVConstantConditionTest(NvCSTestBase):
    "Constant condition test"
    # hard coded constants for 33ms check
    errMargin = 1.0/1000.0
    iterations = 5
    expTime_33ms_check = 0.033
    overridesTarget = None

    # hard coded constants for override path check.
    l4t_overridePath = "/var/nvidia/nvcam/settings/camera_overrides_front.isp"

    def __init__(self, options, logger, sensorSetting):
        NvCSTestBase.__init__(self, options, logger, "constant condition checks")
        self.options = options
        self.sensorSetting = sensorSetting

    def setupGraph(self):
        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.options.imager_id, self.options.sensor_name)
        self.obGraph.setGraphType(GraphType.RAW)

        return NvCSTestResult.SUCCESS

    def getOverrideTypeString(self, overrideType):
        if(overrideType == nvcamera.OVERRIDE_LOCATIONS_TYPE_NONE):
            return "OVERRIDE_LOCATIONS_TYPE_NONE"
        elif(overrideType == nvcamera.OVERRIDE_LOCATIONS_TYPE_OVERRIDE):
            return "OVERRIDE_LOCATIONS_TYPE_OVERRIDE"
        elif(overrideType == nvcamera.OVERRIDE_LOCATIONS_TYPE_FACTBLOB):
            return "OVERRIDE_LOCATIONS_TYPE_FACTBLOB"
        elif(overrideType == nvcamera.OVERRIDE_LOCATIONS_TYPE_CALIBFACTBLOB):
            return "OVERRIDE_LOCATIONS_TYPE_CALIBFACTBLOB"
        raise NvCameraException(NvError_BadParameter, "Invalid OverrideLocationType specified")

    def runTest(self, args):
        retVal = NvCSTestResult.SUCCESS

        self.failIfAohdrEnabled()
        if (args != None):
            self.exposureTimeValues = args

        bMultiExpos = nvcstestsystem.isMultipleExposuresSupported()

        # query and print max exposuretime range
        # we need to start preview to get correct exposure time range
        self.obCamera.startPreview()

        # only do 33ms check for non wdr sensor modes
        if ("WDR" not in self.sensorSetting.sensor_mode_type):
            self.logger.info("===== 33ms Check =====")
            exposureTimeRange = self.obCamera.getAttr(nvcamera.attr_exposuretimerange)

            # check if Max ExpTime is smaller than 33ms. If smaller, the test return with Error
            if (bMultiExpos):
                expTime = exposureTimeRange[1][0]
                if(expTime < self.expTime_33ms_check):
                    self.logger.error("Max exposure time in driver is smaller than 0.033s.")
                    retVal = NvCSTestResult.ERROR
            else:
                expTime = exposureTimeRange[1]
                if(expTime < self.expTime_33ms_check):
                    self.logger.error("Max exposure time in driver is smaller than 0.033s.")
                    retVal = NvCSTestResult.ERROR

            if (retVal == NvCSTestResult.ERROR):
                self.logger.info("Use \"-d constant_condition\" flag to bypass this test, if max ET<33ms is desired.")
            else:
                self.logger.info("constant_condition test: SUCCESS: Max exposure time in driver is %.5fs, which is larger than 0.033s" % expTime)
            self.logger.info("===== 33ms Check Done =====\n")

        # Get the overrides location
        self.logger.info("===== Override Path Check =====")
        if (self.options.overridesPath != ""):
            self.overridesTarget = self.options.overridesPath
        else:
            try:
                OverrideLocations = self.obCamera.getAttr(nvcamera.attr_overridelocations)
            except nvcamera.NvCameraException as err:
                self.logger.error("Failed to query override locations from the sensor")
                self.obCamera.stopPreview()
                return NvCSTestResult.ERROR

            # Iterate through type 1 or OVERRIDE_LOCATIONS_TYPE_OVERRIDE (".isp") files and
            # find the first that is writeable.
            # NvCT only reports writeable paths, but in case of mixed permissions, we will double check.
            writeableOverridePathFound = False
            for path in OverrideLocations:
                self.logger.info(self.getOverrideTypeString(path[0]) + " = " + path[1])

                if( (path[0] == nvcamera.OVERRIDE_LOCATIONS_TYPE_OVERRIDE) and (writeableOverridePathFound == False)):
                    try:
                        self.logger.info("open(" + path[1] + ")")
                        dummyfile = open(path[1], 'wb')
                    except IOError:
                        self.logger.info(path[1] + " is not writeable.")
                    else:
                        dummyfile.close()
                        self.overridesTarget = path[1]
                        writeableOverridePathFound = True
            if (self.overridesTarget is None):
                self.logger.error("No writeable override location (OVERRIDE_LOCATIONS_TYPE_OVERRIDE) available")
                self.obCamera.stopPreview()
                retVal = NvCSTestResult.ERROR

        self.logger.info(bcolors.BOLD+bcolors.UNDERLINE+("Camera Overrides Target: [%s]" % self.overridesTarget)+bcolors.ENDC)
        # self.logger.info(bcolors.BOLD+("Recommanded L4T Override Target: [%s]" % self.l4t_overridePath)+bcolors.ENDC)

        # if (self.overridesTarget == self.l4t_overridePath):
        #     self.logger.info("Queried override targat matches a recommanded target.")
        self.logger.info("===== Override Path Check Done =====\n")

        # Focuser power of 2 check
        self.logger.info("===== Focuser Power of 2 Check =====")
        if (self.obCamera.isFocuserSupported()):
            focusRange = self.obCamera.getAttr(nvcamera.attr_focuspositionphysicalrange)
            totalSteps = abs(focusRange[1] - focusRange[0]) + 1
            focuserMotorSpeed = self.obCamera.getAttr(nvcamera.attr_focusermotorspeedrange)
            if (totalSteps != 0 and totalSteps&(totalSteps-1)==0):
                self.logger.info("Total focuser steps (%d) is a power of 2" %totalSteps)
            elif (focuserMotorSpeed[-1] != 0):
                self.logger.warning("Focuser motor speed is non zero (%d), might be a stepper motor" %focuserMotorSpeed[-1])
            else:
                self.logger.error("Total focuser steps (%d) is not a power of 2" %totalSteps)
                retVal = NvCSTestResult.ERROR

        self.logger.info("===== Focuser Power of 2 Check Done =====\n")

        self.obCamera.stopPreview()

        oGraph = nvcamera.Graph()

        num = oGraph.getNumSupportedSensorEntries()
        if (num <= 0):
            self.logger.error("Number of supported sensor entries is %d" % num)
            return NvCSTestResult.ERROR

        nvctCharBufferUniqueName = [nvcamera.NvctCharBuffer() for i in range(num)]

        # Get all sensor properties and keep them around in a list
        # The reason we do it this way is to print them all out at the end
        # to avoid driver debug spew to interfere with the prints.
        #
        for i in range(num):
            camSPropUniqueName = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_UNIQUE_NAME,
                                               nvcamera.SPROP_TYPE_CBUFFER,
                                               1, nvctCharBufferUniqueName[i])
            oGraph.getSensorProperty(i, camSPropUniqueName);

        self.logger.info("List of Sensor Unique Names")
        for i in range(num):
            if (len(nvctCharBufferUniqueName[i].getBuffer()) == 0):
                self.logger.info("%2d  Null/Missing" % i)
                retVal = NvCSTestResult.ERROR
            else:
                self.logger.info("%2d  %s" % (i, nvctCharBufferUniqueName[i].getBuffer()))

        if (retVal == NvCSTestResult.ERROR):
            self.logger.error("One or more null values of Unique names found")

        return retVal
