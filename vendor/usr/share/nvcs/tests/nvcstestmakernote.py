#-------------------------------------------------------------------------------
# Name:        nvcstestmakernote.py
# Purpose:     test the contents of makernote output
#
# Created:     05/17/2016
#
# Copyright (c) 2016-2020 NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#
#-------------------------------------------------------------------------------
#!/usr/bin/env python

# global mapping between testname and
# test objects

from __future__ import division
from __future__ import print_function

import sys

# Specify the python library search paths for softfp, hardfp, aarch64
sys.path.append('/usr/lib/arm-linux-gnueabi/tegra')
sys.path.append('/usr/lib/arm-linux-gnueabihf/tegra')
sys.path.append('/usr/lib/aarch64-linux-gnu/tegra')

import nvcstest
import nvcstestsystem
import platform
import os
import re
import subprocess
import string
import time
import shutil
import math
import traceback
from nvcstestutils import TestTimer
from nvcstestcore import *
from nvcstestutils import NvCSIOUtil

nvcscommonPath = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'common')
nvcscommonutilsPath = os.path.join(nvcscommonPath, 'nvcsCommonUtils.py')
sys.path.append(nvcscommonPath)
from nvcstestutils import NvCSTestResult
from nvcsCommonUtils import NVCSutil

nvcsUtil = None


