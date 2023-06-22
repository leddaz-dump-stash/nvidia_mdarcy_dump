The purpose of this script is to capture nvraw image in SDR or HDR format.

Usage: nvcamera_capture_image.py <options>

==============================================
please use "--help" or "-h" options for the list of options
I.E. python nvcamera_capture_image.py -h

==============================================
Result:

    Result images are stored under $NVCSPathOnTarget/NVCSCapture

==============================================
Version History:
1.4.0
    update codebase to improve Python 3 compatibility
        - replace Python 2-specific code with Python 2/3 compatible equivalent

1.3.0
    change the default nvraw version from v2 to v3

1.2.19
    fix option message for embeddedOS platform
        - remove jpeg, concurrent, YUV/YUV16 support
1.2.18
    fix setting gain/exposure over boundary for non-HDR mode
       - will only set exposure and gain to either the min or
         the max of the value returned by the sensor when
         the user is trying to set a value which is lower than
         the minimum or higher than the maximum
1.2.17
    remove the HDR restriction in capture script
1.2.16
    remove jpeg capture and auto control in EmbeddedOS/QNX
1.2.15
    Add --nvraw option to choose between nvraw V2 vs V3
1.2.14
    Exit with error message if camera module is not present
1.2.13
    separate  command line options, help screen, and run script between Automotive and Mobile.
1.2.12
    remove -s dependency for HDR mode in Automotive build
1.2.11
    add out of bound check for user inputted exposure time.
1.2.10
    Add support for command line option to specify version of the
    of the generated nvraw file  --nvraw [v3 | v2]
1.2.9
    Fix HDR Exposure Time list issue when HDR is enabled.
1.2.8
    Add options to support using preview window for framing.
1.2.7
    add options to support noise reduction mode
1.2.6
    Update the text coming out of help (-h) option on command line. References to
    front and rear cameras were removed.
1.2.5
    Properly update the use_e_list when a gain or an exposure time argument passed
    on the command line.
1.2.4
    HDR muliple exposure support added for Automotive
1.2.3
    Added info on time consumed by the script.
1.2.1
    Support for display of many new sensor properties like description,
    name, position, module name, mode type, CSI and Dynamic pixel depth etc.
1.2.0
    Multiple frame capture support is added. Supported streaming types are immediate
    and buffered. Cropping images when streaming is now available. The supported
    file types for streaming are: NVRAW, JPEG, YUV. Number of frames can be
    specified for a fixed length of images to stream, or streaming can keep
    going until memory or disk space limit is reached.

1.1.0
    Depricating --preview/-p option to set the preview mode.
    Keep the preview and still capture sensor modes same specified
    via --still/-s option
1.0.2
   Override preview and still resolutions if the manual focus position
   is specified by user.
   Also changed the help text for default values for still and preview
   command lines options to be consistent with actual values in use.
1.0.1
    Option to disable the halfpress algorithm is added. This is mainly used
    to reduce capture time. Version option returns both the version of this
    script and the NvCamera Module Version.

1.0.0
    Capture script is created. Options are added to change various capture
    parameters like exposure, gain, and focus. All main functionalities of
    capturing are added.
