#-------------------------------------------------------------------------------
# Name:        vi_mode.py
# Purpose:
#
# Created:     02/06/2020
#
# Copyright (c) 2020 NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#
#-------------------------------------------------------------------------------
#!/usr/bin/env python

from __future__ import print_function

from optparse import OptionParser
from optparse import make_option
from optparse import OptionValueError
import subprocess
import os
import sys
import threading
import time
import re

class FrameInfo(object):
    def __init__(self, width, height, pix_format):
        self.pix_format = pix_format
        self.width = width
        self.height = height

def terminateProcess(process,a_timeout):
    """Helper function to terminate a process call and raise an exception"""

    process.kill()
    process.terminate()
    #os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    raise Exception('Process #{0} killed after {1} seconds'.format(process.pid, a_timeout))

class VI_MODE_RESULT(object):
    PASS = 0
    FAIL = 1
    SKIP = 2

class CameraSetting(object):
    def __init__(self, sensor_id = 0,
                 sensor_mode = 0,
                 height = 0,
                 width = 0,
                 csiBitDepth = 0,
                 dynamicBitDepth = 0,
                 os = 'l4t',
                 modeList = ["mmap", "user"] ):
        self.sensor_id = sensor_id
        self.sensor_mode = sensor_mode
        self.height = height
        self.width = width
        self.csiPixelBitDepth = csiBitDepth
        self.dynamicPixelBitDepth = dynamicBitDepth
        self.os = os
        self.modeList = modeList

def which(name):
    """ Mimic Unix 'which' command """
    for path in os.getenv('PATH').split(os.path.pathsep):
        target = os.path.join(path, name)
        if os.path.isfile(target):
            return target
    return None

def runCmd(cmd, pass_count=1, criteria=None, delay=1, sudo=False, os='l4t', a_timeoutSec=30.0, a_shell=True):
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
        print("RUN CMD: {0}\n".format(cmd))
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
        out = str(out.rstrip().decode())
        err = str(err.rstrip().decode())
        if err:
            return out, err

        if not criteria or criteria in out:
            return out, err

        count += 1

        if count >= pass_count:
            break

        time.sleep(delay)
    return out, "Trial error (attempted {0} times but failed)".format(pass_count)

