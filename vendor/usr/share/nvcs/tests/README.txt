The purpose of these scripts is to test NVCS (Nvidia Camera Scripting) interface.
NVCS is a python scripting interface for camera. We can either run group of sanity
tests or pick and choose tests that we want to run. The usage and the description
of the tests and scripts are given below.

Usage: nvcstestmain.py <options>

Options:
  -h, --help     show this help message and exit
  -s             Run Sanity tests
  -n             Number of times to run
  -t TEST_NAME   Test name to execute
  -d TEST_NAME   Disable the test
  -i IMAGER_ID   set imager id. 0 for rear facing, 1 for front facing, a for all modes
  -m SENSOR_MODE set sensor mode of selected imager, a for all modes

==============================================

options description:

-s
    runs the sanity tests
        "jpeg_capture"
        "raw_capture"
        "concurrent_raw"
        "exposuretime"
        "gain"
        "focuspos"
        "fuseid"
        "crop"
        "multiple_raw"
        "v4l2_compliance"
        "vi_mode"
        "nvtunerd_tunable"
        "nvtunerd_host_process"
        "nvtunerd_live_stream"
        "makernote"

-t TEST_NAME

    runs the TEST_NAME. Multiple -t arguments are supported.

-d TEST_NAME

    disables the TEST_NAME. multiple -d arguments are supported.

==============================================
Result:

    Result images and logs are stored under $HOME/NVCSTest directory.

    Each test will have directory under $HOME/NVCSTest, which should have
    result images for that test

    Summary log is saved at $HOME/NVCSTest/summarylog.txt


==============================================
List of tests:

"jpeg_capture"
    captures a jpeg image and checks for the existence of the image.

"raw_capture"
    captures a raw image and checks for the existence of the raw image.

"concurrent_raw"
    captures a jpeg+raw image concurrently. Checks the max pixel value (should be <= 1023)

"exposuretime"
    captures concurrent jpeg+raw images, setting the exposure time within supported exposure time range linearly. Checks the exposure value in the header and value returned from the get attribute function

"gain"
    captures concurrent jpeg+raw images, setting the gains within supported gain range linearly. Checks the sensor gains value in the raw header
    and value returned from the get attribute function.

"focuspos"
    captures concurrent jpeg+raw images, setting the focus position within supported focuser range linearly. Checks the focus position in the raw header and value returned from the get attribute function.

"crop"
    capture raw image with [top, left, bottom, right] = [0, 0 ,320, 240] dimentions

"multiple_raw"
    captures 100 concurrent jpeg+raw images. Checks for the existence of raw images and the max pixel value (should be <= 1023)

"linearity"
    captures a series of jpeg+raw images. Linearly increases gain and exposure values and analyzes the raw images for correlating linear pixel values.

"linearity3"
    captures a series of raw images. Linearly increases gain and exposure values and analyzes the raw images for correlating linear pixel values.
    This is the next "linearity" test, but needs more validation first.

"sharpness"
    captures concurrent raw+jpeg images from min to max focus positions and checks for the change in sharpness with the change in focus position.
    Performs the same steps going from max to min focus position and also checks if the sharpenss measurements are the same as previous iteration for the same focus position.

"blacklevel"
    captures 15 (default) raw images and outputs statistics on image black levels

"bayerphase"
    captures 1 raw images and checks raw pattern for expected relative intensities based on light panel

"fuseid"
    queries the fuse id from the driver and checks that its value is reasonable.

"autoexposure"
    captures a series of 3 raw images. Tests linearity of brightness in images to test auto exposure algorithm used in device factory calibration.

"constant_condition"
    Check if max ET in driver is larger than 33ms. Check if focuser range is power of 2. Print Camera
    Override target paths.

"aperture_conformance"
    Launch nvctconform test, record test results. Currently only aperture conformance test is available.

"makernote"
    Captures jpeg with different settings and validates makernote info.

"sensor_dt_compliance"
    Launch sensor DT compliance test (sensor-kernel-tests binary needs to be installed). Checks if sensor DT is compliant.

"v4l2_compliance"
    Launch v4l2 compliance tests (v4l2-compliance binary needs to be installed), record test results.

