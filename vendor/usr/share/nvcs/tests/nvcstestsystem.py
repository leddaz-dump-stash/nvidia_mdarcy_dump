# Copyright (c) 2014-2019, NVIDIA Corporation.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#

import platform
import os
import nvcamera
import stat

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

def is_method(obj, name):
    for item in dir(nvcamera):
        if (item == name):
            return 1
    return 0

def isMultipleExposuresSupported():

    # Multiple exposures are supported from Major Version 3
    majorVer = int((nvcamera.__version__).split('.')[0])

    if (majorVer >= 3):
        return True
    return False

#
# getSingleExposureIndex()
# This function looks at the command line parameters and makes sure that
# certain rules are followed.
# For this function, "use_eall" should not be set. Hence the caller should
# call this function only when he wants to get the index of the single exposure.
#
def getSingleExposureIndex(numExposures, bOnlyE0Allowed, options, logger):

    #
    # use_eall can not be used here.
    #
    if (options.use_eall == True):
        logger.error("Command line option use_eall not allowed")
        return (-1, 0)

    use_e_list = [ options.use_e0, options.use_e1, options.use_e2, options.use_e3,
                   options.use_e4, options.use_e5, options.use_e6, options.use_e7 ]

    #
    # use_exposure_options beyond numExposures should be set to False - This can be checked
    # Ex: numExposures = 3
    # use_e_list[] = [ False, True, False, False, False, False, False, False]
    #
    for i in range(numExposures, len(use_e_list), 1):
        if (use_e_list[i] == True):
            logger.error("Command line options use_e0...use_e7 " + str(use_e_list) + " beyond numExposures (%d) should not be set" % numExposures)
            return (-1, 0)
    #
    # Only one use_exposure_options within numExposures should be set.
    #
    count = 0
    start = 0
    if (bOnlyE0Allowed == True):
        start = 1
    for i in range(start, numExposures, 1):
        if (use_e_list[i] == True):
            count = count + 1

    if (count > 1 and bOnlyE0Allowed == False):
        logger.error("Only one of the command line options use_e0...use_e7 " + str(use_e_list) + " can be set.")
        return (-1, 0)
    elif (count > 0 and bOnlyE0Allowed == True):
        logger.error("Only one of the command line option use_e0 (or no use_ex option) is allowed.")
        return (-1, 0)

    # Now return the first exposure that is set
    for i in range(0, numExposures, 1):
        if (use_e_list[i] == True):
            return (i, 1<< i)

    # None of them are set. At this point the options are sane.
    # Use the index 0
    return (0, 0x1)

#
# getMultipleExposureMode()
# This function looks at the command line parameters and makes sure that
# certain rules are followed.
# This function takes into account use_e0,... use_e7 as well as use_eall
# Call this function when you want more than one index to be used as the
# exposure mode.
#
def getMultipleExposureMode(numExposures, options, logger):

    use_e_list = [ options.use_e0, options.use_e1, options.use_e2, options.use_e3,
                   options.use_e4, options.use_e5, options.use_e6, options.use_e7 ]

    #
    # use_exposure_options beyond numExposures should be set to False - This can be checked
    # Ex: numExposures = 3
    # use_e_list[] = [ False, True, False, False, False, False, False, False]
    #
    for i in range(numExposures, len(use_e_list), 1):
        if (use_e_list[i] == True):
            logger.error("Command line options use_e0...use_e7 " + str(use_e_list) + " beyond numExposures (%d) should not be set" % numExposures)
            return -1

    #
    # use_eall will override everything else
    #
    if (options.use_eall == True):
        exposureMode = (1 << numExposures) -1
        return exposureMode

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
            logger.error("getMultipleExposureMode: Unsupported combination on command line.")
            logger.error("    More than one exposure is specified that is not HDR.")
            logger.error("    ExposureMode 0x%X Number of exposures %d " % (exposureMode, numExposures))
            return -1

    return exposureMode



