package com.ultron.android.identity

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.PrivateKey
import java.security.PublicKey
import java.security.Signature
import java.security.MessageDigest

class NodeIdentity {
    private val keyAlias = "UltronNodeIdentityKey"
    private val providerName = "AndroidKeyStore"

    init {
        generateEnclaveKeyPair()
    }

    /**
     * Generates a cryptographically secure 2048-bit RSA keypair inside the hardware enclave.
     * Enforces that the private key remains inside the AndroidKeyStore and is NEVER exportable (Correction 2).
     */
    private fun generateEnclaveKeyPair() {
        val keyStore = KeyStore.getInstance(providerName).apply { load(null) }
        if (!keyStore.containsAlias(keyAlias)) {
            val kpg = KeyPairGenerator.getInstance(
                KeyProperties.KEY_ALGORITHM_RSA,
                providerName
            )
            val parameterSpec = KeyGenParameterSpec.Builder(
                keyAlias,
                KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
            ).run {
                setDigests(KeyProperties.DIGEST_SHA256, KeyProperties.DIGEST_SHA512)
                setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PKCS1)
                setKeySize(2048)
                build()
            }
            kpg.initialize(parameterSpec)
            kpg.generateKeyPair()
        }
    }

    private fun getPrivateKey(): PrivateKey {
        val keyStore = KeyStore.getInstance(providerName).apply { load(null) }
        return keyStore.getKey(keyAlias, null) as PrivateKey
    }

    fun getPublicKey(): PublicKey {
        val keyStore = KeyStore.getInstance(providerName).apply { load(null) }
        return keyStore.getCertificate(keyAlias).publicKey
    }

    /**
     * Derives the persistent, immutable lowercase hexadecimal SHA-256 public-key fingerprint
     * to use as the canonical, collision-safe device ID (Correction 3).
     */
    fun getNodeDeviceId(): String {
        val pubKeyBytes = getPublicKey().encoded
        val digest = MessageDigest.getInstance("SHA-256")
        val hashedBytes = digest.digest(pubKeyBytes)

        // Convert to lowercase hexadecimal string
        val hexString = StringBuilder()
        for (b in hashedBytes) {
            val hex = Integer.toHexString(0xff and b.toInt())
            if (hex.length == 1) hexString.append('0')
            hexString.append(hex)
        }
        return "android_" + hexString.toString()
    }

    /**
     * Signs an outgoing payload using SHA256withRSA to verify authenticity on the host.
     */
    fun signPayload(payload: String): String {
        val privateKey = getPrivateKey()
        val signature = Signature.getInstance("SHA256withRSA").apply {
            initSign(privateKey)
            update(payload.toByteArray())
        }
        val signedBytes = signature.sign()
        return Base64.encodeToString(signedBytes, Base64.NO_WRAP)
    }
}