"vi_mode"
    Launch vi mode tests (v4l2-ctl binary needs to be installed), record test results. Both 'mmap' and 'user' modes, and the first available frame size are used by default.

"nvtunerd_tunable"
    Launch nvtunerd_systemtests with "-t test_tunable" as the option. The test checks if device is tunable through NVTuner daemon.

"nvtunerd_host_process"
    Launch nvtunerd_systemtests with "-t test_host_process" as the option. The test checks if daemon can pick up host path image, and apply host path tuning.

"nvtunerd_live_stream"
    Launch nvtunerd_systemtests with "-t test_live_stream" as option. The test checks if daemon can perform live streaming, and checks if received preview frame is corrupted.

==============================================
VERSION HISTORY
7.8.1
    fix resolution and pixel format setting in the vi_mode test
        - set the resolution and pixel format based on the selected sensor mode

7.8.0
    update codebase to improve Python 3 compatibility
        - replace Python 2-specific code with Python 2/3 compatible equivalent

7.7.4
    limit the upper bound of EP constant during the exposure product test for sensor with small gain range
        - EP test will limit the EP constant to the product of the mid-gain setting and maximum exposure time
        if the maximum gain of the sensor is less than or equal to 4

7.7.3
    double blacklevel test spread of averages tolerance for PWL mode
        - blacklevel test spread of averages tolerance has been increased from 1% to 2%
        for PWL sensor mode with more than 10 output bits
        - blacklevel test spread of averages tolerance has been increased from 6% to 12%
        for PWL sensor mode with 10 output bits

7.7.2
    print exposure times and gains if PWL mode is detected
        - print PWL mode if it is detected
        - print all exposure times and gains after each PWL capture

7.7.1
    fix pixel format error introduced by version 7.7.0
        - pixel format has been altered to Int16 for all sensor mode under all platform
            -- the pixel format should not be altered to int16 if it is not a compressed image
        - undo the pixel format change and only change the pixel format to the compressed image after decompression

7.7.0
    add multi-frame/plane support in nvraw_v3
        - metadata and pixel value extraction will be stored in to a list, which indexed based on the frame number and plane number
    add decompanding support for nvraw_v3 python interface
        - add NvRawFile_decompress_direct and computePwlTable call from nvraw_v3
        - remove the code that load the decompression LUT from nvraw header
        - add codes to convert pwl to decompression LUT

7.6.0
    change the default nvraw version from v2 to v3
        - fix nvraw v3 support for black level test
        - fix an issue where the AE stability test outputs nvraw v2 files even though --nvraw=v3 is specified

7.5.13
    Fix the --lps option
        - sensor mode property is missing in getSensorInfo() function; this is an
          error introduced in version 7.5.9.

7.5.12
    Fix the hang stage of vi_mode test by applying a timeout and set the subprocess
    to non-shell mode to the updated runCmd() call

7.5.11
    improve nvcstestutils::runCmd() call
    add a timer thread to monitor the runCmd call
        - if the subprocess is running longer than the timeout (default 60sec),
          the timer thread will kill the process and raise an exception
    add an arugment to allow user to turn on/off of the shell environment of
    the suprocess call.

7.5.10
    Add a work around for issue of black image capture from jpeg_capture test.
    During jpeg capture, we do not have half press enabled and we do not wait for
    any events from preview before initiating a still capture. Because of this, the
    auto exposure is running and when the capture happens, the auto exposure has not
    completed and the image could come out dark. Hence providing a delay for the
    AE to settle down.

7.5.9
    move vi_mode to a subprocess
        - nvcs is conflicting with the v4l2-ctrl; the Graph memory is corrupted
          after calling v4l2-ctrl. In this case, we move the v4l2-ctrl call to a
          new process which holds its own memory stack

7.5.8
    fix run-time errors
    1. check_sensor_mode_ctrl did not properly pass down the sensor mode to the v4l2-ctl
        - add -d switch with the correct device path of the selected sensor mode to v4l2-ctl
    2. set the starting gain to 4.0 in gain linearity test if and only if the
       current starting gain is smaller than 4.0 and the maximum gain is greater than 4.0

