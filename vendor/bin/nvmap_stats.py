# Copyright (c) 2018, NVIDIA CORPORATION.  All Rights Reserved.
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited

from common import RunCmd, PrintLine

def nvmap_stats(CVSRAM):
    """
    Dump nvmap related information from nvmap debugfs
    """

    print "\n---------------NvMap IOVMM Usage---------------"
    print "Procrank :"
    data, err = RunCmd("cat /sys/kernel/debug/nvmap/iovmm/procrank")
    if not err:
        print data
    else:
        print "Stderr : " + err

    PrintLine()
    print "\nOrphan handles :"
    data, err = RunCmd("cat /sys/kernel/debug/nvmap/iovmm/orphan_handles")
    if not err:
        print data
    else:
        print "Stderr : " + err

    PrintLine()
    print "\nMaps :"
    data, err = RunCmd("cat /sys/kernel/debug/nvmap/iovmm/maps")
    if not err:
        print data
    else:
        print "Stderr : " + err

    PrintLine()
    print "\nPagepool :"
    data, err = RunCmd("ls /sys/kernel/debug/nvmap/pagepool")
    if not err:
        for line in data.split():
            if line:
                data, err = RunCmd("cat /sys/kernel/debug/nvmap/pagepool/" + line)
                print line + " = " + data.strip()
    else:
        print "Stderr : " + err

    if not CVSRAM:
        print "\n---------------NvMap CVSRAM Usage---------------"
        print ("CVSRAM Base: "),
        data, err = RunCmd("cat /sys/kernel/debug/nvmap/cvsram/base")
        if not err:
            print data
        else:
            print "Stderr : " + err
        print ("CVSRAM Size: "),
        data, err = RunCmd("cat /sys/kernel/debug/nvmap/cvsram/size")
        if not err:
            size = int(data, 16)/1024
            print str(size) + "KB"
        else:
            print "Stderr : " + err

        PrintLine()
        print "\nAll_allocations :"
        data, err = RunCmd("cat /sys/kernel/debug/nvmap/cvsram/all_allocations")
        if not err:
            print data
        else:
            print "Stderr : " + err

        PrintLine()
        print "\nAllocations :"
        data, err = RunCmd("cat /sys/kernel/debug/nvmap/cvsram/allocations")
        if not err:
            print data
        else:
            print "Stderr : " + err

        PrintLine()
        print "\nMaps :"
        data, err = RunCmd("cat /sys/kernel/debug/nvmap/cvsram/maps")
        if not err:
            print data
        else:
            print "Stderr : " + err

        PrintLine()
        print "\nOrphan_handles :"
        data, err = RunCmd("cat /sys/kernel/debug/nvmap/cvsram/orphan_handles")
        if not err:
            print data
        else:
            print "Stderr : " + err
