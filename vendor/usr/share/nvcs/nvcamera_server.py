# Copyright (c) 2012-2018 NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#

# note, if you're using an old version of android, you need to run:
# adb push nvcamera_server.py /vendor/usr/share/nvcs/nvcamera_server.py
# for L4T: /home/ubuntu/nvcs/nvcamera_server.py, or /var/nvidia/nvcam/apps/nvcs

import sys
# Specify the python library search paths for softfp, hardfp, aarch64
sys.path.append('/usr/lib/arm-linux-gnueabi/tegra')
sys.path.append('/usr/lib/arm-linux-gnueabihf/tegra')
sys.path.append('/usr/lib/aarch64-linux-gnu/tegra')

import nvcamera
import socket
import traceback
import os
import os.path
import shutil
import struct
import string
import time
import re


class SocketStream:
    "Socket stream class"
    sock = None
    sockBufSize = None

    def __init__(self, sock):
        self.sock = sock
        self.sockBufSize = 4096

    def receiveMessage(self):
        # get message length
        msglen  = self.getInt()
        if not msglen: return None
        #print msglen

        readin  = 0
        msg = ""

        # get the message content
        while(msglen > readin):
            try:
                recvedmsg = self.sock.recv(self.sockBufSize)
                msg = msg + recvedmsg
                readin = readin + len(msg)
            except socket.errorTab, msg:
                msg = None

        return msg

    def sendMessage(self, msg):
        # send message length
        msglen = len(msg);
        #print msglen

        # convert to network byte order
        msglen = struct.pack('!i', msglen)
        self.sock.sendall(msglen)

        #print msg

        # send message
        self.sock.sendall(msg)

    def getInt(self):
        bytes = self.sock.recv(4)
        if not bytes: return None
        intVal = struct.unpack('!i', bytes[:4])[0]
        #print intVal
        return intVal


class nvCameraServerImpl:
    "nvcamera Server implementaion class"

    graph = None
    camera = None
    imageDir =  None

    def __init__(self):
        self.graph = nvcamera.Graph()
        self.camera = nvcamera.Camera()
        self.system = System(self.camera, self.graph)

    def executeCommand(self, command):
        "execute command received from server"

        retVal =  None
        cmdObj = string.split(command, '.')

        if cmdObj[0] == 'camera' and cmdObj[1].startswith("still"):
            # prepend the image directory to the image filename
            command = re.sub( \
                            r'camera.still\(\"(.*)\"(,?)\s*(.*)\)', \
                            "camera.still(\"%s/\\1\"\\2\\3)" % self.imageDir, \
                            command \
                        )

        if cmdObj[0] == 'graph' or cmdObj[0] == 'camera' or cmdObj[0] == 'system':
            command = 'self.' + command

        retVal = eval(command)
        return retVal

    def setImageDir(self, imageDir):
        self.imageDir = imageDir

    def getOsId(self):
        info = self.graph.getInfo()
        if (info.osInfo.osInfoAvailable):
            return info.osInfo.osID
        else:
            raise RuntimeError("os info not available!!")

class nvCameraServer:
    "nvcamera Server class"
    oServerImpl = None

    # socket
    sock = None
    port = None
    host = None
    sockStream = None
    imageDir = None

    def __init__(self, host = '0.0.0.0', port = 12321):
        self.oServerImpl = nvCameraServerImpl()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = int(port)

    def startServer(self):
        # create the nvcc_test_images directory
        # if it doesn't exist
        # delete nvcc directory otherwise
        if (self.oServerImpl.getOsId() == nvcamera.NvctOsID_Android):
            if os.path.exists('/data/nvcc'):
                shutil.rmtree('/data/nvcc/')
            os.mkdir('/data/nvcc/')
            self.imageDir = "/data/nvcc"
        elif (self.oServerImpl.getOsId() == nvcamera.NvctOsID_L4T or \
              self.oServerImpl.getOsId() == nvcamera.NvctOsID_Embedded_Linux or \
              self.oServerImpl.getOsId() == nvcamera.NvctOsID_QNX):
            homeDirectory = os.environ["HOME"]
            self.imageDir = homeDirectory + "/" + "nvcc/"
            if os.path.exists(self.imageDir):
                shutil.rmtree(self.imageDir)
            os.mkdir(self.imageDir)
        else:
            raise RuntimeError("This OS is not supported!")

        self.oServerImpl.setImageDir(self.imageDir)

        # associate the socket with the port
        self.sock.bind((self.host, self.port))

        # accept call from a client
        self.sock.listen(1)
        conn, addr = self.sock.accept()

        #print 'client is at', addr

        # create a file like object
        self.sockStream = SocketStream(conn)

        while 1:
            #print "waiting to receive message..."
            cmd = self.sockStream.receiveMessage()
            #print "received %s..." % cmd
            if not cmd: break

            cmd = string.strip(cmd)
            if (cmd != '') and (cmd[:1] != '#'):
                #print "Executing command: %s" % cmd
                if (cmd[:4] == 'pull'):
                    #print "pulling the file:" + cmd[5:]
                    self.sendfile(cmd[5:], conn)
                else:
                    try:
                        # execute the command string
                        retVal = self.oServerImpl.executeCommand(cmd)
                    except Exception, err:
                        msgstr = 'Exception ' + str(err)
                        self.sockStream.sendMessage(msgstr)
                    else:
                        msgstr = self.getStrFromReturnValue(retVal)
                        self.sockStream.sendMessage(msgstr)

            else:
                self.sockStream.sendMessage(cmd)

        # delete nvcc directory
        shutil.rmtree(self.imageDir)

        conn.close()

    def sendfile(self, filename, conn):
        #print 'dirName: %s' % dirName
        fname = os.path.join(self.imageDir, filename)
        print fname
        if os.path.exists(fname):
            pass
        else:
            fileList = os.listdir(dirName)
            print "%s/%s" % (dirName, fileList[0])
            if os.path.exists(os.path.join(self.imageDir, fileList[0])):
                fname = os.path.join(self.imageDir, fileList[0])
            else:
                err = "Error: file %s doesn't exist\n" % fname
                self.sockStream.sendMessage('Exception ' + str(err))
                return
        #print 'filename: ' + fname
        fin = open(fname, 'rb')

        data = fin.read()
        self.sockStream.sendMessage(data)

        #print 'sent image: %s' % fname
        fin.close()

        # removing the file after sending it back to client
        os.remove(fname)

    def getStrFromReturnValue(self, value):
        strRetValue = 'None'

        if(isinstance(value, int)):
            strRetValue = 'int ' + str(value)
            return strRetValue
        elif(isinstance(value, str)):
            strRetValue = 'string ' + value
            return strRetValue
        elif(isinstance(value, float)):
            strRetValue = 'float ' + str(value)
            return strRetValue
        elif(isinstance(value, list)):
            # check for the first value of the list
            # to determine if it is a number or string array or vfloat
            strRetValue = 'array '
            if(len(value) != 0):
                if(isinstance(value[0], int)):
                    strRetValue += 'int '
                    strRetValue += ' '.join([`litem` for litem in value])
                    return strRetValue
                elif(isinstance(value[0], float)):
                    strRetValue += 'float '
                    strRetValue += ' '.join([`litem` for litem in value])
                    return strRetValue
                elif(isinstance(value[0], list) and isinstance(value[0][0], float)):
                    strRetValue += 'vfloat '
                    for i in range(len(value)):
                       strRetValue += 'beginarray '
                       strRetValue += ' '.join([`litem` for litem in value[i]])
                       strRetValue += ' '
                    return strRetValue
                else:
                    strRetValue += 'string '
                    strRetValue += ' '.join([`litem` for litem in value])
                    return strRetValue
            # this should never happen
            else:
                raise Exception("List is empty")

        else:
            return strRetValue

    def startDebugServer(self, filename):
        "starts debug server which basically \
         reads a file and interprets it line by line."

        filero = open(filename)

        for line in filero:
            line = line.strip()
            print "Line: %s" % line
            if (line != '') and (line[:1] != '#'):
                retVal = self.oServerImpl.executeCommand(line)
                print retVal

        filero.close()

