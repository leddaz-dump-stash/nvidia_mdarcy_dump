# Copyright (c) 2014-2020 NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#

from __future__ import division
from __future__ import print_function

from nvcstestcore import *
import nvcstestutils
import nvcstestsystem
import nvrawfile
import os.path
import time
import re
import subprocess
import stat
import sys
nvcscommonPath = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'common')
nvcscommonutilsPath = os.path.join(nvcscommonPath, 'nvcsCommonUtils.py')
sys.path.append(nvcscommonPath)
from nvcsCommonUtils import NVCSutil

class NvCSCaptureScriptTest(NvCSTestBase):
    "Capture Script test"

    scriptPath = "/examples/nvcamera_capture_image.py"
    pythonPath = sys.executable
    nvrf       = None
    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    def __init__(self, options, logger, sensorSetting):
        NvCSTestBase.__init__(self, options, logger, "CaptureScript", sensorSetting)
        self.options = options
        self.nvcsPath = nvcsUtil.getNVCSPath()
        self.sensorSetting = sensorSetting
        self.nvrf = nvrawfile.NvRawFile()

    def setupGraph(self):
        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.sensorSetting.imager_id, self.sensorSetting.imager_name)
        self.obGraph.setGraphType(GraphType.RAW)
        return NvCSTestResult.SUCCESS

    def streamingValidation(self, outputString = None, gain = None, exposure = None):
        if outputString == None or gain == None or exposure == None:
            return 1
        else :
            consecutiveFile = None
            # parse out the capture nvraw image path
            filePath = nvcsUtil.getCaptureScriptLogPath()
            for line in outputString :
                if filePath in line :
                    # remove first and last character []
                    line = line[1:-1]
                    # check if file really exist
                    if  not os.path.isfile(line):
                        self.logger.error("file[%s] does not existed"%line)
                        return 1
                    else :
                        # compare the file name see if there is a frame dropped
                        word = line.split('/')
                        if consecutiveFile == None :
                            consecutiveFile = word[-1]
                            consecutiveFile = consecutiveFile.split('.') # split file name and .nvraw
                            consecutiveFile = consecutiveFile[0].split('_') # split file name
                            consecutiveFile = consecutiveFile[-1]
                        else :
                            currentFile = word[-1]
                            currentFile = currentFile.split('.') # split file name and .nvraw
                            currentFile = currentFile[0].split('_') # split file name
                            currentFile = currentFile[-1]
                            if (int(currentFile) - int(consecutiveFile)) == 1 :
                                consecutiveFile = currentFile
                            else :
                                self.logger.error("not consecutive frame saved; frame dropped")
                                return 1
                        # check the metadata;
                            if not self.nvrf.readFile(line):
                                self.logger.error("couldn't open the file: %s" % line)
                                return 1
                            else :
                                 if (abs(self.nvrf.getExposureTime() - exposure) > 0.001) and \
                                    (abs(self.nvrf.getSensorGain() - gain) > 0.001):

                                        self.logger.error("captured raw file : gain [%f] does not match to set values: gain[%f]" % (self.nvrf.getSensorGain(), gain))
                                        self.logger.error("captured raw file :exposure [%f] does not match to set values: exposure[%f]" % (self.nvrf.getExposureTime(), exposure))
                                        return 1
                        self.logger.info("RAW: %s" % line)
            # TODO: in the future we can use vivid to check the image accuracy
            #       or do some IQ matrix

            return 0

    def runTestMobile(self, args):
        #TODO: need to add better validation for capture script; I.E check the setting with the raw file
        focus = 250
        exposure = 0.02
        gain = 1.0
        names = []
        results = []
        runtimes = []

        self.obCamera.startPreview()
        hasFocuser = True if (self.obCamera.isFocuserSupported()) else False
        self.obCamera.stopPreview()
        self.obGraph.stopAndDeleteGraph()

      # Concurrent Raw+Jpeg Capture - Auto
        names.append("Concurrent Raw+Jpeg Capture - Auto 3As")
        command = None
        command = "%s %s -i %d -t c -s %d -n nvcs_test_auto_i%d_m%d" % (self.pythonPath, self.nvcsPath + self.scriptPath,
                                                                self.sensorSetting.imager_id, self.sensorSetting.sensor_mode,
                                                                self.sensorSetting.imager_id, self.sensorSetting.sensor_mode)
        self.logger.info("running: \"%s\"" % command)
        startTime = time.time()
        results.append(subprocess.call(command.split()))
        endTime = time.time()
        runtimes.append(endTime - startTime)
        self.logger.info("Script Runtime (%s):    %fs" % (names[-1], runtimes[-1]))
        self.logger.info("Exit Code: %d" % results[-1])

      # Concurrent Raw+Jpeg Capture - Manual
        names.append("Concurrent Raw+Jpeg Capture - Manual 3As")

        command = "%s %s -i %d -e %f -g %f -t c -s %d -n nvcs_test_manual_i%d_m%d" % (self.pythonPath, self.nvcsPath + self.scriptPath,
                                                                              self.sensorSetting.imager_id, exposure, gain,self.sensorSetting.sensor_mode,
                                                                              self.sensorSetting.imager_id, self.sensorSetting.sensor_mode)
        if hasFocuser:
            command += " -f %d" % focus
        self.logger.info("running: \"%s\"" % command)
        startTime = time.time()
        results.append(subprocess.call(command.split()))
        endTime = time.time()
        runtimes.append(endTime - startTime)
        self.logger.info("Script Runtime (%s):    %fs" % (names[-1], runtimes[-1]))
        self.logger.info("Exit Code: %d" % results[-1])

      # file streaming test MOBILE only
        streamType = "buffered"
        streamNumber = 10
        names.append("capture streaming images - %d consecutive frames" % streamNumber)
        if (nvcsUtil.isMobile()):
            command = "%s %s -i %d -e %f -g %f --preview %d --stream-type %s --stream-frame %d" % (self.pythonPath, self.nvcsPath + self.scriptPath,
                                                                            self.sensorSetting.imager_id, exposure, gain,self.sensorSetting.sensor_mode,
                                                                            streamType, streamNumber)
        self.logger.info("running: \"%s\"" % command)
        startTime = time.time()
        from subprocess import PIPE, Popen
        proc = Popen(command.split(), stdout = PIPE)
        outputString = proc.communicate()[0].decode().split()
        results.append(self.streamingValidation(outputString, gain, exposure))
        endTime = time.time()
        runtimes.append(endTime - startTime)
        self.logger.info("Script Runtime (%s):    %fs" % (names[-1], runtimes[-1]))
        self.logger.info("Exit Code: %d" % results[-1])
      # Results
        self.logger.info("=================")
        self.logger.info("==   Results   ==")
        self.logger.info("=================")
        for i in range(len(names)):
            self.logger.info("%s\t: %fs\t: %s" % ("PASS" if results[i] == 0 else "FAIL", runtimes[i], names[i]))
        for i in results:
            if i != 0:
                self.logger.error("At least one capture script call failed.")
                return NvCSTestResult.ERROR
        return NvCSTestResult.SUCCESS

    def runTestAutomotive(self, args):
        exposure = 0.02
        gain = 1.0
        names = []
        results = []
        runtimes = []

        self.obCamera.startPreview()
        exposureTimeRange = self.obCamera.getAttr(nvcamera.attr_exposuretimerange)
        gainRange = self.obCamera.getAttr(nvcamera.attr_gainrange)
        self.obCamera.stopPreview()
        self.obGraph.stopAndDeleteGraph()

        if (0 == len(exposureTimeRange)) or (0 == len(gainRange)) or \
            (len(exposureTimeRange) != len(gainRange)) or \
            (len(exposureTimeRange[0]) != len(gainRange[0])):
            self.logger.error("nvcsframeworktests::runTestAutomotive:: exposure range(%d) :: gain range(%d) is not valid" % \
                len(exposureTimeRange), len(gainRange))
            return NvCSTestResult.ERROR
        for i in range(0, len(exposureTimeRange[0])):
            self.logger.info("Exposure time range for index %d (%2.4f, %2.4f)" % \
                  (i, exposureTimeRange[0][i], exposureTimeRange[1][i]))
            self.logger.info("Gain range for index %d (%2.4f, %2.4f)" % \
                (i, gainRange[0][i], gainRange[1][i]))

        # SDR Raw Capture
        names.append("SDR Raw Capture")
        command = "{0} {1} --cf {2} --c {3} --use_eall -n nvcs_test_manual_SDR".format(
            self.pythonPath, self.nvcsPath + self.scriptPath, self.options.sensor_config_file, self.options.sensor_name)
        command += " --e0 {0} --g0 {1}".format(exposureTimeRange[0][0], gainRange[1][0])


        self.logger.info("running: \"%s\"" % command)
        startTime = time.time()
        results.append(subprocess.call(command.split()))
        endTime = time.time()
        runtimes.append(endTime - startTime)
        self.logger.info("Script Runtime (%s):    %fs" % (names[-1], runtimes[-1]))
        self.logger.info("Exit Code: %d" % results[-1])

        # Results
        self.logger.info("=================")
        self.logger.info("==   Results   ==")
        self.logger.info("=================")
        for i in range(len(names)):
            self.logger.info("%s\t: %fs\t: %s" % ("PASS" if results[i] == 0 else "FAIL", runtimes[i], names[i]))
        for i in results:
            if i != 0:
                self.logger.error("At least one capture script call failed.")
                return NvCSTestResult.ERROR
        return NvCSTestResult.SUCCESS

    def runTest(self, args):
        if (nvcsUtil.isMobile()):
            return self.runTestMobile(args)
        elif (nvcsUtil.isEmbeddedOS()):
            return self.runTestAutomotive(args)

