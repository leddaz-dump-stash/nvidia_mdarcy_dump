# Copyright (c) 2012-2017, NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#

import array
from nvcstestcore import *
import nvcstestutils

class NvCSHostSensorTest(NvCSTestBase):
    "Host Sensor Basic Test"

    numImages = 3
    rawImageWidth = 2592
    rawImageHeight = 1944

    def __init__(self, options, logger, sensorSetting):
        NvCSTestBase.__init__(self, options, logger, "Host_Sensor", sensorSetting)
        self.options = options
        self.sensorSetting = sensorSetting
        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.sensorSetting.imager_id, self.sensorSetting.imager_name)

        if(self.options.width != 0):
            self.rawImageWidth = self.options.width
        if(self.options.height != 0):
            self.rawImageHeight = self.options.height

    def needAutoGraphSetup(self):
        # need to setup the graph manually for host sensor mode
        return False

    def runTest(self, args):

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
        # This test does not support any exposure apart from e0
        #
        index, exposureMode = nvcstestsystem.getSingleExposureIndex(numExposures, True, self.options, self.logger)
        if (index == -1):
            self.logger.error("getSingleExposureIndex: Command line options error")
            return NvCSTestResult.ERROR

        if self.options.input:
            self.nvrf = nvcstestutils.NvCSRawFile()
            if not self.nvrf.readFile(self.options.input):
                return NvCSTestResult.ERROR
        else:
            self.nvrf = nvcameraimageutils.createTestNvRawFile(
                            self.rawImageWidth,
                            self.rawImageHeight,
                            "RGGB",
                            nvcameraimageutils.TestImagePattern.TIP_COLORS_2x2)

        header = self.nvrf.makeLegacyHeader()

        if(self.options.numTimes > 0):
            self.numImages = self.options.numTimes
        elif(self.options.numTimes < 0):
            self.logger.warning("User entered invalid number of samples (negative).  Using default (%d)" % self.numImages)

        for i in range(self.numImages):
            # ---- setup the host sensor graph ---- #
            self.obGraph.setGraphType(GraphType.HOST_SENSOR)
            self.obGraph.setStillParams(self.nvrf._width, self.nvrf._height)

            self.logger.info("Creating and running the jpeg graph")
            self.obGraph.createAndRunGraph()
            self.logger.info("Created jpeg graph")
            # enable ANR
            self.obCamera.setAttr(nvcamera.attr_anr, 1)

            bMultiExpos = nvcstestsystem.isMultipleExposuresSupported()

            for j in range(self.options.numCaptures):
                # set the exposure time from the raw file
                self.logger.debug("Setting the exposure time to: %f" % self.nvrf._exposureTime)

                # set the bayergains from raw file
                self.logger.debug("Setting the bayergains to: %s" % str(self.nvrf._sensorGains))

                if (bMultiExpos):
                    self.obCamera.setAttr(nvcamera.attr_exposuretime, self.nvrf._exposureTime)
                    self.obCamera.setAttr(nvcamera.attr_bayergains, self.nvrf._sensorGains[0])
                else:
                    self.obCamera.setAttr(nvcamera.attr_exposuretime, self.nvrf._exposureTime)
                    self.obCamera.setAttr(nvcamera.attr_bayergains, self.nvrf._sensorGains)

                # append the image number and mode number at the end
                fileName = "%s_%d_%d_i%d_m%d" % (self.testID, i, j, self.sensorSetting.imager_id, self.sensorSetting.sensor_mode)
                jpegFilePath = os.path.join(self.testDir, fileName + ".jpg")

                # pass the raw image header, data and iteration information
                self.obCamera.setRawImage(header, self.nvrf._pixelData, j)
                self.obCamera.captureJpegImage(jpegFilePath)

                if (os.path.exists(jpegFilePath) != True):
                    self.logger.error("Couldn't capture the jpeg image: %s" % jpegFilePath)
                    return NvCSTestResult.ERROR

            self.obGraph.stopAndDeleteGraph()

        return NvCSTestResult.SUCCESS
