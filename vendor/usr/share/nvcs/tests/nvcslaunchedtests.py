# Copyright (c) 2016-2020 NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#

import os
import sys
import subprocess
import string
import time
import shutil
import math
import traceback
import re
import nvrawfile
import nvcstestutils
from nvcstestutils import NvCSIOUtil

import nvcamera
from nvcstestcore import *
from nvcssensortests import *
from nvcsflashtests import *
from nvcsfocusertests import *
from nvcshostsensortests import *
from nvcsframeworktests import *


class NvCSApertureConformanceTest(NvCSTestBase):
    "Nvcameratools aperture conformance tests"

    executePath = "nvctconform"
    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    def __init__(self, options, logger):
        NvCSTestBase.__init__(self, options, logger, "ApertureConformance")
        self.options = options
        self.nvcsPath = nvcsUtil.getNVCSPath()

    def setupGraph(self):
        return NvCSTestResult.SUCCESS

    def runTest(self, args):
        names = []
        results = []
        runtimes = []

        self.obGraph.stopAndDeleteGraph()

      # Aperture conformance test
        names.append("Nvcameratools conformance: aperture conformance test")
        command = self.executePath + " -t aperture_conformance"
        self.logger.info("running: \"%s\"" % command)
        try:
            startTime = time.time()
            result = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
            output = result.communicate()[0]
            endTime = time.time()
            runtimes.append(endTime - startTime)
        except Exception as e:
            self.logger.error("Running nvctconform: " + str(e))
            return NvCSTestResult.ERROR

        self.logger.info("Conformance Runtime (%s):    %fs" % (names[-1], runtimes[-1]))

        results.append(result.returncode)
        for line in output.split('\n'):
            if 'INFO' in line:
                self.logger.info(line)
            elif 'DEBUG' in line:
                self.logger.debug(line)
            elif 'WARNING' in line:
                self.logger.warning(line)
            elif 'ERROR' in line:
                self.logger.error(line)
            elif 'FATAL' in line:
                self.logger.fatal(line)

        self.logger.info("Exit Code: %d" % results[-1])

      # Results
        self.logger.info("=================")
        self.logger.info("==   Results   ==")
        self.logger.info("=================")
        for i in range(len(names)):
            self.logger.info("%s\t: %fs\t: %s" % ("PASS" if results[i] == 0 else "FAIL", runtimes[i], names[i]))

        for i in results:
            if i != 0:
                self.logger.error("Aperture test failed.")
                return NvCSTestResult.ERROR
        return NvCSTestResult.SUCCESS


