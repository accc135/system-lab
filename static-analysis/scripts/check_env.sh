#!/usr/bin/env bash

echo "== Java =="
java -version
javac -version

echo
echo "== Maven =="
mvn -version | head -n 3

echo
echo "== Android SDK =="
echo "ANDROID_HOME=$ANDROID_HOME"
echo "ANDROID_SDK_ROOT=$ANDROID_SDK_ROOT"
echo "sdkmanager=$(which sdkmanager)"
echo "adb=$(which adb)"
ls "$ANDROID_HOME/platforms" 2>/dev/null || echo "[ERROR] platforms not found"

echo
echo "== FlowDroid =="
FLOWDROID_JAR=/data4/chzhou/Lab4-1-static/tools/flowdroid/soot-infoflow-cmd-jar-with-dependencies.jar
ls -lh "$FLOWDROID_JAR" 2>/dev/null || echo "[ERROR] FlowDroid jar not found"
java -jar "$FLOWDROID_JAR" --help >/tmp/flowdroid_help.txt 2>&1 && head -n 5 /tmp/flowdroid_help.txt || echo "[WARN] FlowDroid help failed"

echo
echo "== DroidBench =="
find /data4/chzhou/Lab4-1-static/DroidBench -name "*.apk" 2>/dev/null | head -n 5
