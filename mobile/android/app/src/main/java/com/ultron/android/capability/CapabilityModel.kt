package com.ultron.android.capability

import android.content.Context
import android.content.pm.PackageManager
import android.hardware.SensorManager

object CapabilityModel {
    /**
     * Scans and returns local Android hardware capabilities authoritatively as device observations.
     */
    fun getDeviceCapabilities(context: Context): Map<String, String> {
        val pm = context.packageManager
        val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager

        return mapOf(
            "camera" to if (pm.hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY)) "KNOWN" else "UNKNOWN",
            "microphone" to if (pm.hasSystemFeature(PackageManager.FEATURE_MICROPHONE)) "KNOWN" else "UNKNOWN",
            "gps" to if (pm.hasSystemFeature(PackageManager.FEATURE_LOCATION_GPS)) "KNOWN" else "UNKNOWN",
            "accelerometer" to if (sensorManager.getDefaultSensor(android.hardware.Sensor.TYPE_ACCELEROMETER) != null) "KNOWN" else "UNKNOWN",
            "biometric_support" to if (pm.hasSystemFeature(PackageManager.FEATURE_FINGERPRINT)) "KNOWN" else "UNKNOWN"
        )
    }
}
