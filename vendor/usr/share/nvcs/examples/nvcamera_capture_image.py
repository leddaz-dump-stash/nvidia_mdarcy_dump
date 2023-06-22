# Copyright (c) 2011-2020 NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#
#

from __future__ import division
from __future__ import print_function

try:
    input = raw_input
except NameError:
    pass

from optparse import OptionParser
from optparse import OptionValueError
import sys
import os

# Specify the python library search paths for softfp, hardfp, aarch64
sys.path.append('/usr/lib/arm-linux-gnueabi/tegra')
sys.path.append('/usr/lib/arm-linux-gnueabihf/tegra')
sys.path.append('/usr/lib/aarch64-linux-gnu/tegra')

import traceback
import nvcamera
import time
import platform
import types
import subprocess
import stat
import signal
nvcscommonPath = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'common')
nvcscommonutilsPath = os.path.join(nvcscommonPath, 'nvcsCommonUtils.py')
sys.path.append(nvcscommonPath)
from nvcsCommonUtils import NVCSutil

# nvcamera_capture_image script version
__version__ = "1.4.0"

# Following are Bitmasks
# Concurrent is a combination of raw and jpeg and hence both bits are set
# For everything else, only one bit should be set.
OUTTYPE_UNSPECIFIED = 0
OUTTYPE_NVRAW = 1
OUTTYPE_JPEG = 2
OUTTYPE_CONCURRENT = 3 # 1 + 2
OUTTYPE_YUV = 4
OUTTYPE_YUV16 = 8

SYSINFO_MEMORY = 0
SYSINFO_DISK = 1

STREAMING_BUFFER_COUNT = 3

SET_GET_ATTRIBUTE_SYNC = 5.0 # maximum 5 seconds wait for attribute synchronization

info          = None
exp_time_list = []
gain_list     = []
nvcsUtil      = None
oCamera       = None
osName        = ""
use_e_list    = None
exp_time_list = None
gain_list     = None

#### main() ####

def main():

    start_time = time.time()

    oGraph = None
    # create and run camera graph
    oGraph = nvcamera.Graph()

    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    global use_e_list, exp_time_list, gain_list

    global info
    info = oGraph.getInfo()
    print("OS: \"" + nvcsUtil.getOsName() + "\"")
    if (info.osInfo.osInfoAvailable == 1):
        print("OS Distribution: \"" + info.osInfo.osDistributeVersion + "\" Processor: \"" + info.osInfo.processor + "\"")
    default_output_dir = nvcsUtil.getCaptureScriptLogPath()

# define options class
class CommonOptions(object):
    m_usage = None
    m_parser = None
    m_optionType = None
    m_captureScriptPath  = None
    m_default_output_dir = None
    def __init__(self):
        # get the path of nvcamera_capture_image.py
        self.m_captureScriptPath =  os.path.abspath(__file__)
        self.optionType = "Automotive"
        global nvcsUtil
        if nvcsUtil is None:
            nvcsUtil = NVCSutil()
        imageType = "jpeg"
        if nvcsUtil.isEmbeddedOS():
            imageType = "nvraw"
        self.m_default_output_dir = nvcsUtil.getCaptureScriptLogPath()
        # parse arguments
        self.m_usage = "prog <options>" \
                  "\nCaptures an image with AE, AWB, and AF defaulted to Automatic" \
                  "\nTwo ways to capture: " \
                  "\n     - Use single frame capture " \
                  "\n     - Use streaming (This is a beta feature right now) " \
                  "\nNOTE: for the options that require sensor ID or sensor mode, one can do the following steps first to" \
                  " retrieve all necessary information." \
                  "\nI.E:\n1. to list all valid sensor ID and sensor mode: one can use <--lps> option" \
                  "\n\npython %s --lps" \
                  "\n\nexample output:" \
                  "\nNumber of supported sensor entries 3" \
                  "\nEntry  Source Mode      Uniquename      Resolution   FR BitDepth  Mode" \
                  "\nIndex  Index  Index                                            CSI Dyn" \
                  "\n  0      0     0   e3326_front_P5V27C    2592x1944    30  10  10  Bayer" \
                  "\n  1      0     1   e3326_front_P5V27C    2592x1458    30  10  10  Bayer" \
                  "\n  2      0     2   e3326_front_P5V27C    1280x720     120 10  10  Bayer" \
                  "\n\n2. to list all sensor mode of an selected sensor: one can use <--l> option along with <-i> option" \
                  "\n\npython %s -i 0 -l" \
                  "\n\nAvailable Sensor Modes:" \
                  "\n0:      2592x1944 : 30.00 fps : HDR: 0" \
                  "\n1:      2592x1458 : 30.00 fps : HDR: 0" \
                  "\n2:      1280x720 : 120.00 fps : HDR: 0" \
                  "\n\nEXAMPLE: to capture a %s file with sensor 0 mode 0" \
                  "\npython %s -i 0 -s 0 -t %s" % (self.m_captureScriptPath, imageType, self.m_captureScriptPath,self.m_captureScriptPath, imageType)
        if nvcsUtil.isEmbeddedOS():
            self.m_usage = "prog <options>" \
                  "\nNOTE: There is only one sensor mode and sensor ID can be supported at the run-time." \
                  "\nUsers must provide the sensor name via <--c> option and the sensor configuration file via <--cf> option" \
                  "\nIn addition, user may observe all supported sensor information by using <--lps> option" \
                  "\n\nI.E. python %s --cf ddpx-a.conf --c SF3325-CSI-A --lps" \
                  "\n\nexample output:" \
                  "\nNumber of supported sensor entries 24" \
                  "\nIndex  Uniquename      Description" \
                  "\n0   SF3324-CSI-A    Sekonix SF3324 module - 120-deg FOV, DVP AR0231-RCCB, MAX96705" \
                  "\n1   SF3324-CSI-C    Sekonix SF3324 module - 120-deg FOV, DVP AR0231-RCCB, MAX96705" \
                  "\n2   SF3324-CSI-E    Sekonix SF3324 module - 120-deg FOV, DVP AR0231-RCCB, MAX96705" \
                  "\n...." \
                  "\n\nEXAMPLE: to capture a %s file with default settings" \
                  "\npython %s --cf ddpx-a.conf --c SF3325-CSI-A -t %s" \
                  "\n\nEXAMPLE: to capture a nvraw file and manually set the HDR exposure and gains"\
                  "\npython %s --cf ddpx-a.conf --c SF3325-CSI-A --g0 1 --e0 0.0004 --g1 2 --e1 0.0005 --g2 3 --e2 0.0006 --use_eall" \
                  % (self.m_captureScriptPath, self.m_captureScriptPath, imageType, self.m_captureScriptPath, imageType)


        self.m_parser = OptionParser(self.m_usage)
        for i in range(0, 8, 1):
            self.m_parser.add_option('--g' + str(i), '--gain' + str(i), dest='gain' + str(i), default=-1, type="float", metavar="GAIN" + str(i),
                        help = 'Sets the HDR Gain %d                   \
                                Default = -1 [Auto]                                     ' % i)
        for i in range(0, 8, 1):
            self.m_parser.add_option('--e' + str(i), '--exp' + str(i), dest='exp_time' + str(i), default=-1, type="float", metavar="EXP_TIME" + str(i),
                        help = 'Sets the HDR Exposure Time %d (in seconds)                     \
                                Default = -1 [Auto]                                     ' % i)

        for i in range(0, 8, 1):
            self.m_parser.add_option('--use_e' + str(i), '--use_e' + str(i), dest='use_e' + str(i), action='store_true', metavar="LIST_CONFIGS", default = False,
                        help = 'Specify the HDR Exposures that need to be used')

        self.m_parser.add_option('--use_eall', dest='use_eall', default=False, action="store_true",
                    help = 'Specifies use of all HDR Exposure Time values')
        self.m_parser.add_option('-n', '--name', dest='fname', default="nvcs_test", type="str", metavar="FILE_NAME",
                    help = 'Sets the Name of the Output File                        \
                            Default = nvcs_test                                     ')
        self.m_parser.add_option('-o', '--outdir', dest='output_dir',  type="str", metavar="OUTPUT_DIR", default = None,
                    help = 'Sets the Name of the Output Directory                   \
                            Default = %s                                      ' % self.m_default_output_dir)

        supportType = "nvraw, jpeg, concurrent, yuv"
        if nvcsUtil.isEmbeddedOS():
            supportType = "nvraw"
        self.m_parser.add_option('-t', '--outputtype', dest='output_type', type="str", metavar="OUTPUT_TYPE", default = 'nvraw',
                    help = 'Sets the Type of Output                                 \
                            Default = nvraw                                         \
                            Supported Types: %s           ' %(supportType))

        self.m_parser.add_option('-v', '--version', dest='version', action='store_true', metavar="VERSION", default = False,
                    help = 'Prints NvCamera Module Version and NvCamera_capture_image Script Version   \
                            Default = False                                         ')
        self.m_parser.add_option('--cf', '--configfile', dest='sensor_config_file', type="str", metavar="SENSOR_CONFIG_FILE", default="",
                    help = '[Option specific to Automotive]\n \
                            Specify Sensor Configuration file that has a list of supported sensor configurations\n\
                            Default = "" ')
        self.m_parser.add_option('--c', '--sensorname', dest='sensor_name', type="str", metavar="SENSOR_NAME", default="",
                    help = '[Option specific to Automotive]\n\
                            Specify Sensor name\n\
                            Default = "" ')

        self.m_parser.add_option('--lps', '--listconfigs', dest='list_configs', action='store_true', metavar="LIST_CONFIGS", default = False,
                    help = 'Prints supported sensor configuration for user selection. Lists all supported modes for all supported sensors\n                \
                            Default = False')

    def getParser(self):
        return self.m_parser

