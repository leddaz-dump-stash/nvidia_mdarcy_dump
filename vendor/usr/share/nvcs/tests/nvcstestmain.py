#-------------------------------------------------------------------------------
# Name:        nvcstestmain.py
# Purpose:
#
# Created:     01/23/2012
#
# Copyright (c) 2012-2020 NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#
#-------------------------------------------------------------------------------
#!/usr/bin/env python

# global mapping between testname and
# test objects

from __future__ import division
from __future__ import print_function

import sys

# Specify the python library search paths for softfp, hardfp, aarch64
sys.path.append('/usr/lib/arm-linux-gnueabi/tegra')
sys.path.append('/usr/lib/arm-linux-gnueabihf/tegra')
sys.path.append('/usr/lib/aarch64-linux-gnu/tegra')

import nvcstest
import nvcstestutils
import nvcstestsystem
import os
import time
import shutil
import subprocess
from optparse import OptionParser
from optparse import make_option
from optparse import OptionValueError
import nvcamera
import stat
from nvcstestutils import SensorSetting
from nvcstestutils import NvCSIOUtil
import re
from nvcsCommonUtils import NVCSutil
nvcsUtil      = None

class SensorProperty(object) :
    def __init__(self, configFile = None):
        self.oGraph = nvcamera.Graph()
        self.configFile = None
        if (configFile != None):
            self.oGraph.setSensorConfigFile(configFile)
            self.configFile = configFile
        self.numSupportedSensorEntries= self.oGraph.getNumSupportedSensorEntries()
        self.sourceIndex = list(range(self.numSupportedSensorEntries))
        self.sensorModeIndex = list(range(self.numSupportedSensorEntries))
        self.nvctCharBufferUniqueName = list(range(self.numSupportedSensorEntries))
        self.nvctCharBufferName = list(range(self.numSupportedSensorEntries))
        self.nvctCharBufferPos = list(range(self.numSupportedSensorEntries))
        self.nvctCharBufferModuleName = list(range(self.numSupportedSensorEntries))
        self.nvctCharSensorDescription = list(range(self.numSupportedSensorEntries))
        self.nvctSensorMode = list(range(self.numSupportedSensorEntries))
        self.csiPixelBitDepth = list(range(self.numSupportedSensorEntries))
        self.dynamicPixelBitDepth = list(range(self.numSupportedSensorEntries))
        self.modeType = list(range(self.numSupportedSensorEntries))
        self.uint_temp = nvcamera.uint32pc()
        self.sensorModeMatrix = list(range(self.numSupportedSensorEntries))
        # set a valid sensor ID / Sensor Mode combination to 1; invalid to 0
        for i in range(self.numSupportedSensorEntries) :
            self.sensorModeMatrix[i] = [0] * self.numSupportedSensorEntries

    def grepSensorInfo(self):
        # Get all sensor properties and keep them around in a list
        # The reason we do it this way is to print them all out at the end
        # to avoid driver debug spew to interfere with the prints.
        #
        sourceIndex = 0
        modeIndex   = 0
        if(self.configFile != None) :
            self.oGraph.setSensorConfigFile(self.configFile)
        for i in range(0, self.numSupportedSensorEntries):
            if not (nvcsUtil.isEmbeddedOS()):
                camSsourceIndex = nvcamera.CamSProperty(nvcamera.SPROP_SOURCE_INDEX,
                                            nvcamera.SPROP_TYPE_UINT32,
                                            1, self.uint_temp)
                self.oGraph.getSensorProperty(i, camSsourceIndex)
                self.sourceIndex[i] = camSsourceIndex.getUint32ElementAtIndex(0)
                sourceIndex = self.sourceIndex[i]

                camSsensorModeIndex = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_MODE_INDEX,
                                            nvcamera.SPROP_TYPE_UINT32,
                                            1, self.uint_temp)
                self.oGraph.getSensorProperty(i, camSsensorModeIndex)
                self.sensorModeIndex[i] = camSsensorModeIndex.getUint32ElementAtIndex(0)
                modeIndex = self.sensorModeIndex[i]
                # set sensorModeMatrix[sensor][mode] to 1; 0 == false, 1 == true
                (self.sensorModeMatrix[sourceIndex][modeIndex]) = 1

            self.nvctCharBufferUniqueName[i] = nvcamera.NvctCharBuffer()
            camSPropUniqueName = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_UNIQUE_NAME,
                                            nvcamera.SPROP_TYPE_CBUFFER,
                                            1, self.nvctCharBufferUniqueName[i])
            self.oGraph.getSensorProperty(i, camSPropUniqueName)

            self.nvctCharBufferName[i] = nvcamera.NvctCharBuffer()
            camSPropName = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_NAME,
                                            nvcamera.SPROP_TYPE_CBUFFER,
                                            1, self.nvctCharBufferName[i])
            self.oGraph.getSensorProperty(i, camSPropName)


            self.nvctCharBufferPos[i] = nvcamera.NvctCharBuffer()
            camSPropPos = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_POS,
                                            nvcamera.SPROP_TYPE_CBUFFER,
                                            1, self.nvctCharBufferPos[i])
            self.oGraph.getSensorProperty(i, camSPropPos)

            self.nvctCharBufferModuleName[i] = nvcamera.NvctCharBuffer()
            camSPropModuleName = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_MODULE_NAME,
                                            nvcamera.SPROP_TYPE_CBUFFER,
                                            1, self.nvctCharBufferModuleName[i])
            self.oGraph.getSensorProperty(i, camSPropModuleName)

            self.nvctCharSensorDescription[i] = nvcamera.NvctCharBuffer()
            camSPropSensorDescription = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_DESCRIPTION,
                                            nvcamera.SPROP_TYPE_CBUFFER,
                                            1, self.nvctCharSensorDescription[i])
            self.oGraph.getSensorProperty(i, camSPropSensorDescription)


            camSPropCSIBitDepth = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_CSIPIXEL_BITDEPTH,
                                            nvcamera.SPROP_TYPE_UINT32,
                                            1, self.uint_temp)
            self.oGraph.getSensorProperty(i, camSPropCSIBitDepth)
            self.csiPixelBitDepth[i] = camSPropCSIBitDepth.getUint32ElementAtIndex(0)

            camSPropDynamicBitDepth = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_DYNAMICPIXEL_BITDEPTH,
                                            nvcamera.SPROP_TYPE_UINT32,
                                            1, self.uint_temp)
            self.oGraph.getSensorProperty(i, camSPropDynamicBitDepth)
            self.dynamicPixelBitDepth[i] = camSPropDynamicBitDepth.getUint32ElementAtIndex(0)

            camSPropModeType = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_MODETYPE,
                                            nvcamera.SPROP_TYPE_UINT32,
                                            1, self.uint_temp)
            self.oGraph.getSensorProperty(i, camSPropModeType)
            self.modeType[i] = nvcstestsystem.getModeType(camSPropModeType.getUint32ElementAtIndex(0))

            self.nvctSensorMode[i] = nvcamera.NvCameraToolsSensorMode()
            camSProp2 = nvcamera.CamSProperty(nvcamera.SPROP_NVCTSENSORMODE,
                                        nvcamera.SPROP_TYPE_NVCTSENSORMODE,
                                        1, self.nvctSensorMode[i])
            self.oGraph.getSensorProperty(i, camSProp2)
        self.oGraph.stop()
        self.oGraph.close()

