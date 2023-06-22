# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All Rights Reserved.
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited

import os
from common import RunCmd, PrintClients, PrintLine

smmus=['12000000.iommu', '10000000.iommu', '8000000.iommu']
debug_path='/sys/kernel/debug/'
num_smmus=1

soc_path1 = "/sys/module/tegra_fuse/parameters/tegra_chip_id"
soc_path2 = "/sys/devices/soc0/soc_id"

def get_soc_id():
    if os.path.exists(soc_path1):
        socid = int(open(soc_path1).read())
    elif os.path.exists(soc_path2):
        socid = int(open(soc_path2).read())
    else:
        socid = 0
    return hex(socid)

def smmu_stats(client):
    """
    Read and dump smmu related things
    """
    soc_id = get_soc_id()
    if (soc_id == '0x00'):
        print('Error: Unable to get SOC ID')
        sys.exit(1)

    if (soc_id == '0x23'):
        num_smmus = 3
    elif (soc_id == '0x19'):
        num_smmus = 2

    for i in range(0, num_smmus):
        smmu_clients = []
        data, err = RunCmd('ls ' + debug_path + smmus[i] + '/masters')
        if data:
            for line in data.split("\n"):
                if line:
                    smmu_clients.append(line)

        if smmu_clients:
            print "\n---------------SMMU" + str(i) + " Clients---------------"
            PrintClients(smmu_clients)

    if client:
        PrintLine()
        for i in range(0, num_smmus):
            data, err = RunCmd("find -L /d/" + smmus[i] + "/masters/" + client + " -name ptdump")
            if data:
                iova, err = RunCmd("cat " + data.strip())
                if not err:
                    print "\n" + client + " IOVA mappings :"
                    print iova
                else:
                    print "Stderr : " + err
            break

        if not data:
            print "\n" + client + " : No such client!"