class NvCSPfpFileAPITest(NvCSTestBase):
    "Streaming and per frame API unit test1"
    PFPStr = (\
    " #\n"
    " # Start of first frame properties\n"
    " #\n"
    "frame[0].property[0].name = PROP_EXPOSURE_TIME;\n"
    "frame[0].property[0].value = {0.030};\n"
    "\n"
    "frame[1].property[1].name = PROP_FOCUS_POS;\n"
    "frame[1].property[1].value = 100;\n"
    "#\n"
    "frame[2].property[2].name = PROP_SENSOR_ANALOG_GAIN;\n"
    "frame[2].property[2].value = {2.0};\n"
    "\n")

    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    def __init__(self, options, logger):
        NvCSTestBase.__init__(self, options, logger, "PFP_Streaming_File")
        self.options = options

    def setupGraph(self):
        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.options.imager_id, self.options.sensor_name)
        self.obGraph.setGraphType(GraphType.RAW)

        return NvCSTestResult.SUCCESS

    def runTest(self, args):
        # enable PFP
        self.obCamera.PFP_enable(1)

        # create pfpLoadFile file
        loadFileName = os.path.join(self.testDir, "pfpLoadFile")
        dumpFileName = os.path.join(self.testDir, "pfpDumpFile")
        pfpLoadFile = open(loadFileName, 'w')
        pfpLoadFile.write(self.PFPStr)
        pfpLoadFile.close()

        # Open the file, load and dump the file to the disk.
        # We do this to make sure that there are no spaces, blank lines,
        # comments in the file.
        self.obCamera.PFP_loadFile(loadFileName)
        self.obCamera.PFP_dumpFile(loadFileName)

        # Open the pfpLoadFile again, read and dump the read contents to disk
        # pfpDumpFile. We are exercizing the whole path of reading, cleaning up,
        # populating the data structures and dumping.
        self.obCamera.PFP_loadFile(loadFileName)
        self.obCamera.PFP_dumpFile(dumpFileName)

        # compare two files. they should be same
        pfpLoadFile = open(loadFileName, 'rb')
        pfpDumpFile = open(dumpFileName, 'rb')

        if (os.fstat(pfpLoadFile.fileno()).st_size != \
            os.fstat(pfpDumpFile.fileno()).st_size):
            self.logger.error(loadFileName + "and " + dumpFileName + " are not of same size")
            return NvCSTestResult.ERROR

        print(pfpLoadFile.read())
        print(pfpDumpFile.read())

        if (pfpLoadFile.read() != pfpDumpFile.read()):
            self.logger.error("contents  of " + loadFileName + " and " + dumpFileName
                              + "are not of same size")
            return NvCSTestResult.ERROR

        pfpLoadFile.close()
        pfpDumpFile.close()

        # Set permission to 0666 for these two files
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
        if (nvcsUtil.setFileMode(loadFileName, mode) != True):
            raise ValueError("Error: Setting file %s with mode to %o" % (loadFileName, mode))

        if (nvcsUtil.setFileMode(dumpFileName, mode) != True):
            raise ValueError("Error: Setting file %s with mode to %o" % (dumpFileName, mode))

        return NvCSTestResult.SUCCESS

