#
# Copyright (c) 2013-2020, NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#

from __future__ import print_function
from __future__ import division

import array
import struct
import os
import nvcamera
import nvrawfile_pinterface

def isLegacyFormat(first8bytes):
    "Return True if header sample shows this is a legacy nvraw file"
    assert isinstance(first8bytes, bytes)

    magic,version = struct.unpack('<LL', first8bytes)
    result = (magic == 1 and (version >= 1 and version <= 4))
    return result

def isChunkyFormat(first8bytes):
    "Return True if header sample shows this is a new, chunky nvraw file"
    assert isinstance(first8bytes, bytes)

    result = (first8bytes == b'NVRAWFIL')  # First bytes are start of HeaderChunk UUID
    return result

def NV_SFX_TO_FP(s):
    "Convert 32bit SFx type to float"
    return s / 65536.0

def NV_FP_TO_SFX(f):
    "Convert float to SFx fixed point"
    return int(f * 65536 + 0.5)

def getBayerPhaseString(bayerPhase):
    "Get bayer phase string from integer"
    packedBayerPhase = struct.pack('<l', bayerPhase)
    return struct.unpack('<4s', packedBayerPhase)[0][::-1].decode()

def getBayerPhaseNumber(bayerPhaseString):
    "Get bayer phase number from string"
    packedBayerPhase = struct.pack('<4s', bayerPhaseString[::-1].encode())
    bayerPhase =  struct.unpack('<l', packedBayerPhase)[0]
    return bayerPhase