class System:
    ''' System class is used to get all the system related
    information and static properties/version information'''

    def __init__(self, obCamera, obGraph):
        ''' Initialize System class '''
        self.camera = obCamera
        self.graph = obGraph

    def getTargetOS(self):
        ''' gets the os running on the target device '''

        info = self.graph.getInfo()
        if (info.osInfo.osInfoAvailable == 1):
            if (info.osInfo.osID == nvcamera.NvctOsID_Android):
                osName = "Android"
            elif (info.osInfo.osID == nvcamera.NvctOsID_L4T):
                osName = "L4T"
            elif (info.osInfo.osID == nvcamera.NvctOsID_Embedded_Linux):
                osName = "Embedded Linux"
            elif (info.osInfo.osID == nvcamera.NvctOsID_QNX):
                osName = "QNX"
            else:
                osName = "Unsupported OS. Id: " + str(info.osInfo.osID)
        return osName

    def getNvCameraVersion(self):
        return nvcamera.__version__

    def isMultipleExposureSupported(self):
        ''' Returns whether multiple exposures are supported in nvcamera '''
        # Multiple exposures are supported from Major Version 3
        majorVer = int((nvcamera.__version__).split('.')[0])
        if (majorVer >= 3):
            return 1
        return 0

    def isHDRSupported(self):
        ''' Returns whether HDR is supported in the sensor '''
        global _hdr_capabilities
        if (self.isMethodSupported("nvcamera", "NvHdrCapabilities")):
            print "HDR supported in nvcamera"
            _hdr_capabilities = nvcamera.NvHdrCapabilities()
            self.camera.getHdrCapabilities(_hdr_capabilities)
            if (_hdr_capabilities.bHdrSupported == 1):
                return 1
            else:
                return 0
        else:
            print "HDR is not supported in nvcamera..."
            return 0

    def getNumExposuresForAutomotiveHDRMode(self):
        ''' Returns the number of exposures for Automotive HDR sensor if HDR is supported '''
        global _hdr_capabilities
        if (self.isHDRSupported()):
            return _hdr_capabilities.getNumExposuresAt(nvcamera.NvHdrMode_Automotive1)
        else: return nvcamera.NvError_NotSupported

    def getNumGainsForAutomotiveHDRMode(self):
        ''' Returns the number of gains for Automotive HDR sensor if HDR is supported '''
        global _hdr_capabilities
        if (self.isHDRSupported()):
            return _hdr_capabilities.getNumSensorAnalogGainsAt(nvcamera.NvHdrMode_Automotive1)
        else: return nvcamera.NvError_NotSupported

    def isMethodSupported(self, strObjectType, strMethod):
        ''' Returns whether method is supported in either nvcamera module
            camera class or graph class '''

        if (strObjectType == 'nvcamera'):
            for item in dir(nvcamera):
                if (strMethod == item):
                    return 1
            return 0
        elif (strObjectType == 'camera'):
            for item in dir(self.camera):
                if (strMethod == item):
                    return 1
            return 0
        elif (strObjectType == 'graph'):
            for item in dir(self.graph):
                if (strMethod == item):
                    return 1
            return 0
        return 0

def main():
    oServer = nvCameraServer()
    #oServer.startDebugServer(sys.argv[1])
    oServer.startServer()

# calls main function
if __name__ == '__main__':
    main()
