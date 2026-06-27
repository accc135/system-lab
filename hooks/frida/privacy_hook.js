// Frida Hook Script for Privacy Data Collection Monitoring
// 监控5类个人信息的访问

var results = {
    device_ids: [],
    mac_addresses: [],
    locations: [],
    installed_apps: [],
    clipboard: []
};

// 1. 设备号监控 (IMEI, OAID, Android ID)
function hookDeviceIds() {
    try {
        // Hook IMEI
        var TelephonyManager = Java.use('android.telephony.TelephonyManager');

        TelephonyManager.getDeviceId.overload().implementation = function() {
            var result = this.getDeviceId();
            if (result) {
                results.device_ids.push({
                    type: 'IMEI',
                    value: result,
                    method: 'TelephonyManager.getDeviceId()',
                    timestamp: new Date().toISOString()
                });
                send({type: 'device_id', subtype: 'IMEI', value: result});
            }
            return result;
        };

        TelephonyManager.getDeviceId.overload('int').implementation = function(slotId) {
            var result = this.getDeviceId(slotId);
            if (result) {
                results.device_ids.push({
                    type: 'IMEI',
                    value: result,
                    method: 'TelephonyManager.getDeviceId(int)',
                    timestamp: new Date().toISOString()
                });
                send({type: 'device_id', subtype: 'IMEI', value: result});
            }
            return result;
        };

        // Hook IMEI via getImei
        if (TelephonyManager.getImei) {
            TelephonyManager.getImei.overload().implementation = function() {
                var result = this.getImei();
                if (result) {
                    results.device_ids.push({
                        type: 'IMEI',
                        value: result,
                        method: 'TelephonyManager.getImei()',
                        timestamp: new Date().toISOString()
                    });
                    send({type: 'device_id', subtype: 'IMEI', value: result});
                }
                return result;
            };
        }

        // Hook Android ID
        var Settings = Java.use('android.provider.Settings$Secure');
        var getString = Settings.getString.overload('android.content.ContentResolver', 'java.lang.String');
        getString.implementation = function(resolver, name) {
            var result = getString.call(this, resolver, name);
            if (name === 'android_id' && result) {
                results.device_ids.push({
                    type: 'Android ID',
                    value: result,
                    method: 'Settings.Secure.getString(android_id)',
                    timestamp: new Date().toISOString()
                });
                send({type: 'device_id', subtype: 'Android ID', value: result});
            }
            return result;
        };

        // Hook OAID (移动安全联盟统一设备标识)
        try {
            var MdidSdkHelper = Java.use('com.bun.miitmdid.core.MdidSdkHelper');
            MdidSdkHelper.InitSdk.implementation = function(context, listener) {
                send({type: 'device_id', subtype: 'OAID', value: 'OAID SDK initialized'});
                return this.InitSdk(context, listener);
            };
        } catch(e) {
            // OAID SDK not present
        }

        send({type: 'info', message: 'Device ID hooks installed'});
    } catch(e) {
        send({type: 'error', message: 'Device ID hook error: ' + e.message});
    }
}

// 2. MAC地址监控
function hookMacAddress() {
    try {
        // Hook Wi-Fi MAC
        var WifiInfo = Java.use('android.net.wifi.WifiInfo');
        WifiInfo.getMacAddress.implementation = function() {
            var result = this.getMacAddress();
            if (result) {
                results.mac_addresses.push({
                    type: 'Wi-Fi MAC',
                    value: result,
                    method: 'WifiInfo.getMacAddress()',
                    timestamp: new Date().toISOString()
                });
                send({type: 'mac_address', subtype: 'Wi-Fi', value: result});
            }
            return result;
        };

        // Hook NetworkInterface
        var NetworkInterface = Java.use('java.net.NetworkInterface');
        NetworkInterface.getHardwareAddress.implementation = function() {
            var result = this.getHardwareAddress();
            if (result) {
                var mac = '';
                for (var i = 0; i < result.length; i++) {
                    mac += ('0' + (result[i] & 0xFF).toString(16)).slice(-2);
                    if (i < result.length - 1) mac += ':';
                }
                results.mac_addresses.push({
                    type: 'Hardware MAC',
                    value: mac,
                    method: 'NetworkInterface.getHardwareAddress()',
                    timestamp: new Date().toISOString()
                });
                send({type: 'mac_address', subtype: 'Hardware', value: mac});
            }
            return result;
        };

        // Hook BluetoothAdapter
        var BluetoothAdapter = Java.use('android.bluetooth.BluetoothAdapter');
        BluetoothAdapter.getAddress.implementation = function() {
            var result = this.getAddress();
            if (result) {
                results.mac_addresses.push({
                    type: 'Bluetooth MAC',
                    value: result,
                    method: 'BluetoothAdapter.getAddress()',
                    timestamp: new Date().toISOString()
                });
                send({type: 'mac_address', subtype: 'Bluetooth', value: result});
            }
            return result;
        };

        send({type: 'info', message: 'MAC address hooks installed'});
    } catch(e) {
        send({type: 'error', message: 'MAC address hook error: ' + e.message});
    }
}

