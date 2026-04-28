package com.example.vishield

import android.content.Context
import android.os.Build
import android.telecom.TelecomManager
import android.telephony.PhoneStateListener
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager
import androidx.annotation.RequiresApi
import java.lang.reflect.Method

/**
 * CallDetector
 *
 * Surveille l'état des appels téléphoniques en arrière-plan.
 * Notifie via un callback lorsqu'un appel entre/sort.
 * Fournit une méthode pour raccrocher l'appel en cours.
 */
class CallDetector(
    private val context: Context,
    private val onCallStarted: () -> Unit,   // Callback : appel détecté
    private val onCallEnded: () -> Unit       // Callback : appel terminé
) {

    private val telephonyManager =
        context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager

    // Listener pour API < 31
    private var phoneStateListener: PhoneStateListener? = null

    // Callback pour API >= 31
    private var telephonyCallback: TelephonyCallback? = null

    // État interne pour éviter les déclenchements multiples
    private var isInCall = false

    /**
     * Démarre la surveillance des appels.
     * Utilise TelephonyCallback (API 31+) ou PhoneStateListener (API < 31).
     */
    fun startListening() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            startListeningModern()
        } else {
            startListeningLegacy()
        }
    }

    @RequiresApi(Build.VERSION_CODES.S)
    private fun startListeningModern() {
        telephonyCallback = object : TelephonyCallback(), TelephonyCallback.CallStateListener {
            override fun onCallStateChanged(state: Int) {
                handleCallState(state)
            }
        }
        telephonyManager.registerTelephonyCallback(
            context.mainExecutor,
            telephonyCallback!!
        )
    }

    @Suppress("DEPRECATION")
    private fun startListeningLegacy() {
        phoneStateListener = object : PhoneStateListener() {
            override fun onCallStateChanged(state: Int, phoneNumber: String?) {
                handleCallState(state)
            }
        }
        telephonyManager.listen(
            phoneStateListener,
            PhoneStateListener.LISTEN_CALL_STATE
        )
    }

    /**
     * Gère les transitions d'état d'appel.
     */
    private fun handleCallState(state: Int) {
        when (state) {
            TelephonyManager.CALL_STATE_RINGING,
            TelephonyManager.CALL_STATE_OFFHOOK -> {
                // Un appel est en cours ou en attente
                if (!isInCall) {
                    isInCall = true
                    android.util.Log.i("CallDetector", "Appel entrant détecté")
                    onCallStarted()
                }
            }
            TelephonyManager.CALL_STATE_IDLE -> {
                // Plus d'appel
                if (isInCall) {
                    isInCall = false
                    android.util.Log.i("CallDetector", "Appel terminé")
                    onCallEnded()
                }
            }
        }
    }

    /**
     * Raccroche l'appel en cours.
     * Nécessite la permission ANSWER_PHONE_CALLS (API 28+).
     */
    fun hangUp() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            val telecomManager =
                context.getSystemService(Context.TELECOM_SERVICE) as TelecomManager
            try {
                telecomManager.endCall()
            } catch (e: SecurityException) {
                e.printStackTrace()
            }
        } else {
            // Méthode legacy via réflexion (API < 28)
            hangUpLegacy()
        }
        android.util.Log.i("CallDetector", "Vishield a raccroché")
    }

    /**
     * Raccroche via réflexion pour les anciennes API.
     * Non garanti sur tous les appareils.
     */
    private fun hangUpLegacy() {
        try {
            val serviceManagerClass = Class.forName("android.os.ServiceManager")
            val getService: Method = serviceManagerClass.getMethod("getService", String::class.java)
            val binder = getService.invoke(null, "phone")
            val stubClass = Class.forName("com.android.internal.telephony.ITelephony\$Stub")
            val asInterface: Method = stubClass.getMethod("asInterface", android.os.IBinder::class.java)
            val telephonyService = asInterface.invoke(null, binder)
            val endCall: Method = telephonyService.javaClass.getMethod("endCall")
            endCall.invoke(telephonyService)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    /**
     * Arrête la surveillance des appels.
     */
    fun stopListening() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            telephonyCallback?.let { telephonyManager.unregisterTelephonyCallback(it) }
        } else {
            @Suppress("DEPRECATION")
            phoneStateListener?.let {
                telephonyManager.listen(it, PhoneStateListener.LISTEN_NONE)
            }
        }
        isInCall = false
    }
}