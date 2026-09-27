#!/usr/bin/env bash
# Builds Rately.apk from app/src/main with the plain SDK command-line tools
# (aapt2, javac, dx, zipalign, apksigner) — no Gradle or Android Gradle Plugin.
#
# Works with Ubuntu/Debian's packaged SDK out of the box:
#   sudo apt-get install android-sdk android-sdk-platform-23
# or point ANDROID_HOME / BUILD_TOOLS / ANDROID_JAR at a regular SDK.
#
# The app only uses framework APIs (no AndroidX), so the API 23 android.jar is
# enough to compile against; newer APIs are reached by intent action strings.
set -euo pipefail

cd "$(dirname "$0")"

APP_ID="uk.co.cheltenhamdata.rately"
VERSION_CODE="${VERSION_CODE:-2}"
VERSION_NAME="${VERSION_NAME:-1.1}"
MIN_SDK=23
TARGET_SDK=34

ANDROID_HOME="${ANDROID_HOME:-/usr/lib/android-sdk}"
BUILD_TOOLS="${BUILD_TOOLS:-$(ls -d "$ANDROID_HOME"/build-tools/* | sort -V | tail -1)}"
ANDROID_JAR="${ANDROID_JAR:-$(ls -d "$ANDROID_HOME"/platforms/android-*/android.jar | sort -V | tail -1)}"

KEYSTORE="${KEYSTORE:-rately.keystore}"
KS_PASS="${KS_PASS:-rately}"
KEY_ALIAS="${KEY_ALIAS:-rately}"

SRC=app/src/main
OUT=build
rm -rf "$OUT"
mkdir -p "$OUT/gen" "$OUT/classes" "$OUT/dex"

echo "build-tools: $BUILD_TOOLS"
echo "android.jar: $ANDROID_JAR"

# The source manifest has no package attribute (the Gradle build takes it from
# `namespace`), but aapt2 needs one.
sed "s|<manifest |<manifest package=\"$APP_ID\" |" "$SRC/AndroidManifest.xml" > "$OUT/AndroidManifest.xml"

echo "== aapt2 compile"
"$BUILD_TOOLS/aapt2" compile --dir "$SRC/res" -o "$OUT/res.zip"

echo "== aapt2 link"
"$BUILD_TOOLS/aapt2" link \
    -I "$ANDROID_JAR" \
    --manifest "$OUT/AndroidManifest.xml" \
    --min-sdk-version "$MIN_SDK" \
    --target-sdk-version "$TARGET_SDK" \
    --version-code "$VERSION_CODE" \
    --version-name "$VERSION_NAME" \
    -A "$SRC/assets" \
    --java "$OUT/gen" \
    -o "$OUT/app-unaligned.apk" \
    "$OUT/res.zip"

echo "== javac"
# Java 8 bytecode without lambdas: dx cannot desugar them.
find "$SRC/java" "$OUT/gen" -name '*.java' > "$OUT/sources.txt"
javac -nowarn -Xlint:-options -encoding UTF-8 \
    -source 8 -target 8 \
    -bootclasspath "$ANDROID_JAR" \
    -d "$OUT/classes" @"$OUT/sources.txt"

echo "== dx"
"$BUILD_TOOLS/dx" --dex --min-sdk-version="$MIN_SDK" --output="$OUT/dex/classes.dex" "$OUT/classes"
(cd "$OUT/dex" && zip -q -u ../app-unaligned.apk classes.dex)

echo "== zipalign"
"$BUILD_TOOLS/zipalign" -f -p 4 "$OUT/app-unaligned.apk" "$OUT/app-aligned.apk"

echo "== apksigner"
if [ ! -f "$KEYSTORE" ]; then
    keytool -genkeypair -keystore "$KEYSTORE" -alias "$KEY_ALIAS" \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -storepass "$KS_PASS" -keypass "$KS_PASS" -dname "CN=Rately"
fi
"$BUILD_TOOLS/apksigner" sign --ks "$KEYSTORE" --ks-key-alias "$KEY_ALIAS" \
    --ks-pass "pass:$KS_PASS" --key-pass "pass:$KS_PASS" \
    --out Rately.apk "$OUT/app-aligned.apk"
"$BUILD_TOOLS/apksigner" verify Rately.apk
rm -f Rately.apk.idsig

echo "Built $(pwd)/Rately.apk ($(du -h Rately.apk | cut -f1))"
