# Copyright (c) 2012-2020, NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#

from __future__ import division
from __future__ import print_function

try:
    input = raw_input
except NameError:
    pass

import traceback
import os.path
import nvrawfile
import nvrawfileV3
import shutil
import math
import time
import os
import stat

import nvraw_v3
import nvcamera
import nvcstestutils
import nvcstestsystem
import nvcameraimageutils
import sys
nvcscommonPath = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'common')
nvcscommonutilsPath = os.path.join(nvcscommonPath, 'nvcsCommonUtils.py')
sys.path.append(nvcscommonPath)
from nvcstestutils import NvCSTestResult
from nvcsCommonUtils import NVCSutil

nvcsUtil = None
info = None

class GraphState(object):
    STOPPED = 1
    PAUSED = 2
    RUNNING = 3
    CLOSED = 4

class GraphType(object):
    JPEG = 1
    RAW = 2
    HOST_SENSOR = 3

class NvCSTestException(Exception):
    "NvCSTest Exception Class"

    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class NvCSTestGraph(object):
    "NvCSTest Graph wrapper class"

    _imagerID = 0
    _state = GraphState.CLOSED
    _stillWidth = 0
    _stillHeight = 0
    _previewWidth = 0
    _previewHeight = 0
    _hostSensorWidth = 0
    _hostSensorHeight = 0
    _graphType = GraphType.JPEG
    _previewModeNumber=-1
    _stillModeNumber=-1
    _obGraph = None
    logger = None
    # Options from command line
    _options = None

    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    def __init__(self, options, graphType=GraphType.JPEG):
        self.graphType = graphType
        self._options = options

        self._obGraph = nvcamera.Graph()
        self._state = GraphState.CLOSED

        # OptionParser has already constrainted the nvRawVersion to v2 or v3
        self._nvRawVersion = int(options.nvraw_version[1])
        self._obGraph.setNvRawVersion(self._nvRawVersion)

        self.logger = nvcstestutils.Logger()
        if nvcsUtil.isAndroid():
            self.logger.info("running \"stayon\"")
            os.system("svc power stayon true && echo main >/sys/power/wake_lock")

    def setPreviewParams(self, width = 0, height = 0, modeNumber=-1):
        self._previewWidth = width
        self._previewHeight = height
        self._previewModeNumber = modeNumber

    def setStillParams(self, width = 0, height = 0, modeNumber=-1):
        self._stillWidth = width
        self._stillHeight = height
        self._stillModeNumber = modeNumber

    def setHostSensorParams(self, width, height):
        self._hostSensorWidth = width
        self._hostSensorHeight = height

    #def setImager(self, imagerID):
    #    self._imagerID = imagerID
    #    self._capture_config = ""

    def setSensorConfigFile(self, sensor_config_file):
        self._sensor_config_file = sensor_config_file
        # print "nvcstestcore: setSensorConfigFile(" + sensor_config_file + ")"

    def setImager(self, imagerID, sensor_name):
        self._imagerID = imagerID
        self._sensor_name = sensor_name
        # print 'imagerID ' + str(imagerID) + ' sensor_name ' + str(sensor_name)

    def setGraphType(self, graphType):
        self._graphType = graphType

    def createAndRunGraph(self):
        if (self._state == GraphState.CLOSED):
            # Reinstate the nvraw version after a reset
            self._obGraph.setNvRawVersion(self._nvRawVersion)

            err = self._obGraph.setSensorConfigFile(self._sensor_config_file)
            if (err != nvcamera.NvSuccess):
                raise NvCSTestException("setSensorConfigFile() failed. File %s not found or is corrupt" % self._sensor_config_file)

            if(self._graphType == GraphType.HOST_SENSOR):
                self._obGraph.setImager("host", self._sensor_name)
            else:
                self._obGraph.setImager(self._imagerID, self._sensor_name)

            if(self._graphType != GraphType.HOST_SENSOR):
                self._obGraph.preview(self._previewWidth, self._previewHeight, self._previewModeNumber)

            graphTypeString = self.getGraphTypeString()
            if(graphTypeString ==  None):
                raise ValueError("Invalid graph type")

            self._obGraph.still(self._stillWidth, self._stillHeight, graphTypeString, self._stillModeNumber)

            #
            # Check if HDR and multiple exposures are supported
            # If so, we need to construct the exposureMode and call
            # setExposureMode
            #
            bMultiExpos = nvcstestsystem.isMultipleExposuresSupported()

            (ret, numExposures, numGains, \
                supportedMode, currentMode, bHdrChangeable) = self.getHDRInfo()

            if (ret != NvCSTestResult.SUCCESS):
                self.logger.error("Error: getHDRInfo() returned error")
                return NvCSTestResult.ERROR

            exposureMode = nvcstestsystem.getMultipleExposureMode(numExposures, self._options, self.logger)
            if (exposureMode == -1):
                self.logger.error("getMultipleExposureMode: Command line options error")
                return NvCSTestResult.ERROR

            if (bMultiExpos):
                self._obGraph.setExposureMode(exposureMode)

            self._obGraph.run()

            self._state = GraphState.RUNNING
            return nvcamera.NvSuccess
        else:
            self.logger.error("Couldn't create and run the graph")
            raise NvCSTestException("Graph is in invalid state: %s" % self.getGraphStateString())

    def stopAndDeleteGraph(self):
        if(self._state == GraphState.RUNNING):
            self._obGraph.stop()
            self._state = GraphState.STOPPED
        if(self._state == GraphState.STOPPED):
            self._obGraph.close()
            self._state = GraphState.CLOSED

    def getGraphTypeString(self):
        if(self._graphType == GraphType.JPEG or self._graphType == GraphType.HOST_SENSOR):
            return "Jpeg"
        elif(self._graphType == GraphType.RAW):
            return "Bayer"
        else:
            return None

    def getGraphType(self):
        return self._graphType

    def getGraphStateString(self):
        if(self._state == GraphState.CLOSED):
            return "CLOSED"
        elif(self._state == GraphState.PAUSED):
            return "PAUSED"
        elif(self._state == GraphState.RUNNING):
            return "RUNNING"
        else:
            return "STOPPED"

    def getGraphState(self):
        return self._state

    def getCurrentPreviewMode(self):
        return self._obGraph.getCurrentPreviewMode()

    def getCurrentStillMode(self):
        return self._obGraph.getCurrentStillMode()

    def setNvRawVersion(self, version):
        self._nvRawVersion = version
        return self._obGraph.setNvRawVersion(version)

    def getHDRInfo(self):

        ret = NvCSTestResult.SUCCESS
        exposureCount = 0
        analogGainCount = 0
        supportedMode = nvcamera.NvHdrMode_Disabled
        currentMode = nvcamera.NvHdrMode_Disabled
        bHdrChangeable = False
        capabilities = nvcamera.NvHdrCapabilities()
        capabilities = self._obGraph.getHdrCapabilities(capabilities)

        if (capabilities.bHdrSupported):
            for i in range(nvcamera.NvHdrMode_Last):
                et_count = capabilities.getNumExposuresAt(i)
                sag_count = capabilities.getNumSensorAnalogGainsAt(i)

                if (et_count > 0):
                     exposureCount = et_count
                if (sag_count > 0):
                      analogGainCount = sag_count
                if (exposureCount > 0 or analogGainCount > 0):
                   supportedMode = i;
                   break;

        currentMode = self._obGraph.getHdrCurrentMode()

        if (exposureCount == 0):
            exposureCount = 1
        if (analogGainCount == 0):
            analogGainCount = 1

        bHdrChangeable = capabilities.bHdrChangeable

        self.logger.info("getHdrCapabilities: exposureCount %d gainCount %d " \
              "currentMode %d bHdrChangeable %d " \
              % (exposureCount, analogGainCount, currentMode, bHdrChangeable))

        if (exposureCount != analogGainCount):
            self.logger.error("Error: getHDRInfo: Number of Gains (%d) is different from Number of Exposures (%d)" % \
                              (analogGainCount, exposureCount))
            ret = NvCSTestResult.ERROR

        if (exposureCount > nvcamera.HDR_MAX_EXPOSURES or \
                analogGainCount > nvcamera.HDR_MAX_EXPOSURES):
            self.logger.error("Error: getHDRInfo: exposure count or analog gain count value "
                "is > than max supported value: %d" % nvcamera.HDR_MAX_EXPOSURES)
            self.logger.error("exposure count: %d, analog gain count: %d" % \
                              (exposureCount, analogGainCount))
            ret = NvCSTestResult.ERROR

        return (ret, exposureCount, analogGainCount, supportedMode, currentMode, bHdrChangeable)



