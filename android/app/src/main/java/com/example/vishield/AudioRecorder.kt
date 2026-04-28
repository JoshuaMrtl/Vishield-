package com.example.vishield

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioPlaybackCaptureConfiguration
import android.media.AudioRecord
import android.media.projection.MediaProjection
import kotlinx.coroutines.*
import java.io.File
import java.io.FileOutputStream
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * AudioRecorder
 *
 * Enregistre l'audio du microphone ET la lecture audio du téléphone (downlink),
 * les mélange en une seule piste mono, puis écrit des buffers de BUFFER_DURATION_SEC
 * secondes dans des fichiers .wav numérotés.
 *
 * Requiert Android 10+ (API 29) pour AudioPlaybackCapture.
 * Requiert une MediaProjection active pour capturer l'audio sortant.
 */
class AudioRecorder(
    private val context: Context,
    private val outputDir: File,            // Dossier de sortie des fichiers .wav
    private val mediaProjection: MediaProjection?,  // Null = micro seulement
    private val onNewFile: (File) -> Unit   // Callback à chaque nouveau fichier .wav
) {

    companion object {
        @JvmStatic
        var BUFFER_DURATION_SEC: Int = 5

        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        private const val BYTES_PER_SAMPLE = 2
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO

        // Sample rate natif de l'appareil — pas de rééchantillonnage nécessaire
        val SAMPLE_RATE: Int
            get() = android.media.AudioTrack.getNativeOutputSampleRate(
                android.media.AudioManager.STREAM_MUSIC
            )
    }

    private var isRecording = false
    private var recordingJob: Job? = null

    // Taille d'un buffer complet (BUFFER_DURATION_SEC secondes de données)
    private val fullBufferSize: Int
        get() = SAMPLE_RATE * BYTES_PER_SAMPLE * BUFFER_DURATION_SEC

    // Taille minimale du buffer hardware
    private val minBufferSize: Int
        get() = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)

    private var micRecorder: AudioRecord? = null
    private var playbackRecorder: AudioRecord? = null

    /**
     * Démarre l'enregistrement en continu dans une coroutine.
     */
    fun start() {
        val nativeSampleRate = android.media.AudioTrack.getNativeOutputSampleRate(
            android.media.AudioManager.STREAM_MUSIC
        )
        android.util.Log.d("AudioRecorder", "Sample rate natif de l'émulateur : $nativeSampleRate Hz")
        android.util.Log.d("AudioRecorder", "Sample rate utilisé : $SAMPLE_RATE Hz")

        if (isRecording) return

        micRecorder = buildMicRecorder()

        if (micRecorder == null) {
            android.util.Log.e("AudioRecorder", "Impossible de démarrer : micro non disponible")
            return
        }

        playbackRecorder = mediaProjection?.let { buildPlaybackRecorder(it) }

        micRecorder?.startRecording()
        playbackRecorder?.startRecording()

        isRecording = true

        recordingJob = CoroutineScope(Dispatchers.IO).launch {
            var fileIndex = 0
            val bufferSize = SAMPLE_RATE * BYTES_PER_SAMPLE * BUFFER_DURATION_SEC
            val micBuffer = ByteArray(bufferSize)
            val playBuffer = ByteArray(bufferSize)

            while (isRecording) {
                readFull(micRecorder!!, micBuffer)

                if (playbackRecorder != null) {
                    readFull(playbackRecorder!!, playBuffer)
                }

                val mixed = mixBuffers(
                    micBuffer,
                    if (playbackRecorder != null) playBuffer else null
                )

                val outputFile = File(outputDir, "buffer_${fileIndex++}.wav")
                writeWavFile(outputFile, mixed)  // SAMPLE_RATE natif écrit dans l'en-tête WAV

                withContext(Dispatchers.Main) {
                    onNewFile(outputFile)
                }
            }
        }
    }

    /**
     * Arrête l'enregistrement et libère les ressources.
     */
    fun stop() {
        isRecording = false
        recordingJob?.cancel()
        micRecorder?.stop()
        micRecorder?.release()
        micRecorder = null
        playbackRecorder?.stop()
        playbackRecorder?.release()
        playbackRecorder = null
    }

    // =========================================================================
    // Construction des AudioRecord
    // =========================================================================

    private fun buildMicRecorder(): AudioRecord? {
        return try {
            AudioRecord(
                android.media.MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                maxOf(minBufferSize, fullBufferSize)
            ).also { recorder ->
                if (recorder.state != AudioRecord.STATE_INITIALIZED) {
                    recorder.release()
                    return null
                }
            }
        } catch (e: SecurityException) {
            android.util.Log.e("AudioRecorder", "Permission RECORD_AUDIO refusée : ${e.message}")
            null
        }
    }

    private fun buildPlaybackRecorder(projection: MediaProjection): AudioRecord? {
        return try {
            val config = AudioPlaybackCaptureConfiguration.Builder(projection)
                .addMatchingUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                .addMatchingUsage(AudioAttributes.USAGE_MEDIA)
                .build()

            AudioRecord.Builder()
                .setAudioFormat(
                    AudioFormat.Builder()
                        .setEncoding(AUDIO_FORMAT)
                        .setSampleRate(SAMPLE_RATE)
                        .setChannelMask(AudioFormat.CHANNEL_IN_MONO)
                        .build()
                )
                .setBufferSizeInBytes(maxOf(minBufferSize, fullBufferSize))
                .setAudioPlaybackCaptureConfig(config)
                .build()
                .also { recorder ->
                    if (recorder.state != AudioRecord.STATE_INITIALIZED) {
                        recorder.release()
                        return null
                    }
                }
        } catch (e: SecurityException) {
            android.util.Log.e("AudioRecorder", "Permission lecture audio refusée : ${e.message}")
            null
        }
    }

    // =========================================================================
    // Lecture complète d'un buffer
    // =========================================================================

    /**
     * Lit exactement buffer.size octets depuis un AudioRecord.
     * Boucle jusqu'à ce que le buffer soit rempli.
     */
    private fun readFull(recorder: AudioRecord, buffer: ByteArray) {
        var offset = 0
        while (offset < buffer.size && isRecording) {
            val read = recorder.read(buffer, offset, buffer.size - offset)
            if (read > 0) offset += read
        }
        android.util.Log.i("Recorder", "Buffer audio enregistré")
    }

    // =========================================================================
    // Mélange des pistes audio
    // =========================================================================

    /**
     * Mélange deux buffers PCM 16bit en une seule piste par moyenne pondérée.
     * Si playBuffer est null, retourne micBuffer tel quel.
     */
    private fun mixBuffers(micBuffer: ByteArray, playBuffer: ByteArray?): ShortArray {
        val samples = micBuffer.size / BYTES_PER_SAMPLE
        val result = ShortArray(samples)

        val micShorts = toShortArray(micBuffer)

        if (playBuffer == null) {
            return micShorts
        }

        val playShorts = toShortArray(playBuffer)

        for (i in 0 until samples) {
            // Moyenne des deux pistes, clampée dans [-32768, 32767]
            val mixed = (micShorts[i].toInt() + playShorts[i].toInt()) / 2
            result[i] = mixed.coerceIn(Short.MIN_VALUE.toInt(), Short.MAX_VALUE.toInt()).toShort()
        }

        return result
    }

    private fun toShortArray(bytes: ByteArray): ShortArray {
        val shorts = ShortArray(bytes.size / 2)
        ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer().get(shorts)
        return shorts
    }

    // =========================================================================
    // Écriture du fichier WAV
    // =========================================================================

    /**
     * Écrit un fichier WAV valide à partir de données PCM 16bit mono.
     */
    private fun writeWavFile(file: File, pcmData: ShortArray) {
        val dataSize = pcmData.size * BYTES_PER_SAMPLE
        val totalSize = 36 + dataSize

        FileOutputStream(file).use { fos ->
            // --- En-tête WAV (44 octets) ---
            val header = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN)

            // RIFF chunk
            header.put("RIFF".toByteArray())
            header.putInt(totalSize)
            header.put("WAVE".toByteArray())

            // fmt sub-chunk
            header.put("fmt ".toByteArray())
            header.putInt(16)                          // Taille du chunk fmt
            header.putShort(1)                         // Format PCM
            header.putShort(1)                         // Mono
            header.putInt(SAMPLE_RATE)                 // Sample rate
            header.putInt(SAMPLE_RATE * BYTES_PER_SAMPLE) // Byte rate
            header.putShort(BYTES_PER_SAMPLE.toShort())   // Block align
            header.putShort(16)                        // Bits per sample

            // data sub-chunk
            header.put("data".toByteArray())
            header.putInt(dataSize)

            fos.write(header.array())

            // --- Données PCM ---
            val dataBuffer = ByteBuffer.allocate(dataSize).order(ByteOrder.LITTLE_ENDIAN)
            for (s in pcmData) dataBuffer.putShort(s)
            fos.write(dataBuffer.array())
        }
    }
}