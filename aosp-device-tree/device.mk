#
# Copyright (C) 2023 The LineageOS Project
#
# SPDX-License-Identifier: Apache-2.0
#

# Health
PRODUCT_PACKAGES += \
    android.hardware.health@2.1-impl \
    android.hardware.health@2.1-impl.recovery \
    android.hardware.health@2.1-service

# Overlays
PRODUCT_ENFORCE_RRO_TARGETS := *

# Product characteristics
PRODUCT_CHARACTERISTICS := tv

# Rootdir
PRODUCT_PACKAGES += \
    adbenable.sh \
    badblk.sh \
    bt_loader.sh \
    config_hwmon.sh \
    cyupdate.sh \
    cyupdate_config.sh \
    geupdate.sh \
    install-recovery.sh \
    lkm_loader.sh \
    nvphsd_setup.sh \
    run_ss_status.sh \
    supplicant_log_monitor.sh \
    wifi_loader.sh \

PRODUCT_PACKAGES += \
    fstab.abca \
    init.abca.rc \
    init.abcb.rc \
    init.comms.rc \
    init.darcy.rc \
    init.e2190.rc \
    init.e2220.rc \
    init.e3350.rc \
    init.foster_e.rc \
    init.foster_e_common.rc \
    init.foster_e_hdd.rc \
    init.hdcp.rc \
    init.lkm.rc \
    init.loki_e_base.rc \
    init.loki_e_common.rc \
    init.loki_e_lte.rc \
    init.loki_e_wifi.rc \
    init.loki_foster_e_common.rc \
    init.none.rc \
    init.nv_dev_board.usb.rc \
    init.nvphsd_setup.rc \
    init.ray_touch.rc \
    init.sata.configs.rc \
    init.sif.rc \
    init.t18x-interposer.rc \
    init.t18x-interposer_common.rc \
    init.t210.rc \
    init.t210_common.rc \
    init.tegra.rc \
    init.tegra_emmc.rc \
    init.tegra_sata.rc \
    init.tlk.rc \
    init.touch.0.rc \
    init.xusb.configfs.usb.rc \
    init.recovery.usb.rc \
    init.recovery.sif.rc \
    init.recovery.lkm.rc \
    init.recovery.foster_e_hdd.rc \
    init.recovery.foster_e.rc \
    init.recovery.darcy.rc \

# Shipping API level
PRODUCT_SHIPPING_API_LEVEL := 28

# Soong namespaces
PRODUCT_SOONG_NAMESPACES += \
    $(LOCAL_PATH)

# Inherit the proprietary files
$(call inherit-product, vendor/nvidia/mdarcy/mdarcy-vendor.mk)
