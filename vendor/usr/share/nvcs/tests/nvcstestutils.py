# Copyright (c) 2012-2020, NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#

# Copyright (c) 2001-2003 Gregory P. Ward.  All rights reserved.
# Copyright (c) 2002-2003 Python Software Foundation.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
#  * Neither the name of the author nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import os
import platform
import time
import shutil
import datetime
import optparse
import textwrap
import nvrawfile
import nvraw_v3
import nvrawfileV3
import nvrawfile_pinterface
import nvcstestsystem
import subprocess
import nvcamera
import signal
import stat
import struct
import sys
import threading

nvcscommonPath = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'common')
nvcscommonutilsPath = os.path.join(nvcscommonPath, 'nvcsCommonUtils.py')
sys.path.append(nvcscommonPath)
from nvcsCommonUtils import NVCSutil

nvcsUtil = None

class NvCSTestResult(object):
    ERROR   = 0
    SUCCESS = 1
    SKIPPED = 2

class SensorSetting(object) :
    width  = 0
    height = 0
    sensor_mode = 0;
    imager_id = 0;
    imager_name = ""
    sensor_mode_type = ""
    dynamicPixelBitDepth = 0
    csiPixelBitDepth = 0
    frameRate = 0.0

    def __init__(self, width = 0, height = 0, sensor_mode = 0, \
                 imager_id = 0, imager_name = None, sensor_mode_type = None, \
                 dynamicPixelBitDepth = 0, csiPixelBitDepth = 0, frameRate = 0.0) :
        self.width       = width
        self.height      = height
        self.sensor_mode = sensor_mode
        self.imager_id   = imager_id
        self.imager_name = imager_name
        self.sensor_mode_type = sensor_mode_type
        self.dynamicPixelBitDepth = dynamicPixelBitDepth
        self.csiPixelBitDepth = csiPixelBitDepth
        self.frameRate = frameRate

class LogLevel(object):
    debug = 1
    info = 2
    warning = 3
    error = 4
    fatal = 5

class Singleton(object):
    """ A Pythonic Singleton """
    def __new__(cls, *args, **kwargs):
        if '_inst' not in vars(cls):
            cls._inst = object.__new__(cls, *args, **kwargs)
        return cls._inst