class NvCSPfpAPITest(NvCSTestBase):
    "Streaming and per frame API unit test2"

    frameCount = 8
    framesToIgnore = 3
    exposureTimeTable = [0.060, 0.060, 0.060, 0.060, 0.120,
                         0.240, 0.360, 0.480]

    def __init__(self, options, logger, sensorSetting):
        NvCSTestBase.__init__(self, options, logger, "PFP_Streaming")
        self.options = options
        self.sensorSetting = sensorSetting

    def setupGraph(self):
        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.sensorSetting.imager_id, self.sensorSetting.imager_name)
        self.obGraph.setGraphType(GraphType.RAW)

        return NvCSTestResult.SUCCESS

    def initializeExposureTimeTable(self):

        bMultiExpos = nvcstestsystem.isMultipleExposuresSupported()

        # For this test we use only exposure 0.
        index = 0

        exposureTimeRange = self.obCamera.getAttr(nvcamera.attr_exposuretimerange)

        if (bMultiExpos == False):
            self.logger.info("Exposure time range (%2.4f, %2.4f)" % \
                  (exposureTimeRange[0], exposureTimeRange[1]))
            et_delta = (exposureTimeRange[1] - exposureTimeRange[0]) \
                        / (self.frameCount - self.framesToIgnore)
        else:
            self.logger.info("Exposure time range for index %d (%2.4f, %2.4f)" % \
                  (index, exposureTimeRange[0][index], exposureTimeRange[1][index]))
            et_delta = (exposureTimeRange[1][index] - exposureTimeRange[0][index]) \
                        / (self.frameCount - self.framesToIgnore)

        for i in range(0, len(self.exposureTimeTable)):
            if (i <= self.framesToIgnore):
                self.exposureTimeTable[i] = et_delta;
            else:
                self.exposureTimeTable[i] = (i - self.framesToIgnore + 1) * et_delta;
            # print "(%2d, %2.4f)" % (i, self.exposureTimeTable[i])


    def runTest(self, args):
        retVal = NvCSTestResult.SUCCESS

        self.initializeExposureTimeTable()

        # set AE and AF to off
        self.obCamera.setAttr(nvcamera.attr_aemode, 1)
        self.obCamera.setAttr(nvcamera.attr_afmode, 1)

        # set gain to 1
        self.obCamera.setAttr(nvcamera.attr_sensoranaloggain, 1.0)

        self.obCamera.PFP_enable(1)
        self.obCamera.PFP_setFrameLoopCount(1000)

        i = 0
        for expTime in self.exposureTimeTable:
            camProperty = self.obCamera.getCamPropertyObject(nvcamera.attr_exposuretime, expTime)
            #print "Setting expTime %4.2f for frame %d" % (expTime, i)
            self.obCamera.PFP_addFrameProperty(i, 0, camProperty)
            i = i + 1

        streamingParams = nvcamera.StreamingParameters()
        streamingParams.frameCount = len(self.exposureTimeTable)
        streamingParams.imageFormat = nvcamera.ImageFormat_NvRaw
        streamingParams.frameDestination = nvcamera.FrameDest_DumpToDisk_Immediate
        streamingParams.filename = os.path.join(self.testDir, "capture.nvraw")

        self.obCamera.setStreamingParameters(streamingParams)

        self.obCamera.startPreview()
        self.obCamera.stopPreview()

        streamingStats = nvcamera.StreamingStats()
        self.obCamera.getStreamingStats(streamingStats)

        self.obCamera.PFP_removeAll()

        # get the exposuretime from captured raw files and compare
        # them with exposure time set using the API. The should match
        # skip first 3 frames as we need to account fo outstanding buffers
        for i in range(3, streamingStats.fileList.size()):
            frameFileName = streamingStats.fileList.GetFilename(i)
            print(frameFileName)
            if (os.path.exists(frameFileName) != True):
                self.logger.error("Couldn't find the raw image: %s" % frameFileName)
                return NvCSTestResult.ERROR

            if not self.nvrf.readFile(frameFileName):
                self.logger.error("couldn't open the file: %s" % frameFileName)
                return NvCSTestResult.ERROR

            if (abs(self.nvrf.getExposureTime() - self.exposureTimeTable[i]) > 1e-7):
                self.logger.error("Frame number %d Expected "
                                  "value %3.4f Read from the file %3.4f\n" %
                                  (i, self.exposureTimeTable[i], self.nvrf.getExposureTime()))
                retVal = NvCSTestResult.ERROR

        return retVal