class MobileOption(CommonOptions):
    def __init__(self):
        self.optionType = "Mobile"
        CommonOptions.__init__(self)
        self.m_parser.add_option('-i', '--imager', dest='imager_id', default=0, type="int", metavar="IMAGER_ID",
                    help = '[Option specific to Android/L4T]\nSet imager id. Value is 0 based sensor id   \
                            Default = 0')
        self.m_parser.add_option('-f', '--focus', dest='focus', default=-1, type="int", metavar="FOCUS",
                    help = 'Sets the Focus Position                                 \
                            Default = -1 [Auto]                              ')
        self.m_parser.add_option('-g', '--gain', dest='gain', default=-1, type="float", metavar="GAIN",
                    help = 'Sets the amount of Digital Gain                         \
                            Default = -1 [Auto]                                     ')
        self.m_parser.add_option('-e', '--exp', dest='exp_time', default=-1, type="float", metavar="EXP_TIME",
                    help = 'Sets the Exposure Time (in seconds)                     \
                            Default = -1 [Auto]                                     ')
        self.m_parser.add_option('-p', '--preview', dest='preview', default=-1, type="int",
                    metavar="PREVIEW_MODE",
                    help = 'Sets the preview sensor mode                            \
                            Default = -1 [Maximum Supported Resolution at 30 FPS]              \
                            --preview <mode number> \
                               Note: <mode number> can be retrieved by calling \
                               nvcamera_capture_image.py -i <sensor> -l \
                               or \
                               nvcamera_capture_image.py --lps           ')
        self.m_parser.add_option('-w', '--preview_wait', dest='preview_wait', default=0, type="int", metavar="PREVIEW_WAIT",
                    help = 'Sets the number of seconds to wait before capture       \
                            Default = 0                                             ')
        self.m_parser.add_option('-s', '--still', dest='still', default=-1, type="int",
                    metavar="STILL_MODE",
                    help = 'Sets the capture sensor mode                            \
                            Default = -1 [Maximum Supported Resolution]              \
                            --still <mode number> \
                               Note: <mode number> can be retrieved by calling \
                               nvcamera_capture_image.py -i <sensor> -l \
                               or \
                               nvcamera_capture_image.py --lps           ')
        self.m_parser.add_option('-l', '--listmodes', dest='list_modes', action='store_true', metavar="LIST_MODES", default = False,
                    help = 'Prints a list of all available sensor modes for the currently selected sensor   \
                            Default = False                                         ')
        self.m_parser.add_option('--crop', dest='crop_percent', default=100, type="float", metavar="CROP_PERCENT",
                    help = 'Sets the percentage of the image to capture             ' +
                           'Only available for greater than 1 frame captures        \
                            Default = 100                                           ')
        self.m_parser.add_option('--stream-frames', dest='stream_frames', default = 1, type="int", metavar="FRAMES",
                    help = 'Sets the number of frames to capture for streaming      \
                            Default = 1, set -1 for continuous streaming')
        self.m_parser.add_option('--stream-type', dest='stream_type', type="str", metavar="STREAM_TYPE", default=None,
                   help = 'Sets the streaming type for greater than 1 frame         \
                            captures                                                \
                           Supported streaming types: immediate, buffered\n \
                           immediate: dump to disk soon after frame is received\n \
                           buffered: buffer every frame received in memory, \
                           do not process in between and dump at the very end\n \
                           Default = None' )
        self.m_parser.add_option('--hpdisable', dest='halfpress_disable', default=False, action='store_true',
                    help = 'Disables halfpress algorithm                            \
                            Default = False                                         ')
        # the noise reduction mode was mapeped to anroid.noiseReduction.mode; also the default will use the initial settion from PublicControl
        self.m_parser.add_option('--denoise', dest='nr_mode', type="int", default = 0, metavar="NOISE_REDUCTION",
                    help = 'Sets the noise reduction mode: 0 = OFF : denoise algorithm are disabled - default mode\n\
                                                           1 = FAST : TNR is applied; \
                                                           will not slow down frame rate relative to raw bayer output\n\
                                                           2 = HIGH_QUALITY : DCT is applied; may slow down the capture rate')
        self.m_parser.add_option('--pw', "--previewwindow", dest='previewWindow', type='int', default = -1, metavar="PREVIEWWINDOW",
                    help = 'Launches the argus_preview4script app as a preview        \
                            window.                                                   \
                            Takes an integer as parameter.\n                          \
                            <0: skip launching preview window;\n                      \
                            =0: launch the preview window using the default time;\n   \
                            >0: launch the preview window for number of \
                            seconds specified by user;\n\n                            \
                            Default = -1.')
        self.m_parser.add_option('--force', dest='force', default=False, action="store_true",
                    help = 'Runs the capture script without any prompts.\n\
                            Default = False', metavar="FORCE")
        self.m_parser.add_option('--nvraw', dest='nvraw_version', metavar="NVRAW_VERSION", default="v3", choices=["v2", "v3"],
                help = 'nvraw version\n'
                       'Takes the following parameters (default is v3):\n'
                       'v2\n'
                       'v3')
#### main() ####

