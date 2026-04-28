package com.example.vishield

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import java.nio.LongBuffer

/**
 * TextToNote
 *
 * Analyse un buffer de texte avec un modèle BERT fine-tuné pour la détection de vishing.
 * Retourne un Pair<Boolean, Float> :
 *   - Boolean : true si le texte est suspect (vishing détecté)
 *   - Float   : score de confiance [0.0, 1.0]
 *
 * PRÉREQUIS :
 *   - Convertir model.safetensors → model.onnx (voir instructions ci-dessous)
 *   - Placer bert_model.onnx dans app/src/main/assets/
 *   - Placer vocab.txt (vocabulaire BERT) dans app/src/main/assets/
 *
 * CONVERSION model.safetensors → ONNX :
 *   pip install transformers optimum torch
 *   from optimum.exporters.onnx import main_export
 *   main_export("./votre_modele", output="./bert_onnx", task="text-classification")
 *
 * Le modèle doit avoir :
 *   - Entrées : input_ids [batch, seq], attention_mask [batch, seq], token_type_ids [batch, seq]
 *   - Sortie  : logits [batch, 2]  (classe 0=normal, classe 1=vishing)
 */
class TextToNote(private val context: Context) {

    private val ortEnv: OrtEnvironment = OrtEnvironment.getEnvironment()
    private var ortSession: OrtSession? = null
    private var tokenizer: BertTokenizer? = null

    companion object {
        private const val MAX_SEQ_LENGTH = 128  // Longueur max de séquence BERT
        private const val VISHING_CLASS = 1     // Index de la classe "vishing"
    }

    init {
        loadModel()
        loadTokenizer()
    }

    /**
     * Charge le modèle BERT ONNX depuis les assets.
     */
    private fun loadModel() {
        try {
            val modelBytes = context.assets.open("bert_model.onnx").readBytes()
            val options = OrtSession.SessionOptions().apply {
                setIntraOpNumThreads(2)
            }
            ortSession = ortEnv.createSession(modelBytes, options)
        } catch (e: Exception) {
            e.printStackTrace()
            android.util.Log.w("TextToNote", "Modèle BERT absent ou invalide.")
        }
    }

