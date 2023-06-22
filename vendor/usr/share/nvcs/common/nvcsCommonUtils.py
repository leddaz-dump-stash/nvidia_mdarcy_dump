# Copyright (c) 2017-2020 NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#

from __future__ import print_function

import nvcamera
import os
import sys
import time
import errno

class Timer(object):
    "Profile Timer class"
    verboseFlag = False
    start = 0
    end   = 0
    secs  = 0.0

    def __init__ (self, verboseFlag = False, functionName = None) :
        self.verboseFlag  = verboseFlag
        self.functionName = functionName

    def __enter__(self):
        if self.verboseFlag:
            self.start = time.time()
    def __exit__(self, *args):
        if self.verboseFlag :
            self.end = time.time()
            self.secs = self.end - self.start
            print('[%s] elapsed time: %f second(s)' % (self.functionName, self.secs))

class NVCSutil(object):
    "NVCS utility class"
    info   = None
    oGraph = None
    osName = ""
    qnxNvCamTopDirEnvVariable = "NVCAM_TOP_DIR"

    def __init__(self):
        self.oGraph = nvcamera.Graph()
        self.info = self.oGraph.getInfo()

    def isAndroid(self):
        return (self.info.osInfo.osID == nvcamera.NvctOsID_Android)

    def isL4T(self):
        return (self.info.osInfo.osID == nvcamera.NvctOsID_L4T)

    def isEmbeddedLinux(self):
        return (self.info.osInfo.osID == nvcamera.NvctOsID_Embedded_Linux)

    def isEmbeddedQNX(self):
        return (self.info.osInfo.osID == nvcamera.NvctOsID_QNX)

    def isEmbeddedOS(self):
        return (self.isEmbeddedLinux() or self.isEmbeddedQNX())

    def isMobile(self):
        return (self.isL4T() or self.isAndroid())

    def getOsName(self):
        if (self.osName == "" and self.info.osInfo.osInfoAvailable == 1):
            if (self.info.osInfo.osID == nvcamera.NvctOsID_Android):
                self.osName = "Android"
            elif (self.info.osInfo.osID == nvcamera.NvctOsID_L4T):
                self.osName = "L4T"
            elif (self.info.osInfo.osID == nvcamera.NvctOsID_Embedded_Linux):
                self.osName = "Embedded Linux"
            elif (self.info.osInfo.osID == nvcamera.NvctOsID_QNX):
                self.osName = "Embedded QNX"
            else:
                self.osName = "Unsupported OS. Id: " + str(self.info.osInfo.osID)
        return self.osName

    def getQnxTopDirEnvVariable(self):
        return self.qnxNvCamTopDirEnvVariable;

    def getQnxTopFolder(self):
        qnxTopFolder = os.environ.get(self.getQnxTopDirEnvVariable())
        if qnxTopFolder:
            print("Environment variable %s is found, value %s" % (self.getQnxTopDirEnvVariable(), qnxTopFolder))
        else:
            # Return the default value
            qnxTopFolder = '/mnt/nvidia/nvcam'
            print("Environment variable %s is not found, Returning default value %s" % (self.getQnxTopDirEnvVariable(), qnxTopFolder))
        return qnxTopFolder


    def getCaptureScriptLogPath(self):
        if self.isAndroid():
            return '/data/vendor/nvcam/NVCSCapture'
        elif self.isEmbeddedLinux():
            return '/opt/nvidia/nvcam/NVCSCapture'
        elif self.isEmbeddedQNX():
            return self.getQnxTopFolder() + '/NVCSCapture'
        elif self.isL4T():
            return '/var/nvidia/nvcam/NVCSCapture'
        else:
            raise ValueError("Not a recognized OS. Cannot determine correct output path.")

    def getExecutablePath(self):
        if (self.isAndroid()):
            return '/system/vendor/bin'
        elif (self.isL4T()):
            return '/usr/sbin'
        else:
            raise ValueError("getExecutablePath: Error getting executable path. Unrecognized OS")

    # Peer function to getToolsTopPath()
    # Path to writable location for temporary files
    def getWritableTopPath(self):
        if (self.isAndroid()):
            return '/data/vendor/nvcam'
        elif (self.isL4T()):
            return '/var/nvidia/nvcam'
        elif (self.isEmbeddedLinux()):
            return '/opt/nvidia/nvcam'
        elif (self.isEmbeddedQNX()):
            return self.getQnxTopFolder()
        else:
            raise ValueError("getWritableTopPath: Error getting writable top path. Unrecognized OS")

    def getToolsTopPath(self):
        if (self.isAndroid()):
            return '/data/vendor/nvcam'
        elif (self.isEmbeddedLinux()):
            return '/opt/nvidia/nvcam'
        elif (self.isEmbeddedQNX()):
            return '/opt/nvidia/nvcam'
        elif (self.isL4T()):
            return '/var/nvidia/nvcam'
        else:
            raise ValueError("getToolsTopPath: Error getting tools path. Unrecognized OS")

    def getNVCSPath(self):
        toolsTop = self.getToolsTopPath()
        if (self.isAndroid()):
            return '/vendor/usr/share/nvcs'
        elif (self.isL4T() or
              self.isEmbeddedLinux() or
              self.isEmbeddedQNX()):
            return toolsTop + '/apps/nvcs'
        else:
            raise ValueError("Not a recognized OS.  Cannot determine correct tools path.")

    def getCameraDevicePath(self):
        if (self.isAndroid()):
            return '/dev/camera'
        elif (self.isL4T()):
            return '/dev'
        else:
            raise ValueError("getCameraDevicePath: Error getting device path. Unrecognized OS")

    def getLogPath(self):
        return self.getWritableTopPath() + '/output/NVCSTest'

    def getOutputDir(self):
        return self.getWritableTopPath() + '/output'

    def getInputDir(self):
        return self.getWritableTopPath() + '/input'

    def getSettingsDir(self):
        return self.getWritableTopPath() + '/settings'

    def getSettingsDir(self):
        return self.getWritableTopPath() + '/settings'

    #
    # createDirSetMode creates a directory (and top level directories in the path)
    # and sets the mode
    #
    def createDirSetMode(self, dirName, mode):
        try:
            os.makedirs(dirName)
            os.chmod(dirName, mode)
        except OSError as e:
            if (e.errno == errno.EACCES):
                print("createDirSetMode: Permission error while creating directory %s" % dirName)
            else:
                print("createDirSetMode: Error while creating directory %s" % dirName)
            print("createDirSetMode: Please make sure that this directory is writable or set the environmental variable %s" % self.getQnxTopDirEnvVariable())
            print("Example: export %s=/mnt/nvidia/nvcam" % self.getQnxTopDirEnvVariable())
            return False

        st = os.stat(dirName)
        return bool((st.st_mode & mode) == mode)

    #
    # setFileMode sets the mode for an existing file
    #
    def setFileMode(self, fileName, mode):
        try:
            os.chmod(fileName, mode)
            st = os.stat(fileName)
        except OSError as e:
            if (e.errno == errno.EACCESS):
                print("setFileMode: Permission error during chmod on file %s" % fileName)
            else:
                print("setFileMode: Error chmod on file %s" % fileName)
            return false
        return bool((st.st_mode & mode) == mode)