class NvCSMakernoteTests(NvCSTestBase):

    global nvcsUtil
    if nvcsUtil is None:
        nvcsUtil = NVCSutil()

    mnOutputSaved = ''
    prctError = 0.05
    timer = None

    executePath = "nvmakernote"
    filterPath = ''
    fieldTable = {'AE': r'Exposure(.*)',
                  'CmnGain': r'CmnGain:(.*)',
                  'Lmts': r'Lmts:(.*)',
                  'AF': r'AF:(.*)'}

    def __init__(self, options, logger, sensorSetting):
        NvCSTestBase.__init__(self, options, logger, 'Makernote_Tests')
        self.filterPath = nvcsUtil.getToolsTopPath() + '/nvmakernote.dat'
        self.options = options
        self.sensorSetting = sensorSetting
        self.etRange = None


    def needAutoGraphSetup(self):
        self.obGraph.setSensorConfigFile(self.options.sensor_config_file)
        self.obGraph.setImager(self.sensorSetting.imager_id, self.sensorSetting.imager_name)

        return NvCSTestResult.SUCCESS


    def setupTest(self):
        return NvCSTestResult.SUCCESS

    def runPreTest(self, args=None):
        result = NvCSTestResult.SUCCESS
        name = self.executePath
        exePath = NvCSIOUtil.which(name)
        if exePath is None:
            self.logger.error("Executable \"%s\" is not available in PATH environment variable.\n" \
                            "\tPlease make sure it is getting built and is part of flashed image. Test skipped." % name)
            result = NvCSTestResult.SKIPPED
        return result

    def runTest(self, args):
        # get the ET and gain ranges
        bMultiExpos = nvcstestsystem.isMultipleExposuresSupported()

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
        # Get the index of the exposure that we need to use.
        #
        index, exposureMode = nvcstestsystem.getSingleExposureIndex(numExposures, False, self.options, self.logger)
        if (index == -1):
            self.logger.error("getSingleExposureIndex: Command line options error")
            return NvCSTestResult.ERROR

        # Query ranges to use minimum configuration settings
        self.obCamera.startPreview()
        exposureTimeRange = self.obCamera.getAttr(nvcamera.attr_exposuretimerange)
        self.obCamera.stopPreview()

        if (bMultiExpos):
            self.logger.info("Index   ETMin      ETMax")
            for i in range(0, numExposures, 1):
                self.logger.info("  %d   %2.6f   %2.6f " % (i, exposureTimeRange[0][i], exposureTimeRange[1][i]))
            self.etRange = [exposureTimeRange[0][index], exposureTimeRange[1][index]]
        else:
            self.logger.info("%2.6f   %2.6f " % (exposureTimeRange[0], exposureTimeRange[1]))
            self.etRange = [exposureTimeRange[0], exposureTimeRange[1]]

        self.obGraph.stopAndDeleteGraph()

        # tests are run in an order such that capture and makernote calls can be minimized
        if (self.options.timer_enable):
            self.timer = TestTimer('Makernote_Tests')
            self.timer.totTimeStart()

        # a previously made override file (if exists) is deleted
        self.deleteOverrides()

        totSkipped = False
        totResult = False
        if (self.filterExists()):
            test_ET_result, test_ET_skipped = self.makernote_test_ET(overrideReq=False, captureReq=True, mnCallReq=True, mnOutput=None)
            test_Brgt_Crt_result, test_Brgt_Crt_skipped = self.makernote_test_Brgt_and_Crt(overrideReq=False, captureReq=False, mnCallReq=False, mnOutput=self.mnOutputSaved)
            test_posC_result, test_posC_skipped = self.makernote_test_posC(overrideReq=False, captureReq=False, mnCallReq=False, mnOutput=self.mnOutputSaved)
            test_Gn_ET_result, test_Gn_ET_skipped = self.makernote_test_Gn_and_ET(overrideReq=True, captureReq=True, mnCallReq=True, mnOutput1=None)
            test_FR_result, test_FR_skipped = self.makernote_test_FR(overrideReq=False, captureReq=False, mnCallReq=False, mnOutput=self.mnOutputSaved)

            totSkipped = test_ET_skipped and test_Brgt_Crt_skipped and test_posC_skipped and test_Gn_ET_skipped and test_FR_skipped
            totResult = test_ET_result and test_Brgt_Crt_result and test_posC_result and test_Gn_ET_result and test_FR_result
        else:
            test_ET_result, test_ET_skipped = self.makernote_test_ET(overrideReq=False, captureReq=True, mnCallReq=True, mnOutput=None)
            test_Gn_ET_result, test_Gn_ET_skipped = self.makernote_test_Gn_and_ET(overrideReq=True, captureReq=True, mnCallReq=True, mnOutput1=None)

            totSkipped = test_ET_skipped and test_Gn_ET_skipped
            totResult = test_ET_result and test_Gn_ET_result

        # the latest override file is deleted before exiting
        self.deleteOverrides()

        if (self.options.timer_enable):
            self.timer.totTimeStop()
            if (not totSkipped):
                self.timer.displayResults(self.logger)

        if (totSkipped):
            return NvCSTestResult.SKIPPED
        elif (totResult):
            return NvCSTestResult.SUCCESS
        else:
            return NvCSTestResult.ERROR


    # test 3
    # tests if ET value is displayed properly in makernote output
    # returns tuple of (pass/fail, skip/no-skip)
    def makernote_test_ET(self, overrideReq, captureReq, mnCallReq, mnOutput):
        subTestName = 'makernote_test_ET'
        if (self.options.timer_enable):
            self.timer.addSubTimer(subTestName)
            self.timer.getSubTimer(subTestName).totTimeStart()

        self.logger.info(subTestName + ' +++ starting')

        AEavail, ETavail, ETfilled, ETcorrect = [False] * 4

        inputET, actualET = (self.etRange[0] + self.etRange[1]) / 2, 0.0
        deltaET = (self.prctError + 1.0) * inputET
        inputSettings = ['-e', str(inputET), '-g', '1.0', '-f', '300']    # adding focus setting for test 18

        if (captureReq):
            capOut = self.runCapture(inputSettings, subTestName)
            if (capOut == ''):
                return False

        if (mnCallReq):
            mnOutput = self.runMakernote(subTestName)
            if (mnOutput == ''):
                return False

        self.mnOutputSaved = mnOutput
        AEavail, info = self.getMakernoteInfo( self.fieldTable['AE'], mnOutput, subTestName)
        # skipping
        if (not AEavail):
            self.logger.info(subTestName + ': SKIP: AE field is not available in makernote output. Skipping test')
            if (self.options.timer_enable):
                self.timer.removeSubTimer(subTestName)
            return (True, True)

        if (info[0] == 'Exposure'):
            ETavail = True
            try:
                actualET = float((info[2].partition('ms'))[0]) / 1000
                ETfilled = True
            except ValueError:
                pass
            if ( abs(actualET - inputET) <= deltaET ):
                ETcorrect = True

        # asserting and displaying outputs
        result = ETavail and ETfilled and ETcorrect
        if (not result):
            if (not ETavail):
                self.logger.error(subTestName + ': Exposure Time is not present in makernote output')
            elif (not ETfilled):
                self.logger.error(subTestName + ': Exposure Time is not a number')
            elif (not ETcorrect):
                self.logger.error(subTestName + ': Exposure Time is not equal/close to input of {0}s, with a tolerance of +/-{1}. Actual ET is {2}s'.format(ETinputVal, ETepsilon, ETactualVal))

        if (self.options.timer_enable):
            self.timer.getSubTimer(subTestName).totTimeStop()
        return (result, False)


    # test 4
    # tests if Gn value is displayed properly in makernote output, and if Gn increases as ET is decreased
    # returns tuple of (pass/fail, skip/no-skip)
    def makernote_test_Gn_and_ET(self, overrideReq, captureReq, mnCallReq, mnOutput1):
        subTestName = 'makernote_test_Gn_and_ET'
        if (self.options.timer_enable):
            self.timer.addSubTimer(subTestName)
            self.timer.addSubTimer(subTestName + '2')
            self.timer.getSubTimer(subTestName).totTimeStart()

        self.logger.info(subTestName +' +++ starting')

        # creating camera overrides
        if (overrideReq):
            lines = []
            for i in range(8):
                lines.append('ae.VFRTable.Still[' + str(i) + '] = { 0.0333, 30.0000 };\n')
            success = self.createOverrides(lines, subTestName)
            if (not success):
                return False

        inputGain1, actualGain1 = 6.0, 0.0
        deltaGain1 = (self.prctError + 1.0) * inputGain1
        inputSettings1 = ['-g', str(inputGain1), '-f', '300']
        if (captureReq):
            capOut = self.runCapture(inputSettings1, subTestName)
            if (capOut == ''):
                return False
        if (mnCallReq):
            mnOutput1 = self.runMakernote(subTestName)
            if (mnOutput1 == ''):
                return False

        # second capture and makernote call
        # always do the 2nd capture and makernote call to avoid duplicate makernote outputs
        inputGain2, actualGain2 = 8.0, 0.0
        deltaGain2 = (self.prctError + 1.0) * inputGain2
        inputSettings2 = ['-g', str(inputGain2)]
        capOut = self.runCapture(inputSettings2, subTestName + '2')
        if (capOut == ''):
            return False
        mnOutput2 = self.runMakernote(subTestName + '2')
        if (mnOutput2 == ''):
            return False
        # save makernote output
        self.mnOutputSaved = mnOutput2


        actualET1, actualET2 = 0.0, 0.0
        (AEavail1, gainAvail1, gainFilled1, gainCorrect1,
        AEavail2, gainAvail2, gainFilled2, gainCorrect2,
        ETdecreasing) = [False] * 9

        AEavail1, info1 = self.getMakernoteInfo( self.fieldTable['AE'], mnOutput1, subTestName + ' Capture 1')
        AEavail2, info2 = self.getMakernoteInfo( self.fieldTable['AE'], mnOutput2, subTestName + ' Capture 2')
        # skipping
        if (not AEavail1 or not AEavail2):
            self.logger.info(subTestName + ': SKIP: AE field is not available in makernote output. Skipping test')
            if (self.options.timer_enable):
                self.timer.removeSubTimer(subTestName)
                self.timer.removeSubTimer(subTestName + '2')
            return (True, True)

        if (info1[3] == 'Gain'):
            gainAvail1 = True
            try:
                actualET1 = float((info1[2].partition('ms'))[0]) / 1000
                actualGain1 = float(info1[4])
                gainFilled1 = True
            except ValueError:
                pass
            if ( abs(actualGain1 - inputGain1) <= deltaGain1 ):
                gainCorrect1 = True
        if (info2[3] == 'Gain'):
            gainAvail2 = True
            try:
                actualET2 = float((info2[2].partition('ms'))[0]) / 1000
                actualGain2 = float(info2[4])
                gainFilled2 = True
            except ValueError:
                pass
            if ( abs(actualGain2 - inputGain2) <= deltaGain2 ):
                gainCorrect2 = True
        # if gain is increased, ET should decrease
        if (gainFilled1 and gainFilled2):
            if (actualET2 < actualET1):
                ETdecreasing = True
                self.logger.info(subTestName + ': actualET1: {0} , actualET2: {1}'.format( str(actualET1), str(actualET2) ))

        # TODO: the current result will be independent to the ETdecreasing. ETdecreasing is highly depending to the
        #       environmental setting. Therefore, we will remove the ETdecreasing as a pass/fail factor for this test.
        #       we will have to find a proper place to validate ETdecreasing in the future.
        """result = (gainAvail1 and gainFilled1 and gainCorrect1 and
                  gainAvail2 and gainFilled2 and gainCorrect2 and
                  ETdecreasing) """
        result = (gainAvail1 and gainFilled1 and gainCorrect1 and
                  gainAvail2 and gainFilled2 and gainCorrect2)
        if (not result):
            if (not gainAvail1):
                self.logger.error(subTestName + ': Gain is not present in makernote output of 1st capture')
            elif (not gainFilled1):
                self.logger.error(subTestName + ': Gain is not a number in makernote output of 1st capture')
            elif (not gainCorrect1):
                self.logger.error(subTestName + ': Gain from 1st capture is not equal/close to input of {0}, with a tolerance of +/-{1}. Actual Gain is {2}'.format(
                                  str(inputGain1), str(deltaGain), str(actualGain1) ))

            if (not gainAvail2):
                self.logger.error(subTestName + ': Gain is not present in makernote output of 2nd capture')
            elif (not gainFilled2):
                self.logger.error(subTestName + ': Gain is not a number in makernote output of 2nd capture')
            elif (not gainCorrect2):
                self.logger.error(subTestName + ': Gain from 2nd capture is not equal/close to input of {0}, with a tolerance of +/-{1}. Actual Gain is {2}'.format(
                                  str(inputGain2), str(deltaGain), str(actualGain2) ))
        # TODO: find out what to do with ETdecreasing later; For now, we will just write out a warning message if ETdcreasing failed.
        #       Print out a warning message for now.
        if (not ETdecreasing):
            self.logger.warning(subTestName + ': ET is not decreasing as gain increases.\n' +
                'For input gain {0}: output gain is {1}, output ET is {2}s\n'.format(
                str(inputGain1), str(actualGain1), str(actualET1)) +
                'For input gain {0}: output gain is {1}, output ET is {2}s'.format(
                str(inputGain2), str(actualGain2), str(actualET2)))

        if (self.options.timer_enable):
            self.timer.getSubTimer(subTestName).totTimeStop()
            self.timer.getSubTimer(subTestName).appendTimes(self.timer.getSubTimer(subTestName + '2'))
            self.timer.removeSubTimer(subTestName + '2')
        return (result, False)


    # test 7
    # cannot check if Crt value is correct, because F-Number is not available programmatically
    # depends on test 3 to have run right before
    # tests if Brgt and Crt values are displayed properly in makernote output
    # returns tuple of (pass/fail, skip/no-skip)
    def makernote_test_Brgt_and_Crt(self, overrideReq, captureReq, mnCallReq, mnOutput):
        subTestName = 'makernote_test_Brgt_and_Crt'
        if (self.options.timer_enable):
            self.timer.addSubTimer(subTestName)
            self.timer.getSubTimer(subTestName).totTimeStart()

        self.logger.info(subTestName + ' +++ starting')

        CmnGainavail, Brgtavail, Crtavail, Brgtfilled, Crtfilled = [False] * 5

        CmnGainavail, info = self.getMakernoteInfo( self.fieldTable['CmnGain'], mnOutput, subTestName)
        # skipping
        if (not CmnGainavail):
            self.logger.info(subTestName + ': SKIP: CmnGain field is not available in makernote output. Skipping test')
            if (self.options.timer_enable):
                self.timer.removeSubTimer(subTestName)
            return (True, True)

        if (info[1] == 'Brgt'):
            Brgtavail = True
            try:
                actualBrgt = float(info[2])
                Brgtfilled = True
            except ValueError:
                pass
        if (info[3] == 'Crt'):
            Crtavail = True
            try:
                actualCrt = [ float(info[4]), float(info[5]) ]
                Crtfilled = True
            except ValueError:
                pass

        result = Brgtavail and Crtavail and Brgtfilled and Crtfilled
        if (not result):
            if (not Brgtavail):
                self.logger.error(subTestName + ': Brgt within CmnGain is not present in makernote output')
            elif (not Brgtfilled):
                self.logger.error(subTestName + ': Brgt value is not a number')
            if (not Crtavail):
                self.logger.error(subTestName + ': Crt within CmnGain is not present in makernote output')
            elif (not Crtfilled):
                self.logger.error(subTestName + ': Crt values are not numbers')

        if (self.options.timer_enable):
            self.timer.getSubTimer(subTestName).totTimeStop()
        return (result, False)


    # test 10
    # depends on test 4 to have run right before
    # tests if FR value is displayed properly in makernote output
    # returns tuple of (pass/fail, skip/no-skip)
    def makernote_test_FR(self, overrideReq, captureReq, mnCallReq, mnOutput):
        subTestName = 'makernote_test_FR'
        if (self.options.timer_enable):
            self.timer.addSubTimer(subTestName)
            self.timer.getSubTimer(subTestName).totTimeStart()
        self.logger.info(subTestName + ' +++ starting')

        inputFR = 30.0
        actualFRs = [0.0, 0.0, 0.0]
        Lmtsavail, FRavail, FRfilled, FRcorrect = [False] * 4

        Lmtsavail, info = self.getMakernoteInfo( self.fieldTable['Lmts'], mnOutput, subTestName)
        # skipping
        if (not Lmtsavail):
            self.logger.info(subTestName + ': SKIP: Lmts field is not available in makernote output. Skipping test')
            if (self.options.timer_enable):
                self.timer.removeSubTimer(subTestName)
            return (True, True)

        if (info[7] == 'FR'):
            FRavail = True
            try:
                actualFRs = [float(info[8]), float(info[9]), float(info[10])]
                FRfilled = True
            except ValueError:
                pass
            if (actualFRs[0] == inputFR):
                FRcorrect = True

        result = FRavail and FRfilled and FRcorrect
        if (not result):
            if (not FRavail):
                self.logger.error(subTestName + ': FR within Lmts is not present in makernote output')
            elif (not FRfilled):
                self.logger.error(subTestName + ': FR values are not numbers')
            elif (not FRcorrect):
                self.logger.error(subTestName + ': FR values are not equal to input of {0}. Actual FR values are {1}'.format(inputFR, actualFRs))

        if (self.options.timer_enable):
            self.timer.getSubTimer(subTestName).totTimeStop()
        return (result, False)


    # test 18
    # depends on makernote output of test 3
    # tests if posC value is displayed properly in makernote output, and if it's within the FR range
    # returns tuple of (pass/fail, skip/no-skip)
    def makernote_test_posC(self, overrideReq, captureReq, mnCallReq, mnOutput):
        subTestName = 'makernote_test_posC'
        if (self.options.timer_enable):
            self.timer.addSubTimer(subTestName)
            self.timer.getSubTimer(subTestName).totTimeStart()
        self.logger.info(subTestName + ' +++ starting')

        AFavail, posCavail, posCfilled, posCcorrect, posCinRange, fravail, frfilled = [False] * 7
        inputposC, actualposC = 300, 0
        frRange = []

        AFavail, info = self.getMakernoteInfo( self.fieldTable['AF'], mnOutput, subTestName)
        # skipping
        if (not AFavail):
            self.logger.info(subTestName + ': SKIP: AF field is not available in makernote output. Skipping test')
            if (self.options.timer_enable):
                self.timer.removeSubTimer(subTestName)
            return (True, True)

        if (info[10] == 'posC'):
            posCavail = True
            try:
                actualposC = float(info[11])
                posCfilled = True
            except ValueError:
                pass
        if (info[16] == 'fr'):
            fravail = True
            try:
                frRange.append( float(info[17]) )
                frRange.append( float(info[18]) )
                frfilled = True
            except ValueError:
                pass

        if (inputposC == actualposC):
            posCcorrect = True
        if (frfilled):
            if (inputposC >= frRange[0] and inputposC <= frRange[1]):
                posCinRange = True

        result = posCavail and posCfilled and posCcorrect and posCinRange and fravail and frfilled
        if (not result):
            if (not posCavail):
                self.logger.error(subTestName + ': posC within AF is not present in makernote output')
            elif (not posCfilled):
                self.logger.error(subTestName + ': posC value is not a number')
            elif (not posCcorrect):
                self.logger.error(subTestName + ': posC value is not equal to input focus value of {0}. Actual posC value: {1}'. format(
                                  inputposC, actualposC))
            if (not fravail):
                self.logger.error(subTestName + ': Crt within CmnGain is not present in makernote output')
            elif (not frfilled):
                self.logger.error(subTestName + ': Crt values are not numbers')
            elif (not posCinRange):
                self.logger.error(subTestName + ': posC value is not withing fr working range : [{0},{1}]'.format(
                                  frRange[0], frRange[1]))

        if (self.options.timer_enable):
            self.timer.getSubTimer(subTestName).totTimeStop()
        return (result, False)


    # captures jpeg image
    def runCapture(self, inputSettings, testName):
        out = ''
        if (self.options.timer_enable):
            if (self.timer.testName == testName):
                self.timer.capTimeStart()
            else:
                self.timer.getSubTimer(testName).capTimeStart()

        try:
            self.logger.info('Capturing image ...')
            sensor = ['-i', str(self.options.imager_id)]
            pythonPath = sys.executable
            capCmd = [pythonPath, str(nvcsUtil.getNVCSPath()) + '/examples/nvcamera_capture_image.py'
                     ] + sensor + inputSettings + ['-t', 'jpeg', '--hpdisable']
            print(" ".join(capCmd))
            capProcess = subprocess.Popen(capCmd, stdout=subprocess.PIPE)
            capProcess.wait()
            out = capProcess.stdout
        except Exception as e:
            self.logger.error('Running capture: ' + str(e))
            out = ''

        if (self.options.timer_enable):
            if (self.timer.testName == testName):
                self.timer.capTimeStop()
            else:
                self.timer.getSubTimer(testName).capTimeStop()
        return out


    # runs makernote on the most recent captured image
    def runMakernote(self, testName):
        out = ''
        if (self.options.timer_enable):
            if (self.timer.testName == testName):
                self.timer.mnTimeStart()
            else:
                self.timer.getSubTimer(testName).mnTimeStart()

        try:
            self.logger.info('Calling makernote ...')
            # using makernote on Android, until nvmakernote support is added
            mnPath = nvcsUtil.getExecutablePath() + "/" + self.executePath
            mnCmd = [mnPath, '-i', str(nvcsUtil.getToolsTopPath()) + '/NVCSCapture/nvcs_test.jpg']
            mnCmd += ['-t', self.filterPath] if (self.filterExists()) else []
            mnProcess = subprocess.Popen(mnCmd, stdout=subprocess.PIPE)
            mnProcess.wait()
            out = mnProcess.communicate()[0].decode()
        except Exception as e:
            self.logger.error('Running makernote: ' + str(e))
            out = ''

        if (self.options.timer_enable):
            if (self.timer.testName == testName):
                self.timer.mnTimeStop()
            else:
                self.timer.getSubTimer(testName).mnTimeStop()
        return out


    # creates override .isp file
    def createOverrides(self, lines, testName):
        result = False
        if (self.options.timer_enable):
            if (self.timer.testName == testName):
                self.timer.overrideTimeStart()
            else:
                self.timer.getSubTimer(testName).overrideTimeStart()

        try:
            cameraOverridesPath = nvcsUtil.getToolsTopPath() + '/camera_overrides.isp'
            cameraOverrides = open(cameraOverridesPath, 'wt')
            for line in lines:
                cameraOverrides.write(line)
            cameraOverrides.close()
            result = True
        except Exception as e:
            self.logger.error('Creating overrides isp file: ' + str(e))

        if (self.options.timer_enable):
            if (self.timer.testName == testName):
                self.timer.overrideTimeStop()
            else:
                self.timer.getSubTimer(testName).overrideTimeStop()
        return result

    def deleteOverrides(self):
        try:
            overrideFilePath = nvcsUtil.getToolsTopPath() + '/camera_overrides.isp';
            if (os.path.exists(overrideFilePath)):
                os.remove( overrideFilePath )
            return True
        except Exception as e:
            self.logger.info('Unable to delete overrides isp file: ' + str(e))
            return False

    def filterExists(self):
        try:
            exists = os.path.isfile(self.filterPath)
            return exists
        except Exception:
            self.logger.info('Unable to find filter file: ' + self.filterPath)
            return False

    # searches through makernote output for a regular expression
    def getMakernoteInfo(self, regex, mnOutput, testName):
        lineFound = False
        info = None
        searchObj = re.search( regex, mnOutput, flags=0 )
        if (searchObj != None):
            lineFound = True
            self.logger.info( testName + ':==================Makernote relevant output:===================')
            line = searchObj.group()
            self.logger.info(line)
            self.logger.info( testName + ':===============================================================')
            info = (str(line)).replace(':',' ').replace(';',' ').replace(',',' ').split()
        return (lineFound, info)