class TestFactory(object):
    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    #
    # testDict starter values. These dictionary elements are common to
    # Android, L4T and EmbeddedLinux, EmbeddedQNX
    #
    testDict = {                # enabled
        "jpeg_capture"          : 1,
        "raw_capture"           : 1,
        "concurrent_raw"        : 1,
        "exposuretime"          : 1,
        "gain"                  : 1,
        "multiple_raw"          : 1,
        "linearity"             : 1,
        "host_sensor"           : 1,
        "sharpness"             : 1,
        "blacklevel"            : 1,
        "fuseid"                : 1,
        "crop"                  : 1,
        "ae_stability"          : 1,
        "capture_script"        : 1,
        "constant_condition"    : 1,
        "makernote"             : 1,
    }

    #
    # testDictionary specific to Android and L4T
    #
    testDictOnlyAndroidL4T = {
                "linearity3"            : 1,
                "bayerphase"            : 1,
                "focuspos"              : 1,
                "hdr_ratio"             : 1,
                "pfp_streaming_file"    : 1,
                "pfp_streaming"         : 1,
                "constant_condition"    : 1,
                "aperture_conformance"  : 0,
                "sensor_dt_compliance"  : 1,
                "v4l2_compliance"       : 1,
                "vi_mode"               : 1,
                "nvtunerd_tunable"      : 1,
                "nvtunerd_host_process" : 1,
                "nvtunerd_live_stream"  : 1,
                }

    #
    # testDictionary disabled for EmbeddedLinux/EmbeddedQNX
    #
    testDictOnlyEmbeddedOS = {
                "jpeg_capture"          : 0,
                "ae_stability"          : 0,
                "fuseid"                : 0,
                "crop"                  : 0,
                "concurrent_raw"        : 0,
                "linearity3"            : 0,
                "bayerphase"            : 0,
                "hdr_ratio"             : 0,
                "pfp_streaming_file"    : 0,
                "pfp_streaming"         : 0,
                "constant_condition"    : 0,
                "aperture_conformance"  : 0,
                "sharpness"             : 0,
                "v4l2_compliance"       : 0,
                "vi_mode"               : 0,
                "nvtunerd_tunable"      : 0,
                "nvtunerd_host_process" : 0,
                "nvtunerd_live_stream"  : 0,
                "host_sensor"           : 0,
                "makernote"             : 0,
                }

    if (nvcsUtil.isMobile()):
        # Add all Android and L4T specific tests
        testDict.update(testDictOnlyAndroidL4T)
    elif (nvcsUtil.isEmbeddedOS()):
        # Add all Embedded Linux specific tests
        testDict.update(testDictOnlyEmbeddedOS)

    sanityNameList = [
                        "raw_capture",
                        "exposuretime",
                        "gain",
                        "multiple_raw"
                     ]
    conformanceNameList = [
                                "blacklevel",
                                "linearity",
                          ]
    utilityNameList = []

    if (nvcsUtil.isMobile()):
        sanityNameList += [
                             "capture_script",
                             "jpeg_capture",
                             "concurrent_raw",
                             "fuseid",
                             "crop",
                             "focuspos",
                             "host_sensor",
                             "pfp_streaming_file",
                             "pfp_streaming",
                             "constant_condition",
                             "sensor_dt_compliance",
                             "v4l2_compliance",
                             "vi_mode",
                             "nvtunerd_tunable",
                             "nvtunerd_host_process",
                             "nvtunerd_live_stream",
                             "makernote"
                          ]
        conformanceNameList += [
                                "sharpness",
                                "ae_stability"
                          ]
        utilityNameList += [
                          "ae_stability"
                      ]


    sanityStagingNameList = [
                                #"aStagingTestName"
                            ]

    conformanceStagingNameList = [
                                    #"linearity3"
                                    #"aperture_conformance"
                                 ]


    if (nvcsUtil.isAndroid() or nvcsUtil.isL4T()):
        utilityNameList += [ "hdr_ratio" ]

    def __init__(self):
        pass

    @classmethod
    def getTestObject(self, testName, options, logger, sensorSetting = None):
        if (testName == "jpeg_capture"):
            return nvcstest.NvCSJPEGCapTest(options, logger, sensorSetting)
        elif (testName == "raw_capture"):
            return nvcstest.NvCSRAWCapTest(options, logger, sensorSetting)
        elif (testName == "concurrent_raw"):
            return nvcstest.NvCSConcurrentRawCapTest(options, logger, sensorSetting)
        elif (testName == "exposuretime"):
            return nvcstest.NvCSExposureTimeTest(options, logger, sensorSetting)
        elif (testName == "gain"):
            return nvcstest.NvCSGainTest(options, logger, sensorSetting)
        elif (testName == "focuspos"):
            return nvcstest.NvCSFocusPosTest(options, logger, sensorSetting)
        elif (testName == "multiple_raw"):
            return nvcstest.NvCSMultipleRawTest(options, logger, sensorSetting)
        elif (testName == "linearity"):
            return nvcstest.NvCSLinearityRawTest(options, logger, sensorSetting)
        elif (testName == "linearity3"):
            return nvcstest.NvCSLinearityV3Test(options, logger, sensorSetting)
        elif (testName == "blacklevel"):
            return nvcstest.NvCSBlackLevelRawTest(options, logger, sensorSetting)
        elif (testName == "bayerphase"):
            return nvcstest.NvCSBayerPhaseTest(options, logger, sensorSetting)
        elif (testName == "host_sensor"):
            return nvcstest.NvCSHostSensorTest(options, logger, sensorSetting)
        elif (testName == "sharpness"):
            return nvcstest.NvCSSharpnessTest(options, logger, sensorSetting)
        elif (testName == "fuseid"):
            return nvcstest.NvCSFuseIDTest(options, logger, sensorSetting)
        elif (testName == "crop"):
            return nvcstest.NvCSCropTest(options, logger, sensorSetting)
        elif (testName == "ae_stability"):
            return nvcstest.NvCSAutoExposureTest(options, logger, sensorSetting)
        elif (testName == "capture_script"):
            return nvcstest.NvCSCaptureScriptTest(options, logger, sensorSetting)
        elif (testName == "pfp_streaming_file"):
            return nvcstest.NvCSPfpFileAPITest(options, logger)
        elif (testName == "pfp_streaming"):
            return nvcstest.NvCSPfpAPITest(options, logger, sensorSetting)
        elif (testName == "constant_condition"):
            return nvcstest.NVConstantConditionTest(options, logger, sensorSetting)
        elif (testName == "makernote"):
            return nvcstest.NvCSMakernoteTests(options, logger, sensorSetting)
        elif (testName == "aperture_conformance"):
            return nvcstest.NvCSApertureConformanceTest(options, logger, sensorSetting)
        elif (testName == "sensor_dt_compliance"):
            return nvcstest.NvCSSensorDTComplianceTest(options, logger)
        elif (testName == "vi_mode"):
            return nvcstest.NvCSViModeTest(options, logger, sensorSetting)
        elif (testName == "v4l2_compliance"):
            return nvcstest.NvCSV4l2ComplianceTest(options, logger)
        elif (testName == "nvtunerd_tunable"):
            return nvcstest.NvCSNvtunerdTunableTest(options, logger)
        elif (testName == "nvtunerd_host_process"):
            return nvcstest.NvCSNvtunerdHostProcessTest(options, logger)
        elif (testName == "nvtunerd_live_stream"):
            return nvcstest.NvCSNvtunerdLiveStreamTest(options, logger)
        else:
            return None

    @classmethod
    def hasTest(self, testName):
        return testName in self.testDict

    @classmethod
    def disableTest(self, testName):
        if (testName in self.testDict):
            self.testDict[testName] = 0

    @classmethod
    def enableTest(self, testName):
        if (testName in self.testDict):
            self.testDict[testName] = 1

    @classmethod
    def isEnabled(self, testName):
        if (testName in self.testDict):
            return self.testDict[testName]
        else:
            return 0