7.5.7
    gain range and exposure time range validation
        - skip the gain and EP linearity test if the minimum gain and maximum gain are the same
        - skip the exposure linearity and EP test if the minimum exposure time and maximum exposure time are the same
        - give a warning message if minimum exposure time and maximum exposure time are equal in exposure time test
        - give a warning message if minimum gain and maximum are equal in the gain test

7.5.6
    updating the Linearity test
      - add the linearityMode advanced option
          - to run one or all linearity tests
      - reduce the ETprecisionThreshold for EP linearity test to support lower gain
7.5.5
    add advanced option --gainGranularity
        - set the gain step based on the gainGranularity (unit in dB).
7.5.4
    change the pixel value threshold validation logic in the linearity test.
        - will failed the linearity test only if the average pixel values are below
        the threshold for all Bayer channels. The old method fails the
        Linearity test if only the average pixel value is below the threshold in
        one Bayer channel.
7.5.3
    update the capture_script test for Automotive platform.
    In Automotive platform, the capture_script test will just
    perform a SDR raw capture and a HDR raw capture.
7.5.2
    Update sensor_dt_compliance test binary path.
7.5.1
    Support for QNX root file system becoming readonly.
7.5.0
    Add sensor_dt_compliance test.
7.4.2
    Changes basic data container to integer.
7.4.1
    Add "--nvraw" option to allow selecting nvraw version (v2 or v3)
    This is Mobile only option for now, so Automotive will always use nvraw v2 for now.
7.4.0
    Adding nvraw v3 support for conformance.
    Conformance version number of the original change was 7.3.13
    Conformance version number of the reverted change was 7.3.14
7.3.22
    fix black level capturing in linearity test. It will try to capture
    an image with the exposure time lower than the minimum boundary
    of the sensor.
        -- will only set the exposure to a lower number if the lower
           exposure time is still valid in the range. Otherwise, we
           will set the exposure time to the median between max and
           min.
7.3.21
    Support of  12 bit compressed. Also changes basic data container for
    bayer pixels from 16 bit unsigned to 32 bit float.
7.3.20
    For mobile sensors, use minimum supported sensor gain to run linearity
    instead of setting minimum gain to 4.0
7.3.19
    Use sensor_mode option in v4l2-ctl commands if avaiable
    Select the correct resolution and pixel format when running vi_mode test
7.3.18
    Skip all the tests if no sensor entries are found
    Handle no camera module case
7.3.17.1
   remove auto control for automotive
   - Automotive does not support any auto-control (i.e. half-press), so
     will remove it from automotive
   - jpg and concurrent raw are remove in conformance
   - jpg support is removed from capture script
7.3.17
    Use sensor mode 0 by default
    Use ET and gain ranges per sensor mode
    Change constant_condition and makernote tests to use ET based on ET range
7.3.16
    WAR to disable USERPTR for vi_mode
    Disable 33ms check for WDR sensor modes in constant_condition test
7.3.15
    Custom exposure linearity for special sensors(I.E IMX390, IMX424).
    - Use minimum supported gain value in case it is less than 4.0 instead
      of scaling it to 4.0
    - Ask user to increase the target brightness and re-run environment
      check before running exposure linearity
    - remove the round() for calculating the slope in linearity test
    - add AR0820 to the special sensor list, which avoiding the EP linearity test.
7.3.14
    custom linearity and gain test for special sensors(I.E IMX390, IMX424). These sensors
    can set the gain value only when exposure time is set to the capped value. Hence,
    custom linearity:
        set the exposure time to capped value for gain linearity and skip exposure time production test
    custom gain:
        set the exposure time to the capped value
7.3.13
    separate command line options, help screen, and test list between Automotive and Mobile
7.3.12
    modify the method to check the blacklevel fluctuation
    -validate whether the delta of the minimum and maximum
     blacklevel is within 1% variation of the average blacklevel
7.3.11
    update the exposure time test by using the minimum
    exposure time retrieved from sensor instead of clamping
    the minimum exposure time to 100us
7.3.10
    fix the VI-Mode test by correcting the v4l2-ctl calls
7.3.9
    increase the minimum gain for exposure linearity test
7.3.8
    change the exposure time setting for gain linearity test
7.3.7
    add support for command line option to specify version of the
    of the generated nvraw file  --nvraw [v3 | v2]
