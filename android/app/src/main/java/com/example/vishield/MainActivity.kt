package com.example.vishield

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Button
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.localbroadcastmanager.content.LocalBroadcastManager

/**
 * MainActivity — Interface principale
 *
 * Gère les 4 états / vues de l'application :
 *   ATTENTE          → Vue avec bouton Power
 *   ECOUTE           → Vue d'enregistrement actif
 *   VISHING_PROBABLE → Vue d'alerte modérée
 *   VISHING_SUR      → Vue d'alerte maximale
 *
 * Le pipeline audio tourne dans DetectionService (foreground service).
 * MainActivity reçoit les changements d'état via BroadcastReceiver.
 */
class MainActivity : AppCompatActivity() {

    // =========================================================================
    // État de l'application
    // =========================================================================
    enum class AppState { ATTENTE, ECOUTE, VISHING_PROBABLE, VISHING_SUR }

    private var currentState: AppState = AppState.ATTENTE

    // =========================================================================
    // Composants métier
    // =========================================================================
    private lateinit var callDetector: CallDetector

    // =========================================================================
    // Vues UI
    // =========================================================================
    private lateinit var viewAttente: View
    private lateinit var viewEcoute: View
    private lateinit var viewVishingProbable: View
    private lateinit var viewVishingSur: View
    private lateinit var btnPower: Button

    // =========================================================================
    // BroadcastReceiver — reçoit les changements d'état depuis DetectionService
    // =========================================================================
    private val stateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == DetectionService.ACTION_STATE_CHANGED) {
                val stateName = intent.getStringExtra(DetectionService.EXTRA_NEW_STATE)
                Log.d("MainActivity", "Broadcast reçu : $stateName")
                val newState = AppState.valueOf(stateName ?: return)
                transitionTo(newState)
            }
        }
    }

    // =========================================================================
    // Demande de permissions
    // =========================================================================
    private val permissionsLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        results.forEach { (permission, granted) ->
            Log.d("MainActivity", "Permission $permission : $granted")
        }
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        bindViews()
        requestRequiredPermissions()
        setupCallDetector()
        showState(AppState.ATTENTE)

        btnPower.setOnClickListener {
            if (currentState == AppState.ATTENTE) {
                transitionTo(AppState.ECOUTE)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        val filter = IntentFilter(DetectionService.ACTION_STATE_CHANGED)
        LocalBroadcastManager.getInstance(this)
            .registerReceiver(stateReceiver, filter)
        Log.d("MainActivity", "BroadcastReceiver enregistré")
    }

    override fun onPause() {
        super.onPause()
        try {
            LocalBroadcastManager.getInstance(this)
                .unregisterReceiver(stateReceiver)
            Log.d("MainActivity", "BroadcastReceiver désenregistré")
        } catch (e: IllegalArgumentException) {
            Log.w("MainActivity", "Receiver déjà désenregistré")
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        callDetector.stopListening()
        Log.d("MainActivity", "MainActivity détruite")
    }

    // =========================================================================
    // Liaison des vues
    // =========================================================================

    private fun bindViews() {
        viewAttente         = findViewById(R.id.view_attente)
        viewEcoute          = findViewById(R.id.view_ecoute)
        viewVishingProbable = findViewById(R.id.view_vishing_probable)
        viewVishingSur      = findViewById(R.id.view_vishing_sur)
        btnPower            = findViewById(R.id.btn_power)

        // Boutons "Arrêter l'écoute" — les 3 font la même chose
        val stopListener = View.OnClickListener {
            Log.d("MainActivity", "Arrêt manuel de l'écoute")
            transitionTo(AppState.ATTENTE)
        }
        findViewById<Button>(R.id.btn_stop_ecoute).setOnClickListener(stopListener)
        findViewById<Button>(R.id.btn_stop_probable).setOnClickListener(stopListener)
        findViewById<Button>(R.id.btn_stop_sur).setOnClickListener(stopListener)
    }

    // =========================================================================
    // Machine à états
    // =========================================================================

    /**
     * Effectue une transition vers un nouvel état.
     * Démarre ou arrête DetectionService selon l'état cible.
     */
    private fun transitionTo(newState: AppState) {
        Log.i("MainActivity", "Transition : $currentState → $newState")
        currentState = newState
        showState(newState)

        when (newState) {
            AppState.ATTENTE -> {
                stopDetectionService()
            }
            AppState.ECOUTE -> {
                startDetectionService()
            }
            AppState.VISHING_PROBABLE -> {
                // Le service continue d'écouter, on ne fait rien ici
            }
            AppState.VISHING_SUR -> {
                callDetector.hangUp()
                stopDetectionService()
            }
        }
    }

    /**
     * Affiche la vue correspondant à l'état.
     */
    private fun showState(state: AppState) {
        viewAttente.visibility         = View.GONE
        viewEcoute.visibility          = View.GONE
        viewVishingProbable.visibility = View.GONE
        viewVishingSur.visibility      = View.GONE

        when (state) {
            AppState.ATTENTE          -> viewAttente.visibility = View.VISIBLE
            AppState.ECOUTE           -> viewEcoute.visibility = View.VISIBLE
            AppState.VISHING_PROBABLE -> viewVishingProbable.visibility = View.VISIBLE
            AppState.VISHING_SUR      -> viewVishingSur.visibility = View.VISIBLE
        }
    }

    // =========================================================================
    // Gestion de DetectionService
    // =========================================================================

    private fun startDetectionService() {
        val intent = Intent(this, DetectionService::class.java).apply {
            action = DetectionService.ACTION_START
        }
        startForegroundService(intent)
        Log.d("MainActivity", "DetectionService démarré")
    }

    private fun stopDetectionService() {
        val intent = Intent(this, DetectionService::class.java).apply {
            action = DetectionService.ACTION_STOP
        }
        startService(intent)
        Log.d("MainActivity", "DetectionService arrêté")
    }

    // =========================================================================
    // CallDetector
    // =========================================================================

    private fun setupCallDetector() {
        callDetector = CallDetector(
            context = this,
            onCallStarted = {
                runOnUiThread {
                    Log.d("MainActivity", "Appel détecté par CallDetector")
                    if (currentState == AppState.ATTENTE) {
                        transitionTo(AppState.ECOUTE)
                    }
                }
            },
            onCallEnded = {
                runOnUiThread {
                    Log.d("MainActivity", "Fin d'appel détectée par CallDetector")
                    if (currentState != AppState.ATTENTE) {
                        transitionTo(AppState.ATTENTE)
                    }
                }
            }
        )
        callDetector.startListening()
        Log.d("MainActivity", "CallDetector démarré")
    }

    // =========================================================================
    // Permissions
    // =========================================================================

    private fun requestRequiredPermissions() {
        val permissions = mutableListOf(
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.READ_PHONE_STATE,
            Manifest.permission.ANSWER_PHONE_CALLS
        )
        // POST_NOTIFICATIONS requis sur Android 13+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        val missing = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isNotEmpty()) {
            Log.d("MainActivity", "Permissions manquantes : $missing")
            permissionsLauncher.launch(missing.toTypedArray())
        }
    }
}