class NvCSTestCamera(object):
    _obGraph = None
    _obCamera = None
    _isPreviewRunning = False
    logger = None
    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    def __init__(self, obGraph):
        if(obGraph == None):
            raise ValueError("Graph is not open")
        self._obGraph = obGraph
        self._obCamera = nvcamera.Camera()
        self.logger = nvcstestutils.Logger()

    # redirect the setAttr call to nvcamera.Camera object
    def setAttr(self, attribute, value):
        self._obCamera.setAttr(attribute, value)

    # redirect the getAttr call to nvcamera.Camera object
    def getAttr(self, attribute):
        return self._obCamera.getAttr(attribute)

    # lock Auto Algs. Preview has to be started by the user.
    def lockAutoAlgs(self):
        self._obCamera.halfpress(10000)
        self._obCamera.waitForEvent(12000, nvcamera.CamConst_ALGS)

    # unlock Auto Algs
    def unlockAutoAlgs(self):
        self._obCamera.hp_release()

    # redirect the setRawImage call to nvcamera Camera object
    def setRawImage(self, header, pixelData, iteration):
        self._obCamera.setRawImage(header, pixelData, iteration)

    def isConcurrentRawCaptureSupported(self):
        retVal = True
        try:
            self._obCamera.setAttr(nvcamera.attr_concurrentrawdumpflag, 7)
        except nvcamera.NvCameraException as err:
            retVal = False
        return retVal

    def isFocuserSupported(self):
        retVal = True
        try:
            physicalRange = self._obCamera.getAttr(nvcamera.attr_focuspositionphysicalrange)
        except nvcamera.NvCameraException as err:
            if (err.value == nvcamera.NvError_NotSupported):
                self.logger.info("focuser is not supported")
                retVal = False
            else:
                print(err.value)
                raise
        else:
            if (physicalRange[0] == physicalRange[1]):
                self.logger.info("focuser is not present")
                retVal = False
        return retVal

    def captureRAWImage(self, imageName, needHalfPress=False):
        self.logger.debug("Capturing RAW image: %s" % imageName)
        graphType = self._obGraph.getGraphType()
        if nvcsUtil.isEmbeddedOS():
            # always set half press to false in automotive mode
            needHalfPress = False
        if(graphType == GraphType.RAW):
            if(needHalfPress):
                self._obCamera.halfpress(10000)
                self._obCamera.waitForEvent(12000, nvcamera.CamConst_ALGS)

            self._obCamera.still(imageName)
            self._obCamera.waitForEvent(12000, nvcamera.CamConst_CAP_READY, nvcamera.CamConst_CAP_FILE_READY)
            if(needHalfPress):
                self._obCamera.hp_release()
        else:
            self.logger.error("Can't capture RAW image with %s graph" %
                              self._obGraph.getGraphTypeString())
            raise NvCSTestException("Can't capture RAW image with %s graph" %
                                     self._obGraph.getGraphTypeString())
        self.printCaptureAttributes()

    def captureConcurrentJpegAndRawImage(self, imageName, needHalfPress=True):
        # determine the jpeg and raw filepaths
        jpegPath = imageName
        (fileName, ext) = os.path.splitext(jpegPath)
        rawPath = fileName + ".nvraw"

        self.logger.debug("Capturing concurrent RAW and jpeg images:\n    %s\n    %s" % (rawPath, jpegPath))

        graphType = self._obGraph.getGraphType()
        if(graphType == GraphType.JPEG):
            self.logger.debug("Setting concurrent raw dump flag to 7")
            self._obCamera.setAttr(nvcamera.attr_concurrentrawdumpflag, 7)
            self._obCamera.setAttr(nvcamera.attr_pauseaftercapture, 1)

            # remove old raw+jpeg files
            if os.path.exists(jpegPath):
                self.logger.info("removing old %s file" % jpegPath)
                os.remove(jpegPath)
            if os.path.exists(rawPath):
                self.logger.info("removing old %s file" % rawPath)
                os.remove(rawPath)

            # capture an image
            self.captureJpegImage(jpegPath, needHalfPress)

            if os.path.exists(jpegPath) and os.path.exists(rawPath):
                self.logger.info("Concurrent RAW and jpeg capture successful")
            else:
                if not os.path.exists(jpegPath):
                    self.logger.error("Jpeg file %s does not exist" % jpegPath)
                if not os.path.exists(rawPath):
                    self.logger.error("Raw file %s does not exist" % rawPath)
                self.logger.error("Couldn't capture concurrent RAW and jpeg")
                raise NvCSTestException("Couldn't capture concurrent RAW and jpeg")
        else:
            self.logger.error("Can't capture concurrent RAW and jpeg image with %s graph" %
                              self._obGraph.getGraphTypeString())
            raise NvCSTestException("Can't capture concurrent RAW and jpeg image with %s graph" %
                                    self._obGraph.getGraphTypeString())
        self.printCaptureAttributes()

    def captureJpegImage(self, imageName, needHalfPress=True):
        self.logger.debug("Capturing jpeg image: %s" % imageName)
        graphType = self._obGraph.getGraphType()

        if(graphType == GraphType.JPEG):
            if(needHalfPress):
                self._obCamera.halfpress(10000)
                self._obCamera.waitForEvent(12000, nvcamera.CamConst_ALGS)
            else:
                self.logger.info("Half Press disabled, sleep for 1000 ms")
                time.sleep(1000 / 1000)
            self._obCamera.still(imageName)
            self._obCamera.waitForEvent(12000, nvcamera.CamConst_CAP_READY, nvcamera.CamConst_CAP_FILE_READY)
            if(needHalfPress):
                self._obCamera.hp_release()
        elif(graphType == GraphType.HOST_SENSOR):
            self._obCamera.still(imageName)
            self._obCamera.waitForEvent(12000, nvcamera.CamConst_CAP_READY, nvcamera.CamConst_CAP_FILE_READY)
        else:
            self.logger.error("Can't capture jpeg image with %s graph" %
                              self._obGraph.getGraphTypeString())
            raise NvCSTestException("Can't capture jpeg image with %s graph" %
                                    self._obGraph.getGraphTypeString())
        self.printCaptureAttributes()

    def startPreview(self):
        if(not self._isPreviewRunning):
            self._obCamera.startPreview()
            self._obCamera.waitForEvent(12000, nvcamera.CamConst_FIRST_PREVIEW_FRAME)
            self._isPreviewRunning = True

    def stopPreview(self):
        if(self._isPreviewRunning):
            self._obCamera.stopPreview()
            self._obCamera.waitForEvent(12000, nvcamera.CamConst_PREVIEW_EOS)
            self._isPreviewRunning = False

    def getHdrCapabilities(self, hdrCapabilities):
        return self._obCamera.getHdrCapabilities(hdrCapabilities)

    def enableHdr(self, hdrMode):
        return self._obCamera.enableHdr(hdrMode)

    def getHdrCurrentMode(self):
        return self._obCamera.getHdrCurrentMode()

    def getDctCapabilities(self, dctCapabilities):
        return self._obCamera.getHdrCapabilities(dctCapabilities)

    def PFP_enable(self, enable):
        self._obCamera.PFP_enable(enable)

    def PFP_loadFile(self, pFilename):
        self._obCamera.PFP_loadFile(pFilename)

    def PFP_dumpFile(self, pFilename):
        self._obCamera.PFP_dumpFile(pFilename)

    def PFP_addFrameProperty(self, frameNumber, propertyNumber, camProperty):
        self._obCamera.PFP_addFrameProperty(frameNumber, propertyNumber, camProperty)

    def PFP_addFrameProperty(self, frameNumber, propertyNumber, camProperty):
        self._obCamera.PFP_addFrameProperty(frameNumber, propertyNumber, camProperty)

    def PFP_removeProperty(self, frameNumber, propertyNumber):
        self._obCamera.PFP_removeProperty(frameNumber, propertyNumber)

    def PFP_removeFrame(self, frameNumber):
        self._obCamera.PFP_removeFrame(frameNumber)

    def PFP_removeAll(self):
        self._obCamera.PFP_removeAll()

    def PFP_setFrameLoopCount(self, count):
        self._obCamera.PFP_setFrameLoopCount(count)

    def getCamPropertyObject(self, attr, value):
        return self._obCamera.getCamPropertyObject(attr, value)

    def setStreamingParameters(self, streamingParams):
        return self._obCamera.setStreamingParameters(streamingParams)

    def getStreamingStats(self, streamingStats):
        return self._obCamera.getStreamingStats(streamingStats)

    def setExposureMode(self, exposureMode):
        return self._obCamera.setExposureMode(exposureMode)

    def printCaptureAttributes(self):
        exposureTimes = self._obCamera.getAttr(nvcamera.attr_exposuretime)
        sensorAnalogGains = self._obCamera.getAttr(nvcamera.attr_sensoranaloggain)
        mode = self.getHdrCurrentMode()

        if mode == nvcamera.NvHdrMode_MobileCamera2:
            self.logger.info("WDR PWL capture detected")

            dynamicRangeExposureCount = min(len(exposureTimes), len(sensorAnalogGains))
            for i in range(dynamicRangeExposureCount):
                self.logger.info("Dynamic Range Exposure [{0}]: Exposure Time = {1}, Sensor Gain = {2}".format(
                    i, exposureTimes[i], sensorAnalogGains[i]))