class NvCSSensorDTComplianceTest(NvCSTestBase):
    "sensor dt compliance tests"

    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    exeName = "sensor-kernel-tests"
    os = ''

    def __init__(self, options, logger):
        NvCSTestBase.__init__(self, options, logger, "SensorDTCompliance")
        self.options = options
        if nvcsUtil.isAndroid():
            self.os = "android"
        elif nvcsUtil.isL4T():
            self.os = "l4t"
        else:
            raise NvCSTestException("Not a recognized OS. Cannot determine correct known failures.")

    def needAutoGraphSetup(self):
        return False

    def runPreTest(self, args=None):
        result = NvCSTestResult.SUCCESS
        msg = "Executable \"%s\" is not available in PATH environment variable.\n" \
                           "\t Please make sure it is getting built and is part of flashed image. Test skipped."

        # SKT always uses the absolute path on L4T. The tests are ran
        # as "sudo" ignoring the (normally non-root) user's $PATH.
        if nvcsUtil.isL4T():
            self.exeName = "/usr/sbin/" + self.exeName

        for name in [self.exeName, 'sh']:
            exePath = NvCSIOUtil.which(name)
            if exePath is None:
                self.logger.warning(msg % name)
                result = NvCSTestResult.SKIPPED

        return result

    def querySensorNodeProp(self, path, prop):
        command = "cat {0}/{1}".format(path, prop)
        try:
            output, err, returncode = NvCSIOUtil.runCmd(command, os=self.os, logger=self.logger)
        except Exception as e:
            self.logger.error("Could not determine sensor DT node prop {0}: {1}".format(prop, str(e)))
            return ''

        if err:
            return ''
        return output

    def runTest(self, args):
        failPattern = re.compile("FAIL")
        passPattern = re.compile("\[  PASSED  \]")
        hasPassed = False
        testName = "Nvcameratools conformance: sensor DT compliance test"
        sensorDTPath = ''
        sensorCompatible= ''
        sensorName = ''
        returnCode = 0
        runtime = 0.0
        # Null byte needs removed from /proc/*. Remove some others as well.
        unProcStr = lambda x: x.rstrip(' \t\r\n\0')
        startTime = time.time()

        # Get sensor DT path and query compatible & name
        command = "cat /proc/device-tree/tegra-camera-platform/modules/module{0}/drivernode0/proc-device-tree".format(str(self.options.imager_id))
        try:
            output, err, returncode = NvCSIOUtil.runCmd(command, os=self.os, logger=self.logger)
        except Exception as e:
            self.logger.error("Could not determine sensor DT path: " + str(e))
            return NvCSTestResult.ERROR

        if err:
            self.logger.error("Could not determine sensor DT path: " + str(err))
            return NvCSTestResult.ERROR

        sensorDTPath = unProcStr(output)
        sensorCompatible = unProcStr(self.querySensorNodeProp(sensorDTPath, "compatible"))
        sensorName = unProcStr(self.querySensorNodeProp(sensorDTPath, "name"))
        if not sensorCompatible or not sensorName:
            self.logger.error("Could not get sensor DT node properties")
            return NvCSTestResult.ERROR

        # Sensor DT compliance tests
        command = "{0} -f \"Sensor DT Test\" -c {1} -n {2}".format(self.exeName, sensorCompatible, sensorName)
        try:
            output, err, returncode = NvCSIOUtil.runCmd(command, os=self.os, logger=self.logger,sudo=True)
        except Exception as e:
            self.logger.error("Running sensor DT compliance tests: " + str(e))
            return NvCSTestResult.ERROR

        if err:
            # Error will be dumped to user later
            returnCode = 1

        for line in output.split('\n'):
            f = failPattern.match(line)
            if f is not None:
                failureItem = f.group(1)
                self.logger.error("Failure detected: " + failureItem)
                returnCode = 1
            p = passPattern.match(line)
            if p is not None:
                hasPassed = True

        # Fail REGEX cannot catch other errors (bad sensor name, etc.).
        if not hasPassed:
            returnCode = 1

        self.logger.info("Exit Code: %d" % returnCode)
        runtime = time.time() - startTime

        # Result
        self.logger.info("=====================")
        self.logger.info("==   Test Result   ==")
        self.logger.info("=====================")
        self.logger.info("%s\t: %fs\t: %s" % ("PASSED" if returnCode == 0 else "FAILED", runtime, testName))

        if returnCode != 0:
            self.logger.error("sensor DT compliance tests failed.")
            return NvCSTestResult.ERROR
        return NvCSTestResult.SUCCESS