# function that will parse the option :specific for sensor mode and sensor id
# it will convert the option from string to int and set the all mode/sensor flag
# if the option is "a"

def multiModeSensorParser(option):
    arg = []
    allFlag = False
    flag = False
    if (option is None) :
        arg.append(0)
    else :
        for item in option :
            if (len(item) > 1) :
                for subitem in item :
                    if subitem.isdigit() :
                        arg.append(int(subitem))
                    elif subitem == 'a' :
                        allFlag = True
                        break
            else :
                if item.isdigit() :
                    arg.append(int(item))
                elif item == 'a' :
                    allFlag = True
                    break
    return arg, allFlag

# this function will read the valid imager list and mode list
# and create a valid LUT of sensor/mode combination
def createImagerModeComb(sensorProp, imagerArg, allImager, modeArg, allMode):
    if not (nvcsUtil.isEmbeddedOS()):
        # create a sensor mode look up matrix; loop through the number of sensor; loop through the number
        # of mode from each sensor; create the look up table if the sensor_id + the sensor mode is a
        # valid combination from the sensor configuration.
        funcLogger = nvcstestutils.Logger()
        imagerModeComb = []
        # case to create LUT with all sensor and available mode combination
        if ((allMode == True) and (allImager == True)) :
            for imagerIdx in range (len(sensorProp.sensorModeMatrix)):
                for modeIdx in range(len(sensorProp.sensorModeMatrix[imagerIdx])):
                    if (1 == sensorProp.sensorModeMatrix[imagerIdx][modeIdx]) :
                        imagerModeComb.append([imagerIdx, modeIdx])

        # case to create LUT with selected sensor and all available mode combination
        elif ((allMode == True) and (allImager == False)):
            for imagerIdx in imagerArg:
                if (imagerIdx < len(sensorProp.sensorModeMatrix)) :
                    for modeIdx in range(len(sensorProp.sensorModeMatrix[imagerIdx])):
                        if (1 == sensorProp.sensorModeMatrix[imagerIdx][modeIdx]) :
                            imagerModeComb.append([imagerIdx,modeIdx])

        # case to create LUT with all sensor and selected mode combination
        elif ((allMode == False) and (allImager == True)):
            for imagerIdx in range(len(sensorProp.sensorModeMatrix)):
                for modeIdx in modeArg :
                    if (modeIdx < len(sensorProp.sensorModeMatrix[imagerIdx])) :
                        if (1 == sensorProp.sensorModeMatrix[imagerIdx][modeIdx]) :
                            imagerModeComb.append([imagerIdx,modeIdx])
                    else :
                        funcLogger.error("sensor mode index %d is out of range" % modeIdx)

        # case to create LUT with selected sensor and selected mode
        else :
            for imagerIdx in imagerArg :
                if (imagerIdx < len(sensorProp.sensorModeMatrix)) :
                    for modeIdx in modeArg :
                        if (modeIdx < len(sensorProp.sensorModeMatrix[imagerIdx])) :
                            if (0 == sensorProp.sensorModeMatrix[imagerIdx][modeIdx]) :
                                funcLogger.info ("not a valid combination of options.sensor[%d] with options.mode[%d]" % (imagerIdx,modeIdx))
                            else :
                                imagerModeComb.append([imagerIdx,modeIdx])
                        else :
                            funcLogger.error("sensor mode index %d is out of range" % modeIdx)
                else :
                    funcLogger.error("sensor mode index %d is out of range" % imagerIdx)
        return imagerModeComb
#NOTE: this is a temperary solution for automotive by creating a LUT based on the config file
#      until the automotive has integrated the changes for source index
def createSensorIdLUTbyConfigFile(configFile):
    sensor_id = []
    sensor_name = []
    width = []
    height = []
    with open(configFile, "r") as ifread:
        for line in ifread:
            if re.search('capture-params-set', line, re.M|re.I):
                words = line.split()
                # based on the config file; second words should be the sensor ID
                newWord = words[1][:-1]
                sensor_id.append(int(newWord) - 1)
            elif re.search('capture-name', line, re.M|re.I):
                words = line.split()
                newWord = re.sub('["]','',words[2])
                sensor_name.append(newWord)
            elif re.search('resolution', line, re.M|re.I):
                words = line.split()
                x, y = re.split(r"[x]", words[2])
                x = re.sub('["]','',x)
                y = re.sub('["]','',y)
                width.append(x)
                height.append(y)
    return sensor_id, sensor_name, width, height

