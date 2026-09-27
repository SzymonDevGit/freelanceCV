plugins {
    id("com.android.application")
}

android {
    namespace = "uk.co.cheltenhamdata.rately"
    compileSdk = 34

    defaultConfig {
        applicationId = "uk.co.cheltenhamdata.rately"
        minSdk = 23
        targetSdk = 34
        versionCode = 2
        versionName = "1.1"
    }

    // Same key as build.sh, so either build can update an installed copy without
    // uninstalling it (which would wipe the saved tier lists).
    signingConfigs {
        create("rately") {
            storeFile = rootProject.file("rately.keystore")
            storePassword = "rately"
            keyAlias = "rately"
            keyPassword = "rately"
        }
    }

    buildTypes {
        getByName("debug") {
            signingConfig = signingConfigs.getByName("rately")
        }
        getByName("release") {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("rately")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
}