class ViModeTest(object):
    "vi mode test"
    mode_list = ["mmap"]
    os = 'l4t'
    camera_device_path = None

    def __init__(self, cameraSetting = None):
        os = cameraSetting.os
        if (self.os == 'l4t'):
            self.camera_device_path = '/dev'
        else:
            self.camera_device_path = '/dev/camera'
        self.cameraSetting = cameraSetting
        self.mode_list = cameraSetting.modeList

    def getCameraDevicePath(self):
        return self.camera_device_path

    def list_ctrl(self, sensor_id):
        """List V4L2 controls available"""
        cmd = 'v4l2-ctl -L -d {0}/video{1} | grep Controls'.format(self.getCameraDevicePath(), sensor_id)
        out, err = runCmd(cmd, os=self.os)
        if err:
            print("ERROR:{0}".format(err))
            return False
        if bool('v4l2-ctl: not found' in out):
            print("ERROR:{0}".format(out))
            return False
        elif out is '':
            return False
        else:
            return True

    def check_sensor_mode_ctrl(self, sensor_id):
        """ Checks whether sensor_mode control exists"""
        cmd = 'v4l2-ctl -l -d {0}/video{1} | grep sensor_mode\ \(int\)'.format(self.getCameraDevicePath(), sensor_id)
        out, err = runCmd(cmd, os=self.os)
        if err:
            print("ERROR:{0}".format(err))
            return False
        if bool('v4l2-ctl: not found' in out):
            print("ERROR:{0}".format(out))
            return False
        elif out is '':
            return False
        else:
            return True

    def get_frame_info(self, sensor_id):
        """ list of available framesizes ([(w,h),..., (w,h)])
        :param sensor_id:
        :return: list of available framesizes ([(w,h),..., (w,h)])
        """
        frameInfo = []

        cmd = 'v4l2-ctl -d {0}/video{1} --list-formats-ext'.format(self.getCameraDevicePath(), sensor_id)
        out, err = runCmd(cmd, os=self.os,sudo=True)
        if (len(err) > 0):
            raise Exception('v4l2-ctl failed: {0}'.format(err))

        # parse the output based on the index
        outList = out.split('\n')
        indices = [i for i, string in enumerate(outList) if 'Index' in string]
        for i in range(len(indices)):
            restructedOut = ''
            if i+1 < len(indices):
                restructedOut = "".join(outList[indices[i]:indices[i+1]])
            else:
                restructedOut = "".join(outList[indices[i]:])
            wh_list = re.findall('(\d+)(?:x)(\d+)', restructedOut)
            pix_format = re.findall('\'(.+?)\'', restructedOut)
            print("Available frame sizes:{0}".format(str(wh_list)))
            print("Available pixel format:{0}".format(str(pix_format)))
            for wh in wh_list:
               frameInfo.append(FrameInfo(wh[0], wh[1], pix_format[0]))
        return frameInfo

    def get_frame_interval(self, sensor_id, width, height, format="RG10"):
        """ get fps for given resolution and format """
        cmd = 'v4l2-ctl -d {0}/video{1} --list-frameintervals=width={2},height={3},pixelformat={4}'.format(
            self.getCameraDevicePath(), sensor_id, width, height, format)
        out, err = runCmd(cmd, os=self.os)
        wh_list = re.findall('\((\d+\.\d+) fps\)', out)
        if wh_list:
            return float(wh_list[0])
        else:
            return None

    def get_current_fmt(self, sensor_id):
        """check current framesizes"""
        cmd = 'v4l2-ctl --get-fmt-video -d {0}/video{1}'.format(self.getCameraDevicePath(), sensor_id)
        out, err = runCmd(cmd, os=self.os)
        wh = re.findall('(\d+)(?:\/)(\d+)', out)
        return wh[0][0], wh[0][1]

    def capture_video(self, sensor_id, stream_option):
        """Test Capture video"""
        cmd = 'v4l2-ctl --device={0}/video{1} -I'.format(self.getCameraDevicePath(), sensor_id)
        out, err = runCmd(cmd, os=self.os, sudo=True)
        if err:
            print("ERROR:{0}".format(err))
            return False

        return self.capture_video_sensor(sensor_id, stream_option)

    def capture_video_sensor(self, sensor_id, stream_option, tolerance = 0.02):
        print("Sensor mode info:")
        print("    WxH:%dx%d, csiPixelBitDepth: %s" % (self.cameraSetting.width, self.cameraSetting.height, self.cameraSetting.csiPixelBitDepth))
        # look at the sensor mode and select w, h and pixel format based on sensor mode
        frameInfoList = self.get_frame_info(sensor_id)
        if not frameInfoList:
            print("ERROR: NvCSViModeTest::capture_video_sensor: frame info list is empty")
            return False

        formatIndex = -1
        for idx, frameInfo in enumerate(frameInfoList):
            if (str(self.cameraSetting.width) == frameInfo.width) and (str(self.cameraSetting.height) == frameInfo.height):
                if (str(self.cameraSetting.csiPixelBitDepth) in str(frameInfo.pix_format)):
                    formatIndex = idx
                    break
        if -1 == formatIndex:
            print("ERROR: NvCSViModeTest:: cannot find frame info matches to the sensor mode\n"
                    "width = {0}\n"
                    "height = {1}\n"
                    "pix_format = {2}\n".format(self.cameraSetting.wdith, self.cameraSetting.height, self.cameraSetting.csiPixelBitDepth))
            return False
        w = frameInfoList[formatIndex].width
        h = frameInfoList[formatIndex].height
        pix_format = frameInfoList[formatIndex].pix_format
        cmd = 'v4l2-ctl --device={0}/video{1} --set-ctrl bypass_mode=0 --set-ctrl override_enable=0'.format(self.getCameraDevicePath(), sensor_id)
        out, err = runCmd(cmd, os=self.os, sudo=True)
        if 'Fail' in out:
            print("ERROR:{0}".format(out))
            return False
        print("we will use the pixel format {0} matching the selected sensor mode.".format(pix_format))
        avail_fps = self.get_frame_interval(sensor_id, w, h, pix_format)
        if avail_fps is None:
            print("ERROR:Cannot detect available fps for {0}x{1}".format(w, h))
            return False
        fps_criterion = avail_fps * (1.0 - tolerance)
        print("Available fps:{0} for {1}x{2} (fps from this test should not lower than {3})".format(avail_fps, w, h, fps_criterion))
        req_num_frames = int(avail_fps) * 3 # request [fps x 3] frames to get at least two fps stats
        if (self.check_sensor_mode_ctrl(self.cameraSetting.sensor_id)):
            cmd = ('v4l2-ctl -c sensor_mode={0} --set-fmt-video=width={1},height={2},pixelformat={3} --stream-{4}' +
                   ' --stream-count={5} -d {6}/video{7} 2>&1').format(self.cameraSetting.sensor_mode, w, h, pix_format, stream_option, req_num_frames, self.getCameraDevicePath(), sensor_id)
        else:
            cmd = ('v4l2-ctl --set-fmt-video=width={0},height={1},pixelformat={2} --stream-{3}' +
                   ' --stream-count={4} -d {5}/video{6} 2>&1').format(w, h, pix_format, stream_option, req_num_frames, self.getCameraDevicePath(), sensor_id)
        out, err = runCmd(cmd, os=self.os, sudo=True)
        if 'Fail' in out:
            print("ERROR: {0}".format(out))
            return False
        print(out)
        frame_count = out.count('<')
        last_fps = 0
        if frame_count != req_num_frames:
            print("ERROR: Number of captured frames {0} from Seneor {1} is not equal to requested number of frames ({2}).".format(
                frame_count, sensor_id, req_num_frames))
            return False
        for line in out.splitlines():
            fps = re.findall('\d+\.\d+', line)
            if len(fps) != 0:
                last_fps = fps[0]
            if len(fps) != 0 and float(fps[0]) < fps_criterion:
                print('ERROR: Low fps : {0} (< {1})'.format(fps[0], fps_criterion))
                return False
        if last_fps == 0:
            print('ERROR: Cannot get fps stats.')
            return False

        curw, curh = self.get_current_fmt(sensor_id)
        if int(curw) != int(w) or int(curh) != int(h):
            print("ERROR: Invalid size : {0}x{1} (actual size is {2}x{3}".format(w, h, curw, curh))
            return False

        print('Sensor: {0}  Buffer mode: {1}  Captured: {2}  Last period fps: {3}  Resolution: {4}x{5}'.format(sensor_id, stream_option, frame_count,
            last_fps, w, h))
        return True

    def runPreTest(self, args=None):
        result = VI_MODE_RESULT.PASS
        for name in ['dmesg', 'v4l2-ctl', 'sh']:
            exePath = which(name)
            if exePath is None:
                self.logger.warning("Executable \"%s\" is not available in PATH environment variable.\n" \
                           "\t Please make sure it is getting built and is part of flashed image. Test skipped." % name)
                result = VI_MODE_RESULT.SKIP
        return result

    def runTest(self, args=None):
        testName = "Nvcameratools sanity: vi mode test"
        returnCode = 0
        runtime = 0.0
        startTime = time.time()
        # Clear dmesg
        kout, err = runCmd('dmesg -c > /dev/null', sudo=True, os=self.os)
        if not self.list_ctrl(self.cameraSetting.sensor_id):
            print('ERROR: Failed to list controls for sensor{0}'.format(self.cameraSetting.sensor_id))
            returnCode = 1
        else:
            for mode in self.mode_list:
                if not self.capture_video(self.cameraSetting.sensor_id, mode):
                    print('Failed to capture video --stream-{0} for sensor{1}'.format(mode, self.cameraSetting.sensor_id))
                    returnCode = 1

        kout, err = runCmd('dmesg -c | grep sync', sudo=True, os=self.os)
        if 'time' in kout: # if syncpt time error occured
            print("ERROR: {0}".format(kout))
            returnCode = 1

        print("Exit Code: %d" % returnCode)
        runtime = time.time() - startTime

        # Result
        print("=====================")
        print("==   Test Result   ==")
        print("=====================")
        print("VI_MODE Test %s\t: %fs\t: %s" % ("PASSED" if returnCode == 0 else "FAILED", runtime, testName))

        if returnCode != 0:
            return VI_MODE_RESULT.FAIL

        return VI_MODE_RESULT.PASS

