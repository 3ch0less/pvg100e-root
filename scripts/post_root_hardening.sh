#!/bin/sh
# Post-root hardening for the PVG100E: OTA kill, bloat, telemetry, ATFWD, hosts block.
# Everything is reversible (pm enable / pm install-existing / unset props).
set -e
D="adb shell pm disable-user --user 0"
U="adb shell pm uninstall --user 0"

echo "[1/4] killing OTA + bloat"
$D com.tcl.vodafone.fota
$D com.tcl.vodafone.fota.overlay
$D com.facebook.appmanager
$D com.facebook.services
$D com.facebook.system
$D com.android.providers.partnerbookmarks
$D com.android.providers.partnerbookmarks.overlay
$D com.android.partnerbrowsercustomizations.example
$D com.android.partnerbrowsercustomizations.example.overlay
$D com.android.email.partnerprovider
$D com.android.email.partnerprovider.overlay
$D com.google.android.partnersetup

echo "[2/4] telemetry agents"
$D com.qualcomm.qti.StatsPollManager
$D com.qualcomm.qti.autoregistration
$D com.qti.dpmserviceapp
$D com.qapp.secprotect
$D com.google.android.backuptransport
$D com.google.android.syncadapters.contacts
$D com.google.android.onetimeinitializer

echo "[3/4] ATFWD daemon (persistent off)"
adb shell "su -c 'setprop persist.radio.atfwd.start false'"

echo "[4/4] hosts blocklist (StevenBlack, systemless)"
curl -sLO https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts
adb push hosts /data/local/tmp/hosts
adb shell "su -c 'cp /data/local/tmp/hosts /data/adb/hosts && chmod 644 /data/adb/hosts &&
 printf \"#!/system/bin/sh\nmount --bind /data/adb/hosts /system/etc/hosts\n\" > /data/adb/service.d/99hosts.sh &&
 chmod 755 /data/adb/service.d/99hosts.sh && mount --bind /data/adb/hosts /system/etc/hosts'"
rm -f hosts

echo "verify: $(adb shell ping -c1 -W2 googleadservices.com 2>&1 | head -1)"
echo "done. Reboot to bake it in."
