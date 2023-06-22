#!/system/bin/sh

log_tool="/system/bin/log"
Genesys_tool="/vendor/bin/genesys_hub_update"
Genesys_bin_file="/system/vendor/firmware/GL3521_foster.bin"
Genesys_ini_file="/system/vendor/firmware/GL_SS_HUB_ISP_foster.ini"
fw_target="F/W:8724"

sleep 10
$log_tool -t "Genesys_hub_update" -p d "check current f/w version..."
if [ -f "$Genesys_tool" ]
then
	$log_tool -t "Genesys_hub_update" -p d "Genesys tool found"
else
	$log_tool -t "Genesys_hub_update" -p d "Genesys tool not found"
fi
if [ -f "$Genesys_ini_file" ]
then
	$log_tool -t "Genesys_hub_update" -p d "Genesys ini file found"
else
	$log_tool -t "Genesys_hub_update" -p d "Genesys ini file not found"
fi

fwVer_result=$($Genesys_tool -i $Genesys_ini_file -v)
if [ "$fwVer_result" == "$fw_target" ]; then
	$log_tool -t "Genesys_hub_update" -p d "FW latest ($fwVer_result)"
else
	$log_tool -t "Genesys_hub_update" -p d "current $fwVer_result, target $fw_target"
	$log_tool -t "Genesys_hub_update" -p d "USB Hub fw update begins..."

	if [ -f "$Genesys_bin_file" ]
	then
		$log_tool -t "Genesys_hub_update" -p d "Genesys bin file found"
	else
		$log_tool -t "Genesys_hub_update" -p d "Genesys bin file not found"
	fi

	i=1
	max_attempts=5
	status="failed"
	while [ $i -le $max_attempts ]
	do
		genesys_result=$($Genesys_tool -i $Genesys_ini_file -b $Genesys_bin_file)
		if [ "$genesys_result" == "pass" ]; then
			$log_tool -t "Genesys_hub_update" -p d "attempt $i passed"
			status="passed"
			break;
		else
			$log_tool -t "Genesys_hub_update" -p d "attempt $i failed and retry"
		fi
		i=$((i+1))
	done
	$log_tool -t "Genesys_hub_update" -p d "Genesys $status!"
fi
