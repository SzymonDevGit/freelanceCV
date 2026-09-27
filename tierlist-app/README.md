# Rately

A tier-list app for Android. Add photos, crop them square, and rate them quickly
by tapping a tier. The design is a cartoon take on a dusk camp on the moors:
striped purple-to-gold sky, rolling hills and a little tent.

This folder is listed in the site's `.assetsignore`, so none of it is served on
cheltenhamdata.co.uk.

## Install

1. On your phone, open [`Rately.apk`](Rately.apk) on GitHub and tap **Download**
   (or "View raw").
2. Open the downloaded file. Android will ask you to allow installs from your
   browser or file manager. Allow it, then tap **Install**.
3. Play Protect may warn that it doesn't recognise the app, because it's
   self-signed and not from the Play Store. Tap **Install anyway**.

It needs Android 6.0 or newer and asks for no permissions. Photos come in
through the system photo picker.

## Using it

- **Home** lists every tier list, most recently changed first. Tap **New tier
  list** to make one. Long-press a card to rename or delete it.
- **Board** has one row per tier, with the pictures still to rate in the dock at
  the bottom.
  - **Add** opens the photo picker. You can pick several photos at once.
  - **Rate** starts quick rating.
  - Long-press a picture and drag it to another row, to a position within a
    row, or back to the dock.
  - Tap a picture to move it with one tap, send it back to the to-rate pile,
    or delete it.
  - The pencil button edits tiers: rename, recolour, reorder, add or remove
    them. Removing a tier sends its pictures back to the to-rate pile.
  - The ⋯ menu can rename the list, re-rate everything or delete the list.
- **Crop** shows each new photo under a square frame. Pinch to zoom, drag to
  move and double-tap to reset. **Use this + auto-crop N more** keeps your
  current crop and centre-crops the rest, for when you're in a hurry.
- **Quick rate** shows one big card at a time. Tap a tier and the card flies
  into it while the next one pops up. **Undo** steps back through the ratings
  and **Skip** sends a card to the back of the pile.

Everything saves as you go. Each change is written to disk straight away, and
again when you leave a screen, so closing or killing the app loses nothing.
Lists are JSON files in the app's private storage. Pictures are saved as
720×720 JPEGs.

## Building

`build.sh` builds `Rately.apk` with the plain SDK command-line tools (aapt2,
javac, dx, zipalign and apksigner). It doesn't use Gradle. On Ubuntu or Debian:

```sh
sudo apt-get install android-sdk android-sdk-platform-23
./build.sh
```

To use a different SDK, set `ANDROID_HOME`, `BUILD_TOOLS` or `ANDROID_JAR`.
Bump `VERSION_CODE` when you ship an update, for example
`VERSION_CODE=2 VERSION_NAME=1.1 ./build.sh`.

The app uses only Android framework APIs (no AndroidX), written in Java 8
without lambdas, so this toolchain is enough. APIs newer than the API 23
compile target, such as the Android 13 photo picker, are reached through
intent action strings or reflection. `targetSdkVersion` is 34.

The Gradle files are there so the project opens in Android Studio. They
weren't run when the app was built, because the build machine couldn't reach
Google's Maven repository.

### Signing key

`rately.keystore` (password `rately`) signs every build, from `build.sh` and
from Gradle. Android only installs an update over an existing copy when both
are signed with the same key. Changing the key means uninstalling first, which
deletes your saved tier lists.

This is a personal debug-style key and it is public in this repository. It is
fine for sideloading, but don't use it for anything published.

## Layout

```
app/src/main/
  AndroidManifest.xml
  java/uk/co/cheltenhamdata/rately/
    MainActivity    home screen and list cards
    BoardActivity   tier rows, drag and drop, the to-rate dock, the photo picker
    RateActivity    quick rating
    CropActivity    the crop flow; CropView is the pinch-and-drag square cropper
    TierEditor      the edit-tiers dialog
    TierList, Store the data model and JSON persistence
    Images, Thumbs  decoding, EXIF rotation, saving, and the cached thumbnail loader
    Toon, ToonDrawable, ToonText, Icon, ThumbView, FlowLayout, SunsetView
                    the cartoon look
  res/              launcher icon, theme, colours
  assets/fonts/     Fredoka (SIL Open Font License, see OFL.txt)
```
