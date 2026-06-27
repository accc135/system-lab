// Frida脚本 - 隐私监控 + SSL Pinning绕过
// 同时监控隐私数据访问并绕过证书固定

var results = {
    device_ids: [],
    mac_addresses: [],
    locations: [],
    installed_apps: [],
    clipboard: []
};

// ========== SSL Pinning 绕过 ==========
function bypassSSLPinning() {
    try {
        // 方法1: 绕过TrustManagerImpl
        var TrustManagerImpl = Java.use('com.android.org.conscrypt.TrustManagerImpl');
        TrustManagerImpl.verifyChain.implementation = function(untrustedChain, trustAnchorChain, host, clientAuth, ocspData, tlsSctData) {
            return untrustedChain;
        };
        send({type: 'info', message: 'SSL Pinning bypassed (TrustManagerImpl)'});
    } catch(e) {}

    try {
        // 方法2: 绕过OkHttp3 CertificatePinner
        var CertificatePinner = Java.use('okhttp3.CertificatePinner');
        CertificatePinner.check.overload('java.lang.String', 'java.util.List').implementation = function(hostname, peerCertificates) {
            return;
        };
        send({type: 'info', message: 'SSL Pinning bypassed (OkHttp3)'});
    } catch(e) {}

    try {
        // 方法3: 绕过X509TrustManager
        var X509TrustManager = Java.use('javax.net.ssl.X509TrustManager');
        var SSLContext = Java.use('javax.net.ssl.SSLContext');

        var TrustManager = Java.registerClass({
            name: 'dev.nul.TrustManager',
            implements: [X509TrustManager],
            methods: {
                checkClientTrusted: function(chain, authType) {},
                checkServerTrusted: function(chain, authType) {},
                getAcceptedIssuers: function() { return []; }
            }
        });

        var TrustManagers = [TrustManager.$new()];
        var sslContext = SSLContext.getInstance("TLS");
        sslContext.init(null, TrustManagers, null);
        send({type: 'info', message: 'SSL Pinning bypassed (X509TrustManager)'});
    } catch(e) {}

    try {
        // 方法4: 绕过WebViewClient
        var WebViewClient = Java.use('android.webkit.WebViewClient');
        WebViewClient.onReceivedSslError.implementation = function(view, handler, error) {
            handler.proceed();
        };
    } catch(e) {}
}

// ========== 隐私信息监控 ==========

function hookDeviceIds() {
    try {
        var TelephonyManager = Java.use('android.telephony.TelephonyManager');

        try {
            TelephonyManager.getDeviceId.overload().implementation = function() {
                var result = this.getDeviceId();
                if (result) {
                    send({type: 'device_id', subtype: 'IMEI', value: result});
                }
                return result;
            };
        } catch(e) {}

        try {
            TelephonyManager.getImei.overload().implementation = function() {
                var result = this.getImei();
                if (result) {
                    send({type: 'device_id', subtype: 'IMEI', value: result});
                }
                return result;
            };
        } catch(e) {}

        var Settings = Java.use('android.provider.Settings$Secure');
        var origGetString = Settings.getString.overload('android.content.ContentResolver', 'java.lang.String');
        origGetString.implementation = function(resolver, name) {
            var result = origGetString.call(this, resolver, name);
            if (name === 'android_id' && result) {
                send({type: 'device_id', subtype: 'Android_ID', value: result});
            }
            return result;
        };

        send({type: 'info', message: 'Device ID hooks installed'});
    } catch(e) {
        send({type: 'error', message: 'Device ID hook error: ' + e.message});
    }
}

function hookMacAddress() {
    try {
        var WifiInfo = Java.use('android.net.wifi.WifiInfo');
        WifiInfo.getMacAddress.implementation = function() {
            var result = this.getMacAddress();
            if (result) {
                send({type: 'mac_address', subtype: 'WiFi', value: result});
            }
            return result;
        };

        var NetworkInterface = Java.use('java.net.NetworkInterface');
        NetworkInterface.getHardwareAddress.implementation = function() {
            var result = this.getHardwareAddress();
            if (result) {
                var mac = '';
                for (var i = 0; i < result.length; i++) {
                    mac += ('0' + (result[i] & 0xFF).toString(16)).slice(-2);
                    if (i < result.length - 1) mac += ':';
                }
                send({type: 'mac_address', subtype: 'Hardware', value: mac});
            }
            return result;
        };

        send({type: 'info', message: 'MAC address hooks installed'});
    } catch(e) {
        send({type: 'error', message: 'MAC hook error: ' + e.message});
    }
}

function hookLocation() {
    try {
        var Location = Java.use('android.location.Location');

        Location.getLatitude.implementation = function() {
            var result = this.getLatitude();
            send({type: 'location', subtype: 'Latitude', value: String(result)});
            return result;
        };

        Location.getLongitude.implementation = function() {
            var result = this.getLongitude();
            send({type: 'location', subtype: 'Longitude', value: String(result)});
            return result;
        };

        send({type: 'info', message: 'Location hooks installed'});
    } catch(e) {
        send({type: 'error', message: 'Location hook error: ' + e.message});
    }
}

function hookInstalledApps() {
    try {
        var ApplicationPackageManager = Java.use('android.app.ApplicationPackageManager');

        ApplicationPackageManager.getInstalledPackages.overload('int').implementation = function(flags) {
            var result = this.getInstalledPackages(flags);
            if (result && result.size() > 0) {
                send({type: 'installed_apps', method: 'getInstalledPackages', count: result.size()});
            }
            return result;
        };

        ApplicationPackageManager.getInstalledApplications.overload('int').implementation = function(flags) {
            var result = this.getInstalledApplications(flags);
            if (result && result.size() > 0) {
                send({type: 'installed_apps', method: 'getInstalledApplications', count: result.size()});
            }
            return result;
        };

        send({type: 'info', message: 'Installed apps hooks installed'});
    } catch(e) {
        send({type: 'error', message: 'Apps hook error: ' + e.message});
    }
}

function hookClipboard() {
    try {
        var ClipboardManager = Java.use('android.content.ClipboardManager');

        ClipboardManager.getPrimaryClip.implementation = function() {
            var result = this.getPrimaryClip();
            if (result) {
                try {
                    var text = result.getItemAt(0).getText();
                    if (text) {
                        send({type: 'clipboard', value: text.toString()});
                    }
                } catch(e) {}
            }
            return result;
        };

        send({type: 'info', message: 'Clipboard hooks installed'});
    } catch(e) {
        send({type: 'error', message: 'Clipboard hook error: ' + e.message});
    }
}

// ========== 主入口 ==========
Java.perform(function() {
    send({type: 'info', message: 'Script loaded, installing hooks...'});

    bypassSSLPinning();
    hookDeviceIds();
    hookMacAddress();
    hookLocation();
    hookInstalledApps();
    hookClipboard();

    send({type: 'info', message: 'All hooks installed!'});
});