def main():
    global SET_GET_ATTRIBUTE_SYNC
    start_time = time.time()

    oGraph = None
    # create and run camera graph
    oGraph = nvcamera.Graph()

    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    global use_e_list, exp_time_list, gain_list

    global info
    info = oGraph.getInfo()
    print("OS: \"" + nvcsUtil.getOsName() + "\"")
    if (info.osInfo.osInfoAvailable == 1):
        print("OS Distribution: \"" + info.osInfo.osDistributeVersion + "\" Processor: \"" + info.osInfo.processor + "\"")
    try:
        # parse arguments

        captureOption = None
        if nvcsUtil.isEmbeddedOS():
            captureOption = CommonOptions()
        elif nvcsUtil.isMobile():
            captureOption = MobileOption()
        else:
            print("[ERROR]: unknown OS; exit the program")
            exit (1)

        # parse the command line arguments
        (options, args) = captureOption.getParser().parse_args()

        # special case for Automotive
        if nvcsUtil.isEmbeddedOS():
            options.imager_id = 0
            options.focus = -1
            options.gain = -1
            options.exp_time = -1
            options.preview = -1
            options.preview_wait = 0
            options.still = -1
            options.list_modes = None
            options.crop_percent = 100
            options.stream_frames = 1
            options.stream_type = None
            options.halfpress_disable = False
            options.previewWindow = -1
            options.force = False
            options.nr_mode = 0
        # print nvcamera module version
        if (options.version):
            print("nvcamera version: %s" %nvcamera.__version__)
            print("nvcamera_capture_image script version: %s" %__version__)
            return

        # check if user has specified to use previewWindow
        # display a preview window
        if (options.previewWindow >= 0):
            cmdOption = ""
            path = ""
            cmd = "argus_preview4script"
            if nvcsUtil.isAndroid():
                path += "/vendor/bin/"
                os.environ["PATH"] += os.pathsep + "/vendor/bin/"
            elif nvcsUtil.isL4T():
                path += "/home/ubuntu/"
                os.environ["PATH"] += os.pathsep + "/home/ubuntu/"
            if not os.path.isfile(os.path.join(path,cmd)):
                print("Error: %s is not found, please check if Argus is supported on this device." % cmd)
                print("Exiting capture script now.")
                exit(1)

            if (options.previewWindow > 0):
                cmdOption = " -s %d" % (options.previewWindow)
                cmd += cmdOption
            print("Running cmd: " + cmd)
            try:
                p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
                if not options.force:
                    input("\n\nPress ENTER to continue capture.\n\n")
                    os.kill(p.pid, signal.SIGINT)
                # wait for argus to stop
                p.wait()
                print("Capture starts")
            except OSError as e:
                print("Error: ",e.strerror)
                print("Error: ",e.filename)

        # check if user has specified the --preview/-p option and
        # display a wanrning message
        if (options.preview != -1):
            print("-p/--preview option is deprecated. Preview and still captures will use same sensor mode \
                   as specified by --still/-s option")
            options.preview = options.still

        if options.output_dir == None:
            options.output_dir = nvcsUtil.getCaptureScriptLogPath()

        # Create Output Directory
        if not os.path.exists(options.output_dir):
            # directory permission/mode is 0777
            mode = stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
            if (createDirSetMode(options.output_dir, mode) != True):
                print("Error: Could not create directory %s and set mode to %o" % (a_dir, mode))
                exit(1)

        outType = OUTTYPE_UNSPECIFIED

        # Determine Output Type
        if (options.output_type in ('r', 'raw', 'nvraw')): #NVRAW
            outType = OUTTYPE_NVRAW
        elif (options.output_type in ('j', 'jpg', 'jpeg')): #JPEG
            if (nvcsUtil.isEmbeddedOS()) :
                print("ERROR: jpeg/jpg is not a supported output type")
                exit(1)
            outType = OUTTYPE_JPEG
        elif (options.output_type in ('c', 'concurrent', 'concurrent_raw')): #CONCURRENT
            if (nvcsUtil.isEmbeddedOS()) :
                print("ERROR: concurrent/concurrent_raw is not supported output type")
                exit(1)
            outType = OUTTYPE_CONCURRENT
        elif (options.output_type in ('y', 'yuv')): #YUV
            if (nvcsUtil.isEmbeddedOS()) :
                print("ERROR: YUV is not supported output type")
                exit(1)
            outType = OUTTYPE_YUV
        elif (options.output_type in ('yuv16')): #YUV16
            if (nvcsUtil.isEmbeddedOS()) :
                print("ERROR: YUV16 is not supported output type")
                exit(1)
            outType = OUTTYPE_YUV16
        else: #Unknown
            raise Exception("Unknown Capture Type")

        # Determine and validate streaming type
        streamType = None
        if (options.stream_type != None):
            if (options.stream_type[0] in ('i', 'immediate')): # immediate
                streamType = nvcamera.FrameDest_DumpToDisk_Immediate
            elif (options.stream_type[0] in ('b', 'buffered')): # buffered
                streamType = nvcamera.FrameDest_DumpToDisk_Buffered
            else:                                               # invalid
                print('Error: invalid streaming type. Please specify one of the supported streaming types: ' +
                      'immediate, buffered')
                exit(1)

        # Validate frames selection
        if ((options.stream_type != None and options.stream_frames == 0) or \
            (options.stream_type != None and options.stream_frames < -1)):
            print("Error: Invalid number of frames. Please choose >= 1 number of frames to stream, or -1 for continuous streaming.")
            exit(1)

        if (options.stream_type == None and outType == OUTTYPE_YUV):
            print("YUV still captures are not currently supported.\nIn order to capture YUV, streaming workflow must be used.\n" +
                  "Please specify streaming type and number of frames")
            exit(1)

        valid3A = True
        if (options.gain < 0 and options.gain != -1):
            print("Error: Invalid gain (\"-g %d\").  Must be positive or exactly -1 (auto)." % options.gain)
            valid3A = False
        if (options.exp_time < 0 and options.exp_time != -1):
            print("Error: Invalid exposure time (\"-e %f\").  Must be positive or exactly -1 (auto)." % options.exposuretime)
            valid3A = False
        if (options.focus < 0 and options.focus != -1):
            print("Error: Invalid focus position (\"-f %d\").  Must be positive or exactly -1 (auto)." % options.focus)
            valid3A = False
        if not valid3A:
            exit(1)

        # Validate percent to crop selection
        if (options.crop_percent <= 0 or options.crop_percent > 100):
            print("Error: crop percentage parameter needs to be between 1 and 100\n")
            exit(1)
        if (outType == OUTTYPE_JPEG and options.crop_percent < 7):
            print("Error: percent parameter needs to be more than 7 for JPEGs\n")
            exit(1)
        if (options.crop_percent != 100 and options.stream_type == None):
            print("Error: cannot crop images for regular still capture. If you want to crop for 1 frame capture, " +
                  "please specify a stream type that is not \'none\'.")
            exit(1)
        percentToCrop = ((100.0 - options.crop_percent) / 2.0) / 100.0

        # NvRaw version is already validated by the parser
        nvraw_version_int = int(options.nvraw_version[1])

        if options.output_dir == None:
            options.output_dir = nvcsUtil.getCaptureScriptLogPath()

        if (nvcsUtil.isEmbeddedOS()):
            if (not os.path.exists(options.sensor_config_file)):
                print("Error: You need to specify the configuration file path")
                return

            if ((len(options.sensor_name) == 0) and options.list_configs == False):
                print("Error: You need to specify the capture configuration file")
                return

            print("Sensor Config File: " + options.sensor_config_file)
            print("Sensor Name: " + options.sensor_name)
            print("list_configs: " + str(options.list_configs))

        oGraph.setSensorConfigFile(options.sensor_config_file)
        if (options.list_configs == True):
            listConfigs()
            return

        if (options.nr_mode != None):
            if ((options.nr_mode < 0) or (options.nr_mode > 2)):
                print("Error: invalid noise reduction mode (%d). Must be positive and between 0 to 2" % options.nr_mode)
                exit(1)
            else:
                options.nr_mode = convertOptionToNoiseReductionMode(options.nr_mode)

        try:
            oGraph.setImager(options.imager_id, options.sensor_name)
        except nvcamera.NvCameraException as err:
            if (err.value == nvcamera.NvError_ModuleNotPresent):
                print("ERROR: Camera sensor not present!")
                exit(1)

        # get list of modes
        modes = oGraph.getSupportedModes()

        # Check if the modeNumber is within the range
        # Default or uninitialized value will be -1
        # Initialized value is between 0 and count-1
        printList = False
        useHDR = False
        exp_time_list = [ options.exp_time0, options.exp_time1, options.exp_time2, options.exp_time3,
                  options.exp_time4, options.exp_time5, options.exp_time6, options.exp_time7 ]
        gain_list = [ options.gain0, options.gain1, options.gain2, options.gain3,
              options.gain4, options.gain5, options.gain6, options.gain7 ]
        use_e_list = [ options.use_e0, options.use_e1, options.use_e2, options.use_e3,
                options.use_e4, options.use_e5, options.use_e6, options.use_e7 ]
        if (not (options.still >= -1 and options.still < len(modes))):
            print("Error: Wrong sensor mode %d supplied. Should be between 0 and %d" % (options.still, len(modes)-1))
            printList = True
        elif nvcsUtil.isMobile():
            numMode = oGraph.getNumSupportedSensorEntries()
            if ((options.still > -1) and (options.still < numMode) and modes[options.still].hdrMode != 0) :
                useHDR = True
        elif nvcsUtil.isEmbeddedOS():
            #special case for Automotive; only 1 mode
            if (modes[0].hdrMode != 0) :
                useHDR = True
        else:
            print("ERROR: unknown still mode[%d] and unknown OS[%s]"%(options.still, nvcsUtil.getOsName()))

        # special case for Automotive; Automotive  will use HDR mode whenever use_eall is set or
        # the number of use_e# is greater than 1. It should not depend on the -s option to set the
        # HDR mode
        if nvcsUtil.isEmbeddedOS():
            use_e_total = 0
            if len(gain_list) is not len(exp_time_list) :
                print("Error: size of gain list is not the same as the size of exp list");
                oGraph.close()
                exit(0)
            for idx in range(0, len(use_e_list),1):
                if (gain_list[idx] is not -1) and \
                (exp_time_list[idx] is not -1) and ((use_e_list[idx] is True) or (options.use_eall)):
                    use_e_total += 1
            if (0 is use_e_total) :
                print("AE is not supported; please provide at least 1 exposure and 1 gain\n")
                oGraph.close()
                exit(0)
            if (use_e_total > 1) and (modes[0].hdrMode != 0) : # automotive only has one mode
                useHDR = True

        if(options.list_modes or printList == True):
            print("Available Sensor Modes:")
            i = 0
            for mode in modes:
                print("%d:\t%dx%d : %3.2f fps : HDR: %d" % (i, mode.Resolution.width, mode.Resolution.height, mode.FrameRate, mode.hdrMode))
                i = i+1
            # exit after printing the list
            oGraph.close()
            exit(0)

        global oCamera
        oCamera = nvcamera.Camera()
        bMultipleExpos = isMultipleExposuresSupported()

        numExposures = 1
        numGains = 1

        if (is_method(oCamera, "NvHdrCapabilities")):
            hdrCapabilities = nvcamera.NvHdrCapabilities()
            oCamera.getHdrCapabilities(hdrCapabilities)
            if hdrCapabilities.bHdrSupported :
                print("HDR supported in nvcamera")
                if useHDR:
                    print("Using HDR mode")
                    #
                    # NvHdrMode enumerates different HDR modes in mobile and Automotive.
                    # These index into the exposure time and gain arrays. If the HDR is
                    # enabled, we are supposed to get the number of exposures and gains
                    # from the exposure time and gain arrays indexed by the HDR mode.
                    # So run through the ET and gain arrays and grab the values.
                    #
                    for i in range(0, nvcamera.NvHdrMode_Last -1, 1):
                        numExposures = hdrCapabilities.getNumExposuresAt(i)
                        numGains = hdrCapabilities.getNumSensorAnalogGainsAt(i)
                        if (numExposures > 0 and numGains > 0):
                            print("mode %d numExposures %d numGains %d " % (i, numExposures, numGains))
                            break
            else:
                print("This version of nvcamera does not support HDR")

        if (numExposures != numGains):
            print("Error: Number of exposures %d different from Number of gains %d " % (numExposures, numGains))
            oGraph.close()
            exit(0)
        #
        # Convert command line options to lists
        #
        createLists(numExposures, numGains, options, useHDR)
        exposureMode = getExposureModeFromOptions(numExposures, options)
        if (exposureMode == -1):
            oGraph.close()
            exit(0)

        oCamera.setExposureMode(exposureMode)

        print("Number of exposures %d Number of gains %d ExposureMode 0x%X" % (numExposures, numGains, exposureMode))

        # picking a mode in the same way graph.preview() does
        mode = None
        modeInd = options.preview
        if (modeInd >= 0 and modeInd < len(modes)):
            mode = modes[modeInd]
        else:
            # find the largest rate with 30 fps
            for m in modes:
                if (m.FrameRate == 30):
                    mode = m
                    break
            # if can't find a mode with rate at 30 fps
            # pick first one greater than 30fps
            if (mode == None):
                for m in modes:
                    if (m.FrameRate > 30):
                        mode = m
                        break
            # if still can't fine any, then pick max resolution
            if (mode == None):
                currMaxWidth = 0
                currMaxHeight = 0
                for m in modes:
                    if((currMaxWidth < m.Resolution.width) or (currMaxHeight < m.Resolution.height)):
                        mode = m
                        currMaxWidth = mode.Resolution.width
                        currMaxHeight = mode.Resolution.height

        imageFormat = nvcamera.ImageFormat_NvRaw if (outType == OUTTYPE_NVRAW) else nvcamera.ImageFormat_Jpeg if (outType == OUTTYPE_JPEG) else nvcamera.ImageFormat_Yuv

        # Calculate # of frames that can be captured in current memory and disk space
        # with specified resolution and output type
        free_mem = 0
        free_disk = 0
        bufferSize = 0
        posFrames = 0
        if (options.stream_type != None and options.stream_frames != 0):
            free_mem = getFreeSystemSpace(sysInfo = SYSINFO_MEMORY)
            free_disk = getFreeSystemSpace(sysInfo = SYSINFO_DISK, loc = nvcsUtil.getCaptureScriptLogPath())
            if (free_mem == 0 or free_disk == 0):
                oGraph.stop()
                oGraph.close()
                exit(1)
            bufferSize = getBufferSize(mode.Resolution.width, mode.Resolution.height, imageFormat)

            if ((free_mem // bufferSize) <= STREAMING_BUFFER_COUNT):
                # badly out of memory
                print("Error: Not enough memory available in system to stream")
                oGraph.stop()
                oGraph.close()
                exit(1)

            if (streamType == nvcamera.FrameDest_DumpToDisk_Immediate):
                # Using 50% of actual available disk space to not overuse disk
                posFrames = int(free_disk * 0.5) // bufferSize
                if (posFrames < options.stream_frames):
                    print("Error: Not enough disk space available in system to store %d frames." % options.stream_frames)
                    print("Disk has space for around %d frames" % posFrames)
                    oGraph.stop()
                    oGraph.close()
                    exit(1)
            elif (streamType == nvcamera.FrameDest_DumpToDisk_Buffered):
                # Using 80% of actual available memory to not overuse memory
                posFramesInMem = int(free_mem * 0.8) // bufferSize
                posFramesInDisk = int(free_disk * 0.5) // bufferSize
                posFrames = posFramesInMem if (posFramesInMem < posFramesInDisk) else posFramesInDisk
                if (posFrames < options.stream_frames):
                    if (posFramesInMem < posFramesInDisk):
                        print("Error: Not enough memory available in system to store %d frames." % options.stream_frames)
                    else:
                        print("Error: Not enough disk space available in system to store %d frames." % options.stream_frames)
                    print("Memory and Disk space allow around %d frames" % posFrames)
                    oGraph.stop()
                    oGraph.close()
                    exit(1)

        graphType = "Jpeg"
        if(outType == OUTTYPE_NVRAW):
            graphType = "Bayer"

        if (nvraw_version_int != 0):
            oGraph.setNvRawVersion(nvraw_version_int)

        # set preview resolution
        oGraph.preview(modeNumber = options.still)
        # set capture resolution
        oGraph.still(modeNumber = options.still)

        oGraph.run()

        if (options.stream_type == None):
            oCamera.setAttr(nvcamera.attr_pauseaftercapture, 1)
            # Start Camera and Wait until Ready

        # set the Noise Reduction mode
        setNoiseReductionMode(options.nr_mode)

        # Create Output Directory
        if not os.path.exists(options.output_dir):
            os.mkdir(options.output_dir)

        # Start Camera and Wait until Ready
        oCamera.startPreview()
        oCamera.waitForEvent(1000, nvcamera.CamConst_FIRST_PREVIEW_FRAME)

        exposureTimeRange = oCamera.getAttr(nvcamera.attr_exposuretimerange)
        gainRange = oCamera.getAttr(nvcamera.attr_gainrange)
        if (bMultipleExpos == False):
            print("Exposure time range (%2.8f, %2.8f)" % \
                  (exposureTimeRange[0], exposureTimeRange[1]))
            print("Gain range (%2.2f, %2.2f)" % (gainRange[0], gainRange[1]))
        else:
            if (nvcsUtil.isEmbeddedOS()) :
                if (len(exposureTimeRange[0]) != len(gainRange[0])) :
                    print("the number of plane for gain range [%d] and number of plane for exposure time [%d] do not match" \
                    %(len(gainRange[0], len(exposureTimeRange[0]))))
                    oCamera.stopPreview()
                    oGraph.stop()
                    oGraph.close()
                    exit(1)
                for idx in range(len(exposureTimeRange[0])):
                    print("Exposure time range plane %d [%2.8f ~ %2.8f]" % (idx, exposureTimeRange[0][idx], exposureTimeRange[1][idx]))
                    print("gain time range plane %d [%2.8f ~ %2.8f]" % (idx, gainRange[0][idx], gainRange[1][idx]))
            else :
                index = 0
                eMode = exposureMode
                #
                # If only one bit is set in exposureMode, get the index
                #
                if (eMode and (not(eMode & (eMode -1)))):
                    # Now get the index from the bit mask
                    while (eMode > 0):
                        eMode = eMode >> 1
                        index = index + 1
                    index = index - 1

                print("Exposure time range (%2.8f, %2.8f)" % \
                    (exposureTimeRange[0][index], exposureTimeRange[1][index]))
                print("Gain range (%2.2f, %2.2f)" % \
                        (gainRange[0][index], gainRange[1][index]))

        #
        # setAttr() for exposure time or gain is an override function that can take single value (legacy - non HDR)
        # or list with multiple values (HDR). In the following two cases for ET and gain, we can use the
        # list. But the single value call is left intentionally to demonstrate the usage.
        #
        if (numExposures == 1 and options.exp_time != -1):
            if (exposureTimeRange[1][0] >= options.exp_time) and \
               (exposureTimeRange[0][0] <= options.exp_time):
                oCamera.setAttr(nvcamera.attr_exposuretime, options.exp_time)
            else:
                if (exposureTimeRange[1][0] < options.exp_time):
                    print(("[WARNING]: exposure_time %2.8f is greater than the maximum exposure range %2.8f; " \
                    %(options.exp_time, exposureTimeRange[1][0]), "setting the exposure to the maximum exposure"))
                    options.exp_time = exposureTimeRange[1][0]
                else :
                    print(("[WARNING]: exposure_time %2.8f is less than the minimum exposure range %2.8f; " \
                    %(options.exp_time, exposureTimeRange[0][0]), "setting the exposure to the minimum exposure"))
                    options.exp_time = exposureTimeRange[0][0]
        elif (numExposures > 1):
            if ((len(exp_time_list) < len(exposureTimeRange[0])) or
                (len(exp_time_list) < len(exposureTimeRange[1]))):
                print("[error]: exp_time_list size (%d) is less than the size of exposureTimeRange[0] (%d) or" \
                       " exposureTimeRange[1] (%d)" % \
                       (len(exp_time_list), len(exposureTimeRange[0]), len(exposureTimeRange[1])))
                oCamera.stopPreview()
                oGraph.stop()
                oGraph.close()
                exit(1)

            # Run through the list which is the same length as the
            # number of expsures
            autoExpCount = 0
            for expIdx in range(len(exposureTimeRange[0])):
                exp_time = exp_time_list[expIdx]
                if ((exp_time < exposureTimeRange[0][expIdx]) and (exp_time is not -1)) or \
                   (exp_time > exposureTimeRange[1][expIdx]):

                    if (exp_time < exposureTimeRange[0][expIdx]) :
                        print("[WARNING]: exposure_time %2.8f is less than the minimum exposure range %2.8f" \
                               %(exp_time, exposureTimeRange[0][expIdx]))
                        print("[WARNING]: set exposure_time to the  minimum exposure %2.8f" % (exposureTimeRange[0][expIdx]))
                        exp_time_list[expIdx] = exposureTimeRange[0][expIdx]
                    else:
                        print("[WARNING]: exposure_time %2.8f is greater than the maximum exposure range %2.8f" \
                               %(exp_time, exposureTimeRange[1][expIdx]))
                        print("[WARNING]: set exposure_time to the  maximum exposure %2.8f" % (exposureTimeRange[1][expIdx]))
                        exp_time_list[expIdx] = exposureTimeRange[1][expIdx]
                else:
                    autoExpCount += exp_time
            if autoExpCount == (numExposures * -1):
                print("Exposuretime will be determined by AE")
            else:
                errMsg = "[warning]: user defined exposure time used "
                for expIdx in range(len(exposureTimeRange[0])):
                    errMsg += '[' + str(exp_time_list[expIdx]) + ']'
                print(errMsg)
            oCamera.setAttr(nvcamera.attr_exposuretime, exp_time_list)
        else:
            print("Exposuretime will be determined by AE")

        #
        # If the exposure time is set and gain is not set,
        # we need to set the gain to 1
        #
        gain = -1
        if (numGains == 1):
            if (options.gain != -1):
                gain = options.gain
            elif (options.exp_time != -1):
                gain = 1.0
            else:
                print("Gain will be determined by AE")
        elif (numGains > 1):
            for i in range(0, numExposures, 1):
                if (exp_time_list[i] != -1 and gain_list[i] == -1):
                    gain_list[i] = 1.0

        if (numGains == 1 and gain != -1):
            if (gainRange[0][0] <= gain) and (gainRange[1][0] >= gain) :
                oCamera.setAttr(nvcamera.attr_bayergains, gain)
            else :
                if (gainRange[1][0] < gain):
                    print(("[WARNING]: gain %2.8f is greater than the maximum gain range %2.8f; " \
                    %(gain, gainRange[1][0]), "setting the gain to the maximum gain"))
                    # assign the gain in the format of list instead of just type float
                    # because the list type is used for comparison later
                    gain = options.gain = gainRange[1]
                else :
                    print(("[WARNING]: gain %2.8f is less than the minimum gain range %2.8f; " \
                    %(gain, gainRange[0][0]), "setting the gain to the minimum gain"))
                    # assign the gain in the format of list instead of just type float
                    # because the list type is used for comparison later
                    options.gain = gain = gainRange[0]
        elif (numGains > 1):
            for gainIdx in range(len(gainRange[0])):
                gain_val = gain_list[gainIdx]
                if ((gain_val < gainRange[0][gainIdx]) and (gain_val is not -1)) or \
                   (gain_val > gainRange[1][gainIdx]):
                    if (gain_val < gainRange[0][gainIdx]) :
                        print("[WARNING]: gain %2.8f is less than the minimum gain range %2.8f" \
                               %(gain_val, gainRange[0][gainIdx]))
                        print("[WARNING]: set gain to the  minimum gain %2.8f" % (gainRange[0][gainIdx]))
                        gain_list[gainIdx] = gainRange[0][gainIdx]
                    else:
                        print("[WARNING]: gain %2.8f is greater than the maximum gain range %2.8f" \
                               %(gain_val, gainRange[1][gainIdx]))
                        print("[WARNING]: set gain to the  maximum gain %2.8f" % (gainRange[1][gainIdx]))
                        gain_list[gainIdx] = gainRange[1][gainIdx]
            oCamera.setAttr(nvcamera.attr_bayergains, gain_list)

        if nvcsUtil.isMobile():
            hasFocuser = True
            try:
                physicalRange = oCamera.getAttr(nvcamera.attr_focuspositionphysicalrange)
            except nvcamera.NvCameraException as err:
                print("focuser is not supported")
                hasFocuser = False
            else:
                if (physicalRange[0] == physicalRange[1]):
                    print("focuser is not present")
                    hasFocuser = False
            if((hasFocuser != True) and (options.focus != -1)):
                print("\nFocuser is not supported. Can't use -f or --focus.")

            if(hasFocuser):
                if(options.focus != -1):
                    oCamera.setAttr(nvcamera.attr_focuspos, options.focus)
                else:
                    oCamera.setAttr(nvcamera.attr_autofocus, 1)

        if (nvcsUtil.isMobile()):
            # check whether the set attribute has properly changed sensor property
            validSetting = True
            exposureTime = oCamera.getAttr(nvcamera.attr_exposuretime)
            gain = oCamera.getAttr(nvcamera.attr_bayergains)
            if (len(exposureTime) != numExposures):
                print("[error]: the size of exp_time_list[%d] and exposureTime[%d] do not match"%(numExposures, len(exposureTime)))
                validSetting = False
            elif (len(gain) != numGains):
                print("[error]: the size of gain_list[%d] and gain[%d] do not match"%(numGains, len(gain)))
                validSetting = False

            if validSetting:
                validationTime = time.time()
                if (options.preview_wait > 0):
                    time.sleep(options.preview_wait)
                else:
                    if (bMultipleExpos == False):
                        while ((False == checkAttributeTolerance(options.exp_time, exposureTime)) and
                            (False == checkAttributeTolerance(options.gain, gain))):
                            exposureTime = oCamera.getAttr(nvcamera.attr_exposuretime)
                            gain = oCamera.getAttr(nvcamera.attr_bayergains)
                            if ((time.time() - validationTime) > SET_GET_ATTRIBUTE_SYNC):
                                print("[error] exposure time %s set to driver does not match to the " \
                            "exposure time %s get from the driver"%(str(options.exp_time), str(exposureTime)))
                                print("[error] gain %s set to driver does not match to the " \
                            "exposure time %s get from the driver"%(str(options.gain), str(gain)))
                            validSetting = False
                            break
                    else:
                        while ((False == checkAttributeTolerance(exp_time_list, exposureTime)) and
                            (False == checkAttributeTolerance(gain_list, gain))):
                                exposureTime = oCamera.getAttr(nvcamera.attr_exposuretime)
                                gain = oCamera.getAttr(nvcamera.attr_bayergains)
                                if ((time.time() - validationTime) > SET_GET_ATTRIBUTE_SYNC):
                                    gainListStr = "["
                                    gainStr= "["
                                    for gainIdx in range(0,numGains,1):
                                        gainListStr += str(exp_time_list[gainIdx]) + ','
                                        gainStr += str(exposureTime[gainIdx]) + ','
                                    gainListStr = gainListStr[:-1] + ']'
                                    gainStr = gainStr[:-1] + ']'
                                    print("[error] gain set %s to driver does not match to " \
                                        "the gain %s get from the driver"%(gainListStr, gainStr))
                                    expTimeListStr = "["
                                    expTimeStr= "["
                                    for expIdx in range(0,numExposures,1):
                                        expTimeListStr += str(exp_time_list[expIdx]) + ','
                                        expTimeStr += str(exposureTime[expIdx]) + ','
                                    expTimeListStr = expTimeListStr[:-1] + ']'
                                    expTimeStr = expTimeStr[:-1] + ']'
                                    print("[error] exposure time %s set to driver does not match to " \
                                        "the exposure time %s get from the driver"%(expTimeListStr,expTimeStr))
                                    validSetting = False
                                    break
            if not validSetting:
                oGraph.stop()
                oGraph.close()
                exit(1)

        # Generate Image Path
        if (outType == OUTTYPE_NVRAW):
            filePath = os.path.join(options.output_dir, options.fname + ".nvraw")
        elif (outType & OUTTYPE_JPEG):
            filePath = os.path.join(options.output_dir, options.fname + ".jpg")
        elif (outType & OUTTYPE_YUV):
            filePath = os.path.join(options.output_dir, options.fname + ".yuv")
        elif (outType & OUTTYPE_YUV16):
            filePath = os.path.join(options.output_dir, options.fname + ".yuv16")
        else:
            print("Error: No image type specified\n")
            exit(0)

        # If output file already exists, delete it first.
        if os.path.exists(filePath):
            os.remove(filePath)

        if(outType == OUTTYPE_CONCURRENT):
            oCamera.setAttr(nvcamera.attr_concurrentrawdumpflag, 7)

        doHalfpress = False
        if nvcsUtil.isMobile() :
            if((not outType == OUTTYPE_NVRAW or (hasFocuser == True and options.focus == -1)
                or options.exp_time == -1) and not options.halfpress_disable):
                doHalfpress = True
            else:
                doHalfpress = False

        if (options.stream_type == None):
            # ---- STILL CAPTURING START ---- #
            if doHalfpress:
                oCamera.halfpress(5000)
            # Capture an Image
            oCamera.still(filePath)
            oCamera.waitForEvent(12000, nvcamera.CamConst_CAP_READY, nvcamera.CamConst_CAP_FILE_READY)
            if doHalfpress:
                oCamera.hp_release()

            # Print exposure times and gains if the current mode is PWL
            printCaptureAttributes(oGraph, oCamera)

            oCamera.stopPreview()
            # (Skip this for now as it causes issues in L4T)
            # oCamera.waitForEvent(2000, nvcamera.CamConst_PREVIEW_EOS)
            # ---- STILL CAPTURING STOP ---- #
        else:
            # ---- STREAMING START ---- #
            oCamera.stopPreview()
            AAA_EVENTS = (nvcamera.CamConst_AF_READY or nvcamera.CamConst_AF_TIMEOUT or
                         nvcamera.CamConst_AE_READY or nvcamera.CamConst_AE_TIMEOUT or
                         nvcamera.CamConst_AWB_READY or nvcamera.CamConst_AWB_TIMEOUT)
            print("Preliminary preview started for Auto Exposure (if used) to settle down...")
            oCamera.startPreview()
            oCamera.waitForEvent(2000, AAA_EVENTS)
            oCamera.stopPreview()
            print("Preliminary preview ended")

            stats = nvcamera.StreamingStats()

            # setting streaming parameters
            parameters = nvcamera.StreamingParameters()
            parameters.cropRectangle.left = (int)(mode.Resolution.width * percentToCrop)
            parameters.cropRectangle.top = (int)(mode.Resolution.height * percentToCrop)
            parameters.cropRectangle.right = mode.Resolution.width - parameters.cropRectangle.left
            parameters.cropRectangle.bottom = mode.Resolution.height - parameters.cropRectangle.top
            parameters.imageFormat = imageFormat
            parameters.frameDestination = streamType
            parameters.filename = filePath

            if (options.stream_frames != -1):
                parameters.frameCount = options.stream_frames
                print("Capturing %d streaming frames\n" % options.stream_frames)
                oCamera.setStreamingParameters(parameters)
                streamTimeout = options.stream_frames * 1000
            else:
                parameters.frameCount = posFrames
                print("*** Max number of frames that can be captured on current memory and disk space: %d" % posFrames)
                oCamera.setStreamingParameters(parameters)
                streamTimeout = posFrames * 1000
            oCamera.startPreview()
            oCamera.waitForEvent(streamTimeout, nvcamera.CamConst_PREVIEW_EOS)
            oCamera.stopPreview()
            oCamera.waitForEvent(3000, nvcamera.CamConst_PREVIEW_EOS)
            oCamera.getStreamingStats(stats)

            # ---- STREAMING STOP ---- #


        # stop and close the graph
        oGraph.stop()
        oGraph.close()


        # display capture settings
        # if camera does not have focuser, "None" is displayed under Focus
        outputStr = ""
        outputStr += "Settings:\n"
        gainStr = ""
        expStr = ""
        if not useHDR:
            gainStr = "Auto"
            expStr = "Auto"
            if (options.gain != -1):
                gainStr = str(options.gain)
            if (options.exp_time != -1):
                expStr = str(options.exp_time)
        else:
            expTotal = 0
            gainTotal = 0
            for i in range(0, numExposures, 1):
                if nvcsUtil.isMobile():
                    expStr += "%2.6f, " % exposureTime[i]
                    gainStr += "%2.2f, " % gain[i]
                elif nvcsUtil.isEmbeddedOS():
                    expStr += "%2.6f, " % exp_time_list[i]
                    gainStr += "%2.6f, " % gain_list[i]
                expTotal += exp_time_list[i]
                gainTotal += gain_list[i]
            if (gainTotal == (numExposures * -1)):
                gainStr = "Auto"
            else:
                gainStr = gainStr[:-2]
            if (expTotal == (numExposures * -1)):
                expStr = "Auto"
            else:
                expStr = expStr[:-2]

        outputStr += " - Gain:      [%s]\n" % gainStr
        outputStr += " - Exposure:  [%s]\n" % expStr
        if nvcsUtil.isMobile():
            outputStr += " - Focus:     [%s]\n" % (str(options.focus) if (hasFocuser and options.focus != -1) else "Auto"
                                                                      if (hasFocuser and options.focus == -1) else "None")
        outputStr += "----------------------------------------------------------\n"

        # display streaming results
        if (options.stream_type != None):
            outputStr += "Streaming Results:\n"
            outputStr += " - Frames received:                       [%d]\n" % stats.framesRx
            outputStr += " - FPS:                                   [%2.2f]\n" % stats.fps
            outputStr += " - Average Frame Processing time in Core: [%2.2fms]\n" % stats.aveTimeFrameProcess
            outputStr += " - Files dumped to disk:                  [%d]\n" % stats.fileList.size()
            outputStr += "----------------------------------------------------------\n"

        outputStr += "Output:\n"

        outTypeStr = ""
        if(outType & OUTTYPE_JPEG):
            outTypeStr = "JPEG"
        elif(outType == OUTTYPE_NVRAW):
            outTypeStr = "RAW"
        elif(outType == OUTTYPE_YUV):
            outTypeStr = "YUV"
        elif(outType == OUTTYPE_YUV16):
            outTypeStr = "YUV16"
        if (options.stream_type == None):
            outputStr += " - %s:      [%s]\n" % (outTypeStr, filePath)
        else:
            for i in range(0, stats.fileList.size()):
                outputStr += " %d. %s:      [%s]\n" % (i+1, outTypeStr, stats.fileList.GetFilename(i))

        if(outputStr[len(outputStr)-1] == '\n'):
            outputStr = outputStr[:-1]

        print("<><><><><><><><><><><><><><><><><><><><><><><><><><><><><>")
        print(outputStr)
        print("<><><><><><><><><><><><><><><><><><><><><><><><><><><><><>")
        print("Time consumed by capture script: %3.2f seconds" % (time.time() - start_time))

    except Exception as err:
        print(traceback.print_exc()) # Add line for debugging
        print(err)
        if(oGraph):
            oGraph.stop()
            oGraph.close()
        print("Time consumed by capture script: %3.2f seconds" % (time.time() - start_time))
        exit(1)


def listConfigs():

    oGraph = nvcamera.Graph()

    num = oGraph.getNumSupportedSensorEntries()
    str1 = ''
    str2 = ''
    uniqueNameLength = 0
    modeTypeLength = 0
    nameLength = 0
    moduleNameLength = 0
    positionLength = 0
    descrLength = 0
    sourceIndex = list(range(num))
    sensorModeIndex = list(range(num))
    nvctCharBufferUniqueName = list(range(num))
    nvctCharBufferName = list(range(num))
    nvctCharBufferPos = list(range(num))
    nvctCharBufferModuleName = list(range(num))
    nvctCharSensorDescription = list(range(num))
    nvctSensorMode = list(range(num))
    csiPixelBitDepth = list(range(num))
    dynamicPixelBitDepth = list(range(num))
    modeType = list(range(num))
    uint_temp = nvcamera.uint32pc()

    # Get all sensor properties and keep them around in a list
    # The reason we do it this way is to print them all out at the end
    # to avoid driver debug spew to interfere with the prints.
    #
    for i in range(0, num):

        camSsourceIndex = nvcamera.CamSProperty(nvcamera.SPROP_SOURCE_INDEX,
                                        nvcamera.SPROP_TYPE_UINT32,
                                        1, uint_temp)
        oGraph.getSensorProperty(i, camSsourceIndex);
        sourceIndex[i] = camSsourceIndex.getUint32ElementAtIndex(0)

        camSsensorModeIndex = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_MODE_INDEX,
                                        nvcamera.SPROP_TYPE_UINT32,
                                        1, uint_temp)
        oGraph.getSensorProperty(i, camSsensorModeIndex);
        sensorModeIndex[i] = camSsensorModeIndex.getUint32ElementAtIndex(0)

        nvctCharBufferUniqueName[i] = nvcamera.NvctCharBuffer()
        camSPropUniqueName = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_UNIQUE_NAME,
                                           nvcamera.SPROP_TYPE_CBUFFER,
                                           1, nvctCharBufferUniqueName[i])
        oGraph.getSensorProperty(i, camSPropUniqueName);

        nvctCharBufferName[i] = nvcamera.NvctCharBuffer()
        camSPropName = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_NAME,
                                        nvcamera.SPROP_TYPE_CBUFFER,
                                        1, nvctCharBufferName[i])
        oGraph.getSensorProperty(i, camSPropName);


        nvctCharBufferPos[i] = nvcamera.NvctCharBuffer()
        camSPropPos = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_POS,
                                        nvcamera.SPROP_TYPE_CBUFFER,
                                        1, nvctCharBufferPos[i])
        oGraph.getSensorProperty(i, camSPropPos);

        nvctCharBufferModuleName[i] = nvcamera.NvctCharBuffer()
        camSPropModuleName = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_MODULE_NAME,
                                        nvcamera.SPROP_TYPE_CBUFFER,
                                        1, nvctCharBufferModuleName[i])
        oGraph.getSensorProperty(i, camSPropModuleName);

        nvctCharSensorDescription[i] = nvcamera.NvctCharBuffer()
        camSPropSensorDescription = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_DESCRIPTION,
                                        nvcamera.SPROP_TYPE_CBUFFER,
                                        1, nvctCharSensorDescription[i])
        oGraph.getSensorProperty(i, camSPropSensorDescription);


        camSPropCSIBitDepth = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_CSIPIXEL_BITDEPTH,
                                        nvcamera.SPROP_TYPE_UINT32,
                                        1, uint_temp)
        oGraph.getSensorProperty(i, camSPropCSIBitDepth);
        csiPixelBitDepth[i] = camSPropCSIBitDepth.getUint32ElementAtIndex(0)

        camSPropDynamicBitDepth = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_DYNAMICPIXEL_BITDEPTH,
                                        nvcamera.SPROP_TYPE_UINT32,
                                        1, uint_temp)
        oGraph.getSensorProperty(i, camSPropDynamicBitDepth);
        dynamicPixelBitDepth[i] = camSPropDynamicBitDepth.getUint32ElementAtIndex(0)

        camSPropModeType = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_MODETYPE,
                                        nvcamera.SPROP_TYPE_UINT32,
                                        1, uint_temp)
        oGraph.getSensorProperty(i, camSPropModeType);
        modeType[i] = getModeType(camSPropModeType.getUint32ElementAtIndex(0))

        nvctSensorMode[i] = nvcamera.NvCameraToolsSensorMode()
        camSProp2 = nvcamera.CamSProperty(nvcamera.SPROP_NVCTSENSORMODE,
                                    nvcamera.SPROP_TYPE_NVCTSENSORMODE,
                                    1, nvctSensorMode[i])
        oGraph.getSensorProperty(i, camSProp2);

        uniqueNameLength = max(len(nvctCharBufferUniqueName[i].getBuffer()), uniqueNameLength)
        modeTypeLength = max(len(modeType[i]), modeTypeLength)
        nameLength = max(len(nvctCharBufferName[i].getBuffer()), nameLength)
        moduleNameLength = max(len(nvctCharBufferModuleName[i].getBuffer()), moduleNameLength)
        positionLength = max(len(nvctCharBufferModuleName[i].getBuffer()), positionLength)
        descrLength = max(len(nvctCharSensorDescription[i].getBuffer()), descrLength)

    #
    # Construct the header
    #
    if (nvcsUtil.isEmbeddedOS()):
        str1 = 'Number of supported sensor entries ' + str(num) + '\n' \
               + 'Index'.ljust(7)  \
               + ' '.ljust(10) + 'Uniquename'.ljust(20) \
               + ' '.ljust(20) + 'Description'.ljust(10) \
               + '\n'
    else:
        #
        # Add only the string headers that have non-null in all entries
        #
        str1 = 'Number of supported sensor entries ' + str(num) + '\n' \
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
    for i in range(0, num):
        if (nvcsUtil.isEmbeddedOS()):
            str2 = str2 + str(i).rjust(3) + ' '.ljust(3) + str(nvctCharBufferUniqueName[i].getBuffer()).ljust(40) \
                   + ' '.ljust(2) + str(nvctCharSensorDescription[i].getBuffer()).ljust(30) + '\n'
        else:
            str2 = str2 + str(i).rjust(3) + str(sourceIndex[i]).rjust(7) + str(sensorModeIndex[i]).rjust(6) + ' '.ljust(2)

            if (uniqueNameLength > 0):
                pad = (max(len('Uniquename'), len(nvctCharBufferUniqueName[i].getBuffer())) - len(nvctCharBufferUniqueName[i].getBuffer())) & ~1
                str2 = str2 + ' '.ljust(pad // 2) + str(nvctCharBufferUniqueName[i].getBuffer()).ljust(uniqueNameLength) + ' '.ljust(pad // 2)

            str2 = str2 + ' '.ljust(3) + str(nvctSensorMode[i].Resolution.width).ljust(4) \
                    + 'x' + str(nvctSensorMode[i].Resolution.height).ljust(4) + ' '.ljust(2) \
                    + ' '.ljust(2) + str(int(round(nvctSensorMode[i].FrameRate))).ljust(3) \
                    + ' '.ljust(0) + str(csiPixelBitDepth[i]) + ' '.ljust(1) \
                    + ' '.ljust(0) + str(dynamicPixelBitDepth[i]) + ' '.ljust(1)

            if (modeTypeLength > 0):
                pad = (max(len('Mode'), len(modeType[i])) - len(modeType[i])) & ~1
                str2 = str2 + ' '.ljust(pad // 2 + 1) + modeType[i].ljust(modeTypeLength) + ' '.ljust(pad // 2)

            if (nameLength > 0):
                pad = (max(len('Name'), len(nvctCharBufferName[i].getBuffer())) - len(nvctCharBufferName[i].getBuffer())) & ~1
                str2 = str2 + ' '.ljust(pad // 2) + str(nvctCharBufferName[i].getBuffer()).ljust(nameLength) + ' '.ljust(pad // 2)

            if (moduleNameLength > 0):
                pad = (max(len('ModuleName'), len(nvctCharBufferModuleName[i].getBuffer())) - len(nvctCharBufferModuleName[i].getBuffer())) & ~1
                str2 = str2 + ' '.ljust(pad // 2) + str(nvctCharBufferModuleName[i].getBuffer()).ljust(moduleNameLength) + ' '.ljust(pad // 2)

            if (positionLength > 0):
                pad = (max(len('Position'), len(nvctCharBufferPos[i].getBuffer())) - len(nvctCharBufferPos[i].getBuffer())) & ~1
                str2 = str2 + ' '.ljust(pad // 2) + str(nvctCharBufferPos[i].getBuffer()).ljust(positionLength) + ' '.ljust(pad // 2)

            if (descrLength > 0):
                pad = (max(len('Description'), len(nvctCharSensorDescription[i].getBuffer())) - len(nvctCharSensorDescription[i].getBuffer())) & ~1
                str2 = str2 + ' '.ljust(pad // 2) + str(nvctCharSensorDescription[i].getBuffer()).ljust(descrLength) + ' '.ljust(pad // 2)

            str2 = str2 + '\n'
    #
    # Print assembled strings now
    #
    print(str1)
    print(str2)
    print('\n')

    del nvctCharBufferUniqueName
    del nvctCharBufferName
    del nvctCharBufferPos
    del nvctCharBufferModuleName
    del nvctCharSensorDescription
    del nvctSensorMode
    del csiPixelBitDepth
    del dynamicPixelBitDepth
    del modeType
    del uint_temp


#### utility methods from nvcstestsystem.py ####

def is_method(obj, name):
    for item in dir(nvcamera):
        if (item == name):
            return 1
    return 0
    #
    # Problem with importing. Otherwise, this following have been the ideal way
    # import inspect
    # return hasattr(obj, name) and inspect.ismethod(getattr(obj, name))
    #

def getFreeSystemSpace(sysInfo, loc=''):
    # Get free disk space of the input arg's filesystem in bytes
    osCmd, free, freeStr, stdout, lines, mult = [], 0.0, '', '', [], 1
    if (sysInfo == SYSINFO_MEMORY):
        osCmd = ['free', '-k']
    elif (sysInfo == SYSINFO_DISK):
        osCmd = ['df', '-P', '-k', str(loc)]
    else:
        return 0
    try:
        cmdProc = subprocess.Popen(osCmd, stdout=subprocess.PIPE)
        cmdProc.wait()
        stdout, err = cmdProc.communicate()
        lines = stdout.decode().split('\n')
        freeStr = (lines[1].split())[3]
    except Exception as e:
        print('Error calling \"df\" command.')
        return 0
    try:
        free = float(freeStr)
        return int(free * 1024)
    except Exception as e:
        print('Error parsing free system space')
        return 0


# buffer-pixel ratios are experimental values for approximating buffer size
def getBufferSize(width, height, imgFormat):
    avgBufferPixelRatio = 0
    if (imgFormat == nvcamera.ImageFormat_NvRaw):
        avgBufferPixelRatio = 2.2033
    elif (imgFormat == nvcamera.ImageFormat_Jpeg):
        avgBufferPixelRatio = 1.9167
    elif (imgFormat == nvcamera.ImageFormat_Yuv):
        avgBufferPixelRatio = 1.9167
    else:
        print("Error: incorrect image format passed to getBufferSize()")
        return 0
    print("WIDTH: %d" % width)
    print("HEIGHT: %d" % height)
    pixels = width * height
    print("PIXELS: %d" % pixels)
    bufferSize = pixels * avgBufferPixelRatio
    return bufferSize

def getModeType(modeType):
    if (modeType == nvcamera.SPROP_SENSORMODETYPE_UNSPECIFIED):
        return "Unspecified"
    elif (modeType == nvcamera.SPROP_SENSORMODETYPE_DEPTH):
        return "Depth"
    elif (modeType == nvcamera.SPROP_SENSORMODETYPE_YUV):
        return "Yuv"
    elif (modeType == nvcamera.SPROP_SENSORMODETYPE_RGB):
        return "RGB"
    elif (modeType == nvcamera.SPROP_SENSORMODETYPE_BAYER):
        return "Bayer"
    elif (modeType == nvcamera.SPROP_SENSORMODETYPE_BAYER_WDR_PWL):
        return "Bayer_WDR_PWL"
    elif (modeType == nvcamera.SPROP_SENSORMODETYPE_BAYER_WDR_DOL):
        return "Bayer_WDR_DOL"
    elif (modeType == nvcamera.SPROP_SENSORMODETYPE_BAYER_WDR_INTERLEAVE):
        return "Bayer_WDR_Interleave"
    else:
        return "Unknown"

def isMultipleExposuresSupported():

    # Multiple exposures are supported from Major Version 3
    majorVer = int((nvcamera.__version__).split('.')[0])

    if (majorVer >= 3):
        return True
    return False

def is_valueSpecified(val, val_list):
    # val is a single float and val_list is an array of floats
    # if any of the values are non -1, it returns true.
    # Useful for Et and Gain
    #
    if (val != -1):
        return 1
    for i in range(0, len(val_list), 1):
        if (int(val_list[i]) != -1):
            return 1
    return 0

def getListCount(val_list):
    # Gets the count of values that are non -1
    # Useful for Et and Gain lists
    #
    count = 0
    for i in range(0, len(val_list), 1):
        if (int(val_list[i]) != -1):
            count = count + 1
    return count

#
# This function does the sanity check for all the supported options
# and returns the exposure mode from the required parameters
#
def getExposureModeFromOptions(numExposures, options):

    global use_e_list
    global exp_time_list
    global gain_list
    exposureMode = 0

    #
    # use_exposure_options beyond numExposures should be set to False - This can be checked
    # Ex: numExposures = 3
    # use_e_list[] = [ False, True, False, False, False, False, False, False]
    #
    for i in range(numExposures, len(use_e_list), 1):
        if (use_e_list[i] == True):
            print("Error: getExposureModeFromOptions: use_e%d is more than supported exposures of %d" % (i, numExposures))
            return -1

    #
    # If use_eall is specified, we ignore all use_eX values.
    #
    if (options.use_eall == True):
        exposureMode = (1 << numExposures) -1
        # Update the list for use below
        for i in range(0, numExposures, 1):
            use_e_list[i] = True
    else:
        #
        # Build the bitmask of all exposures set within numExposures
        #
        exposureMode = 0
        for i in range(0, numExposures, 1):
            if (use_e_list[i] == True):
                exposureMode = exposureMode | (1 << i)

        if (exposureMode == 0):
            # None of them are set. At this point the options are sane.
            # Use the index 0
            exposureMode = 1
        #
        # If the exposure Mode has multiple bits set, the only value it
        # can have is as if use_eall is specified
        #
        if not (exposureMode and (not(exposureMode & (exposureMode -1)))):
            # Multiple bits set
            if (exposureMode != (1 << numExposures) -1):
                print("ERROR: getExposureModeFromOptions: Unsupported combination on command line.")
                print("    More than one exposure is specified that is not HDR.")
                print("    ExposureMode 0x%X Number of exposures %d " % (exposureMode, numExposures))
                return -1

    #
    # We can not have ET and Gain set on a wrong index (wrong use_eX)
    #
    for i in range(0, numExposures, 1):
        if (use_e_list[i] == False and (int(exp_time_list[i]) != -1 or int(gain_list[i]) != -1)):
            print("Error: getExposureModeFromOptions: Exposure Index %d. You can not specify manual " \
                    "exposure time or gain on a wrong/unsupported exposure index" %i)
            return -1

    #
    # Make sure specified manual ET and Gain values are within the boundary
    #
    if (getListCount(exp_time_list) > numExposures):
        print("Number of Exposure time values specified (%d) is more than supported number of exposures (%d) " % (getListCount(exp_time_list), numExposures))
        return -1

    if (getListCount(gain_list) > numExposures):
        print("Number of Gain values specified (%d) is more than supported number of gains (%d) " % (getListCount(gain_list), numExposures))
        return -1

    return exposureMode


#
# Function creates lists from command line arguments specified.
# Three lists are created that are globally accessed.
#
def createLists(numExposures, numGains, options, useHDR):
    #
    # if exp_time (single, legacy) is specified, it overrides
    #
    if (nvcsUtil.isMobile) or (not useHDR):
        if (options.exp_time != -1):
            exp_time_list[0] = options.exp_time
            use_e_list[0] = True
            numExposure = 1
        if (options.gain != -1):
            gain_list[0] = options.gain
            use_e_list[0] = True
            numGain = 1
#
# createDirSetMode creates a directory (and top level directories in the path)
# and sets the mode
#
def createDirSetMode(dirName, mode):
    os.makedirs(dirName)
    os.chmod(dirName, mode)
    st = os.stat(dirName)
    return bool((st.st_mode & mode) == mode)

#
# nrModeToString convert noise reduction mode from int to string representation
# mode is defined in nvcameratools_properties.h
#
def nrModeToString(nrMode):
    switcher = {
        nvcamera.NoiseReductionMode_Off : "NoiseReductionMode_Off",
        nvcamera.NoiseReductionMode_Fast : "NoiseReductionMode_Fast",
        nvcamera.NoiseReductionMode_HighQuality : "NoiseReductionMode_HighQuality"
    }
    return switcher.get(nrMode, "invalid Noise Reduction Mode")

#
# convertOptionTotNoiseReductionMode convert noise reduction mode from argument input
# in commandline to enum defined in nvcamera
# mode is defined in nvcameratools_properties.h
#
def convertOptionToNoiseReductionMode(nrMode):
    result = 0
    if (nrMode == 0) :
        result = nvcamera.NoiseReductionMode_Off
    elif (nrMode == 1) :
        result = nvcamera.NoiseReductionMode_Fast
    elif (nrMode == 2) :
        result = nvcamera.NoiseReductionMode_HighQuality
    else :
        result = nvcamera.NoiseReductionMode_Off #set off mode as default if invalid input
    return result

#
# setNoiseReductionMode set the noise reduction mode in property manager
#
def setNoiseReductionMode(nrMode):
    global oCamera
    if (oCamera != None) :
        # set noise reduction mode
        val = nvcamera.uint32pc()
        val.assign(nrMode)
        propData = nvcamera.PropertyData()
        propData.u32 = val.cast()

        propOb = nvcamera.CamProperty()
        propOb.id = nvcamera.PROP_NOISE_REDUCTION_MODE
        propOb.type = nvcamera.PROP_TYPE_UINT32
        propOb.value = propData

        oCamera._propertyManager.setPropery(propOb)#API typo

        print("Noise Reduction mode is set to [%s]" % (nrModeToString(nrMode)))
    else :
        print("Camera is not instantiated; not able to set the noise reduction mode")


def checkAttributeTolerance(setting,getting):
    tolerance = 0.01 # 1% tolerance threshold
    for i in range(len(getting)):
        gettingValue = float(getting[i])
        settingValue = float(setting[i])
        if settingValue < 0.0:
            continue

        difference = abs((gettingValue - settingValue) / settingValue)
        if difference > tolerance:
            return False
    return True

def printCaptureAttributes(oGraph, oCamera):
    modeNumber = nvcamera.NvCamera().getNvCameraTools().getSensorMode(nvcamera.NvCameraCoreUseCase_Still)

    uint_temp = nvcamera.uint32pc()
    camSPropModeType = nvcamera.CamSProperty(nvcamera.SPROP_SENSOR_MODETYPE,
                            nvcamera.SPROP_TYPE_UINT32,
                            1, uint_temp)
    oGraph.getSensorProperty(modeNumber, camSPropModeType)

    if camSPropModeType.getUint32ElementAtIndex(0) == nvcamera.SPROP_SENSORMODETYPE_BAYER_WDR_PWL:
        exposureTimes = oCamera.getAttr(nvcamera.attr_exposuretime)
        sensorAnalogGains = oCamera.getAttr(nvcamera.attr_sensoranaloggain)

        print("WDR PWL capture detected")

        dynamicRangeExposureCount = min(len(exposureTimes), len(sensorAnalogGains))
        for i in range(dynamicRangeExposureCount):
            print("Dynamic Range Exposure [{0}]: Exposure Time = {1}, Sensor Gain = {2}".format(
                i, exposureTimes[i], sensorAnalogGains[i]))

#### main module clause ####

if __name__ == '__main__':
    main()
