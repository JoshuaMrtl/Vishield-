package com.example.vishield

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import java.io.File
import androidx.localbroadcastmanager.content.LocalBroadcastManager

/**
 * DetectionService
 *
 * Foreground Service qui fait tourner le pipeline de détection
 * en arrière-plan : AudioRecorder → SpeechToText → TextToNote.
 * Communique avec MainActivity via un Intent broadcast.
 */
class DetectionService : Service() {

    companion object {
        const val CHANNEL_ID = "vishield_channel"
        const val NOTIFICATION_ID = 1

        // Actions des broadcasts envoyés à MainActivity
        const val ACTION_STATE_CHANGED = "com.example.vishield.STATE_CHANGED"
        const val EXTRA_NEW_STATE = "new_state"

        // Actions pour démarrer/arrêter le service
        const val ACTION_START = "ACTION_START"
        const val ACTION_STOP = "ACTION_STOP"
    }

    private var audioRecorder: AudioRecorder? = null
    private var speechToText: SpeechToText? = null
    private var textToNote: TextToNote? = null
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private val outputDir: File by lazy {
        File(getExternalFilesDir(null), "audio_buffers").also { it.mkdirs() }
    }

    // =========================================================================
    // Lifecycle du Service
    // =========================================================================

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        Log.d("DetectionService", "Service créé")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                Log.d("DetectionService", "Démarrage du service")
                startForeground(NOTIFICATION_ID, buildNotification("Écoute en cours..."))
                startPipeline()
            }
            ACTION_STOP -> {
                Log.d("DetectionService", "Arrêt du service")
                stopPipeline()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
        // START_STICKY : Android redémarre le service s'il est tué
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        stopPipeline()
        serviceScope.cancel()
        Log.d("DetectionService", "Service détruit")
    }

    // =========================================================================
    // Pipeline de détection
    // =========================================================================

    private fun startPipeline() {
        speechToText = SpeechToText(this)
        textToNote = TextToNote(this)

        audioRecorder = AudioRecorder(
            context = this,
            outputDir = outputDir,
            mediaProjection = null,
            onNewFile = { wavFile -> processBuffer(wavFile) }
        )
        audioRecorder?.start()
        Log.d("DetectionService", "Pipeline démarré")
    }

    private fun stopPipeline() {
        audioRecorder?.stop()
        audioRecorder = null
        speechToText?.close()
        speechToText = null
        textToNote?.close()
        textToNote = null
        Log.d("DetectionService", "Pipeline arrêté")
    }

    private fun processBuffer(wavFile: File) {
        serviceScope.launch {
            Log.d("DetectionService", "Traitement de ${wavFile.name}")

            val text = speechToText?.transcribe(wavFile) ?: return@launch
            Log.d("DetectionService", "Transcription : \"$text\"")

            val (isVishing, score) = textToNote?.analyze(text) ?: return@launch
            Log.d("DetectionService", "Analyse : isVishing=$isVishing, score=$score")

            val newState = when {
                isVishing && score > 0.5f  -> MainActivity.AppState.VISHING_SUR
                isVishing && score <= 0.5f -> MainActivity.AppState.VISHING_PROBABLE
                else -> return@launch
            }

            // Notifier MainActivity du changement d'état
            broadcastStateChange(newState)

            // Mettre à jour la notification
            updateNotification(newState)

            // Si vishing sûr : raccrocher et arrêter
            if (newState == MainActivity.AppState.VISHING_SUR) {
                stopPipeline()
            }
        }
    }

    // =========================================================================
    // Communication avec MainActivity
    // =========================================================================

    private fun broadcastStateChange(newState: MainActivity.AppState) {
        val intent = Intent(ACTION_STATE_CHANGED).apply {
            putExtra(EXTRA_NEW_STATE, newState.name)
        }
        LocalBroadcastManager.getInstance(this).sendBroadcast(intent)
        Log.d("DetectionService", "Broadcast envoyé : ${newState.name}")
    }

    // =========================================================================
    // Notification
    // =========================================================================

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Vishield Detection",
            NotificationManager.IMPORTANCE_LOW  // LOW = pas de son
        ).apply {
            description = "Détection de vishing en cours"
        }
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(channel)
    }

    private fun buildNotification(text: String): Notification {
        // Tap sur la notification → ouvre MainActivity
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Vishield")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(pendingIntent)
            .setOngoing(true)  // Non-dismissable par l'utilisateur
            .build()
    }

    private fun updateNotification(state: MainActivity.AppState) {
        val text = when (state) {
            MainActivity.AppState.ECOUTE           -> "Écoute en cours..."
            MainActivity.AppState.VISHING_PROBABLE -> "⚠ Vishing probable détecté"
            MainActivity.AppState.VISHING_SUR      -> "🚨 Vishing détecté — Appel raccroché"
            else -> "En attente"
        }
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(NOTIFICATION_ID, buildNotification(text))
    }
}