class Logger(Singleton):
    "Logger class"

    logLevel = LogLevel.debug
    logFileHandle = None
    logFileName = "summarylog.txt"
    logWarningList = ""
    logErrorList = ""
    logFatalList = ""
    clientName = ""
    logDir = ""
    timeStamp = False

    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    def __enter__(self):
        if(self.logFileHandle == None):
            self.logDir = nvcsUtil.getLogPath()
            if(os.path.isdir(self.logDir)):
                shutil.rmtree(self.logDir + "/")

            mode = stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
            if (nvcsUtil.createDirSetMode(self.logDir, mode) != True):
                raise ValueError("Error: Could not create directory %s and set mode to %o" % (self.logDir, mode))

            logFilePath = os.path.join(self.logDir, self.logFileName)
            self.logFileHandle = open(logFilePath,"w")
        return self

    def __exit__(self, type, value, traceback):
        if (self.logFileHandle != None):
            self.logFileHandle.close()
            self.logFileHandle = None
            logFilePath = os.path.join(self.logDir, self.logFileName)

            # Set file permission to 0666
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
            if (nvcsUtil.setFileMode(logFilePath, mode) != True):
                raise ValueError("Error: Setting file %s with mode to %o" % (logFilePath, mode))


    def __getLevelString(self, level):
        if (level == LogLevel.debug):
            return "DEBUG"
        elif (level == LogLevel.info):
            return "INFO"
        elif (level == LogLevel.warning):
            return "WARNING"
        elif (level == LogLevel.error):
            return "ERROR"
        elif (level == LogLevel.fatal):
            return "FATAL"

    def setLevel(self, level):
        self.setLevel = level

    def setClientName(self, name):
        self.clientName = name

    def timeStampEnable(self):
        self.timeStamp = True

    def info(self, msg):
        self.__log(LogLevel.info, msg)

    def debug(self, msg):
        self.__log(LogLevel.debug, msg)

    def warning(self, msg):
        self.__log(LogLevel.warning, msg)

    def error(self, msg):
        self.__log(LogLevel.error, msg)

    def fatal(self, msg):
        self.__log(LogLevel.fatal, msg)

    def __log(self, level, msg):
        if (level < self.logLevel):
            return
        levelString = self.__getLevelString(level)
        timeStampString = str(datetime.datetime.now())
        levelStringMsg = "%s: %s" % (levelString, msg)

        if (level == LogLevel.warning):
            self.logWarningList += "%s         %s: %s\n" % (timeStampString, self.clientName, levelStringMsg)
        elif (level == LogLevel.error):
            self.logErrorList += "%s         %s: %s\n" % (timeStampString, self.clientName, levelStringMsg)
        elif (level == LogLevel.fatal):
            self.logFatalList += "%s         %s: %s\n" % (timeStampString, self.clientName, levelStringMsg)
        if (self.timeStamp):
            print("%s %s" % (timeStampString, levelStringMsg))
        else:
            print("%s" % (levelStringMsg))
        self.logFileHandle.write("%s %7s %s\n" % (timeStampString, levelString, msg))

    def dumpWarnings(self, header):
        if (self.logWarningList != ""):
            print("%s" % (header))
            print("%s" % (self.logWarningList))
            timeStampString = str(datetime.datetime.now())
            self.logFileHandle.write("%s         %s\n" % (timeStampString, header))
            self.logFileHandle.write("%s" % (self.logWarningList))

    def dumpErrors(self, header):
        if (self.logErrorList != ""):
            print("%s" % (header))
            print("%s" % (self.logErrorList))
            timeStampString = str(datetime.datetime.now())
            self.logFileHandle.write("%s         %s\n" % (timeStampString, header))
            self.logFileHandle.write("%s" % (self.logErrorList))

    def dumpFatals(self, header):
        if (self.logFatalList != ""):
            print("%s" % (self.logFatalList))
            timeStampString = str(datetime.datetime.now())
            self.logFileHandle.write("%s         %s\n" % (timeStampString, header))
            self.logFileHandle.write("%s" % (self.logFatalList))


class HelpFormatterWithNewLine(optparse.HelpFormatter):
    """Extend optparse.HelpFormatter to allow using
       escape sequences in options help message"""

    def __init__(self,
        indentIncrement=2,
        maxHelpPosition=24,
        width=None,
        shortFirst=1):
        optparse.HelpFormatter.__init__(
            self, indentIncrement, maxHelpPosition, width, shortFirst)

    def format_description(self, description):
        descLines = []

        for line in description.split("\n"):
            descLines.extend(self._format_text(line))

        descLines.append("\n")

        return "\n".join(descLines)

    def format_option(self, option):
        # The help for each option consists of two parts:
        #   * the opt strings and metavars
        #     eg. ("-x", or "-fFILENAME, --file=FILENAME")
        #   * the user-supplied help string
        #     eg. ("turn on expert mode", "read data from FILENAME")
        #
        # If possible, we write both of these on the same line:
        #   -x      turn on expert mode
        #
        # But if the opt string list is too long, we put the help
        # string on a second line, indented to the same column it would
        # start in if it fit on the first line.
        #   -fFILENAME, --file=FILENAME
        #           read data from FILENAME
        result = []
        opts = self.option_strings[option]
        opt_width = self.help_position - self.current_indent - 2
        if len(opts) > opt_width:
            opts = "%*s%s\n" % (self.current_indent, "", opts)
            indent_first = self.help_position
        else:                       # start help on same line as opts
            opts = "%*s%-*s  " % (self.current_indent, "", opt_width, opts)
            indent_first = 0
        result.append(opts)
        if option.help:
            help_text = self.expand_default(option)
            help_lines = []
            [help_lines.extend(
                textwrap.wrap(line, self.help_width)
            ) for line in help_text.split("\n")]
            result.append("%*s%s\n" % (indent_first, "", help_lines[0]))
            result.extend(["%*s%s\n" % (self.help_position, "", line)
                           for line in help_lines[1:]])
        elif opts[-1] != "\n":
            result.append("\n")
        return "".join(result)

    def format_usage(self, usage):
        return "Usage: %s\n" % usage

    def format_heading(self, heading):
        return "%*s%s:\n" % (self.current_indent, "", heading)