7.3.6
    add support to convert s1.14 and U16 pixel format back to Int16 format
7.3.5
    add support to process isp_fp16 pixel format data (Xavier feature)
7.3.4
    add advanced option --gainsteps to support user determined number
    of linearity steps for linearity test
    add a minimum boundary of linearity steps (at least 5 steps)
7.3.3
    add advanced option --segment to suppport partial linearity option
7.3.2
    fix the unknown output format of the NvRAW captured by IMX-185
    WDR mode.
7.3.1
    fix the issue where the calculated gain value is lower than the
    minimum gain returned from the sensor in Linearity test.
7.3.0
    add option -m to support different sensor mode
    modified option -i to take multiple imager index
7.2.29
    Update the text from -h option of nvcstestmain. References to front
    and rear cameras were removed.
7.2.28
   Query sensor unique name from constant condition test.
   Fail the test if any of the entries are null.
7.2.27
    Change the gain step in the linearity to be multiple of 0.3db over the whole gain range
    instead of random steps
7.2.26
    Display full list of overrides paths in the constant_condition test
7.2.25
    Set file permission on creation. Permission is set to 0666 for files and 0777 for
    directories. This ensures a new user would have access over these.
7.2.24
    Fix issues with Product Linearity test.
    Better handling & accouning of embedded lines with respect to actual
    pixel data.
7.2.23
    Add HDR support for nvcs
7.2.22
    Add info on time consumed by the each test and all tests combined.
    Check for existence of nvmakernote executable and flag if not.
7.2.21
    Remove ET decreasing as gain increasing criteria in Marketnote. The test
    will still perform this test case, but the result will not affect the
    sanity test due to the reason that this test is highly depending on the
    environmental setting.
7.2.20
    Add a file path validation safe guard to prevent exception throw by os.remove in nvcstestmakernote.py::deleteOverrides(self)
7.2.19
    Fix precision of exposure time and gain when running linearity test to match with
    results from environment check. Disable halfpress by default during raw caputure for
    linearity test
7.2.18
    Find highest valid exposure time for the gain linearity which should cover
    the whole gain range without over saturating. Change ET precision threshold
    to 5ms from 10ms for linearity and disable halfpress by default
    Relax variation threshold for EP linearity to 5% from 3.16%
7.2.17
    Update AE_Stability tests to change permissions of camera overrides file
    to 0664 after writing the the file
7.2.16
    Add support for following APIs
    Get Info
    setImager with config file support for automotive
7.2.15
    Add 3 nvtuner daemon tests to sanity tests:
    "nvtunerd_tunable", "nvtunerd_host_process", "nvtunerd_live_stream".
    Add "makernote" test to sanity test.
7.2.14
    Add "v4l2_compliance" test to sanity tests.
    Add "vi_mode" test to to sanity tests.
7.2.13
    Added tests to check makernote output of captures with different settings.
    Tests are not yet in sanity and conformance lists.
7.2.12
    Add "aperture_conformance" test.
    Use logarithmic scale to sample Gain for gain linearity test.
    Use logarithmic scale to sample exposure time for exposure time linearity test.
    Disable halfpress under linearity tests.
    Remove sharpness values comparison at min and max focus positions.
7.2.11
    Update ae_stability test to use highest resolution sensor mode
    for both preview and still keeping both preview and still mode the same.
7.2.10
    Power of 2 check on focuser range is moved from focuspos and sharpness
    test to constant_condition test. Add camera override target path query
    under constant_condition test. Add command line option "--ts" to enable
    time stamp printed on terminal. All hard coded parameters for cropping
    now start with "ROT_".
7.2.9
    Update sharpness and focuspos test to use highest resolution sensor mode
    for both preview and still keeping both preview and still mode the same.
7.2.8
    Capture script test would run two tests back to back and both tests
    generate files with same name. First one is overwritten by the second one.
    This change generates files with different filenames and they are named
    after the mode used - auto and manual.
7.2.7
    Let Blacklevel conformance test uses the maximum exposure time returned by
    sensor driver. Add confirm prompt before and after getting Blacklevel and
    Linearity test. Change initialization of MinTracker under SNR calculation.
    Add test "constant_condition", which checks if the max exposure time is smaller
    than 33ms under exposure sanity test. When this new test is ignored, a warning
    will be printed.