class NvCSV4l2ComplianceTest(NvCSTestBase):
    "v4l2 compliance tests"

    KNOWN_FAILURES = { "android": set(),
                       "l4t": set(
                                 ["VIDIOC_G/S/TRY_EXT_CTRLS",
                                  "VIDIOC_(UN)SUBSCRIBE_EVENT/DQEVENT"])}
    exeName = "v4l2-compliance"
    knownFailures = set()
    os = ''
    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    def __init__(self, options, logger):
        NvCSTestBase.__init__(self, options, logger, "V4l2Compliance")
        self.options = options
        if nvcsUtil.isAndroid():
            self.knownFailures = self.KNOWN_FAILURES["android"]
            self.os = "android"
        elif nvcsUtil.isL4T():
            self.knownFailures = self.KNOWN_FAILURES["l4t"]
            self.os = "l4t"
        else:
            raise NvCSTestException("Not a recognized OS. Cannot determine correct known failures.")

    def needAutoGraphSetup(self):
        return False

    def runPreTest(self, args=None):
        result = NvCSTestResult.SUCCESS
        for name in [self.exeName, 'sh']:
            exePath = NvCSIOUtil.which(name)
            if exePath is None:
                self.logger.warning("Executable \"%s\" is not available in PATH environment variable.\n" \
                           "\t Please make sure it is getting built and is part of flashed image. Test skipped." % name)
                result = NvCSTestResult.SKIPPED
        return result

    def runTest(self, args):
        failPattern = re.compile("[\s]*test (\S+): FAIL")
        testName = "Nvcameratools conformance: v4l2 compliance tests"
        returnCode = 0
        runtime = 0.0
        startTime = time.time()

        # V4l2 compliance tests
        command = "{0} --device={1}/video{2}".format(self.exeName, nvcsUtil.getCameraDevicePath(), str(self.options.imager_id))
        try:
            output, err, returncode = NvCSIOUtil.runCmd(command, os=self.os, logger=self.logger)
        except Exception as e:
            self.logger.error("Running v4l2 complliance tests: " + str(e))
            return NvCSTestResult.ERROR

        for line in output.split('\n'):
            m = failPattern.match(line)
            if m is not None:
                failureItem = m.group(1)
                if failureItem in self.knownFailures:
                    self.logger.warning("Known failure detected: test " + failureItem  + " => Ignored")
                else:
                    self.logger.error("Failure detected: test " + failureItem)
                    returnCode = 1

        self.logger.info("Exit Code: %d" % returnCode)
        runtime = time.time() - startTime

        # Result
        self.logger.info("=====================")
        self.logger.info("==   Test Result   ==")
        self.logger.info("=====================")
        self.logger.info("%s\t: %fs\t: %s" % ("PASSED" if returnCode == 0 else "FAILED", runtime, testName))

        if returnCode != 0:
            self.logger.error("v4l2 complinace tests failed.")
            return NvCSTestResult.ERROR
        return NvCSTestResult.SUCCESS

class NvCSViModeTest(NvCSTestBase):
    "vi mode test"
    mode_list = "mmap"
    pythonPath = sys.executable
    os = ''
    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    def __init__(self, options, logger, sensorSetting):
        NvCSTestBase.__init__(self, options, logger, "ViMode")
        self.options = options
        self.sensorSetting = sensorSetting
        if self.options.target_mode:
            self.mode_list = self.options.target_mode
        self.camera_device_path = nvcsUtil.getCameraDevicePath()

        if nvcsUtil.isAndroid():
            self.os = "android"
        elif nvcsUtil.isL4T():
            self.os = "l4t"
        else:
            raise NvCSTestException("Not a recognized OS. Cannot determine correct known failures.")

    def needAutoGraphSetup(self):
        return False

    def runPreTest(self, args=None):
        result = NvCSTestResult.SUCCESS
        currPath = os.path.dirname(os.path.realpath(__file__))
        viModePath = currPath + '/' + 'vi_mode.py --runPreTest'
        out, err, returncode = NvCSIOUtil.runCmd('{0} {1}'.format(self.pythonPath, viModePath), pass_count = 1, sudo=True, os=self.os, logger=self.logger)
        if  os.EX_UNAVAILABLE == returncode:
            result = NvCSTestResult.SKIPPED
        elif os.EX_OK != returncode:
            result = NvCSTestResult.ERROR
        return result

    def runTest(self, args=None):
        result = NvCSTestResult.ERROR
        testName = "Nvcameratools sanity: vi mode test"
        currPath = os.path.dirname(os.path.realpath(__file__))
        viModeCmd = currPath + '/' + 'vi_mode.py --run --width {0} --height {1} --sensorMode {2} --sensorID {3} ' \
            '--csiBitDepth {4} --dynamicBitDepth {5} --targetMode {6} --os {7}'\
            .format(self.sensorSetting.width, self.sensorSetting.height, self.sensorSetting.sensor_mode,
                    self.sensorSetting.imager_id, self.sensorSetting.csiPixelBitDepth, self.sensorSetting.dynamicPixelBitDepth,
                    self.mode_list, self.os)

        out, err, returncode = NvCSIOUtil.runCmd('{0} {1}'.format(self.pythonPath, viModeCmd), pass_count = 1, sudo=True, os=self.os, logger=self.logger, a_timeoutSec=30.0)
        # Result
        if (-1 != out.find("VI_MODE Test PASSED")) and (os.EX_OK == returncode):
            result = NvCSTestResult.SUCCESS
        return result