class ispFP16(object):
    "ISP_FP16 data class"
    eBits        = None
    eMask        = None
    eMax         = None
    eMin         = None
    posExpOffset = None
    negExpOffset = None
    mBits        = None
    mMask        = None
    mMax         = None
    fmBits       = None
    fmMask       = None
    feBits       = None
    fExpOffset   = None
    funcLogger   = None

    def __init__(self):
        self.eBits        = 4
        self.eMask        = (1 << self.eBits) - 1
        self.eMax         = (1 << (self.eBits - 1)) + 1
        self.eMin         = self.eMax + 1
        self.posExpOffset = 9
        self.negExpOffset = 6
        self.mBits        = 12
        self.mMask        = (1 << self.mBits) - 1
        self.mMax         = (1 << self.mBits) - 1
        self.fmBits       = 23
        self.fmMask       = (1 << self.fmBits) - 1
        self.feBits       = 8
        self.fExpOffset   = 127
        self.funcLogger = Logger()

    def convertToFP32(self, ispfpValue):
        # no chroma variation
        if None == ispfpValue:
            self.funcLogger.error("ispFp16::convertToFP32: ispfpValue is None")
            return NvCSTestResult.ERROR
        exp = None
        mantissa = None

        encodedExp = (ispfpValue >> self.mBits) & self.eMask
        sign = 1 if ((encodedExp & 0x8) and ((encodedExp & 0x6) != 0)) else 0
        encodedMantissa = (ispfpValue & self.mMax)

        if ((encodedExp == 0) or (encodedExp == 15)):
            # denormalised numbers
            mantissa = encodedMantissa << (self.fmBits - self.mBits + 1)
            if (mantissa == 0):
                # special case for both zeros
                exp = 0
            else:
                # adjust to normalized IEEE 754 exponent and mantissa
                exp = self.fExpOffset - self.posExpOffset
                # need to find most significant set bit
                while ((mantissa & (1 << self.fmBits)) == 0):
                    mantissa = mantissa << 1
                    exp = exp - 1
                mantissa = mantissa & self.fmMask
        else:
            # construct IEEE 754 exponent and mantissa from ISP_FP16
            # exponent and mantissa
            exp = ((self.fExpOffset + self.negExpOffset) -  encodedExp) if (sign == 1) \
                  else (encodedExp + (self.fExpOffset - self.posExpOffset))
            mantissa = (encodedMantissa << (self.fmBits - self.mBits)) & self.fmMask;

        # look directly at bits of realValue as an IEEE 754 encoded float
        realValue = bin((sign << (self.feBits + self.fmBits)) | (exp << self.fmBits) | mantissa)
        result = struct.unpack('!f',struct.pack('!I', int(realValue, 2)))[0]
        return result

    def findMaxPixel(self, pixelList, pixelFormat):
        if (pixelList == None) or (pixelFormat == None):
            self.funcLogger.error("None  input argument: check either pixelList or pixelFormat")
            return NvCSTestResult.ERROR

        maxExp      = 0
        maxMantissa = 0
        maxIspFP    = 0

        for ispfpValue in pixelList:
            encodedExp  = (ispfpValue >> self.mBits) & self.eMask
            encodedMantissa = (ispfpValue & self.mMax)

            # compare exponent
            if (encodedExp <= self.posExpOffset):
                if (maxExp < encodedExp):
                    maxMantissa = encodedMantissa
                    maxExp      = encodedExp
                    maxIspFP    = ispfpValue
                elif (maxExp == encodedExp):
                    # compare mantissa
                    if (maxMantissa < encodedMantissa) :
                        maxMantissa = encodedMantissa
                        maxExp      = encodedExp
                        maxIspFP    = ispfpValue
        return maxIspFP