7.2.6
    Check if needed directories (input, output and settings) exist and create
    them if they are not already present.
7.2.5
    Add advanced option "--rsquaredmin" to -c, which can set passing criteria
    for R^2 in linearity test. For sensors with good linearity, can get R^2
    above 0.90 and close to 1.0; while for some other sensors with relatively
    poor linearity, can get lower R^2 than 0.90, but shall not be too low like
    0.5 either. Please contact NV camera tool/char/IQ team when using this option.
7.2.4
    Added no_effect color/special effect test. This will run the input image
    through the same pipeline as the other color effects tests, but without
    applying any effects. Took out unncessary debug prints related to graphs,
    added prints for displaying generated output file path for all tests.
7.2.3
    Modify capture script test that enables selecting preview and still capture
    sensor modes through command line options "-p" and "-s". Also add available
    sensor mode listing though "-l" option.
7.2.2
    Update override location handling to use newer, cleaner data packing method.
    Update ae_stability test to use override locations correctly.
7.2.1
    Add "pfp_streaming_file" and "pfp_streaming" to -s
7.2.0
    Add "capture_script" to "-s" and "ae_stability" to "-c"
    Update "capture_script" and "ae_stability" to work on L4T.
7.1.5
    Update Linearity test to use environment check data for ET ranges.
    Remove Linearity3 test code.
7.1.4
    Replace hardcoded EV in EV Linearity test with value computed from environment check.
7.1.3
    Add -e effect tests
    Add --numcaptures to specify number of captures
    Add --input to specify input nvrawfile for host_capture test
7.1.2
    Add OS detection to support differences between L4T and Android.
    Run "stayon" at graph launch.
7.1.1
    Fix host_sensor tests by passing s1.14 data instead of int16
7.1.0
    Add NVCS example script regression test.
    Add additional ET range checks to BlackLevel and Linearity tests.
    Remove Linearity3 from "-c" testplan.
    Reduce "BlackLevelPadding" in linearity to relax underexposure requirements.
    Make Under/Over-exposure error messages more explicit.
7.0.9
    Keep preview on for gain, exposuretime, focuspos, multiple_raw.
    Reduces test runtimes significantly.
7.0.8
    Add jpeg scaling (user-selectable output size of jpeg_capture test).
7.0.7
    Add semi-auto mode to hdr_ratio test.
    Add "--targetratio" to advanced options (for semi-auto hdr_ratio).
7.0.6
    Add "--runs" option for multiple test runs.
    Fix broken logging to "summarylog.txt".
7.0.5
    Add host_sensor test to sanity ("-s")
    Add "--numTimes" support to gain, exposuretime, host_sensor, and focuspos.
    Improve "--numTimes" error checking.
7.0.4
    Use max exposure as upper range for ExposureTime test.
7.0.3
    Fix preview start/stop unbalance in Sharpness test.
7.0.2
    (WAR) delay and re-read gainrange when max gain is too high.
7.0.1
    Update focuser detection code to match BSP method.
7.0.0
    Refactor test code for Release 2.0.
6.2.3
    Update utility class to format help messages
6.2.2
    Skip concurrent raw capture test when aohdr is enabled.
    Uses "attr_enableaohdr" added by nvcamera version 1.9.3.
6.2.1
    Insert delay in Linearity, BlackLevel, and HDR Ratio tests after setting exposure,
    gain, and focus position to allow settings to take effect before capture.
6.2.0
    Add HDR Ratio Test.
    Add AEOverride attribute for HDR Ratio, Linearity, and Blacklevel tests.
    Disable half-press in BlackLevel, Linearity, and HDR Ratio tests.
6.1.0
    Add AE Stability Test
    Add warning to gain test and linearity test when sensor gain max is higher than 16
    Add log output of Gain and Exposure Time range in linearity tests.
6.0.2
    Add focuser physical range power-of-two check to focuser tests.  Also force focus position
    test to check focuser position 0 (even if out of range).
6.0.1
    Add check for pixel values greater than the maximum possible value.  Check occurs after raw captures.