def main():


    start_time = time.time()
    numFailures = 0
    numTests = 0
    numSkippedTests = 0
    numStagingFailures = 0
    numStagingTests = 0
    numStagingSkippedTests = 0
    RunSuccessStr = ""
    sensorProp = None
    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()
    with nvcstestutils.Logger() as logger:

        # parse arguments
        usage = "\n" \
                "%prog <options> - execute the Conformance Test Suite \n\n" \
                "Description:\n" \
                "\t Sanity tests consists of a series of simple basic\n" \
                "\t tests to make sure that the nvcs infrastructure, basic\n" \
                "\t odm functionalities, camera core and algorithm paths are\n" \
                "\t functional.\n" \
                "\n \t Imager tests are more sophisticated and specific\n" \
                "\t setup is required. Each test is designed to catch issues\n" \
                "\t which have been seen by camera team while working on\n" \
                "\t different customer devices. The Sanity tests must pass\n" \
                "\t in order to run the Imager tests."

        sanityOptionHelp = None
        testNameOptionHelp = None
        if (nvcsUtil.isEmbeddedOS()):
            sanityOptionHelp = "Run Sanity tests. Use -l option to look at the" \
                               " list of sanity tests"
            testNameOptionHelp = "Execute the specified test name. Multiple -t options are allowed to execute" \
                               " more than one tests using a single command\n" \
                               " example:\n" \
                               "1) Command to run jpeg_capture test:\n" \
                               "   python {0} --cf ddpx-a.conf  --c SF3324-CSI-A -t jpeg_capture\n" \
                               "2) Command to run multiple tests jpeg_capture and raw_capture \n" \
                               "   using same command:\n" \
                               "   python {0} --cf ddpx-a.conf  --c SF3324-CSI-A  -t jpeg_capture -t raw_capture\n" \
                               " NOTE: see the actual usage of --cf and --c below".format(sys.argv[0])
        elif (nvcsUtil.isMobile()):
            sanityOptionHelp = 'Run Sanity tests. If no -i option is specified, the command will' \
                 + ' run using default imager id 0. Use -l option to look at the' \
                 + ' list of sanity tests'
            testNameOptionHelp = "Execute the specified test name. Multiple -t options are allowed to execute" \
                               "more than one tests using a single command\n" \
                               "example:\n" \
                               "1) Command to run jpeg_capture test for imager id 0:\n" \
                               "   python {0} -t jpeg_capture -i 0\n" \
                               "2) Command to run multiple tests jpeg_capture and raw_capture \n" \
                               "   for imager id 0 using same command:\n" \
                               "   python {0} -t jpeg_capture -t raw_capture -i 0".format(sys.argv[0])
        else:
            logger.error ("cannot create sanity Option due to unknown OS [%s]"%nvcsUtil.getOsName())
            sys.exit(1)

        mobile_options = [
                make_option('--classic', dest='useClassicRanges', default=False, action="store_true",
                        help = 'Do not query sensor for gain and exposure range.'
                             + 'This option is only supported for \"linearity\" test at present'),
                make_option('-d', dest='disabled_test_names', default=None, type="string", action = "append",
                        metavar="TEST_NAME",
                        help = 'Disables the test. The test name specified as an argument will not'
                             + ' execute. Multiple -d options are supported'),
                make_option('-i', dest='imager_id', default=None, type="string", metavar="IMAGER_ID", action = "append",
                        help = "Set imager id. Value is 0 based sensor id and value 'a' is all sensor id\n"
                             + "example:\n"
                             + "- Command to run sanity test suite with imager id 1\n"
                             + "  python %s -s -i 1\n" % sys.argv[0]
                             + "- Command to run sanity test with multiple sensors\n"
                             + "  python %s -s -i 0 -i 2\n" % sys.argv[0]
                             + "- Command to run sanity test with all sensor\n"
                             + "  python %s -s -i a" % sys.argv[0]),
                make_option('--nofocus', dest='ignoreFocuser', default=False, action="store_true",
                        help = 'Ignore ALL focuser commands in the test'),
                make_option('--runs', dest='totalTestRuns', default=1, type="int",
                        help = 'Set number of times to run each test.'
                             + ' Saves NVRaws from the last run only.  Saves logs from all runs.'),
                make_option('--timerenable', dest='timer_enable', action='store_true', default=False,
                        help = 'Print time taken by the tests'),
                make_option('-m', dest='sensor_mode', default=None, type="string", action = "append", metavar="SENSOR_MODE",
                        help = "Set sensor mode. Value is 0 based sensor mode and value 'a' is all sensor modes\n"
                             + "example:\n"
                             + "- Command to run sanity test with monde 1\n"
                             + "  python %s -s -m 1\n" % sys.argv[0]
                             + "- Command to run sanity test with multiple modes\n"
                             + "  python %s -s -m 1 -m 2\n" % sys.argv[0]
                             + "- Command to run sanity test with all modes\n"
                             + "  python %s -s -m a" %  sys.argv[0]),
                make_option('--nvraw', dest='nvraw_version', default="v3", choices=["v2", "v3"], metavar="NVRAW_VERSION",
                    help = "nvraw version\n"
                           "Takes the following parameters (default is v3):\n"
                           "v2\n"
                           "v3")
        ]
        automotive_options = [
                make_option('--cf', '--configfile', dest='sensor_config_file', default="", type="string", metavar="SENSOR_CONFIG_FILE",
                        help = "Specify Sensor Configuration file that has a list of supported sensor configurations\n"),
                make_option('--c', '--sensorname', dest='sensor_name', default="", type="string", metavar="SENSOR_NAME",
                        help = "Specify Sensor name\n")
        ]
        standard_options = [
                make_option('-v', '--version', dest='version', default=False, action="store_true",
                        help = 'Display version information'),
                make_option('-l', '--list', dest='listTestNames', default=False, action="store_true",
                        help = 'Display list of sanity and conformance test names'),
                make_option('-s', dest='sanity', default=False, action="store_true",
                        help = sanityOptionHelp),
                make_option('-c', dest='conformance', default=False, action="store_true",
                        help = 'Run Imager tests. Use -l option to look at the'
                             + ' list of Imager tests'),
                make_option('-t', dest='test_names', default=None, type="string", action = "append",
                        metavar="TEST_NAME",
                        help = testNameOptionHelp),
                make_option('--lps', '--listconfigs', dest='list_configs', default = False, action='store_true', metavar="LIST_CONFIGS",
                        help = "Prints supported configuration for user selection\nLists all supported modes for all supported sensors\n"),
                make_option('-f', dest='force', default=False, action="store_true",
                        help = 'run the tests without any prompts', metavar="FORCE"),
                make_option('--ts', dest = 'time_stamp_enable', default=False,  action="store_true",
                        help = 'Print time stamp on all nvcs test log.'),
                make_option('-h', '-?', '--help', dest='help', action='store_true', default=False,
                        help = 'print this help message'),
                # Can not have a for loop here.
                # for i in range(0, 8, 1):
                #    make_option('--use_e' + str(i), '--use_e' + str(i), dest='use_e' + str(i), default=False, action="store_true",
                #            help = 'Specify the Exposure Time that needs to be picked up'),
                make_option('--use_e0', dest='use_e0', default=False, action="store_true",
                            help = 'Specifies use of HDR Exposure Time 0'),
                make_option('--use_e1', dest='use_e1', default=False, action="store_true",
                            help = 'Specifies use of HDR Exposure Time 1'),
                make_option('--use_e2', dest='use_e2', default=False, action="store_true",
                            help = 'Specifies use of HDR Exposure Time 2'),
                make_option('--use_e3', dest='use_e3', default=False, action="store_true",
                            help = 'Specifies use of HDR Exposure Time 3'),
                make_option( '--use_e4', dest='use_e4', default=False, action="store_true",
                            help = 'Specifies use of HDR Exposure Time 4'),
                make_option('--use_e5', dest='use_e5', default=False, action="store_true",
                            help = 'Specifies use of HDR Exposure Time 5'),
                make_option('--use_e6', dest='use_e6', default=False, action="store_true",
                            help = 'Specifies use of HDR Exposure Time 6'),
                make_option('--use_e7', dest='use_e7', default=False, action="store_true",
                            help = 'Specifies use of HDR Exposure Time 7'),
                make_option('--use_eall', dest='use_eall', default=False, action="store_true",
                            help = 'Specifies use of all HDR Exposure Time values')
            ]

        advanced_options = [
                make_option('--nv', dest='advanced', action='store_true', default=False,
                        help = 'Enable advanced options.'
                             + ' This will enable options for advanced testing and debugging of tests'),
                make_option('-n', dest='numTimes', default=0, type="int",
                        help = 'Set number of samples to use in select tests.'
                             + ' Applies to \"blacklevel\", \"linearity\", \"gain\", and \"exposure\".'),
                make_option('--numcaptures', dest='numCaptures', default=10, type="int",
                        help = 'Set number of captures to use in select tests. Default %default.'
                             + ' Applies to \"host_sensor\".', metavar="NUM"),
                make_option('--nostaging', dest='stagingOff', default=False, action="store_true",
                        help = 'Do not run any of the staging tests in sanity or conformance suite'
                             + ' Staging tests are ran to provide information internally to qualify new tests'),
                make_option('--noshuffle', dest='noShuffle', action='store_true', default=False,
                        help = 'Do not shuffle capture order'
                             + ' Currently only \"linearity\" test supports this option'),
                make_option('--eL', dest='exposureLow', default=0, type="float",
                        help = 'Set minimum exposure for linearity3'),
                make_option('--eH', dest='exposureHigh', default=0, type="float",
                        help = 'Set maximum expsoure for linearity3.'),
                make_option('--threshold', dest='threshold', default=0, type="float",
                        help = 'Set threshold for test (float).'
                             + ' Currently only \"blacklevel\" test supports this option and it sets'
                             + ' threshold for difference between the maximum and minimum black level'
                             + ' variance'),
                make_option('--width', dest='width', default=0, type="int",
                        help = 'Set width for jpeg_capture output or host_sensor input'
                             + ' Default height used by jpeg_capture is sensor default'
                             + ' Default width used by host_sensor is 2592'),
                make_option('--height', dest='height', default=0, type="int",
                        help = 'Set height for jpeg_capture output or host_sensor input'
                             + ' Default height used by jpeg_capture is sensor default'
                             + ' Default height used by host_sensor is 1944'),
                make_option('--overridespath', dest='overridesPath', default="", type="string", metavar=" ",
                        help = 'Manually specify full system path to overrides file.'),
                make_option('--input', dest='input', default=None, type="string", metavar="FILE",
                        help = 'Set input image filename, default is None for test pattern'),
                make_option('--rsquaredmin', dest='rsquaredmin', default=0.97, type="float",
                        help = "Set minimum passing criteria for R^2 in linearity test. "
                             + "For sensors with good linearity, can get R^2 above 0.90 "
                             + "and close to 1.0; while for some other sensors with relatively "
                             + "poor linearity, can get lower R^2 than 0.90, but shall not be "
                             + "too low like 0.5 either"),
                make_option('--segment', dest = 'linearitySegment', default = None, type = "string",
                        help = "linearity gain range segmentation. This argument is only valid with linearity."
                             + "If the argument is not None, we will parse the gain range used by linearity."
                             + "We will ran multiple linearity based on the number of segmented gain range."
                             + "User must provide AT LEAST 2 segmented value: 1 for the starting dB and 1 for the ending dB"
                             + "Any additional input argument will be the next maxium dB for the linearity test.\n"
                             + "For instance, the gain range is default from 1~72db. If the argument is set to \"1,30\",   "
                             + "We will segment the gain range to 1 set : 1~30. The linearity will run one time.\n"
                             + "If the argument is set to \"1,30,72\". We will segment the gain range to 2 sets:           "
                             + "1~30 dB and 30~72 dB. The linearity will run two times.                                    "
                             + "NOTE:\n"
                             + "*the input argument will be treat as decibel (dB).\n"
                             + "*the input value must be in ascending order and should not less than 0"
                             + "or greater than the alllowed sensor's gain value.\n"),
                make_option('--gainsteps', dest = 'gainsteps', default = None, type = "int",
                        help = "manually set the number of gain step for linearity test. This argument is only valid with"
                             + "linearity test. This value will overwrite the gain step calculated in linearity test."
                             + "The gain steps must be a positive number greater than 0"),
                make_option('--cappedExposure', dest = 'cappedExposure', default=False, action="store_true",
                        help = "The flag to enable custom linearity and gain test for special sensor. In case of the special "
                             + "sensor, the gain can only be altered when exposure is set to capped value. When this flag is "
                             + "set to true, the linearity test will skip exposure production test and use the capped exposure "
                             + "time. The gain test will also use the capped exposure time."),
                make_option('--linearityMode', dest = 'linearityMode', default = [], nargs = 1, type = "choice", action="append",
                        choices =('ALL', 'GAIN', 'EXPOSURE', 'EP'),
                        help = "select the linearity test that will be performed in the linearity test. User may choose"
                                + "one or more modes from the following options: ALL, GAIN, EXPOSURE, EP."),
                make_option('--gainGranularity', dest = 'gainGranularity', default = None, type = "float",
                        help = 'Set the gain step granularity in dB. The gain step will be calculated based on granularity.')]
        mobile_advanced_options = [
                make_option('--gain', dest='utilGain', default=0, type="float",
                        help = 'Set the gain for the capture.'
                             + ' Currently only the \"hdr_ratio\" test supports this option'),
                make_option('--exposure', dest='utilExposure', default=0, type="float",
                        help = 'Set the exposure for the capture.'
                             + ' Currently only the \"hdr_ratio\" test supports this option'),
                make_option('--targetratio', dest='targetRatio', default=None, type="float",
                        help = "Specify the driver-hardcoded ET ratio for use with the\n"
                             + "manual HDR test.  Setting this argument automatically\n"
                             + "switches the HDR test into manual mode."),
                make_option('--target-mode', dest='target_mode', default="", type=str,
                        help = "target mode ('mmap' or 'user') for vi_mode test (default: using both modes)")]

        parser = None
        advance_option_list = None
        if nvcsUtil.isMobile():
            option_list = standard_options + mobile_options
            advance_option_list = advanced_options + mobile_advanced_options
        elif nvcsUtil.isEmbeddedOS():
            option_list = standard_options + automotive_options
            advance_option_list = advanced_options
        else:
            logger.error ("not a valid OS [%s]"%nvcsUtil.getOsName())
            sys.exit(1)

        parser = OptionParser(usage, option_list=option_list + advance_option_list,
                              add_help_option=False,
                              formatter=nvcstestutils.HelpFormatterWithNewLine())

        # make a standard option for error checking if --nv is not specified
        standard_parser = OptionParser(usage, option_list,
                                       add_help_option=False,
                                       formatter=nvcstestutils.HelpFormatterWithNewLine())

        # parse the command line arguments
        (test_options, args) = parser.parse_args()
        # if the linearity list is empty, set ALL by default
        if 0 == len(test_options.linearityMode) :
            test_options.linearityMode.append('ALL')
        if (nvcsUtil.isEmbeddedOS()):
            test_options.useClassicRanges = False
            test_options.disabled_test_names = None
            test_options.imager_id = None
            test_options.ignoreFocuser = False
            test_options.totalTestRuns = 1
            test_options.timer_enable = False
            test_options.sensor_mode = None
        elif (nvcsUtil.isMobile()):
            test_options.sensor_config_file = None
            test_options.sensor_name = None

        # parse the standard command line argument of the --nv is not present
        if(not test_options.advanced):
            (options, test_args) = standard_parser.parse_args()

        if(test_options.help):
            if(test_options.advanced):
                # print help message with advanced options
                parser.print_help()
            else:
                # print help message wihtout advanced options
                standard_parser.print_help()
            sys.exit(0)

        if(test_options.time_stamp_enable):
            logger.timeStampEnable()

        # obtaint the sensor info
        if(test_options.sensor_config_file) :
            sensorProp = SensorProperty(test_options.sensor_config_file)
        else :
            sensorProp = SensorProperty()
        sensorProp.grepSensorInfo()

        if (test_options.listTestNames):
            # print test names

            # print sanity test names
            print("SANITY TEST NAMES:")
            for sanity_test in TestFactory.sanityNameList:
                if (TestFactory.isEnabled(sanity_test)):
                    print("\t%s" % sanity_test)

            # print sanity staging test names
            print("SANITY STAGING TEST NAMES:")
            for staging_test in TestFactory.sanityStagingNameList:
                if (TestFactory.isEnabled(staging_test)):
                    print("\t%s" % staging_test)

            print("")

            # print conformance test names
            print("CONFORMANCE TEST NAMES:")
            for conformance_test in TestFactory.conformanceNameList:
                if (TestFactory.isEnabled(conformance_test)):
                    print("\t%s" % conformance_test)

            # print conformance staging test names
            print("CONFORMANCE STAGING TEST NAMES:")
            for staging_test in TestFactory.conformanceStagingNameList:
                if (TestFactory.isEnabled(staging_test)):
                    print("\t%s" % staging_test)

            print("")

            print("UTILITY TEST NAMES:")
            for utility_test in TestFactory.utilityNameList:
                if (TestFactory.isEnabled(utility_test)):
                    print("\t%s" % utility_test)

            print("")

            sys.exit(0)

        if (test_options.list_configs):
            listConfigs(sensorProp)
            return

        # print version infortion
        nvcstest.printVersionInformation(logger)

        if(test_options.version):
            # Already printed version in previous statement
            sys.exit(0)

        # check if needed directories exist and try to create them
        # if they are not present
        neededDirs = [nvcsUtil.getOutputDir(), nvcsUtil.getInputDir(), nvcsUtil.getSettingsDir()]
        for a_dir in neededDirs:
            if (not os.path.exists(a_dir)):
                try:
                    logger.info("Creating directory: %s" % a_dir)
                    # Set directory permission/mode to 0777
                    mode = stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
                    if (nvcsUtil.createDirSetMode(a_dir, mode) != True):
                        raise ValueError("Error: Could not create directory %s and set mode to %o" % (a_dir, mode))

                except Exception as err:
                    logger.error(err)
                    logger.error("Couldn't create directory :%s...exiting..." % a_dir)
                    sys.exit(1)
            else:
                logger.info("Found directory: %s" % a_dir)

        stagingNamesList = []
        testNamesList = []
        if (test_options.sanity):
            testNamesList = TestFactory.sanityNameList
            stagingNamesList = TestFactory.sanityStagingNameList

        elif (test_options.conformance):
            testNamesList = TestFactory.conformanceNameList
            stagingNamesList = TestFactory.conformanceStagingNameList

        elif (test_options.test_names != None):
            testNamesList = test_options.test_names

        __validateTestNames(testNamesList)

        # create a dictionary for disabled test names
        if (test_options.disabled_test_names is not None):
            for testName in test_options.disabled_test_names:
                # get the test object
                if (TestFactory.hasTest(testName)):
                    TestFactory.disableTest(testName)
                if (testName == "constant_condition"):
                    logger.warning("constant_condition test is disabled")

        modeArg = []
        allMode = False
        modeArg, allMode = multiModeSensorParser(test_options.sensor_mode)

        imagerArg = []
        allImager = False
        imagerArg, allImager = multiModeSensorParser(test_options.imager_id)

        imagerModeComb = []
        imagerModeComb = createImagerModeComb(sensorProp, imagerArg, allImager, modeArg, allMode)
        # skip this part if it's not Automotive project
        configSensorID = []
        configSensorName = []
        configWidth = []
        configHeight = []
        if nvcsUtil.isEmbeddedOS():
            configSensorID, configSensorName,configWidth, configHeight = createSensorIdLUTbyConfigFile(test_options.sensor_config_file)

        if allMode:
            sensorModeList = list(range(len(sensorProp.modeType)))
        else:
            sensorModeList = modeArg

        for modeNumber in sensorModeList:
            if sensorProp.modeType[modeNumber] == "Bayer_WDR_PWL":
                logger.info("Detected WDR PWL at mode {0}".format(modeNumber))

        if (not nvcsUtil.isEmbeddedOS()) and ((None == imagerModeComb) or (0 == len(imagerModeComb))) :
            logger.error("no valid imager sensor and mode combination")
            logger.error("No Camera Module Present! Skipping the test!")
            logger.info("TOTAL TEST RUNS: 0")
            logger.info("TOTAL FAILURES: 0")
            logger.info("TOTAL SKIPPED TESTS: 0")
            sys.exit(0)
        else :
            for testrun in range(0, test_options.totalTestRuns):
                if (test_options.stagingOff == False):
                    for testName in stagingNamesList:
                        # get the test object
                        try:
                            # if the test is enabled, execute the test
                            if (TestFactory.isEnabled(testName)):
                                numStagingTests = numStagingTests + 1

                                testOb = TestFactory.getTestObject(testName, test_options, logger, sensorSetting)
                                retVal = testOb.run()

                                if (retVal == nvcstest.NvCSTestResult.SUCCESS):
                                    logger.info("STAGE TEST RESULT: PASS\n")
                                elif (retVal == nvcstest.NvCSTestResult.SKIPPED):
                                    logger.info("STAGE RESULT: SKIP\n")
                                    numStagingSkippedTests = numStagingSkippedTests + 1
                                else:
                                    logger.info("STAGE RESULT: FAIL\n")
                                    numStagingFailures = numStagingFailures + 1

                        except Exception as err:
                            print(err)
                            numStagingFailures = numStagingFailures + 1

                for testName in testNamesList:
                    # get the test object
                    try:
                        # if the test is enabled, execute the test
                        if (TestFactory.isEnabled(testName)):
                            test_start_time = time.time()
                            # special test case; these test case(s) does not care whether different sensor mode
                            # has been selected
                            tmpImagerModeComb = [[0,0]]
                            sensorSetting = None
                            if not (nvcsUtil.isEmbeddedOS()):
                                if (testName != "pfp_streaming_file"):
                                    tmpImagerModeComb = imagerModeComb

                            for modeLenComb in tmpImagerModeComb :
                                sub_test_start_time = time.time()
                                numTests = numTests + 1

                                # overwrite the sensor ID and sensor mode in the options. the new value will be the
                                # currently selected sensor ID and source Index from the LUT
                                if not (nvcsUtil.isEmbeddedOS()):
                                    sourceIdx = modeLenComb[1]
                                    test_options.imager_id = modeLenComb[0] #first index is the sensor ID
                                    test_options.sensor_mode = str(sourceIdx)
                                    propertyIndex = getSensorPropIndex(sensorProp, modeLenComb[0], modeLenComb[1])
                                    if (None == propertyIndex):
                                        logger.error("couldn't not find appropriate property index for sensor[%d] and mode[%d]"%(modeLenComb[0], modeLenComb[1]))
                                        sys.exit(1)
                                    test_options.sensor_name = sensorProp.nvctCharBufferUniqueName[propertyIndex].getBuffer()
                                    sensorSetting = SensorSetting(sensorProp.nvctSensorMode[propertyIndex].Resolution.width,
                                                                  sensorProp.nvctSensorMode[propertyIndex].Resolution.height,
                                                                  sourceIdx,
                                                                  modeLenComb[0],
                                                                  sensorProp.nvctCharBufferUniqueName[propertyIndex].getBuffer(),
                                                                  sensorProp.modeType[propertyIndex],
                                                                  sensorProp.dynamicPixelBitDepth[propertyIndex],
                                                                  sensorProp.csiPixelBitDepth[propertyIndex],
                                                                  sensorProp.nvctSensorMode[propertyIndex].FrameRate)
                                # NOTE: for now, automotive does not support source index; so we cannot support
                                # multiple sensor mode for automotive. Therefore, we will just use [0,0] as temp.
                                # combo (1 sensor and 1 mode)
                                else :
                                    configIdx = -1
                                    found = False
                                    for deviceName in configSensorName:
                                        configIdx += 1
                                        if deviceName == test_options.sensor_name:
                                            found = True
                                            break;
                                    if found:
                                        test_options.sensor_mode = 0 # only one mode for automotive
                                        test_options.imager_id = int(configSensorID[configIdx])
                                        test_options.width = int(configWidth[configIdx])
                                        test_options.height = int(configHeight[configIdx])
                                        sensorSetting = SensorSetting(test_options.width, test_options.height,
                                                                  test_options.sensor_mode, test_options.imager_id, test_options.sensor_name)
                                    else:
                                        logger.error("Couldn't not find proper configuration of sensor[%s]...exiting..." % test_options.sensor_name)
                                        sys.exit(1)

                                testOb = TestFactory.getTestObject(testName, test_options, logger, sensorSetting)
                                retVal = testOb.run()

                                logger.info("Time consumed by %s test: %3.2f seconds" % (testName, (time.time() - sub_test_start_time)))
                                if (retVal == nvcstest.NvCSTestResult.SUCCESS):
                                    logger.info("RESULT: PASS\n")
                                elif (retVal == nvcstest.NvCSTestResult.SKIPPED):
                                    logger.info("RESULT: SKIP\n")
                                    numSkippedTests = numSkippedTests + 1
                                else:
                                    logger.info("RESULT: FAIL\n")
                                    numFailures = numFailures + 1

                    except Exception as err:
                        print(err)
                        numFailures = numFailures + 1
                        logger.info("Time consumed by %s test: %3.2f seconds" % (testName, (time.time() - test_start_time)))
                        logger.info("RESULT: FAIL\n")

            logger.setClientName("")

            if (numFailures == 0):
                RunSuccessStr = "PASS"
            else:
                RunSuccessStr = "FAIL"

            logger.info("Time consumed by all tests: %3.2f seconds" % (time.time() - start_time))
            logger.info("=================================================================")
            logger.dumpWarnings("Accumulated WARNING messages from test run:")
            logger.dumpErrors("Accumulated ERROR messages from test run:")
            logger.info("=================================================================")
            nvcstest.printVersionInformation(logger)
            logger.info("=================================================================")
            if (numStagingTests > 0):
                logger.info("(STAGE RUNS DO NOT AFFECT NVCS FINAL RESULT)")
                logger.info("STAGE RUNS: %d" % numStagingTests)
                logger.info("STAGE FAILURES: %d" % numStagingFailures)
                logger.info("STAGE SKIPPED TESTS: %d" % numStagingSkippedTests)
                logger.info("=================================================================")
            logger.info("TOTAL TEST RUNS: %d" % numTests)
            logger.info("TOTAL FAILURES: %d" % numFailures)
            logger.info("TOTAL SKIPPED TESTS: %d" % numSkippedTests)
            logger.info("=================================================================")
            logger.info("NVCS Final Result: %s" % (RunSuccessStr))
            logger.info("=================================================================")

        if (numFailures > 0):
            sys.exit(1)