class NvCSRawFile(nvrawfile.NvRawFile, nvrawfileV3.NvRawFileV3):
    """!
        NvCSRawFile Wrapper Class
        NvRaw_v2 and NvRawFileV3 wrapper class

        @param nvrawfile.NvRawFile : NvRaw_V2 wrapper module

        @param nvrawfileV3.NvRawFileV3 : NvRaw_V3 wrapper module
    """
    # Add all member variables from nvraw_v3
    # Add all getValue functions for nvraw_v3 to be used later

    ispFP16      = None
    logger       = None
    nvrawV3      = None
    openSuccess  = None
    className    = None

    def __init__(self):
        funcName = self.__class__.__init__.__name__
        self.className = self.__class__.__name__
        try:
            nvrawfile.NvRawFile.__init__(self)
            nvrawfileV3.NvRawFileV3.__init__(self)
            self.ispFP16 = ispFP16()
            self.logger = Logger()
            self.openSuccess = False
        except Exception as inst:
            print("ERROR: {0}::{1}: {2} ".format(self.__class__.__name__,\
                 self.__class__.__init__.__name__, str(inst)))
            raise

    def readFile(self, filename, frameNumStart = 0, numFrames = 1):
        """!
            readFile()
            open the NvRaw file; it will try to open/read the file in NvRaw_v2 or NvRaw_v3
            if the file is NvRaw_V2 format, the NvCSRawFile class will be based on NvRaw_V2 wrapper
            if the file is NvRaw_V3 format, the NvCSRawFile class will be based on NvRaw_V3 wrapper

            @param filename : path to the NvRaw file
            @param frameNumStart : starting frame of the current nvraw_v3 file
            @param numFrames : number of frames to be loaded into FrameDataReader

            @return : return true upon success
        """
        funcName = self.__class__.readFile.__name__
        try:
            # Figure out if file is nvraw_v2 or nvraw_v3
            self.openSuccess = False
            if(nvrawfile.NvRawFile.readFile(self, filename)):
                self.loadHeader()
                self.nvrawV3 = False
                self.openSuccess = True
                return True
            elif (nvrawfileV3.NvRawFileV3.readFileV3(self, filename)):
                if (nvrawfileV3.NvRawFileV3.loadNvraw(self, frameNumStart, numFrames)):
                    self.nvrawV3 = True
                    self.openSuccess = True
                    return True
            return False
        except RuntimeError as inst:
            self.logger.error("{0}::{1}: {2}".format(self.className, funcName, str(inst)))
            raise

    def convertPixelValue(self, value):
        bitShift = 0
        bps = self._bitsPerSample
        if (self._dynamicPixelBitDepth > 0):
            bps = self._dynamicPixelBitDepth

        bitSampleMultiplier = 1 << (bps -1)

        mask = (1 << bps) -1

        if (self.nvrawV3 == True):
            pixelFormat = self._pixelFormat
        elif (self._pixelFormat == nvrawfile_pinterface.NVRAWFILE_PIXEL_FORMAT_S114):
            pixelFormat = nvraw_v3.PIXEL_FORMAT_S114
        elif (self._pixelFormat == nvrawfile_pinterface.NVRAWFILE_PIXEL_FORMAT_INT16):
            pixelFormat = nvraw_v3.PIXEL_FORMAT_INT16
        elif (self._pixelFormat == nvrawfile_pinterface.NVRAWFILE_PIXEL_FORMAT_U16):
            pixelFormat = nvraw_v3.PIXEL_FORMAT_U16
        elif (self._pixelFormat == nvrawfile_pinterface.NVRAWFILE_PIXEL_FORMAT_ISPFP):
            pixelFormat = nvraw_v3.PIXEL_FORMAT_ISP_FP16
        else:
            pixelFormat = None

        if (pixelFormat == nvraw_v3.PIXEL_FORMAT_S114) :
            bitShift = 14 - bps
            if bps == 14:
                bitShift = 1
            return (value >> bitShift) & mask

        elif (self._pixelFormat == nvraw_v3.PIXEL_FORMAT_INT16) :
            # There is no conversion of individual pixel values in the array
            return (value & mask)

        elif (self._pixelFormat == nvraw_v3.PIXEL_FORMAT_U16) :
            bitShift = 16 - bps
            if bps == 14:
                # special case for 14 bits
                bitShift = 16 - 13
            return (value >> bitShift) & mask

        elif (self._pixelFormat == nvraw_v3.PIXEL_FORMAT_ISP_FP16) :
            return int(self.ispFP16.convertToFP32(value) * bitSampleMultiplier)

        else:
            raise ValueError('undefined pixel format', self._pixelFormat)

    def getPixelValue(self, x, y, frameNum = 0, planeNum = 0):
        """!
            getPixelValue()
            return the pixel value of a given x-coordinate and y-coordinate

            @param x : x-coordinate
            @param y : y-coordinate
            @param frameNum : selected frame number from the nvraw  file (v3 only)
            @param planeNum : selected plane number from the nvraw file (v3 only)

            @return : return true upon success
        """
        # In Quill, conversion is from S1.14 to INT16
        # In Galen, conversion is either U16 to INT16
        #                             or FP16 to INT16
        # Converted value is returned as integer
        #
        funcName = self.__class__.getPixelValue.__name__
        assert self._loaded != False, self.logger.error("{0}::{1}: raw file was not loaded properly".format(self.className, funcName))
        if (self.nvrawV3 == True):
            value = self._pixelData[frameNum][planeNum][y * self._width + x]
        else:
            value = self._pixelData[y * self._width + x]

        return self.convertPixelValue(value) if (False == self._pixelDataConverted) else value

    def getMaxPixelValue(self, frameNum = 0, planeNum = 0):
        """!
            getMaxPixelValue()
            return the maximum value from the file

            @param frameNum : selected frame number from the nvraw  file (v3 only)
            @param planeNum : selected plane number from the nvraw file (v3 only)

            @return : return the ConformanceTestResult.SUCCESS upon success
        """
        funcName = self.__class__.getMaxPixelValue.__name__
        if (self._loaded == False):
            self.logger.error("{0}::{1}: raw file was not loaded properly".format(self.className, funcName))
            return NVCSTestResult.ERROR

        if (self.nvrawV3 == True) and (self._pixelDataConverted == True):
            return self._maxPixelValue[frameNum][planeNum]
        elif (self._pixelDataConverted == True):
            return self._maxPixelValue

        if (self.nvrawV3 == True):
            pixelData = self._pixelDataArray[frameNum][planeNum]
        else:
            pixelData = self._pixelData

        maxPixel = -1

        if (self.nvrawV3 == True and (
                self._pixelFormat == nvraw_v3.PIXEL_FORMAT_S114 or \
                self._pixelFormat == nvraw_v3.PIXEL_FORMAT_INT16 or \
                self._pixelFormat == nvraw_v3.PIXEL_FORMAT_U16)) \
            or (self.nvrawV3 == False and (
                self._pixelFormat == nvrawfile_pinterface.NVRAWFILE_PIXEL_FORMAT_S114 or \
                self._pixelFormat == nvrawfile_pinterface.NVRAWFILE_PIXEL_FORMAT_INT16 or \
                self._pixelFormat == nvrawfile_pinterface.NVRAWFILE_PIXEL_FORMAT_U16)):
            rawMaxPixelValue = max(pixelData)
            maxPixel = self.convertPixelValue(rawMaxPixelValue)

        elif (self.nvrawV3 == True and self._pixelFormat == nvraw_v3.PIXEL_FORMAT_ISP_FP16) or \
             (self.nvrawV3 == False and self._pixelFormat == nvrawfile_pinterface.NVRAWFILE_PIXEL_FORMAT_ISPFP):
            rawMaxPixelValue = self.ispFP16.findMaxPixel(pixelData, nvraw_v3.PIXEL_FORMAT_ISP_FP16)
            bitSampleMultiplier = 1 << (bps -1)
            maxPixel = int(self.ispFP16.convertToFP32(rawMaxPixelValue) * bitSampleMultiplier)
        else:
            for x in range(self._width):
                for y in range(self._height):
                    pixelVal = self.getPixelValue(x,y)
                    maxPixel = pixelVal if (pixelVal > maxPixel) else maxPixel

        return maxPixel

    def isHDRImage(self):
        """!
            check if the raw file is in HDR format

            @return : return true if the exposure plane is > 1
        """
        funcName = self.__class__.isHDRImage.__name__
        if (self._loaded == False):
            self.logger.error("{0}::{1}: raw file was not loaded properly".format(self.className, funcName))
            return NVCSTestResult.ERROR
        # check for number of exposure planes. HDR if num > 1
        if (len(self._exposurePlaneVector) > 1):
            return True
        else:
            return False

    def loadHeader(self):
        # sensorGains
        if (self.isHDRImage()):
            self._sensorGains = self._hdrExposureInfos[0].analogGains
        # exposureTime
        if (self.isHDRImage()):
            self._exposureTime = self._hdrExposureInfos[0].exposureTime
        return True

    def getExposureTime(self, frameNum = 0, planeNum = 0):
        """!
            Returns the sensor exposure time value from the raw file metadata; the current code only
            return the exposure time value from long exposure region

            @return : sensor exposure time value
        """
        funcName = self.__class__.getExposureTime.__name__
        try:
            #TODO: add return HDR exposure in a list
            #current code only supports SDR
            expFromFile = None
            if (self.openSuccess == True):
                if (self.nvrawV3 == True):
                    expFromFile = self._frameDataReader[frameNum][planeNum].getExposureTime()
                else:
                    expFromFile = self._exposureTime
            return expFromFile
        except RuntimeError as err:
            self.logger.error("{0}::{1}: {2}".format(self.className, funcName, str(err)))
            raise

    def getSensorGain(self, frameNum = 0, planeNum = 0):
        """!
            Returns the sensor gain value from the raw file metadata; the current code only
            return the gain value from long exposure region

            @return : sensor gain value
        """
        funcName = self.__class__.getSensorGain.__name__
        try:
            #TODO: add return HDR gain in a list
            #current code only supports SDR
            gainFromFile = None
            if (self.openSuccess == True):
                if (self.nvrawV3):
                    gainFromFile = self._frameDataReader[frameNum][planeNum].getSensorGain()
                else:
                    gainFromFile = self._sensorGains[0]
            return gainFromFile
        except RuntimeError as err:
            self.logger.error("{0}::{1}: {2}".format(self.className, funcName, str(err)))
            raise

    def getFocusPosition(self):
        """!
            Returns the focus position value from the raw file metadata

            @return : focus position value
        """
        funcName = self.__class__.getFocusPosition.__name__
        try:
            focusPositionFromFile = None
            if (self.openSuccess == True):
                if (self.nvrawV3):
                    focusPositionFromFile = self._frameDataReader[0][0].getFocusPosition()
                else:
                    focusPositionFromFile = self._focusPosition
            return focusPositionFromFile
        except RuntimeError as err:
            self.logger.error("{0}::{1}: {2}".format(self.className, funcName, str(err)))
            raise

    def getPeakPixelValue(self):
        """!
            Returns the peak pixel value based on the pixel format and bit depths.
            peakvalue is different from the maxValue. peakValue takes bit depth into account
            maxValue is the highest value among capture pixels and is in the range of 0 to peakValue

            @return : peak pixel value
        """
        funcName = self.__class__.getPeakPixelValue.__name__
        try:
            peakValue = None
            if (self.openSuccess == False):
                return peakValue
            if self.nvrawV3 == True:
                peakValue = nvrawfileV3.NvRawFileV3.getPeakPixelValueV3(self)
            else:
                peakValue = nvrawfile.NvRawFile.getPeakPixelValue(self)
            return float(peakValue)
        except RuntimeError as err:
            self.logger.error("{0}::{1}: {2}".format(self.className, funcName, str(err)))
            raise

    def getDynamicBitDepth(self):
        """!
            Returns the dynamic bit depth stored in the nvraw metadata; if not available, we will
            return the dynamic bit depth based on the outputFormat

            @return : dynamic pixel bit depth
        """
        funcName = self.__class__.getDynamicBitDepth.__name__
        try:
            if (self.nvrawV3 == True):
                return self._planeHeaderReader.getDynamicPixelBitDepth()
            else:
                """
                    TODO: THis section is only supporting NvRaw_V2 SDR output format;
                    please check the sensor spec for Mobile and Automotive when
                    we are calling NvRaw_V2 HDR output format (I.E. NvRawFileOutputDataFormat_12BitCombinedCompressed)
                """
                if (self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_10BitLinear):
                    return 10
                elif (self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_12BitLinear):
                    return 12
                elif (self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_16BitLinear):
                    return 16
                elif (self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_20BitLinear):
                    return 20
                else:
                    return 16; ## assuming dynamic bit depth is 16 in the WDR_PWL sensor
                               ## TODO: refer to the sensor spec for different sensor supported in the Mobile
        except RuntimeError as err:
            self.logger.error("{0}::{1}: {2}".format(self.className, funcName, str(err)))
            raise

