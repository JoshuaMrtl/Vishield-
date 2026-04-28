package com.example.vishield

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer

/**
 * SpeechToText
 *
 * Transcrit un fichier .wav en texte via un modèle Whisper exporté en ONNX.
 *
 * PRÉREQUIS :
 *   - Placer whisper.onnx dans app/src/main/assets/
 *   - Le modèle doit accepter un tensor float32 [1, N] de log-mel spectrogramme
 *     et retourner un tensor de token IDs.
 *
 * CONVERSION depuis Python :
 *   pip install openai-whisper optimum onnx
 *   optimum-cli export onnx --model openai/whisper-tiny --task automatic-speech-recognition ./whisper_onnx
 */
class SpeechToText(private val context: Context) {

    private val ortEnv: OrtEnvironment = OrtEnvironment.getEnvironment()
    private var ortSession: OrtSession? = null

    // Vocabulaire Whisper simplifié pour le décodage des tokens
    // En production, charger le fichier vocab.json complet de Whisper
    private val tokenDecoder: WhisperTokenDecoder = WhisperTokenDecoder()

    init {
        loadModel()
    }

    /**
     * Charge le modèle ONNX depuis les assets.
     */
    private fun loadModel() {
        try {
            val modelBytes = context.assets.open("whisper.onnx").readBytes()
            val sessionOptions = OrtSession.SessionOptions().apply {
                setIntraOpNumThreads(2)
                setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            }
            ortSession = ortEnv.createSession(modelBytes, sessionOptions)
        } catch (e: Exception) {
            e.printStackTrace()
            // Le modèle n'est pas encore fourni : mode dégradé (retourne texte vide)
        }
    }

    /**
     * Transcrit un fichier WAV en texte.
     *
     * @param wavFile Fichier .wav produit par AudioRecorder (16kHz, mono, PCM16)
     * @return Texte transcrit, ou chaîne vide en cas d'erreur
     */
    fun transcribe(wavFile: File): String {
        android.util.Log.i("Whisper", "Beginning transcription of $wavFile")
        val session = ortSession ?: return simulateTranscription(wavFile)

        return try {
            // 1. Charger les samples PCM depuis le .wav
            val pcmSamples = readWavPcm(wavFile)

            // 2. Calculer le log-mel spectrogramme (80 bandes, fenêtres de 25ms)
            val melSpectrogram = computeLogMelSpectrogram(pcmSamples)

            // 3. Créer le tensor d'entrée [1, 80, T]
            val shape = longArrayOf(1, 80, melSpectrogram[0].size.toLong())
            val flatData = melSpectrogram.flatMap { it.toList() }.toFloatArray()
            val inputTensor = OnnxTensor.createTensor(
                ortEnv,
                FloatBuffer.wrap(flatData),
                shape
            )

            // 4. Inférence
            val inputs = mapOf("input_features" to inputTensor)
            val output = session.run(inputs)

            // 5. Décoder les tokens en texte
            val tokenIds = (output[0].value as Array<*>).map { (it as Long).toInt() }
            val text = tokenDecoder.decode(tokenIds)

            inputTensor.close()
            output.close()

            android.util.Log.i("Whisper", "$wavFile transcribed : $text")
            text
        } catch (e: Exception) {
            e.printStackTrace()
            ""
        }
    }

    /**
     * Lit les samples PCM 16bit depuis un fichier WAV (skip les 44 octets d'en-tête).
     */
    private fun readWavPcm(file: File): FloatArray {
        val bytes = file.readBytes()
        val headerSize = 44
        val sampleCount = (bytes.size - headerSize) / 2

        val buffer = ByteBuffer.wrap(bytes, headerSize, bytes.size - headerSize)
            .order(ByteOrder.LITTLE_ENDIAN)
            .asShortBuffer()

        return FloatArray(sampleCount) { buffer.get().toFloat() / 32768.0f }
    }

    /**
     * Calcule un log-mel spectrogramme simplifié (80 bandes Mel).
     *
     * NOTE : Implémentation simplifiée pour illustration.
     * En production, utiliser une bibliothèque DSP (ex: TarsosDSP ou implémentation
     * FFT complète) pour un spectrogramme conforme aux attentes de Whisper.
     */
    private fun computeLogMelSpectrogram(samples: FloatArray): Array<FloatArray> {
        val nMels = 80
        val hopLength = 160        // 10ms @ 16kHz
        val windowSize = 400       // 25ms @ 16kHz
        val nFrames = maxOf(1, (samples.size - windowSize) / hopLength + 1)

        // Placeholder : en production, remplacer par FFT + filtre Mel réel
        return Array(nMels) { melBand ->
            FloatArray(nFrames) { frame ->
                val start = frame * hopLength
                val end = minOf(start + windowSize, samples.size)
                val chunk = samples.sliceArray(start until end)
                // Énergie approximative dans la bande Mel
                val energy = chunk.map { it * it }.average().toFloat()
                maxOf(-10.0f, (Math.log((energy + 1e-10).toDouble()) / Math.log(10.0)).toFloat())
            }
        }
    }

    /**
     * Mode dégradé si le modèle n'est pas chargé : simule une transcription.
     * À supprimer une fois le modèle ONNX ajouté.
     */
    private fun simulateTranscription(wavFile: File): String {
        android.util.Log.w("SpeechToText", "Modèle ONNX absent, transcription simulée.")
        return ""
    }

    fun close() {
        ortSession?.close()
        ortEnv.close()
    }
}

/**
 * Décodeur de tokens Whisper simplifié.
 * En production, charger le fichier tokenizer.json du modèle Whisper.
 */
class WhisperTokenDecoder {
    fun decode(tokenIds: List<Int>): String {
        // Implémentation réelle : mapper chaque token ID vers son string via le vocabulaire Whisper
        // Disponible dans le fichier vocab.json du modèle HuggingFace
        return tokenIds
            .filter { it > 50257 } // Exclure les tokens spéciaux Whisper
            .joinToString("") { "<$it>" } // Placeholder
    }
}