class NvCSNvtunerdTestBase(NvCSTestBase):
    "Nvtuner Daemon Test Base"

    executePath = "nvtunerd_systemtests"
    os = None
    cmdOption = None
    testName = None

    def setupGraph(self):
        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.options.imager_id, self.options.sensor_name)
        return NvCSTestResult.SUCCESS

    def runPreTest(self, args=None):
        result = NvCSTestResult.SUCCESS
        name = self.executePath
        exePath = NvCSIOUtil.which(name)
        if exePath is None:
            self.logger.warning("Executable \"%s\" is not available in PATH environment variable.\n" \
                           "\t Please make sure it is getting built and is part of flashed image. Test skipped." % name)
            result = NvCSTestResult.SKIPPED
        return result

    def runTest(self, args):
        names = []
        results = []
        runtimes = []

        cmdOption = self.cmdOption
        testName = self.testName

        self.obGraph.stopAndDeleteGraph()

      # NVTuner daemon tunable test
        names.append("NVTuner Daemon test: " + testName)
        command = self.executePath + cmdOption
        self.logger.info("running: \"%s\"" % command)

        try:
            startTime = time.time()
            result = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.communicate()
            cmdStdout = output[0].decode()
            cmdStderr = output[1].decode()
            endTime = time.time()
            runtimes.append(endTime - startTime)
        except Exception as e:
            self.logger.error("Running nvtunerd_systemtests " + testName + ": " + str(e))
            self.logger.info("nvtunerd_systemtests STDOUT:\n" + cmdStdout)
            self.logger.info("nvtunerd_systemtests STDERR:\n" + cmdStderr)
            return NvCSTestResult.ERROR

        self.logger.info("NVTuner Daemon %s test Runtime (%s): %fs" % (testName, names[-1], runtimes[-1]))

        results.append(result.returncode)

        for line in cmdStdout.split('\n'):
            if 'INFO' in line:
                self.logger.info(line)
            elif 'WARNING' in line:
                self.logger.warning(line)
            elif 'ERROR' in line:
                self.logger.error(line)
            elif 'FATAL' in line:
                self.logger.fatal(line)
            elif 'DEBUG' in line:
                self.logger.debug(line)
            # If test failed, we want all the output lines
            elif result.returncode != 0:
                self.logger.info(line)

        if result.returncode != 0:
            self.logger.info("nvtunerd_systemtests STDERR:\n" + cmdStderr)


        self.logger.info("Exit Code: %d" % results[-1])

      # Results
        self.logger.info("=================")
        self.logger.info("==   Results   ==")
        self.logger.info("=================")
        for i in range(len(names)):
            self.logger.info("%s\t: %fs\t: %s" % ("PASS" if results[i] == 0 else "FAIL", runtimes[i], names[i]))

        for i in results:
            if i != 0:
                self.logger.error("NVTuner Daemon %s test failed." % testName)
                return NvCSTestResult.ERROR
        return NvCSTestResult.SUCCESS

class NvCSNvtunerdTunableTest(NvCSNvtunerdTestBase):
    "Nvtuner Daemon tunable test"

    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    def __init__(self, options, logger):
        NvCSTestBase.__init__(self, options, logger, "DaemonTunableTest")
        self.options = options
        self.nvcsPath = nvcsUtil.getNVCSPath()
        self.cmdOption = " --gtest_filter=SysTest.testIsTunable"
        self.testName = "nvtunerd_tunable"

class NvCSNvtunerdHostProcessTest(NvCSNvtunerdTestBase):
    "Nvtuner Daemon host_process test"

    def __init__(self, options, logger):
        NvCSTestBase.__init__(self, options, logger, "DaemonHostProcessTest")
        self.options = options
        self.nvcsPath = nvcsUtil.getNVCSPath()
        self.cmdOption = " --gtest_filter=SysTest.processOne"
        self.testName = "nvtunerd_host_process"

class NvCSNvtunerdLiveStreamTest(NvCSNvtunerdTestBase):
    "Nvtuner Daemon live_stream process"

    def __init__(self, options, logger):
        NvCSTestBase.__init__(self, options, logger, "DaemonLiveStreamTest")
        self.options = options
        self.nvcsPath = nvcsUtil.getNVCSPath()
        self.cmdOption = " --gtest_filter=SysTest.livePreview"
        self.testName = "nvtunerd_live_stream"