class NvCSTestBase(object):
    "NvCSTest Base Class"

    testID = None
    obCamera = None
    obGraph = None
    logger = None
    nvrf = None
    options = None
    testDir = None
    sensorSetting = None

    def __init__(self, options, logger,  testID=None, sensorSetting = None):
        self.testID = testID
        self.obGraph = NvCSTestGraph(options)
        self.obCamera = NvCSTestCamera(self.obGraph)
        self.testDir = nvcsUtil.getLogPath()
        self.testDir = os.path.join(self.testDir, testID)
        self.logger = logger
        self.logger.setClientName(testID)
        self.nvrf = nvcstestutils.NvCSRawFile()
        self.sensorSetting = sensorSetting

    def run(self, args=None):
        retVal = 0
        try:
            self.logger.info("############################################")
            self.logger.info("Running the %s test..." % self.testID)
            self.logger.info("############################################")
            if (self.sensorSetting is not None) :
                try:
                    self.obGraph.setImager(self.sensorSetting.imager_id,self.sensorSetting.imager_name)
                except nvcamera.NvCameraException as err:
                    if (err.value == nvcamera.NvError_ModuleNotPresent):
                        self.logger.info("Camera sensor not found: %d" % self.sensorSetting.imager_id)
                        self.logger.info("Skipping the %s test..." % self.testID)
                        return NvCSTestResult.SKIP

                self.obGraph.setPreviewParams(self.sensorSetting.width,
                                              self.sensorSetting.height,
                                              self.sensorSetting.sensor_mode)
                self.obGraph.setStillParams(self.sensorSetting.width,
                                            self.sensorSetting.height,
                                            self.sensorSetting.sensor_mode)
            else : # use default value
                sensorMode = 0
                if (None != self.options.sensor_mode) :
                    if isinstance(self.options.sensor_mode, int) :
                        sensorMode = self.options.sensor_mode
                    elif (1 <= len(self.options.sensor_mode)) :
                        if self.options.sensor_mode[0].isdigit() :
                            sensorMode = int(self.options.sensor_mode[0])
                try:
                    self.obGraph.setImager(self.options.imager_id, self.options.sensor_name)
                except nvcamera.NvCameraException as err:
                    if (err.value == nvcamera.NvError_ModuleNotPresent):
                        self.logger.info("Camera sensor not found: %d" % self.options.imager_id)
                        self.logger.info("Skipping the %s test..." % self.testID)
                        return NvCSTestResult.SKIP

                self.obGraph.setPreviewParams(self.options.width,
                                              self.options.height,
                                              sensorMode)
                self.obGraph.setStillParams(self.options.width,
                                            self.options.height,
                                            sensorMode)

            if(self.needAutoGraphSetup()):
                self.setupGraph()
                retVal = self.obGraph.createAndRunGraph()
                if (retVal != nvcamera.NvSuccess):
                    self.logger.error("createAndRunGraph() failed")
                    return retVal

            retVal = self.setupTest()
            if (retVal != NvCSTestResult.SUCCESS):
                self.logger.error("Test is not setup to run")
                self.cleanupTest()
                return retVal

            # create test specific dir
            if(os.path.exists(self.testDir)):
                shutil.rmtree(self.testDir)

            # Set file permission to 0777
            mode = stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
            if (nvcsUtil.createDirSetMode(self.testDir, mode) != True):
                raise ValueError("Error: Could not create directory %s and set mode to %o" % (self.testDir, mode))

            retVal = self.runPreTest()
            if (retVal != NvCSTestResult.SUCCESS):
                self.cleanupTest()
                return retVal

            retVal = self.runTest(args)
            if (retVal != NvCSTestResult.SUCCESS):
                self.cleanupTest()
                return retVal

            retVal = self.runPostTest()
            if (retVal != NvCSTestResult.SUCCESS):
                self.cleanupTest()
                return retVal

            self.obGraph.stopAndDeleteGraph()
            return retVal

        except Exception as err:
            self.logger.error("TEST FAILURE: %s" % self.testID)
            self.logger.error("Error: %s" % str(err))
            traceback.print_exc()
            self.obGraph.stopAndDeleteGraph()
            raise

        return retVal

    def confirmPrompt(self, promptString):
        if(self.options.force == False):
            if(promptString != ''):
                self.logger.info("%s" % promptString)
            # ask user about the confirmation
            ans = input("Press Enter or enter comments when the test setup is ready:")

            if (ans != ''):
                self.logger.info('User comments: %s' % ans)

        return True

    def needTestSetup(self):
        return False

    def getSetupString(self):
        return ''

    def needAutoGraphSetup(self):
        return True

    def setupTest(self):
        retVal = NvCSTestResult.SUCCESS
        if((self.options.force == False) and self.needTestSetup()):
            self.obCamera.startPreview()
            setupString = self.getSetupString()

            if(not self.confirmPrompt(setupString)):
                retVal = NvCSTestResult.ERROR
            self.obCamera.stopPreview()
        return retVal

    def cleanupTest(self):
        self.obGraph.stopAndDeleteGraph()

    def runTest(self, args=None):
        return NvCSTestResult.SUCCESS

    def runPreTest(self, args=None):
        return NvCSTestResult.SUCCESS

    def runPostTest(self, args=None):
        return NvCSTestResult.SUCCESS

    def setupGraph(self):
        return NvCSTestResult.SUCCESS

    def failIfAohdrEnabled(self):
        retVal = True
        aohdrEnabled = 0
        try:
            aohdrEnabled = self.obCamera.getAttr(nvcamera.attr_enableaohdr)
        except:
            self.logger.info("AOHDRenabled query failed.  Assuming aohdr off and proceeding with test.")
        if (aohdrEnabled > 0):
            raise NvCSTestException("RAW Capture not supported with AOHDR enabled.  Re-run test with AOHDR disabled.")
            retVal = False
        return retVal


