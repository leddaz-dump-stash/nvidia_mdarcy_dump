#!/vendor/bin/sh

# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

# config_hwmon.sh -- Configure hwmon type devices under /sys/class/hwmon/

# Parameters:
# $1: device node name
# $2: setup node name
# $3: setup value
# $4: condition (optional)
# case ina3221: use first channel label name as the condition
#               since there could be multiple ina3221 nodes.

# Unconditional examples:
# config_hwmon.sh ina3221 curr1_crit 8000
# Conditional examples
# config_hwmon.sh ina3221 curr2_crit 1800 GPU

# Export PATH to use toolbox (log/ls/rm/ln/...) in vendor partition (/vendor/bin/)
# This avoids sepolicy violation when full_treble is enabled.
export PATH=/vendor/bin:$PATH

########################################################################
# Main function
########################################################################

HWMON_ROOT="/sys/class/hwmon"

for dir in $HWMON_ROOT/*
do
    # Match device node name
    if [ $(< $dir/name) != $1 ]; then continue; fi
    # Check the optional condition
    if [[ ! -z "$4" ]]
    then
        case "$1" in
            ina3221)
                if [ $(< $dir/in1_label) != $4 ]; then continue; fi
                ;;
            *)
                echo "unsupported condition"
                ;;
        esac
    fi
    # Write the value into the target node
    echo $3 > $dir/$2
done
