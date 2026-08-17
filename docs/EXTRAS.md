# Extras

Everything on this page assumes root from the main guide. All of it is reversible.

## Debloat and OTA protection

The OTA updater is the one that matters: an official update would overwrite the boot
partition and either remove root or soft-brick the device.

```sh
# carrier OTA (root-stomping risk)
adb shell pm disable-user --user 0 com.tcl.vodafone.fota
adb shell pm disable-user --user 0 com.tcl.vodafone.fota.overlay

# facebook background installer
adb shell pm disable-user --user 0 com.facebook.appmanager
adb shell pm disable-user --user 0 com.facebook.services
adb shell pm disable-user --user 0 com.facebook.system

# partner cruft
adb shell pm disable-user --user 0 com.android.providers.partnerbookmarks
adb shell pm disable-user --user 0 com.android.providers.partnerbookmarks.overlay
adb shell pm disable-user --user 0 com.android.partnerbrowsercustomizations.example
adb shell pm disable-user --user 0 com.android.partnerbrowsercustomizations.example.overlay
adb shell pm disable-user --user 0 com.android.email.partnerprovider
adb shell pm disable-user --user 0 com.android.email.partnerprovider.overlay
adb shell pm disable-user --user 0 com.google.android.partnersetup
```

Remove Google apps you do not want (vanish from the launcher, system partition untouched):

```sh
adb shell pm uninstall --user 0 com.google.android.youtube
adb shell pm uninstall --user 0 com.google.android.gm          # gmail
adb shell pm uninstall --user 0 com.google.android.apps.maps
adb shell pm uninstall --user 0 com.google.android.apps.photos
adb shell pm uninstall --user 0 com.google.android.apps.docs   # drive
adb shell pm uninstall --user 0 com.google.android.music
adb shell pm uninstall --user 0 com.google.android.videos
adb shell pm uninstall --user 0 com.google.android.calendar
adb shell pm uninstall --user 0 com.google.android.apps.messaging
adb shell pm uninstall --user 0 com.google.android.apps.tachyon # duo
```

Bring anything back with `pm install-existing <pkg>`.

## Telemetry and the ATFWD daemon

```sh
# telemetry agents
adb shell pm disable-user --user 0 com.qualcomm.qti.StatsPollManager
adb shell pm disable-user --user 0 com.qualcomm.qti.autoregistration
adb shell pm disable-user --user 0 com.qti.dpmserviceapp
adb shell pm disable-user --user 0 com.qapp.secprotect
adb shell pm disable-user --user 0 com.google.android.backuptransport
adb shell pm disable-user --user 0 com.google.android.syncadapters.contacts
adb shell pm disable-user --user 0 com.google.android.onetimeinitializer

# the ATFWD daemon (remote AT commands over BT/USB, real CVEs, running by default)
adb shell su -c 'setprop persist.radio.atfwd.start false'
```

Verify after a reboot: `adb shell su -c 'ps -A | grep -i atfwd'` should print nothing.

## Systemwide tracker blocklist

StevenBlack unified hosts, systemlessly:

```sh
curl -LO https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts
adb push hosts /data/local/tmp/hosts
adb shell "su -c 'cp /data/local/tmp/hosts /data/adb/hosts && chmod 644 /data/adb/hosts &&
  printf \"#!/system/bin/sh\nmount --bind /data/adb/hosts /system/etc/hosts\n\" > /data/adb/service.d/99hosts.sh &&
  chmod 755 /data/adb/service.d/99hosts.sh && mount --bind /data/adb/hosts /system/etc/hosts'"
```

Check: `adb shell ping -c1 googleadservices.com` should resolve to 127.0.0.1.

## Diag port (modem introspection)

```sh
adb shell su -c 'setprop sys.usb.config diag,adb'
```

The phone re-enumerates as 05c6:901d: interface 0 is the Qualcomm DIAG channel, interface 1
keeps adb alive. Point SCAT or qcsuper at interface 0 over libusb. Runtime only; add
`persist.sys.usb.config` if you want it permanent. The stock DiagProtector activity is
blank on this build, the setprop path is the working one.

## Hidden apps worth opening

```sh
adb shell am start -n com.EngineeringMode/.ManuList      # Qualcomm engineering test menu
adb shell am start -n com.tcl.engineermode/.telephony.AutoAnswerPreferenceActivity
```

Also present on the stock ROM: `com.qualcomm.qti.qmmi` (factory hardware tests),
`com.tcl.TctRFM` (RF test), `com.tcl.ygps` (GPS test), `com.android.runintest.ddrtest`.

## adbd root (unfinished business, notes for the curious)

The stock adbd on this device is a static build with the root branch compiled out
(`ALLOW_ADBD_ROOT` false; the "cannot run as root in production builds" string is in the
binary). I built a patched adbd with the privilege-drop calls NOPed
(`drop_ugid`/`drop_caps` call sites at file offsets 0x6368c, 0x63698, 0x636b0, 0x636bc),
but on swap-in the daemon does not come back and I have not yet captured why (no tombstone,
no avc denial; suspect the restart chain dies with the adb session before `start adbd`
runs). Functionally irrelevant since `adb shell su -c` is full root, but if you finish it,
document it. Next step: run the patched binary standalone as root and capture stderr, e.g.
via a serial or a second adb channel.