class NvCSTestConfiguration(object):
    filename = "undefined"
    testing = "undefined"
    attr_gain = -1
    attr_expo = -1
    attr_focuspos = -1
    attr_order = 0
    attr_sensorhdrratio = -1
    Avg = {"Color":[0.0, 0.0, 0.0],
            "Region":[0.0, 0.0, 0.0]}
    AvgNames = {"Color":["Red", "Green", "Blue"],
            "Region":["Top", "Middle", "Bottom"]}
    AvgPhaseR = 0.0
    AvgPhaseGR = 0.0
    AvgPhaseGB = 0.0
    AvgPhaseB = 0.0

    ratioR = 0.0
    ratioGR = 0.0
    ratioGB = 0.0
    ratioB = 0.0


    AvgPhaseRShort = 0.0
    AvgPhaseGRShort = 0.0
    AvgPhaseGBShort = 0.0
    AvgPhaseBShort = 0.0
    AvgShort = {"Color":[0.0, 0.0, 0.0],
            "Region":[0.0, 0.0, 0.0]}

    PeakPixelValue = 0
    errMargin = 0.001

    BlackLevelPadding = 4.0
    OverExposureThreshold = 0.90

    MaxIntensity = 0
    MinIntensity = 0

    def __init__(self, subtest, filepath, exposure, gain, focus=450):
        self.attr_expo = exposure
        self.attr_gain = gain
        self.attr_focuspos = focus
        self.testing = subtest
        self.filename = filepath
        self.Avg = {"Color":[0.0, 0.0, 0.0],
                    "Region":[0.0, 0.0, 0.0]}
        self.AvgPhaseR = 0.0
        self.AvgPhaseGR = 0.0
        self.AvgPhaseGB = 0.0
        self.AvgPhaseB = 0.0


    def processRawAvgs(self, nvrf):

        #
        # Calculate image average based on center region
        #                    START
        #

        ROT_CenterRegionSize_W = 640
        ROT_CenterRegionSize_H = 480

        if (nvrf._width < ROT_CenterRegionSize_W):
            ROT_CenterRegionSize_W = nvrf._width
        if (nvrf._height < ROT_CenterRegionSize_H):
            ROT_CenterRegionSize_H = nvrf._height

        # round to even coordinates
        ROT_CenterRegionSize_W = (ROT_CenterRegionSize_W & (~1))
        ROT_CenterRegionSize_H = (ROT_CenterRegionSize_H & (~1))

        # Compute the starting point of the interesting region (even coordinates)
        CenterRegion_left = ((nvrf._width - ROT_CenterRegionSize_W) // 2) & (~1)
        CenterRegion_top = ((nvrf._height - ROT_CenterRegionSize_H) // 2) & (~1)
        CenterRegion_right = CenterRegion_left + ROT_CenterRegionSize_W
        CenterRegion_bottom = CenterRegion_top + ROT_CenterRegionSize_H

        w = CenterRegion_right - CenterRegion_left
        h = CenterRegion_bottom - CenterRegion_top

        bayerIndex = [0.0, 0.0, 0.0, 0.0]
        AvgR = 0.0
        AvgG = 0.0
        AvgB = 0.0
        AvgPhaseR = 0.0
        AvgPhaseGR = 0.0
        AvgPhaseGB = 0.0
        AvgPhaseB = 0.0
        numPixels = 0.0

        bayerPhaseStr = ""
        if (nvrf.nvrawV3):
            bayerPhaseStr = nvrf._baseHeaderReader.getBayerPhase()
        else:
            bayerPhaseStr = nvrf._bayerPhase

        IndexGb = 0;
        IndexB = 0;
        IndexR = 0;
        IndexGr = 0;

        if (bayerPhaseStr == "GBRG" or bayerPhaseStr == nvraw_v3.BAYER_PHASE_GBRG):
            # case NvColorFormat_X6Bayer10GBRG:
            # self.logger.debug("BayerPhase GBRG")
            IndexGb = 0;
            IndexB = 1;
            IndexR = 2;
            IndexGr = 3;
        elif (bayerPhaseStr == "RGGB" or bayerPhaseStr == nvraw_v3.BAYER_PHASE_RGGB):
            # case NvColorFormat_X6Bayer10RGGB:
            # self.logger.debug("BayerPhase RGGB")
            IndexR = 0;
            IndexGr = 1;
            IndexGb = 2;
            IndexB = 3;
        elif (bayerPhaseStr == "BGGR" or bayerPhaseStr == nvraw_v3.BAYER_PHASE_BGGR):
            # case NvColorFormat_X6Bayer10BGGR:
            # self.logger.debug("BayerPhase BGGR")
            IndexB = 0;
            IndexGb = 1;
            IndexGr = 2;
            IndexR = 3;
        elif (bayerPhaseStr == "GRBG" or bayerPhaseStr == nvraw_v3.BAYER_PHASE_GRBG):
            # case NvColorFormat_X6Bayer10GRBG:
            # self.logger.debug("BayerPhase GRBG")
            IndexGr = 0;
            IndexR = 1;
            IndexB = 2;
            IndexGb = 3;
        else:
            # self.logger.error("BayerPhase Not Recognized '%s'", bayerPhaseStr)
            print("BayerPhase Not Recognized '%s'" % bayerPhaseStr)

        # set defaults for max and min intensity from the image
        self.MaxIntensity = 0
        self.MinIntensity = float(nvrf.getPeakPixelValue())

        for y in range(0, h, 2):
            for x in range(0, w, 2):
                bayerIndex[0] = nvrf.getPixelValue(CenterRegion_left+x,   CenterRegion_top+y)
                bayerIndex[1] = nvrf.getPixelValue(CenterRegion_left+x+1, CenterRegion_top+y)
                bayerIndex[2] = nvrf.getPixelValue(CenterRegion_left+x,   CenterRegion_top+y+1)
                bayerIndex[3] = nvrf.getPixelValue(CenterRegion_left+x+1, CenterRegion_top+y+1)

                self.MaxIntensity = max(bayerIndex[0], bayerIndex[1], bayerIndex[2], bayerIndex[3], self.MaxIntensity)
                self.MinIntensity = min(bayerIndex[0], bayerIndex[1], bayerIndex[2], bayerIndex[3], self.MinIntensity)

                AvgR +=  bayerIndex[IndexR]
                AvgG +=  (bayerIndex[IndexGr] + bayerIndex[IndexGb])/2
                AvgB +=  bayerIndex[IndexB]
                AvgPhaseR +=  bayerIndex[IndexR]
                AvgPhaseGR +=  bayerIndex[IndexGr]
                AvgPhaseGB +=  bayerIndex[IndexGb]
                AvgPhaseB +=  bayerIndex[IndexB]
                numPixels += 1.0

        AvgR /= numPixels
        AvgG /= numPixels
        AvgB /= numPixels
        AvgPhaseR /= numPixels
        AvgPhaseGR /= numPixels
        AvgPhaseGB /= numPixels
        AvgPhaseB /= numPixels

        self.Avg["Color"][0] = AvgR
        self.Avg["Color"][1] = AvgG
        self.Avg["Color"][2] = AvgB
        self.AvgPhaseR = AvgPhaseR
        self.AvgPhaseGR = AvgPhaseGR
        self.AvgPhaseGB = AvgPhaseGB
        self.AvgPhaseB = AvgPhaseB

        #
        # Calculate image average based on center region
        #                     END
        #

        #
        # Calculate image black levels (based on top, middle bottom)
        #                          START
        #
        ROT_BLCenterRegionSize_W  = 640
        ROT_BLCenterRegionSize_H  = 480
        if (nvrf._width < ROT_CenterRegionSize_W):
            ROT_BLCenterRegionSize_W = nvrf._width
        # Calculate row region of interest
        CenterRegion_left = ((nvrf._width - ROT_CenterRegionSize_W) // 2) & (~1)
        CenterRegion_right = CenterRegion_left + ROT_CenterRegionSize_W

        w = CenterRegion_right - CenterRegion_left

        # First get top image average
        CenterRegion_top = 0
        BLtop = 0.0
        for x in range(0, w):
            BLtop += nvrf.getPixelValue(CenterRegion_left+x, CenterRegion_top)
        BLtop /= w
        self.Avg["Region"][0] = BLtop

        # Next get middle image average
        CenterRegion_top = nvrf._height // 2
        BLmiddle = 0.0
        for x in range(0, w):
            BLmiddle += nvrf.getPixelValue(CenterRegion_left+x, CenterRegion_top)
        BLmiddle /= w
        self.Avg["Region"][1] = BLmiddle

        # Finally get bottom image average
        CenterRegion_top = nvrf._height * 0.9
        CenterRegion_top = int(CenterRegion_top)
        BLbottom = 0.0
        for x in range(0, w):
            BLbottom += nvrf.getPixelValue(CenterRegion_left+x, CenterRegion_top)
        BLbottom /= w
        self.Avg["Region"][2] = BLbottom
        #
        # Calculate image black levels (based on top, middle bottom)
        #                           END
        #

    @classmethod
    def processLinearityStats(self, testName, testsList, bias=[0.0, 0.0, 0.0]):
        TestSensorRangeMax = 0.95

        # Variables that will be returned
        OverExposed = False
        UnderExposed = False
        rSquared = [0.0,0.0,0.0]
        a = [0.0,0.0,0.0] # Slope
        b = [0.0,0.0,0.0] # Y intercept
        logStr = ""
        csvStr = ""

        # Additional statistics, but not used
        MaxPointError = [0.0, 0.0, 0.0]
        TotalError = [0.0, 0.0, 0.0]

        # Variables used for calculations
        ImageCount = 0
        SumC = [0.0,0.0,0.0]
        SumCSquared = [0.0,0.0,0.0]
        SumCxEv = [0.0,0.0,0.0]
        Ev = 0.0
        SumEv = 0.0
        SumEvSquared = 0.0

        #
        # Given N sets of (ExposureProduct, Red), we are trying to solve a and b so
        # that sum of (Red - a*ExposureProduct + b)^2 is minimal
        # So, we are fitting the data into a line: f(x) = ax + b where x is
        # ExposureProduct and f(x) is Red.
        # We can solve this by the least linear square system: XB = Y =>
        # |x0 1|       |f(x0)|
        # |x1 1| |a|   |f(x1)|
        # | : 1| |b| = |  :  |
        # |xn 1|       |f(xn)|
        #
        # Multiply X^T to both side and we have
        # |x0^2 + ... + xn^2   x0 + ... + xn| |a|   |x0*f(x0) + ... + xn*f(xn)|
        # |x0 + ... + xn               n    | |b| = |f(x0) + ... + f(xn)      |
        #
        # Let SumXSquared = x0^2 + ... + xn^2
        #     SumX = x0 + ... + xn
        #     SumY = f(x0) + ... + f(xn)
        #     SumXY = x0*f(x0) + ... + xn*f(xn)
        # Then, we have two equations
        # SumXSquared * a + SumX * b = SumXY
        # SumX * a + n * b = SumY
        #
        # Therefore,
        # a = (SumX * SumY - n * SumXY) / (SumX * SumX - n * SumXSquared)
        # b = (SumY - SumX * a) / n
        #

        logStr += ("\nUsing a Bias:  R:%.1f, G:%.1f, B:%.1f\n" %
            (bias[0], bias[1], bias[2]))
        logStr += ("-----------------------\n")
        logStr += ("%s\n" % testName)
        logStr += ("-----------------------\n")
        logStr += ("%8s %8s %8s %7s %7s %7s %7s %7s %7s %5s\n" %
            ("Exposure", "Gain", "EP", "R", "G", "B", "R-BL", "G-BL", "B-BL", "Order"))
        csvStr += ("%8s, %8s, %8s, %7s, %7s, %7s, %7s, %7s, %7s, %5s\n" %
            ("Exposure", "Gain", "EP", "R", "G", "B", "R-BL", "G-BL", "B-BL", "Order"))

        PeakPixelValue = testsList[0].PeakPixelValue
        # Iterate through to accumulate color information from each image
        for imageStat in testsList:
            if (imageStat.testing  == "BlackLevel"):
                logStr += ("\nI SHOULD NOT HAVE REACHED THIS CODE, NO BLACKLEVEL CONFIGS\n")
            if (imageStat.Avg["Color"][0] < (bias[0]+self.BlackLevelPadding)):
                UnderExposed = True
            if (imageStat.Avg["Color"][1] < (bias[1]+self.BlackLevelPadding)):
                UnderExposed = True
            if (imageStat.Avg["Color"][2] < (bias[2]+self.BlackLevelPadding)):
                UnderExposed = True

            AvgColor = [0.0, 0.0, 0.0]
            if (imageStat.Avg["Color"][0] > (TestSensorRangeMax*PeakPixelValue)):
                OverExposed = True
            if (imageStat.Avg["Color"][1] > (TestSensorRangeMax*PeakPixelValue)):
                OverExposed = True
            if (imageStat.Avg["Color"][2] > (TestSensorRangeMax*PeakPixelValue)):
                OverExposed = True

            AvgColor[0] = imageStat.Avg["Color"][0] - bias[0];
            AvgColor[1] = imageStat.Avg["Color"][1] - bias[1];
            AvgColor[2] = imageStat.Avg["Color"][2] - bias[2];

            # This saftey check would only be reached in the case of extreme underexposed images
            if (AvgColor[0] < 0.0): AvgColor[0] = 0.0
            if (AvgColor[1] < 0.0): AvgColor[1] = 0.0
            if (AvgColor[2] < 0.0): AvgColor[2] = 0.0

            Ev = imageStat.attr_expo * imageStat.attr_gain
            SumEv += Ev;
            SumEvSquared += (Ev * Ev);
            SumC[0] += AvgColor[0];
            SumC[1] += AvgColor[1];
            SumC[2] += AvgColor[2];
            SumCSquared[0] += AvgColor[0] * AvgColor[0];
            SumCSquared[1] += AvgColor[1] * AvgColor[1];
            SumCSquared[2] += AvgColor[2] * AvgColor[2];
            SumCxEv[0] += (AvgColor[0] * Ev);
            SumCxEv[1] += (AvgColor[1] * Ev);
            SumCxEv[2] += (AvgColor[2] * Ev);

            ImageCount+=1;

            logStr += ("%8.6f %8.3f %8.3f %7.1f %7.1f %7.1f %7.1f %7.1f %7.1f %5d\n" %
                (imageStat.attr_expo, imageStat.attr_gain, imageStat.attr_expo * imageStat.attr_gain,
                imageStat.Avg["Color"][0], imageStat.Avg["Color"][1], imageStat.Avg["Color"][2],
                    AvgColor[0], AvgColor[1], AvgColor[2], imageStat.attr_order))
            csvStr += ("%8.6f, %8.3f, %8.3f, %7.1f, %7.1f, %7.1f, %7.1f, %7.1f, %7.1f, %5d\n" %
                (imageStat.attr_expo, imageStat.attr_gain, imageStat.attr_expo * imageStat.attr_gain,
                imageStat.Avg["Color"][0], imageStat.Avg["Color"][1], imageStat.Avg["Color"][2],
                    AvgColor[0], AvgColor[1], AvgColor[2], imageStat.attr_order))

        # This is a legacy check. Leaving in, but not sure what is failure case
        # other than only running 1 capture
        if (SumEv * SumEv == SumEvSquared):
            logStr += ("\n\nInvalid State: SumEv * Sum Ev == SumEvSquared\n")
            logStr += ("\n\nInvalid State: This may be caused due to improper configurations used in the test\n")
            return logStr, rSquared, a, b, OverExposed, UnderExposed

        #This set of formulas apply linear regression
        for j in range(0, 3):
            t1 = 0
            t2 = 0
            tx = 0
            t3 = (ImageCount * SumEvSquared - SumEv * SumEv)
            a[j] = 0.0 if(t3 == 0.0) else (ImageCount * SumCxEv[j] - SumEv * SumC[j]) / t3
            b[j] = (SumC[j] - a[j] * SumEv) / ImageCount;

            t1 = ImageCount * SumEvSquared - SumEv * SumEv;
            t2 = ImageCount * SumCSquared[j] - SumC[j] * SumC[j];

            tx = (ImageCount * SumCxEv[j] - SumEv * SumC[j]);

            if ((t1 == 0) or (t2 == 0)):
                rSquared[j] = 0.0
            else:
                rSquared[j] = (tx * tx) / abs(t1 * t2);

        # Calculate the mean squared error
        # Not used, but just additional statistical information
        for imageStat in testsList:
            if (imageStat.testing  == "BlackLevel"):
                logStr += ("\nIT SHOULD NOT HAVE REACHED THIS CODE, NO BLACKLEVEL CONFIGS\n")
            AvgColor = [0.0, 0.0, 0.0]
            AvgColor[0] = imageStat.Avg["Color"][0] - bias[0];
            AvgColor[1] = imageStat.Avg["Color"][1] - bias[1];
            AvgColor[2] = imageStat.Avg["Color"][2] - bias[2];
            if (AvgColor[0] < 0.0): AvgColor[0] = 0.0
            if (AvgColor[1] < 0.0): AvgColor[1] = 0.0
            if (AvgColor[2] < 0.0): AvgColor[2] = 0.0

            for j in range(0, 3):
                e = (AvgColor[j] - a[j] * imageStat.attr_expo * imageStat.attr_gain - b[j]);
                e *= e;
                if (e > MaxPointError[j]):
                    MaxPointError[j] = e;
                    TotalError[j] += e;

        # Printing statisal results on image linearity
        for j in range(0, 3):
            colorName = ["Red", "Green", "Blue"]
            TotalError[j] /= ImageCount;

            if (j == 0):
                logStr += ("Color:      R^2   Line\n")

            logStr += ("%5s:  %7.5f   Y=%.2fX + %.2f\n" %
                (colorName[j], rSquared[j], a[j], b[j]))

        return logStr, rSquared, a, b, OverExposed, UnderExposed, csvStr

    @classmethod
    def calculateRSquared(self, testsList, xAttr, yAttrList, listSize):

        rSquared = []

        sumX = [0.0] * listSize
        sumY = [0.0] * listSize
        sumXSquared = [0.0] * listSize
        sumYSquared = [0.0] * listSize
        sumXY = [0.0] * listSize

        numItems = len(testsList)

        for listIndex in range(0, listSize):
            for testIndex in range(0, len(testsList)):
                x = getattr(testsList[testIndex], xAttr)
                y = getattr(testsList[testIndex], yAttrList)[listIndex]

                sumX[listIndex] += x
                sumY[listIndex] += y
                sumXSquared[listIndex] += x * x
                sumYSquared[listIndex] += y * y
                sumXY[listIndex] += x * y

            # Numerator of R
            numerator = numItems * sumXY[listIndex] - sumX[listIndex] * sumY[listIndex]

            # Denominator of R^2
            denominator = ((numItems * sumXSquared[listIndex] - sumX[listIndex] * sumX[listIndex]) *
                           (numItems * sumYSquared[listIndex] - sumY[listIndex] * sumY[listIndex]))

            # Calculate R^2
            rSqrd = 0.0

            # Prints for debugging divide by zero error
            # print "listIndex " + str(listIndex) + " "
            # print "numItems " + str(numItems) + " sumXY[listIndex] " + str(sumXY[listIndex]) + " sumX[listIndex] " + str(sumX[listIndex]) + " sumY[listIndex] " + str(sumY[listIndex])
            # print "numerator " + str(numerator)
            # print "numItems " + str(numItems) + " sumXSquared[listIndex]  " + str(sumXSquared[listIndex] ) + \
            #      " sumYSquared[listIndex] " + str(sumYSquared[listIndex]) + \
            #      " \nsumX[listIndex] " + str(sumX[listIndex]) + " sumY[listIndex] " + str(sumY[listIndex])
            # print "denominator %3.6f abs(denominator) %3.6f " % (denominator, abs(denominator))

            # Avoid divide by zero error
            if (abs(denominator) > 0.0001):
                # print "Denominator is > 0.0001"
                rSqrd = float(numerator * numerator) / denominator

            rSquared.append(rSqrd)

        return rSquared

    @classmethod
    def processVariationStats(self, testName, testsList, attrStr, maxPixelVal, bias=[0.0, 0.0, 0.0]):
        attrVar = [0.0,0.0,0.0]
        Variation = [float("inf"), float("inf"), float("inf")]
        attrName = NvCSTestConfiguration.AvgNames[attrStr]
        ImageCount = 0
        Variance = [0.0, 0.0, 0.0]
        logStr = ""
        csvStr = ""
        MaxTracker = 0
        MinTracker = maxPixelVal

        logStr += ("\nBias used for calculating SNR:  R:%.1f, G:%.1f, B:%.1f\n" % (bias[0], bias[1], bias[2]))
        logStr += ("-----------------------\n")
        logStr += ("%s\n" % testName)
        logStr += ("-----------------------\n")
        logStr += ("%8s %8s %8s %7s %7s %7s %5s\n" % ("Exposure", "Gain", "EP", attrName[0],
                      attrName[1], attrName[2], "Order"))
        csvStr += ("%8s, %8s, %8s, %7s, %7s, %7s, %5s\n" % ("Exposure", "Gain", "EP", attrName[0],
                      attrName[1], attrName[2], "Order"))

        # attrVar is tracking the average of all frames
        for imageStat in testsList:
            attrVar[0] += imageStat.Avg[attrStr][0] - bias[0]
            attrVar[1] += imageStat.Avg[attrStr][1] - bias[1]
            attrVar[2] += imageStat.Avg[attrStr][2] - bias[2]

            logStr += ("%8.6f %8.3f %8.3f %7.1f %7.1f %7.1f %5d\n" %
                (imageStat.attr_expo, imageStat.attr_gain, imageStat.attr_expo * imageStat.attr_gain,
                imageStat.Avg[attrStr][0], imageStat.Avg[attrStr][1], imageStat.Avg[attrStr][2], imageStat.attr_order))
            csvStr += ("%8.6f, %8.3f, %8.3f, %7.1f, %7.1f, %7.1f, %5d\n" %
                (imageStat.attr_expo, imageStat.attr_gain, imageStat.attr_expo * imageStat.attr_gain,
                imageStat.Avg[attrStr][0], imageStat.Avg[attrStr][1], imageStat.Avg[attrStr][2], imageStat.attr_order))

            ImageCount +=1;

        attrVar[0] /= ImageCount;
        attrVar[1] /= ImageCount;
        attrVar[2] /= ImageCount;


        # Calculate the variance across all frames
        for imageStat in testsList:
            e =  attrVar[0] - (imageStat.Avg[attrStr][0] - bias[0]);
            Variance[0] += e * e;
            e =  attrVar[1] - (imageStat.Avg[attrStr][1] - bias[1]);
            Variance[1] += e * e;
            e =  attrVar[2] - (imageStat.Avg[attrStr][2] - bias[2]);
            Variance[2] += e * e;

        Variance[0] /= 1.0*ImageCount
        Variance[1] /= 1.0*ImageCount
        Variance[2] /= 1.0*ImageCount


        bPixelValueLow = False
        pixelValueLowCount = 0
        MinTracker = attrVar[0]
        for j in range(0, len(Variance)):
            stdDev = math.sqrt(Variance[j])
            # SNR (units of dB). Typical imaging definition. Take raw S:N ratio
            # of this test's images, then apply the log-20 rule to convert to dB.
            if (attrVar[j] != 0):
                Variation[j] = 100 * stdDev / attrVar[j]
            else:
                Variation[j] = float("inf")

            if (j == 0):
                logStr += ("%5s  %7s  %7s\n" %
                    (attrStr, "Average", "Variation(%)"))

            logStr += ("%5s  %8.2f  %7.3f\n" %
                (attrName[j], attrVar[j], Variation[j]))

            # Also track the maximum and minimum of averages across images

            # MaxTracker was initialized to 0 to make this logic work
            # MinTracker was initialized to attrVar[0] before entering this for-loop
            # to make this logic work
            if(attrVar[j] > MaxTracker):
                MaxTracker = attrVar[j]
            if(attrVar[j] < MinTracker):
                MinTracker = attrVar[j]

            # Check if the average pixel values are too low (less than 30% of max value)
            avgPixelValTreshold = (maxPixelVal-bias[j]) * 0.30
            if (attrVar[j] < avgPixelValTreshold):
                pixelValueLowCount += 1
                print("Warning: Average Pixel Value for %s (%4.4f) is less than 30 percent of (max value[%u] - bias[%u]) %4.4f " % (attrName[j], attrVar[j], maxPixelVal, bias[j], avgPixelValTreshold))

        if (pixelValueLowCount == len(Variance)):
            bPixelValueLow = True
            print("Warning: average pixel value for all channels (%d) is less than 30 percent of max value %u" %(len(Variance), maxPixelVal))
        # collecting average value for all regions
        avgTracker = sum(attrVar) / len(attrVar)
        return logStr, Variation, MaxTracker, MinTracker, avgTracker, csvStr, bPixelValueLow

    @classmethod
    def runConfig(self, test, testConfig, needHalfPress=False):

        nvcsUtil = NVCSutil()
        if (nvcsUtil.isEmbeddedOS()):
            # always set half press to False in embeddedOS
            needHalfPress = False
        bMultiExpos = nvcstestsystem.isMultipleExposuresSupported()

        #
        # test.obCamera.getHDRInfo() can not be called from here.
        # Hence calling getHdrCapabilities
        #

        numExposures = 0
        numGains = 0
        capabilities = nvcamera.NvHdrCapabilities()
        test.obCamera.getHdrCapabilities(capabilities)

        if (capabilities.bHdrSupported):
            for i in range(nvcamera.NvHdrMode_Last):
                et_count = capabilities.getNumExposuresAt(i)
                sag_count = capabilities.getNumSensorAnalogGainsAt(i)

                if (et_count > 0):
                     numExposures = et_count
                if (sag_count > 0):
                      numGains = sag_count
                if (numExposures > 0 or numGains > 0):
                   supportedMode = i;
                   break;

        if (numExposures == 0):
            numExposures = 1
        if (numGains == 0):
            numGains = 1

        #
        # Check if the comand line options are specified correctly
        # Get the index of the exposure that we need to use.
        #
        index, exposureMode = nvcstestsystem.getSingleExposureIndex(numExposures, False, test.options, test.logger)
        if (index == -1):
            self.logger.error("getSingleExposureIndex: Command line options error")
            return NvCSTestResult.ERROR

        test.obCamera.startPreview()
        if nvcsUtil.isMobile() :
            if(test.options.ignoreFocuser == False):
                if(test.obCamera.isFocuserSupported()):
                    test.obCamera.setAttr(nvcamera.attr_continuousautofocus, 0)
                    test.obCamera.setAttr(nvcamera.attr_autofocus, 0)
                    test.obCamera.setAttr(nvcamera.attr_focuspos, testConfig.attr_focuspos)

        if (bMultiExpos):
            exp_time_list = [-1 for i in range(0, nvcamera.HDR_MAX_EXPOSURES, 1)]
            exp_time_list[index] = testConfig.attr_expo
            test.obCamera.setAttr(nvcamera.attr_exposuretime, exp_time_list)

            gain_list = [-1 for i in range(0, nvcamera.HDR_MAX_EXPOSURES, 1)]
            gain_list[index] = testConfig.attr_gain
            test.obCamera.setAttr(nvcamera.attr_bayergains, gain_list)
        else:
            test.obCamera.setAttr(nvcamera.attr_exposuretime, testConfig.attr_expo)
            test.obCamera.setAttr(nvcamera.attr_bayergains, [testConfig.attr_gain] * 4)

        test.logger.info("Capturing Image:\tET: [%2.6f]\tgain: [%2.2f]" % (testConfig.attr_expo, testConfig.attr_gain))

        # take an image with specified ISO
        fileName = testConfig.filename
        rawFilePath = os.path.join(test.testDir, fileName + ".nvraw")
        try:
            test.obCamera.captureRAWImage(rawFilePath, needHalfPress)
        except nvcamera.NvCameraException as err:
            if (err.value == nvcamera.NvError_NotSupported):
                test.logger.info("raw capture is not supported")
                return NvCSTestResult.SKIPPED
            else:
                raise

        test.obCamera.stopPreview()
        if not test.nvrf.readFile(rawFilePath):
            test.logger.error("couldn't open the file: %s" % rawFilePath)
            return NvCSTestResult.ERROR

        # Check no values over 2**dynamicPixelBitDepth
        maxPixelVal = test.nvrf.getMaxPixelValue()
        if (maxPixelVal > test.nvrf.getPeakPixelValue()):
            test.logger.error("NvCSTestConfiguration::runConfig: pixel value [%d] is over %d." % (maxPixelVal, test.nvrf.getPeakPixelValue()))
            test.logger.error("NvCSTestConfiguration::runConfig: _bitsPerSample [%d] _dynamicPixelBitDepth %d." % (test.nvrf._bitsPerSample, test.nvrf.getDynamicBitDepth()))
            return NvCSTestResult.ERROR

        # Allowed difference is not the same for Automotive and Android/L4T
        diffAllowed = 0.001
        if (nvcsUtil.isEmbeddedOS()):
            diffAllowed = 0.015 # 1.5% diff
        #
        # We try to pick up the sensor gain from the HDR chunk if the exposure index is greater than 0.
        # For 0, if the HDR chunk is not present, we should be able to get it from the capture chunk.
        #
        gainFromFile = test.nvrf.getSensorGain()
        if (not test.nvrf.nvrawV3):
            diffPass = True

        if (nvcsUtil.isEmbeddedOS()):
            diffPass = False if (abs(gainFromFile - float(testConfig.attr_gain))/float(testConfig.attr_gain) > diffAllowed) else True
        else:
            diffPass = False if (abs(gainFromFile - float(testConfig.attr_gain)) > diffAllowed) else True
        if diffPass == False:
            test.logger.error("SensorGains %f is not correct in the raw header: %f" % (testConfig.attr_gain, gainFromFile))
            if (nvcsUtil.isEmbeddedOS()):
                test.logger.error("diffAllowed %f%%" % (diffAllowed*100.0))
            else:
                test.logger.error("diffAllowed %f" % (diffAllowed))
            return NvCSTestResult.ERROR

        # check SensorExposure value
        exposureTimeFromFile = test.nvrf.getExposureTime()
        if (abs(exposureTimeFromFile - testConfig.attr_expo) > 0.001):
            test.logger.error( "exposuretime %f is not correct in the raw header %f..." % (testConfig.attr_expo, exposureTimeFromFile))
            return NvCSTestResult.ERROR

        expTime = test.obCamera.getAttr(nvcamera.attr_exposuretime)
        if (bMultiExpos):
            if (not ((expTime[index] > testConfig.attr_expo - self.errMargin) and (expTime[index] < testConfig.attr_expo + self.errMargin))):
                test.logger.error("exposuretime is not set in the driver...")
                test.logger.error( "exposure value %.6f should be between %.6f and %.6f" %
                                    (expTime[0], testConfig.attr_expo - self.errMargin, testConfig.attr_expo + self.errMargin))
                return NvCSTestResult.ERROR
        else:
            if (not ((expTime > testConfig.attr_expo - self.errMargin) and (expTime < testConfig.attr_expo + self.errMargin))):
                test.logger.error("exposuretime is not set in the driver...")
                test.logger.error( "exposure value %.6f should be between %.6f and %.6f" %
                                    (expTime, testConfig.attr_expo - self.errMargin, testConfig.attr_expo + self.errMargin))
                return NvCSTestResult.ERROR

        testConfig.PeakPixelValue = test.nvrf.getPeakPixelValue()
        testConfig.processRawAvgs(test.nvrf)
        return NvCSTestResult.SUCCESS

    @classmethod
    def runConfigList(self, test, configList, needHalfPress=False):
        for testConfig in configList:
            result = testConfig.runConfig(test, testConfig, needHalfPress)
            # return ERROR or SKIPPED
            if (result != NvCSTestResult.SUCCESS):
                return result
        return NvCSTestResult.SUCCESS