def getSensorPropIndex(sensorProp,sensorID, modeID) :
    for i in range(0, sensorProp.numSupportedSensorEntries):
        if (sensorProp.sensorModeIndex[i] == modeID) and (sensorProp.sourceIndex[i] == sensorID) :
            return i
    return None;

def listConfigs(sensorProp):

    str1 = ''
    str2 = ''
    uniqueNameLength = 0
    modeTypeLength = 0
    nameLength = 0
    moduleNameLength = 0
    positionLength = 0
    descrLength = 0

    # Get all sensor properties and keep them around in a list
    # The reason we do it this way is to print them all out at the end
    # to avoid driver debug spew to interfere with the prints.
    #
    for i in range(0, sensorProp.numSupportedSensorEntries):
        uniqueNameLength = max(len(sensorProp.nvctCharBufferUniqueName[i].getBuffer()), uniqueNameLength)
        modeTypeLength = max(len(sensorProp.modeType[i]), modeTypeLength)
        nameLength = max(len(sensorProp.nvctCharBufferName[i].getBuffer()), nameLength)
        moduleNameLength = max(len(sensorProp.nvctCharBufferModuleName[i].getBuffer()), moduleNameLength)
        positionLength = max(len(sensorProp.nvctCharBufferModuleName[i].getBuffer()), positionLength)
        descrLength = max(len(sensorProp.nvctCharSensorDescription[i].getBuffer()), descrLength)

    #
    # Construct the header
    #
    if (nvcsUtil.isEmbeddedOS()):
        str1 = 'Number of supported sensor entries ' + str(sensorProp.numSupportedSensorEntries) + '\n' \
               + 'Index'.ljust(7) \
               + ' '.ljust(10) + 'Uniquename'.ljust(20) \
               + ' '.ljust(20) + 'Description'.ljust(10) \
               + '\n'
    else:
        #
        # Add only the string headers that have non-null in all entries
        #
        str1 = 'Number of supported sensor entries ' + str(sensorProp.numSupportedSensorEntries) + '\n' \
                    + 'Entry'.ljust(7) + 'Source'.ljust(7) + 'Mode'.ljust(6)
        if (uniqueNameLength > 0):
            pad = (max(len('Uniquename'), uniqueNameLength) - len('Uniquename')) & ~1
            str1 = str1 + ' '.ljust(pad // 2) + 'Uniquename' + ' '.ljust(pad // 2)

        str1 = str1 + ' '.ljust(2) + 'Resolution' + ' '.ljust(2) \
                    + ' '.ljust(0) + 'FR' + ' '.ljust(1) \
                    + 'BitDepth' + ' '.ljust(1)

        if (modeTypeLength > 0):
            pad = (max(len('Mode'), modeTypeLength) - len('Mode')) & ~1
            str1 = str1 + ' '.ljust(pad // 2) + 'Mode' + ' '.ljust(pad // 2)

        if (nameLength > 0):
            pad = (max(len('Name'), nameLength) - len('Name')) & ~1
            str1 = str1 + ' '.ljust(pad // 2) + 'Name' + ' '.ljust(pad // 2)

        if (moduleNameLength > 0):
            pad = (max(len('ModuleName'), moduleNameLength) - len('ModuleName')) & ~1
            str1 = str1 + ' '.ljust(pad // 2) + 'ModuleName' + ' '.ljust(pad // 2)

        if (positionLength > 0):
            pad = (max(len('Position'), positionLength) - len('Position')) & ~1
            str1 = str1 + ' '.ljust(pad) + 'Position' + ' '.ljust(pad // 2)

        if (descrLength > 0):
            pad = (max(len('Description'), descrLength) - len('Description')) & ~1
            str1 = str1 + ' '.ljust(pad) + 'Description' + ' '.ljust(pad // 2)
        str1 = str1 + '\n'
        str1 = str1 + "Index  Index  Index" + ' '.ljust(44) + "CSI Dyn"

    #
    # Now run through the lists and display them
    #
    for i in range(sensorProp.numSupportedSensorEntries):
        if (nvcsUtil.isEmbeddedOS()):
            str2 = str2 + str(i).rjust(3) + ' '.ljust(3) + str(sensorProp.nvctCharBufferUniqueName[i].getBuffer()).ljust(40) \
                   + ' '.ljust(2) + str(sensorProp.nvctCharSensorDescription[i].getBuffer()).ljust(30) + '\n'
        else:
            str2 = str2 + str(i).rjust(3) + str(sensorProp.sourceIndex[i]).rjust(7) + str(sensorProp.sensorModeIndex[i]).rjust(6) + ' '.ljust(2)

            if (uniqueNameLength > 0):
                pad = (max(len('Uniquename'), len(sensorProp.nvctCharBufferUniqueName[i].getBuffer())) - len(sensorProp.nvctCharBufferUniqueName[i].getBuffer())) & ~1
                str2 = str2 + ' '.ljust(pad // 2) + str(sensorProp.nvctCharBufferUniqueName[i].getBuffer()).ljust(uniqueNameLength) + ' '.ljust(pad // 2)

            str2 = str2 + ' '.ljust(3) + str(sensorProp.nvctSensorMode[i].Resolution.width).ljust(4) \
                    + 'x' + str(sensorProp.nvctSensorMode[i].Resolution.height).ljust(4) + ' '.ljust(2) \
                    + ' '.ljust(2) + str(int(round(sensorProp.nvctSensorMode[i].FrameRate))).ljust(3) \
                    + ' '.ljust(0) + str(sensorProp.csiPixelBitDepth[i]) + ' '.ljust(1) \
                    + ' '.ljust(0) + str(sensorProp.dynamicPixelBitDepth[i]) + ' '.ljust(1)

            if (modeTypeLength > 0):
                pad = (max(len('Mode'), len(sensorProp.modeType[i])) - len(sensorProp.modeType[i])) & ~1
                str2 = str2 + ' '.ljust(pad // 2 + 1) + sensorProp.modeType[i].ljust(modeTypeLength) + ' '.ljust(pad // 2)

            if (nameLength > 0):
                pad = (max(len('Name'), len(sensorProp.nvctCharBufferName[i].getBuffer())) - len(sensorProp.nvctCharBufferName[i].getBuffer())) & ~1
                str2 = str2 + ' '.ljust(pad // 2) + str(sensorProp.nvctCharBufferName[i].getBuffer()).ljust(nameLength) + ' '.ljust(pad // 2)

            if (moduleNameLength > 0):
                pad = (max(len('ModuleName'), len(sensorProp.nvctCharBufferModuleName[i].getBuffer())) - len(sensorProp.nvctCharBufferModuleName[i].getBuffer())) & ~1
                str2 = str2 + ' '.ljust(pad // 2) + str(sensorProp.nvctCharBufferModuleName[i].getBuffer()).ljust(moduleNameLength) + ' '.ljust(pad // 2)

            if (positionLength > 0):
                pad = (max(len('Position'), len(sensorProp.nvctCharBufferPos[i].getBuffer())) - len(sensorProp.nvctCharBufferPos[i].getBuffer())) & ~1
                str2 = str2 + ' '.ljust(pad // 2) + str(sensorProp.nvctCharBufferPos[i].getBuffer()).ljust(positionLength) + ' '.ljust(pad // 2)

            if (descrLength > 0):
                pad = (max(len('Description'), len(sensorProp.nvctCharSensorDescription[i].getBuffer())) - len(sensorProp.nvctCharSensorDescription[i].getBuffer())) & ~1
                str2 = str2 + ' '.ljust(pad // 2) + str(sensorProp.nvctCharSensorDescription[i].getBuffer()).ljust(descrLength) + ' '.ljust(pad // 2)

            str2 = str2 + '\n'
    #
    # Print assembled strings now
    #
    print(str1)
    print(str2)
    print('\n')

def __validateTestNames(testNamesList):
    success = True
    for testName in testNamesList:
        if (TestFactory.hasTest(testName) != True):
            success = False
            print("ERROR: Incorrect test name: %s" % testName)

    if (success == False):
        sys.exit(1)

if __name__ == '__main__':
    main()