# times various actions within tests
class TestTimer(object):

    testName = ''
    totTime, overrideTime, capTime, mnTime, analysisTime = [0.0] * 5
    subTimers = {}

    def __init__(self, name):
        self.testName = name
        self.totTime, self.overrideTime, self.capTime, self.mnTime, self.analysisTime = [0.0] * 5

    def totTimeStart(self):
        self.totTime = time.time()
    def totTimeStop(self):
        self.totTime = time.time() - self.totTime
    def overrideTimeStart(self):
        self.overrideTime = time.time()
    def overrideTimeStop(self):
        self.overrideTime = time.time() - self.overrideTime
    def capTimeStart(self):
        self.capTime = time.time()
    def capTimeStop(self):
        self.capTime = time.time() - self.capTime
    def mnTimeStart(self):
        self.mnTime = time.time()
    def mnTimeStop(self):
        self.mnTime = time.time() - self.mnTime
    def appendTimes(self, timer2):
        if (timer2 != None):
            self.totTime += timer2.totTime
            self.overrideTime += timer2.overrideTime
            self.capTime += timer2.capTime
            self.mnTime += timer2.mnTime
    def getTimes(self):
        self.analysisTime = self.totTime - self.overrideTime - self.capTime - self.mnTime
        return [self.totTime, self.overrideTime, self.capTime, self.mnTime, self.analysisTime]

    def addSubTimer(self, name):
        self.subTimers[name] = TestTimer(name)
    def getSubTimer(self, name):
        return self.subTimers[name]
    def removeSubTimer(self, name):
        del self.subTimers[name]

    def displayResults(self, logger):
        logger.info('=============================={0} Timings=============================='.format(self.testName))
        numTests = 1
        if (len(self.subTimers) != 0):
            numTests = len(self.subTimers)
        logger.info('Total time taken for {0} test(s): {1:.4f}s'.format( numTests, self.totTime ))

        # for one individual test
        if (len(self.subTimers) == 0):
            logger.info('       * Override time:  {0:.4f}s'.format((self.getTimes())[1]))
            logger.info('       * Capture time:   {0:.4f}s'.format((self.getTimes())[2]))
            logger.info('       * Makernote time: {0:.4f}s'.format((self.getTimes())[3]))
            logger.info('       * Analysis time:  {0:.4f}s'.format((self.getTimes())[4]))

        # for all subTests
        for name, subTimer in self.subTimers.items():
            logger.info('* {0} Total time:  {1:.4f}s'.format(name, (subTimer.getTimes())[0]))
            logger.info('       * Override time:  {0:.4f}s'.format((subTimer.getTimes())[1]))
            logger.info('       * Capture time:   {0:.4f}s'.format((subTimer.getTimes())[2]))
            logger.info('       * Makernote time: {0:.4f}s'.format((subTimer.getTimes())[3]))
            logger.info('       * Analysis time:  {0:.4f}s'.format((subTimer.getTimes())[4]))
        logger.info('===================================================================================')