    /**
     * Charge le vocabulaire BERT pour la tokenisation.
     */
    private fun loadTokenizer() {
        try {
            val vocabLines = context.assets.open("vocab.txt")
                .bufferedReader()
                .readLines()
            tokenizer = BertTokenizer(vocabLines)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    /**
     * Analyse un texte et retourne (estVishing, scoreConfiance).
     *
     * @param text Texte transcrit par SpeechToText
     * @return Pair<Boolean, Float> — (détecté, score [0..1])
     */
    fun analyze(text: String): Pair<Boolean, Float> {
        android.util.Log.i("Bert", "Beginning analysing : $text")
        if (text.isBlank()) return Pair(false, 0.0f)

        val session = ortSession ?: return simulateAnalysis(text)
        val tok = tokenizer ?: return simulateAnalysis(text)

        return try {
            // 1. Tokeniser le texte
            val encoding = tok.encode(text, MAX_SEQ_LENGTH)

            // 2. Construire les tensors d'entrée [1, MAX_SEQ_LENGTH]
            val batchSize = 1L
            val seqLen = MAX_SEQ_LENGTH.toLong()
            val shape = longArrayOf(batchSize, seqLen)

            val inputIdsTensor = OnnxTensor.createTensor(
                ortEnv, LongBuffer.wrap(encoding.inputIds), shape
            )
            val attentionMaskTensor = OnnxTensor.createTensor(
                ortEnv, LongBuffer.wrap(encoding.attentionMask), shape
            )
            val tokenTypeIdsTensor = OnnxTensor.createTensor(
                ortEnv, LongBuffer.wrap(encoding.tokenTypeIds), shape
            )

            // 3. Inférence
            val inputs = mapOf(
                "input_ids"      to inputIdsTensor,
                "attention_mask" to attentionMaskTensor,
                "token_type_ids" to tokenTypeIdsTensor
            )
            val output = session.run(inputs)

            // 4. Lire les logits [1, 2] et appliquer softmax
            @Suppress("UNCHECKED_CAST")
            val logits = (output[0].value as Array<FloatArray>)[0]
            val probs = softmax(logits)
            val vishingScore = probs[VISHING_CLASS]
            val isVishing = vishingScore > 0.5f

            inputIdsTensor.close()
            attentionMaskTensor.close()
            tokenTypeIdsTensor.close()
            output.close()

            android.util.Log.i("Bert", "Analysed \"$text\" : Is it vishing ? $isVishing, confidence score :  $vishingScore")
            Pair(isVishing, vishingScore)
        } catch (e: Exception) {
            e.printStackTrace()
            Pair(false, 0.0f)
        }
    }

    private fun softmax(logits: FloatArray): FloatArray {
        val max = logits.max()
        val exps = logits.map { Math.exp((it - max).toDouble()).toFloat() }
        val sum = exps.sum()
        return exps.map { it / sum }.toFloatArray()
    }

    /**
     * Mode dégradé si le modèle est absent.
     */
    private fun simulateAnalysis(text: String): Pair<Boolean, Float> {
        android.util.Log.w("TextToNote", "Modèle absent, analyse simulée.")
        return Pair(false, 0.0f)
    }

    fun close() {
        ortSession?.close()
        ortEnv.close()
    }
}

// =============================================================================
// BertTokenizer — Tokeniseur WordPiece simplifié
// =============================================================================

data class BertEncoding(
    val inputIds: LongArray,
    val attentionMask: LongArray,
    val tokenTypeIds: LongArray
)

/**
 * Tokeniseur BERT WordPiece basique.
 * Charge le fichier vocab.txt standard de HuggingFace BERT.
 */
class BertTokenizer(vocabLines: List<String>) {

    private val vocab: Map<String, Int> = vocabLines
        .mapIndexed { index, token -> token.trim() to index }
        .toMap()

    private val clsToken = vocab["[CLS]"] ?: 101
    private val sepToken = vocab["[SEP]"] ?: 102
    private val padToken = vocab["[PAD]"] ?: 0
    private val unkToken = vocab["[UNK]"] ?: 100

    /**
     * Encode un texte en InputIds / AttentionMask / TokenTypeIds
     * avec padding/troncature à maxLength.
     */
    fun encode(text: String, maxLength: Int): BertEncoding {
        val words = text.lowercase().split(" ", "\t", "\n")
        val tokens = mutableListOf<Int>()

        tokens.add(clsToken)
        for (word in words) {
            tokens.addAll(wordPieceTokenize(word))
            if (tokens.size >= maxLength - 1) break
        }
        tokens.add(sepToken)

        val inputIds = LongArray(maxLength) { padToken.toLong() }
        val attentionMask = LongArray(maxLength) { 0L }
        val tokenTypeIds = LongArray(maxLength) { 0L }

        for (i in tokens.indices.take(maxLength)) {
            inputIds[i] = tokens[i].toLong()
            attentionMask[i] = 1L
        }

        return BertEncoding(inputIds, attentionMask, tokenTypeIds)
    }

    /**
     * Tokenisation WordPiece d'un mot.
     */
    private fun wordPieceTokenize(word: String): List<Int> {
        if (word.isEmpty()) return emptyList()
        if (vocab.containsKey(word)) return listOf(vocab[word]!!)

        val tokens = mutableListOf<Int>()
        var remaining = word
        var isFirst = true

        while (remaining.isNotEmpty()) {
            var found = false
            for (end in remaining.length downTo 1) {
                val sub = if (isFirst) remaining.substring(0, end)
                else "##${remaining.substring(0, end)}"
                if (vocab.containsKey(sub)) {
                    tokens.add(vocab[sub]!!)
                    remaining = remaining.substring(end)
                    isFirst = false
                    found = true
                    break
                }
            }
            if (!found) {
                tokens.add(unkToken)
                break
            }
        }
        return tokens
    }
}