def main():
    viMode_options = [
            make_option('--runPreTest', dest='commandRunPreTest', default=False, action="store_true",
                    help = 'run the ViModeTest::preTest() which checks availability of \'v4l2-ctl\''),
            make_option('--run', dest='commandRun', default=False, action="store_true",
                    help = 'run the ViModeTest::run() which calls \'v4l2-ctl\' to check the sensor functionality'),
            make_option('--width', dest='width', default = None, type='int',
                     help = 'set the width of the resolution; \"REQIORED\" only when calling --run'),
            make_option('--height', dest='height', default = None, type='int',
                     help = 'set the height of the resolution; \"REQIORED\" only when calling --run'),
            make_option('--sensorID', dest='sensorID', default = None, type='int',
                     help = 'set the sensor ID; \"REQIORED\" only when calling --run'),
            make_option('--sensorMode', dest='sensorMode', default = None, type='int',
                     help = 'set the sensor mode; \"REQIORED\" only when calling --run'),
            make_option('--csiBitDepth', dest='csiBitDepth', default = None, type='int',
                     help = 'set the csi bit depth of the resolution; \"REQIORED\" only when calling --run'),
            make_option('--dynamicBitDepth', dest='dynamicBitDepth', default = None, type='int',
                     help = 'set the dynamic bit depth of the resolution; \"REQIORED\" only when calling --run'),
            make_option('--targetMode', dest='targetMode',default=None, type=str,
                    help = 'target mode (\'mmap\' or \'user\') for vi_mode test (default: using both modes)'),
            make_option('--os', dest='OS',default='l4t', type=str,
                    help = 'current OS'),
            make_option('-h', '-?', '--help', dest='help', action='store_true', default=False,
                        help = 'print this help message'),]
    parser = OptionParser("This is the VI_MODE test script", option_list=viMode_options,
                        add_help_option=False)
    # parse the command line arguments
    (viMode_options, args) = parser.parse_args()

    if(viMode_options.help):
        # print help message with advanced options
        parser.print_help()
        sys.exit(os.EX_OK)

    if viMode_options.commandRun:
        if None == viMode_options.width or \
           None == viMode_options.height or \
           None == viMode_options.sensorID or \
           None == viMode_options.sensorMode or \
           None == viMode_options.csiBitDepth or \
           None == viMode_options.dynamicBitDepth or\
           None == viMode_options.targetMode:
            print('ERROR: missing required parameters for VI_MODE::run(); call --help for detail')
            sys.exit(os.EX_SOFTWARE)
    mode_list = ["mmap", "user"] if None == viMode_options.targetMode else viMode_options.targetMode,

    cameraSetting = CameraSetting( sensor_id = viMode_options.sensorID,
        sensor_mode = viMode_options.sensorMode,
        width = viMode_options.width,
        height = viMode_options.height,
        csiBitDepth = viMode_options.csiBitDepth,
        dynamicBitDepth = viMode_options.dynamicBitDepth,
        os = viMode_options.OS,
        modeList = mode_list)
    try:
        result = VI_MODE_RESULT.FAIL
        exitCode = os.EX_SOFTWARE
        vi_mode = ViModeTest(cameraSetting)

        if (viMode_options.commandRunPreTest):
            result = vi_mode.runPreTest()
        elif (viMode_options.commandRun):
            result = vi_mode.runTest()

        if (VI_MODE_RESULT.PASS == result):
            exitCode = os.EX_OK
        elif (VI_MODE_RESULT.SKIP == result):
            exitCode = os.EX_UNAVAILABLE
        return exitCode

    except:
        return(os.EX_CANTCREAT)

if __name__ == "__main__":
    sys.exit(main())
