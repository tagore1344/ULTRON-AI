package com.ultron.android.pairing

import android.content.Context
import android.util.Base64
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import com.ultron.android.identity.NodeIdentity
import com.ultron.android.capability.CapabilityModel
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

class PairingManager(private val context: Context, private val identity: NodeIdentity) {
    private val client = OkHttpClient()
    private val mediaType = "application/json; charset=utf-8".toMediaType()

    /**
     * Transmits the device public key and dynamic capability mappings during LAN pairing.
     * Stores the returned session token securely inside Keystore-backed EncryptedSharedPreferences (Correction 1).
     */
    fun pairWithHost(hostIp: String, pairingCode: String, deviceName: String): Boolean {
        val url = "http://$hostIp/api/v1/auth/pair"

        // Export public key as Base64 PEM
        val pubKeyBase64 = Base64.encodeToString(identity.getPublicKey().encoded, Base64.NO_WRAP)

        // Load dynamic hardware capabilities
        val capabilities = CapabilityModel.getDeviceCapabilities(context)

        val jsonPayload = JSONObject().apply {
            put("pairing_code", pairingCode)
            put("device_name", deviceName)
            put("device_type", "android")
            put("device_id", identity.getNodeDeviceId())
            put("public_key", pubKeyBase64)
            put("capabilities", JSONObject(capabilities))
        }

        val body = jsonPayload.toString().toRequestBody(mediaType)
        val request = Request.Builder().url(url).post(body).build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("Pairing rejected: ${response.body?.string()}")

            val responseData = JSONObject(response.body?.string() ?: "{}")
            val accessToken = responseData.getString("access_token")

            // Store securely inside Android Keystore-backed EncryptedSharedPreferences (Correction 1)
            val masterKeyAlias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)
            val securePreferences = EncryptedSharedPreferences.create(
                "SecureUltronKeyring",
                masterKeyAlias,
                context,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )

            securePreferences.edit().putString("BearerToken", accessToken).apply()
            return true
        }
    }
}