# Legacy constants
NVRAW_LEGACY_MAGIC   = 0x01
NVRAW_LEGACY_CORE_HEADER_SIZE = 4*27 # 27 DWORDs including padding and StatsStartMark
NVRAW_LEGACY_M3DATA_SIZE      = 4*(64*64)
NVRAW_LEGACY_AFINPUT_SIZE     = 4*((152*116 // 4) * 16)
NVRAW_LEGACY_SHARPNESS_SIZE   = 4*(16)

NVRAW_STATS_SENTINEL = 0xDeadBeef
NVRAW_BAYER_SENTINEL = 0xCafeFeed
INT_MAX = 0x7fffffff

# Chunk UUIDs
NvRawFileHeaderChunkUuid      = b'NVRAWFILE_111107'
NvRawFileDataChunkUuid        = b'PIXELDATA_111107'
NvRawFileCaptureChunkUuid     = b'CAPTURE___120118'
NvRawFileCameraStateChunkUuid = b'CAMSTATE__120118'
NvRawFileSensorInfoChunkUuid  = b'SENSORINFO120131'
NvRawFileHDRChunkUuid         = b'HDR_______130318'

class NvRFChunk(object):
    def __init__(self, uuid, md5, length, dataOffset):
        assert isinstance(uuid, bytes)
        self._type = uuid

        self._md5 = md5
        self._length = length
        self._dataOffset = dataOffset   # seek position in file of start of data
        self._chunkData = None

class NvRawFile(object):
    def __init__(self):
        self.odfMap = [nvrawfile_pinterface.NvRawFileOutputDataFormat_10BitLinear, \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_2x11_1, \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_3x12, \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_12BitLinear, \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_12BitCombinedCompressed, \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_12BitCombinedCompressedExtended, \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_16bitLinear, \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_16BitLogDomain, \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_16BitLogDomainExtended, \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_20BitLinear, \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_20BitLinearExtended, \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_12BitCompressed, \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_FP16,            \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_16BitCombinedCompressed, \
                       nvrawfile_pinterface.NvRawFileOutputDataFormat_Last]
        self._filename = None
        self._loaded = False
        self._width = 0
        self._height = 0
        self._bayerPhase = ""
        self._iso = 0
        self._fuseId = ""
        self._sensorId = ""
        self._bitsPerSample = 0
        self._exposureTime = 0.0
        self._awbConvergeStatus = 0
        self._awbGains = [0.0, 0.0, 0.0, 0.0]
        self._focusPosition = 0
        self._sensorGains = [0.0, 0.0, 0.0, 0.0]
        self._lux = 0.0
        self._ispDigitalGain = 0.0
        self._pixelData = array.array('H')
        self._chunks = []
        self._hdrNumberOfExposures = 0
        self._hdrReadoutScheme = None
        self._hdrExposureInfos = []
        self._pixelFormat = 'int16'
        self._ispDigitalGain = 0
        self._outputDataFormat = 0
        self._bPixelLittleEndian = 0
        #
        # Embedded top and bottom lines extracted from _pixelData32
        #
        self._embeddedLinesTop = array.array('H')
        self._embeddedLinesBottom = array.array('H')
        #
        # Embedded top and bottom line count
        #
        self._embeddedLineCountTop = 0
        self._embeddedLineCountBottom = 0

        # LUT and its array count
        self._pLut = array.array('f')
        self._lutCount = 0

        self._csiPixelBitDepth = 0
        self._dynamicPixelBitDepth = 0
        self._sensorModeType = 0
        self._zoomMotorStep = 0

        # For quick retrieval of useful frame information
        self._maxPixelValue = 0
        self._pixelDataConverted = False

    def getLegacyHeaderSize(self):
        "Returns total size of legacy header"
        # sum regions of header plus final bayer start mark dword.
        return (NVRAW_LEGACY_CORE_HEADER_SIZE + NVRAW_LEGACY_M3DATA_SIZE +
                NVRAW_LEGACY_AFINPUT_SIZE + NVRAW_LEGACY_SHARPNESS_SIZE + 4)

    def makeLegacyHeader(self):
        "Creates a byte array (array('B')) containing a full legacy nvraw header."
        if self._awbGains[0] == 0.0:
            version = 1
        else:
            version = 2
        result = array.array('B', b'\0' * self.getLegacyHeaderSize())
        # 0: magic, version, width, height
        struct.pack_into('<LLll', result, 0, NVRAW_LEGACY_MAGIC, version, self._width, self._height)
        # 16: bayer order, pad(u32), sensorGUI(U64)
        bayerPhase = getBayerPhaseNumber(self._bayerPhase)
        struct.pack_into('<Llll', result, 16, bayerPhase, 0, 0, 0)

        # 32: exp time, iso, exp comp, illuminant, focus pos
        struct.pack_into('<lllfL', result, 32,
                         NV_FP_TO_SFX(self._exposureTime), self._iso,
                         NV_FP_TO_SFX(0.0), 0, 0)
        # 52: ispRgbGains[4]
        struct.pack_into('<llll', result, 52, 0, 0, 0, 0)
        # 68: sensorGains[4], sensorExposure
        struct.pack_into('<fffff', result, 68, 0.0, 0.0, 0.0, 0.0, 0.0)
        # 88: additionalDebug
        struct.pack_into('<16s', result, 88, b'\0' * 16)
        # 104: statsStartMark
        struct.pack_into('<L', result, 104, NVRAW_STATS_SENTINEL)
        offset = 108

        # append m3stats
        #...
        offset += NVRAW_LEGACY_M3DATA_SIZE

        # append afinput / AWB state info if available
        if version >= 2:
            struct.pack_into('<fflLffff', result, offset,
                             0.0, 0.0, # lastGoodGuess[2]
                             0, # foundSaneGraypoint
                             self._awbConvergeStatus,
                             self._awbGains[0], self._awbGains[1],
                             self._awbGains[2], self._awbGains[3],)
        offset += NVRAW_LEGACY_AFINPUT_SIZE

        # append sharpness
        #...
        offset += NVRAW_LEGACY_SHARPNESS_SIZE

        # append bayerStartMark
        struct.pack_into('<L', result, offset, NVRAW_BAYER_SENTINEL)
        return result

    def _loadLegacyFile(self, infile):
        awbStateSize = 4*8 # fflLffff
        # read it in
        infile.seek(0, os.SEEK_SET)
        coreHeader = infile.read(NVRAW_LEGACY_CORE_HEADER_SIZE)
        infile.seek(NVRAW_LEGACY_M3DATA_SIZE, os.SEEK_CUR)  # skip this blob
        afinput = infile.read(NVRAW_LEGACY_AFINPUT_SIZE)  # Union that contains AWB state
        infile.seek(NVRAW_LEGACY_SHARPNESS_SIZE, os.SEEK_CUR) # skip this blob too
        bayerStartMark = struct.unpack('<L', infile.read(4))[0]
        # Ensure the file structure is accurate by checking bayerStartMark
        if bayerStartMark != NVRAW_BAYER_SENTINEL:
            return False
        # File is as self-consistent as we can confirm, so convert data.
        magic,version = struct.unpack('<ll', coreHeader[0:8])
        print("INFO: Legacy magic %d version %d" % (magic,version))
        self._width,self._height = struct.unpack('<ll', coreHeader[8:16])
        bayerPhase = struct.unpack('<L', coreHeader[16:20])[0]
        self._bayerPhase = getBayerPhaseString(bayerPhase)
        self._exposureTime,self._iso = struct.unpack('<ll', coreHeader[32:40])
        self._exposureTime = NV_SFX_TO_FP(self._exposureTime)

        # unpack ispRgbGains, focusPosition and sensorGains
        self._focusPosition = struct.unpack('<L', coreHeader[48:52])[0]
        ispRgbGains = struct.unpack('<llll', coreHeader[52:68])
        self._sensorGains = struct.unpack('<ffff', coreHeader[68:84])

        if version >= 2:
            # Now convert AWB state data in afinput union
            fields = struct.unpack('<fflLffff', afinput[0:awbStateSize])
            self._awbConvergeStatus = fields[3]
            self._awbGains = fields[4:]

        # Read in pixel data directly:
        #
        self._pixelData = array.array('H')  # H = unsigned short
        self._pixelData.fromfile(infile, self._width * self._height)

        self.adjustPixelData()
        self._bitsPerSample = 10 #legacy format does not have this info so we are assuming a 10 bit raw

        # Done.
        self._loaded = True
        return True

    def _loadChunkyFile(self, infile):
        # Get total file length
        infile.seek(0, os.SEEK_END)
        fileLength = infile.tell()
        infile.seek(0, os.SEEK_SET)
        filePos = 0
        # Read each chunk from the file
        while (fileLength - filePos) >= 36:
            # read header info: UUID(16) + MD5(16) + length(4)
            uuid = infile.read(16)
            md5digest = infile.read(16)
            chunkLength = struct.unpack('<L', infile.read(4))[0]
            chunk = NvRFChunk(uuid, md5digest, chunkLength, infile.tell())
            self._chunks.append(chunk)
            # Advance to next chunk by either seek() or read()
            chunk._chunkData = infile.read(chunkLength)
            filePos = infile.tell()
        #if filePos != fileLength:
        #    print "INFO: File corruption detected, rest of file skipped"
        for chunk in self._chunks:
            #print "Next chunk type is", chunk._type, "length:", chunk._length
            if chunk._type == NvRawFileHeaderChunkUuid:
                self._unmarshalHeaderChunk(chunk)
            elif chunk._type == NvRawFileDataChunkUuid:
                self._unmarshalDataChunk(chunk)
            elif chunk._type == NvRawFileCaptureChunkUuid:
                self._unmarshalCaptureChunk(chunk)
            elif chunk._type == NvRawFileCameraStateChunkUuid:
                self._unmarshalCameraStateChunk(chunk)
            elif chunk._type == NvRawFileSensorInfoChunkUuid:
                self._unmarshalSensorInfoChunk(chunk)
            elif chunk._type == NvRawFileHDRChunkUuid:
                self._unmarshalHDRChunk(chunk)
        # Done.
        self._loaded = True
        self._chunks = []    # free up memory by ditching chunks
        return True

    def _unmarshalHeaderChunk(self, chunk):
        # See nvrawfile.h for structures.
        # width,height,dataFormat,bitsPerSample,samplesPerpixel,numImages,time(S),time(ms),flags
        fields = struct.unpack('<lllllllll', chunk._chunkData)
        self._width = fields[0]
        self._height = fields[1]
        self._bayerPhase = getBayerPhaseString(fields[2])
        self._bitsPerSample = fields[3]
        return

    def _unmarshalDataChunk(self, chunk):
        # version,ordinal,pixelData
        version = struct.unpack('<l', chunk._chunkData[0:4])[0]
        if version == 1:
            ordinal = struct.unpack('<l', chunk._chunkData[4:8])[0]
            self._pixelData = array.array('H', chunk._chunkData[8:])
            self.adjustPixelData()
        return

    def _unmarshalCaptureChunk(self, chunk):
        # vers, expTime, expComp,iso,focusPos,snr, lux, sensorGains,flashPower,
        version = struct.unpack('<L', chunk._chunkData[0:4])[0]
        offset = 0
        if version >= 2:
            fields = struct.unpack('<LffLlfffffffff', chunk._chunkData[:4*14])
            self._exposureTime = fields[1]
            expComp = fields[2]
            self._iso = fields[3]
            self._focusPosition = fields[4]
            snr = fields[5]
            self._lux = fields[6]
            self._sensorGains = fields[7:11]
            flashPower = fields[11]
            flashToAmbientLightRatio = fields[12]
            frameRate = fields[13]
            offset += 4*14

        if version >= 3:
            fields = struct.unpack('<L', chunk._chunkData[offset:offset+4])
            rollingShutterLength = fields[0]
            offset += 4

        if version >= 4:
            self._pixelFormat,length = self._unmarshalString(chunk._chunkData[offset:-4])
            offset += length

        if version >= 5:
            self._ispDigitalGain = struct.unpack('<f', chunk._chunkData[offset:offset+4])[0]
            offset += 4

        if version >= 6:
            #
            # outputDataFormat          4     L
            # bPixelLittleEndian        1     B
            # embeddedLineCountTop      4     L
            # embeddedLineCountBottom   4     L
            # pLut                      4     LFFFFF...
            #
            self._outputDataFormat = struct.unpack('<L', chunk._chunkData[offset:offset+4])[0]
            # print "outputDataFormat from file " + str(self._outputDataFormat)
            odfMapFound = False
            for i in range(len(self.odfMap)) :
                if self.odfMap[i] == self._outputDataFormat :
                    odfMapFound = True
                    break
            if odfMapFound is False :
                errorMsg = "ERROR: [%s] cannot find correct matching NvCameraTools.outputDataFormat of " % os.path.basename(__file__)
                errorMsg += "NvRaw.outputDataFormat enum(%s)" % self._outputDataFormat
                print (repr(errorMsg))
            offset += 4
            self._bPixelLittleEndian = struct.unpack('<B', chunk._chunkData[offset:offset+1])[0]
            offset += 1
            self._embeddedLineCountTop = struct.unpack('<L', chunk._chunkData[offset:offset+4])[0]
            offset += 4
            self._embeddedLineCountBottom = struct.unpack('<L', chunk._chunkData[offset:offset+4])[0]
            offset += 4

            # _unmarshalLut returns the total length that includes the LUT size field as well.
            # We need to subtract the size field to get the actual LUT block size.
            #
            length = self._unmarshalLut(chunk._chunkData[offset:])
            offset += length
            self._lutCount = length - 4

            # We are keeping a count of values here. Convert byte count to array count
            self._lutCount = self._lutCount // 4

            # print "Lut count " + str(self._lutCount)
            # print "Lut Bytes " + str(self._pLut[0]) + " " + str(self._pLut[1]) + " " + str(self._pLut[2]) + " .... " + str(self._pLut[self._lutCount-1])
        if version >= 7:
            #
            # csiPixelBitDepth          4     L
            # dynamicPixelBitDepth      4     L
            # sensorModeType            4     L
            # zoomMotorStep             4     L
            #
            self._csiPixelBitDepth = struct.unpack('<L', chunk._chunkData[offset:offset+4])[0]
            offset += 4
            self._dynamicPixelBitDepth = struct.unpack('<L', chunk._chunkData[offset:offset+4])[0]
            offset += 4
            self._sensorModeType = struct.unpack('<L', chunk._chunkData[offset:offset+4])[0]
            offset += 4
            self._zoomMotorStep = struct.unpack('<L', chunk._chunkData[offset:offset+4])[0]
            offset += 4
        return

    def _unmarshalCameraStateChunk(self, chunk):
        # vers,convergeStatus,gains[4]
        version = struct.unpack('<l', chunk._chunkData[0:4])[0]
        if version == 1:
            fields = struct.unpack('<llffff', chunk._chunkData)
            self._awbConvergeStatus = fields[1]
            self._awbGains = fields[2:]
        return

    def _unmarshalSensorInfoChunk(self, chunk):
        # version, sensorID, fuseId, moduleId
        offset = 0
        version = struct.unpack('<l', chunk._chunkData[offset:offset+4])[0]
        offset = offset + 4
        if version == 1:
            # sensorId
            length = struct.unpack('<l', chunk._chunkData[offset:offset+4])[0]
            offset = offset + 4
            format = '<' + str(length) + 's'
            self._sensorId = struct.unpack(format, chunk._chunkData[offset:offset+length])[0]
            offset = offset + length
            # fuseId
            length = struct.unpack('<l', chunk._chunkData[offset:offset+4])[0]
            offset = offset + 4
            format = '<' + str(length) + 's'
            self._fuseId = struct.unpack(format, chunk._chunkData[offset:offset+length])[0]
            offset = offset + length
            # moduleId (ignoring for the time being)
        return

    def _unmarshalString(self, buffer):
        """Strings are represented by a 32-bit LE unsigned, followed by that number of ASCII chars.
        Returns a (string,len) tuple."""
        stringLength = struct.unpack('<l', buffer[0:4])[0]
        format = "<%ds" % (stringLength)

        string = struct.unpack(format, buffer[4:4+stringLength])[0].decode()
        dataLength = stringLength + 4

        return (string, dataLength)

    def _unmarshalHDRChunk(self, chunk):
        # version, num exposures, readout scheme, exposure info structs
        offset = 0
        version = struct.unpack('<l', chunk._chunkData[offset:offset+4])[0]
        offset = offset + 4
        # for all versions:
        # int
        self._hdrNumberOfExposures = struct.unpack('<l', chunk._chunkData[offset:offset+4])[0]
        offset = offset + 4
        # string
        self._hdrReadoutScheme,length = self._unmarshalString(chunk._chunkData[offset:])
        offset = offset + length
        # extract exposure structs
        for i in range(self._hdrNumberOfExposures):
            infoStruct = hdrInfo()
            # Read symbol and 3 pad
            infoStruct.symbol = struct.unpack('<4s', chunk._chunkData[offset:offset+4])[0]
            offset = offset + 4
            # Read exposure time, 4 analog gains, 4 digital gains
            infoStruct.exposureTime = struct.unpack('<f', chunk._chunkData[offset:offset+4])[0]
            offset = offset + 4
            for j in range(4):
                infoStruct.analogGains[j] = struct.unpack('<f',chunk._chunkData[offset:offset+4])[0]
                offset = offset + 4
            for j in range(4):
                infoStruct.digitalGains[j] = struct.unpack('<f',chunk._chunkData[offset:offset+4])[0]
                offset = offset + 4
            if version >= 2:
                # NVRF_HDR_VERSION >= 2
                for j in range(4):
                    infoStruct.awbGains[j] = struct.unpack('<f',chunk._chunkData[offset:offset+4])[0]
                    offset = offset + 4
                self.bConversionGain = struct.unpack('<L', chunk._chunkData[offset:offset+4])[0]
                offset = offset + 4
            self._hdrExposureInfos.append(infoStruct)
        return

    def _unmarshalLut(self, buffer):
        """Lut has a 32 bit length (byteCount) followed by the stream of bytes.
        Returns a (buffer,len) tuple."""

        # First obtain the length field
        length = struct.unpack('<l', buffer[0:4])[0]

        self._pLut = array.array("f", buffer[4:4+length])

        # Following returns length+4 as length. The caller needs to
        # treat 4 bytes as the size of length field and remaining
        # as the actual data.
        return length + 4

    def readFile(self, filename):
        """Attempt to load an NVRAW file.
        Returns True if successful, or False if not.
        """
        result = False
        try:
            infile = open(filename, 'rb')
            first8bytes = infile.read(8)
            if isLegacyFormat(first8bytes):
                result = self._loadLegacyFile(infile)
            elif isChunkyFormat(first8bytes):
                result = self._loadChunkyFile(infile)
            infile.close()
        except Exception as e:
            print("ERROR: ", str(e))
        return result

    def adjustPixelData(self):
        """Adjust pixel data by taking into account embedded lines at the top
        and bottom
        """
        # print "Original: Width " + str(self._width) + " Height " + str(self._height) + \
        #       " embLineCountTop " + str(self._embeddedLineCountTop) + \
        #       " embLineCountBottom " + str(self._embeddedLineCountBottom) + \
        #       " size of _pixelData " + str(len(self._pixelData))

        if (self._embeddedLineCountTop > 0 or self._embeddedLineCountBottom > 0):
            # print "Copying Embedded Top: From 0 to %u" % ((self._width * self._embeddedLineCountTop) -1)
            self._embeddedLinesTop = self._pixelData[0 : (self._width * self._embeddedLineCountTop)]

            # print "Copying Embedded bottom: From %u to %u" % (((self._height - self._embeddedLineCountBottom) * self._width), (self._height * self._width) -1);
            self._embeddedLinesBottom = self._pixelData[((self._height - self._embeddedLineCountBottom) * self._width) : \
                                                        (self._height * self._width)]

            # print "Copying Pixel data: From %u to %u" % (((self._width * self._embeddedLineCountTop)), \
            #                                ((self._height - self._embeddedLineCountBottom) * self._width));
            self._pixelData = self._pixelData[(self._width * self._embeddedLineCountTop) : \
                                  ((self._height - self._embeddedLineCountBottom) * self._width)]

            # print "Adjusted values: size of embTop " + str(len(self._embeddedLinesTop)) + \
            #      " size of embBottom " + str(len(self._embeddedLinesBottom)) + \
            #      " size of _pixelData " + str(len(self._pixelData))

            # print "\t _embeddedLinesTop [0 : " + str(((self._width * self._embeddedLineCountTop))) +  " ] "
            # print "\t _embeddedLinesBottom [" + str(((self._height - self._embeddedLineCountBottom) * self._width)) + \
            #         " : " + str((self._height * self._width)) + " ]"

            self._height = self._height - (self._embeddedLineCountTop + self._embeddedLineCountBottom)

            # print "\t Width " + str(self._width) + " Height " + str(self._height)

        self._pixelDataConverted = False

        # Now uncompress the data if it is compressed
        isCompr = self.isCompressed()
        if (isCompr == True):
            pixelDataF32 = array.array('f', self._pixelData)
            # map() from unsigned short to float had issues and would result
            # in error in swig function during the call to NvRawFile_decompress_direct
            # Hence using a loop to copy each pixel.
            # pixelDataF32 = map(float, self._pixelData)

            # Decompressed output data will be in self._pixelData
            nvrawfile_pinterface.NvRawFile_decompress_direct(self._pLut, \
                                                             self._height, self._width,   \
                                                             self._pixelData, self._outputDataFormat, pixelDataF32, self._pixelFormat)

            # The pixel values will be normalized to 1 (values from 0.0000 to 1.0000) in the function
            # NvRawFile_decompress_direct. We need to scale these values back to the bitDepth
            # Ex: For IMX185 Mode 4 (12 bit combined compressed), Dynamic bit depth is 16
            # and CSI bit depth is 12. getPeakPixelValue() below will return 2^16 -1 = 65535
            # Pixel values here will be scaled from the range of 0.0000 to 1.0000 to 0.0 to 65535.0
            #
            peakValue = self.getPeakPixelValue()

            # Redefine the array as the long type this time. After decompression, integer values are bigger
            # and we need to fit these back into the integer space holders.
            self._pixelData = array.array('L')

            maxValue = 0.0
            maxValueScaled = 0.0
            for i in range(self._width * self._height):
                val = pixelDataF32[i]
                if (val > maxValue):
                    maxValue = val

                val = pixelDataF32[i] * float(peakValue)
                self._pixelData.append(int(val))
                if (val > maxValueScaled):
                    maxValueScaled = val

            self._maxPixelValue = int(maxValueScaled)
            self._pixelDataConverted = True

            # Set the pixel format to Int16 from here onwards
            self._pixelFormat = nvrawfile_pinterface.NVRAWFILE_PIXEL_FORMAT_INT16

            # print "adjustPixelData: peakValue %u maxValue %4.4f maxValueScaled %4.4f" % \
            #            (peakValue, maxValue, maxValueScaled)
            # print "nvrawfile.py: pixelDataF32 After multiplying with bitDepth: maxValue %u " % (maxValue)
            # print ("%03.4f %03.4f %03.4f %03.4f %03.4f %03.4f %03.4f %03.4f " % (pixelDataF32[0], pixelDataF32[1], pixelDataF32[2], pixelDataF32[3], pixelDataF32[4], pixelDataF32[5], pixelDataF32[6], pixelDataF32[7]))


    def isCompressed(self):
        """ Returns true if the passed output data format is compressed
        """
        if (self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_12BitCombinedCompressed or \
            self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_12BitCombinedCompressedExtended or \
            self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_12BitCompressed or \
            self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_16BitCombinedCompressed or \
            self._dynamicPixelBitDepth > self._csiPixelBitDepth):
            return True

        return False

    def getPeakPixelValue(self):
        """ Returns the peak pixel value based on the pixel format and bit depths.
            peakvalue is different from the maxValue. peakValue takes bit depth into account
            maxValue is the highest value among capture pixels and is in the range of 0 to peakValue
        """
        if (self._dynamicPixelBitDepth > self._csiPixelBitDepth):
            # For newer versions of capture chunk that support these two
            peakValue = self._dynamicPixelBitDepth
        elif (self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_12BitCombinedCompressed or \
              self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_12BitCombinedCompressedExtended or \
              self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_12BitCompressed):
            peakValue = 16
        elif (self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_16BitCombinedCompressed):
            peakValue = 20
        elif (self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_12BitLinear):
            peakValue = 12
        elif (self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_16bitLinear):
            peakValue = 16
        elif (self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_20BitLinear or \
              self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_20BitLinearExtended):
            peakValue = 20
        elif (self._outputDataFormat == nvrawfile_pinterface.NvRawFileOutputDataFormat_10BitLinear):
            peakValue = 10

        peakValue = (1 << peakValue) -1

        return float(peakValue)

    def getActualBitsPerSample(self):
        """ Returns the bit depth
        """
        if (self._dynamicPixelBitDepth > 0):
           return self._dynamicPixelBitDepth
        return self._bitsPerSample


class hdrInfo(object):
    def __init__(self):
        self.symbol = ""
        self.exposureTime = 0.0
        self.analogGains = [0.0, 0.0, 0.0, 0.0]
        self.digitalGains = [0.0, 0.0, 0.0, 0.0]
        self.awbGains = [0.0, 0.0, 0.0, 0.0]
        self.bConversionGain = 0