6.0.0
    Add NvRawfile Version 4 support.  Add NvCSRawFile extension to abstract NvRawfile compatibility.
5.2.3
    Update Fuse ID test to compare Raw Header FuseID against Driver FuseID
    Change Fuse ID test to return an error for test-defined failure cases
5.2.2
    Fixed Linearity3 by catching unused return variable from processLinearityStats()
5.2.1
    Fixed gain test intermittent loop due to race condition resulting in 0 values.
    Camera preview is now enabled for gain range query.
5.2.0
    Fixed host_sensor test. Added --width and --height options for host_sensor test.
    Added utility functions to create test raw image.
5.1.0
    Add crop test to the sanity test suite.
5.0.2
    Remove autofocus call from sharpness test.
    Move focuser to minimum working range before running focuspos test.
5.0.1
    Resorted shuffled linearity configs before printing to log (Capture order printed for reference)
    CSV output implemented for linearity tests
5.0.0
    Restructured logging mechanism to enable accumulative warning and error messages at the end of log.
    Added stage testing mechansim to nvcs test suites. Added linearity3 as a staging test to conformance '-c'.
4.11.0
    Added a next generation linearity3 test code.  This test still needs more validation to verify as a pass/fail requirement.
4.10.0
    Add fuse id test
4.9.3
    Changing host_sensor test to use bayergains instead of iso
4.9.2
    Added a query in linearity for the focuser physical range, and adjusted the test to use the
    minimum physical range for the focuser.  This improves stability.
4.9.1
    Added "--noshuffle" to advanced options and applied number of images flag "-n" to linearity.
4.9.0
    Change sharpness test to use more relaxed constraint
4.8.5
    Add divide-by-zero protection that may occur caused by broken sensor drivers
4.8.4
    remove halfpress (converging auto algorithms) while capturing image from all sanity tests
4.8.3
    Cleanup of parameter variables in linearity.
4.8.2
    Update the content for "-h" option. Add "-l" option to list sanity and conformance test names.
    Add "--nv" to list advanced options "-h" and Move "-n" and "--threshold" to advance options.
4.8.1
    fix syntax error in multiple_raw test
4.8.0
    Use raw-only capture for all the tests except concurrent_raw test
4.7.0
    Add "-c" option to run conformance tests
4.6.1
    Output normalized sharpness values in sharpness test
4.6.0
    Restructured processing functions (used in linearity and black level) to be part of nvcstestcore.
    Enabled querying of range to linearity test.  Test is still able to run old hardcoded range values using "--classic" option flag
    Increased exposure time for blacklevel to 0.100s to prevent test passing with light
4.5.0
    start preview before asking user to setup and confirm the test setup
4.4.2
    fix output message in sharpness test.
4.4.1
    print the version information in the log file
4.4.0
    Modified sharpness test to lock AE throughout the test and added new runPostTest interface
4.3.1
    Modified exposuretime test to use exposuretimerange query. Fix focuspos test file names.
4.3.0
    Added preliminary 'bayerphase' check test.  Similar logic is also included in the linearity test. Also added version parameter (-v, --version).
4.2.2
    Modified prompt logic to include force flag.  In 4.2.1, the force flag would only affect setup, but not mid run prompts.
4.2.1
    Modified prompt logic so it can be utilized mid run.  Added prompts to linearity test.
4.2.0
    Added ignore focuser flag (--nofocus).  Updated linearity message output to detail the environment check.
    Updated blacklevel reference in linearity test to allow a variance of 10, instead of 2x the dimmest capture
    settings the test will run.
4.1.0
    Added black level test and -n option. -n option is the number of times the user wants the test to run. This meaning may vary depending on test.
    Added --threshold option. Currently only black level supports these options. Refactored linearity code.
4.0.0
    Added sharpness test. focuspos test is changed to use physical range of focuser.
3.1.0
    Added --odm option for ODM conformance tests.  Linearity test is ran multiple times to compensate for frame corruption.  Added missing math module.
    Refactored the code for better maintainability
3.0.0
    Refactored the code for better maintainability
2.0.0
    Linearity test is added.  NvCSTestConfiguration class is added to help capture images with specific exposure and gain values.
