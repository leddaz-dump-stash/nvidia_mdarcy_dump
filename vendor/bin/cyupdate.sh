#!/vendor/bin/sh

#avoid firmware update at very first boot, which reboots abruptly
sleep 30

#Load platform-specific config
source cyupdate_config.sh

result_latest="status: latest"
result_update="status: update"
result_error="status: error"
log_tool="/system/vendor/bin/toybox_vendor log"
result=$($tool $version_file v $fw_bin_file | /system/vendor/bin/toybox_vendor grep "status:")

if [ "$result" == "$result_update" ]; then
    $log_tool -t "cyupdate" -p i "Update fw..."
    log=$($tool $dev_file f $fw_bin_file)
# need to print the message for debug purpuse.
    $log_tool -t "cyupdate" -p i $log
    mode=$(cat $boot_mode_file)
    if [ "$mode" == "boot" ]; then
        $log_tool -t "cyupdate" -p i "error detected, retry flash"
        log=$($tool $dev_file f $fw_bin_file)
        $log_tool -t "cyupdate" -p i $log
    fi
    if [ "$mode" == "app" ]; then
        $log_tool -t "cyupdate" -p i "flash successfully"
    fi
    $log_tool -t "cyupdate" -p i "Update fw done"
fi

if [ "$result" == "$result_latest" ]; then
    $log_tool -t "cyupdate" -p i "Fw latest"
fi

if [ "$result" == "$result_error" ]; then
    $log_tool -t "cyupdate" -p i "Error detected, please fix"
fi