// 3. 地理位置监控
function hookLocation() {
    try {
        var Location = Java.use('android.location.Location');

        Location.getLatitude.implementation = function() {
            var result = this.getLatitude();
            results.locations.push({
                type: 'Latitude',
                value: result,
                method: 'Location.getLatitude()',
                timestamp: new Date().toISOString()
            });
            send({type: 'location', subtype: 'Latitude', value: result});
            return result;
        };

        Location.getLongitude.implementation = function() {
            var result = this.getLongitude();
            results.locations.push({
                type: 'Longitude',
                value: result,
                method: 'Location.getLongitude()',
                timestamp: new Date().toISOString()
            });
            send({type: 'location', subtype: 'Longitude', value: result});
            return result;
        };

        // Hook LocationManager
        var LocationManager = Java.use('android.location.LocationManager');
        LocationManager.getLastKnownLocation.implementation = function(provider) {
            var result = this.getLastKnownLocation(provider);
            if (result) {
                send({type: 'location', subtype: 'LastKnown', value: 'Provider: ' + provider});
            }
            return result;
        };

        send({type: 'info', message: 'Location hooks installed'});
    } catch(e) {
        send({type: 'error', message: 'Location hook error: ' + e.message});
    }
}

// 4. 已安装应用列表监控
function hookInstalledApps() {
    try {
        var PackageManager = Java.use('android.content.pm.PackageManager');

        PackageManager.getInstalledPackages.overload('int').implementation = function(flags) {
            var result = this.getInstalledPackages(flags);
            if (result && result.size() > 0) {
                results.installed_apps.push({
                    type: 'Installed Apps',
                    count: result.size(),
                    method: 'PackageManager.getInstalledPackages(int)',
                    timestamp: new Date().toISOString()
                });
                send({type: 'installed_apps', count: result.size(), method: 'getInstalledPackages'});
            }
            return result;
        };

        PackageManager.getInstalledApplications.implementation = function(flags) {
            var result = this.getInstalledApplications(flags);
            if (result && result.size() > 0) {
                results.installed_apps.push({
                    type: 'Installed Apps',
                    count: result.size(),
                    method: 'PackageManager.getInstalledApplications(int)',
                    timestamp: new Date().toISOString()
                });
                send({type: 'installed_apps', count: result.size(), method: 'getInstalledApplications'});
            }
            return result;
        };

        // Hook queryIntentActivities
        PackageManager.queryIntentActivities.overload('android.content.Intent', 'int').implementation = function(intent, flags) {
            var result = this.queryIntentActivities(intent, flags);
            if (result && result.size() > 0) {
                send({type: 'installed_apps', count: result.size(), method: 'queryIntentActivities'});
            }
            return result;
        };

        send({type: 'info', message: 'Installed apps hooks installed'});
    } catch(e) {
        send({type: 'error', message: 'Installed apps hook error: ' + e.message});
    }
}

// 5. 剪贴板监控
function hookClipboard() {
    try {
        var ClipboardManager = Java.use('android.content.ClipboardManager');

        ClipboardManager.getPrimaryClip.implementation = function() {
            var result = this.getPrimaryClip();
            if (result) {
                try {
                    var item = result.getItemAt(0);
                    var text = item.getText();
                    if (text) {
                        results.clipboard.push({
                            type: 'Clipboard',
                            value: text.toString(),
                            method: 'ClipboardManager.getPrimaryClip()',
                            timestamp: new Date().toISOString()
                        });
                        send({type: 'clipboard', value: text.toString()});
                    }
                } catch(e) {
                    // Unable to read clipboard content
                }
            }
            return result;
        };

        ClipboardManager.getText.implementation = function() {
            var result = this.getText();
            if (result) {
                results.clipboard.push({
                    type: 'Clipboard',
                    value: result.toString(),
                    method: 'ClipboardManager.getText()',
                    timestamp: new Date().toISOString()
                });
                send({type: 'clipboard', value: result.toString()});
            }
            return result;
        };

        send({type: 'info', message: 'Clipboard hooks installed'});
    } catch(e) {
        send({type: 'error', message: 'Clipboard hook error: ' + e.message});
    }
}

// Main execution
Java.perform(function() {
    send({type: 'info', message: 'Frida script started'});

    // 等待一下确保APP完全初始化
    setTimeout(function() {
        hookDeviceIds();
        hookMacAddress();
        hookLocation();
        hookInstalledApps();
        hookClipboard();

        send({type: 'info', message: 'All hooks installed successfully'});
    }, 2000);
});