def terminateProcess(process, a_timeout):
    """Helper function to terminate a process call and raise an exception"""

    process.kill()
    process.terminate()
    #os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    raise Exception('Process #{0} killed after {1} seconds'.format(process.pid, a_timeout))

class NvCSIOUtil(object):
    """ A collection of IO-related methods """
    @staticmethod
    def which(name):
        """ Mimic Unix 'which' command """
        for path in os.getenv('PATH').split(os.path.pathsep):
            target = os.path.join(path, name)
            if os.path.isfile(target):
                return target
        return None

    @staticmethod
    def runCmd(cmd, pass_count=1, criteria=None, delay=1, sudo=False, os='android', logger=None, a_timeoutSec=60.0, a_shell=True):
        """Helper function to capture STDOUT/STDERR"""
        """set the default timeout to 60 seconds; timer thread will terminate the tool after 60 seconds
           NOTE: 1. subprocess.terminate() is only valid when not running under shell environment.
                 2. subprocess.timeoutExpired is not supoorted in python 2.7; hence, we are using timer thread to
                    terminate the process"""

        executable=None
        if os == 'android':
            executable="/system/bin/sh"
            cmd = "{0} -c '{1}'".format(executable, cmd)
        elif os == 'l4t':
            executable="/bin/sh"
            cmd = "{0} -c '{1}'".format(executable, cmd)
            if sudo:
                cmd = "sudo {0}".format(cmd)

        count = 0
        while True:
            if logger:
                logger.info("RUN CMD: {0}".format(cmd))
            if executable:
                p = subprocess.Popen(cmd, shell=a_shell, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, executable=executable)
            else:
                p = subprocess.Popen(cmd, shell=a_shell, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)

            try:
                timer = threading.Timer(a_timeoutSec,terminateProcess,[p, a_timeoutSec])
                timer.start()
                out, err = p.communicate()
                while p.poll() is None:
                    # wait the process to exit
                    time.sleep(delay)
                timer.cancel()
            except Exception as err:
                raise Exception('command \'{0}\' failed\n{1}'.format(cmd, err))
            returncode = p.returncode

            out = str(out.rstrip().decode())
            err = str(err.rstrip().decode())
            if logger and out:
                logger.info(out)
            if logger and err:
                logger.error(err)
            if err:
                return out, err , returncode

            if not criteria or criteria in out:
                return out, err, returncode

            count += 1
            if count >= pass_count:
                break

            time.sleep(delay)
        return out, "Trial error (attempted {0} times but failed)".format(pass_count), returncode

