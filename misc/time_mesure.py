import re
from collections import defaultdict

LOG_FILE = "vishield_output.txt"

# Regex patterns
pattern = re.compile(
    r'^(\d+\.\d+)\s+\[(Speaker|Mic|Mixer|Whisper)\]\s+(.+)$'
)

mic_capture    = {}   # buffer_id -> timestamp
mixer_save     = {}   # buffer_id -> timestamp
whisper_start  = {}   # buffer_id -> timestamp
whisper_end    = {}   # buffer_id -> timestamp

with open(LOG_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        m = pattern.match(line)
        if not m:
            continue

        ts     = float(m.group(1))
        actor  = m.group(2)
        msg    = m.group(3)

        # [Mic] Buffer Y captured
        if actor == "Mic":
            bm = re.search(r'Buffer (\d+) captured', msg)
            if bm:
                buf_id = int(bm.group(1))
                mic_capture[buf_id] = ts

        # [Mixer] Buffer Y saved → recordings\callRecord_X_Y.wav
        elif actor == "Mixer":
            bm = re.search(r'Buffer (\d+) saved.*callRecord_\d+_(\d+)\.wav', msg)
            if bm:
                buf_id = int(bm.group(2))   # Y in callRecord_X_Y
                mixer_save[buf_id] = ts

        # [Whisper] Beginning transcription of file recordings\callRecord_X_Y.wav
        elif actor == "Whisper" and "Beginning transcription" in msg:
            bm = re.search(r'callRecord_\d+_(\d+)\.wav', msg)
            if bm:
                buf_id = int(bm.group(1))
                whisper_start[buf_id] = ts

        # [Whisper] recordings\callRecord_X_Y.wav converted to new text buffer : ...
        elif actor == "Whisper" and "converted to new text buffer" in msg:
            bm = re.search(r'callRecord_\d+_(\d+)\.wav', msg)
            if bm:
                buf_id = int(bm.group(1))
                whisper_end[buf_id] = ts


def avg(deltas):
    return sum(deltas) / len(deltas) if deltas else float('nan')


# ── Metric 1 : Mic capture → Mixer save (same buffer id) ─────────────────────
deltas_mic_to_mixer = []
for buf_id, mic_ts in mic_capture.items():
    if buf_id in mixer_save:
        deltas_mic_to_mixer.append(mixer_save[buf_id] - mic_ts)

# ── Metric 2 : Mixer save → Whisper start (same buffer id) ───────────────────
deltas_mixer_to_whisper_start = []
for buf_id, mix_ts in mixer_save.items():
    if buf_id in whisper_start:
        deltas_mixer_to_whisper_start.append(whisper_start[buf_id] - mix_ts)

# ── Metric 3 : Whisper start → Whisper end (same buffer id) ──────────────────
deltas_whisper_duration = []
for buf_id, ws_ts in whisper_start.items():
    if buf_id in whisper_end:
        deltas_whisper_duration.append(whisper_end[buf_id] - ws_ts)


print("=" * 60)
print("  ViShield – Analyse des temps de traitement")
print("=" * 60)

print(f"\n① Temps d'enregistrement  (Mic capture → Mixer save)")
if deltas_mic_to_mixer:
    for i, d in enumerate(deltas_mic_to_mixer):
        print(f"   Buffer {i} : {d:.3f} s")
    print(f"   ► Moyenne : {avg(deltas_mic_to_mixer):.3f} s")
else:
    print("   Aucune donnée appariée.")

print(f"\n② Délai avant transcription (Mixer save → Whisper start)")
if deltas_mixer_to_whisper_start:
    for i, d in enumerate(deltas_mixer_to_whisper_start):
        print(f"   Buffer {i} : {d:.3f} s")
    print(f"   ► Moyenne : {avg(deltas_mixer_to_whisper_start):.3f} s")
else:
    print("   Aucune donnée appariée.")

print(f"\n③ Durée de transcription   (Whisper start → Whisper end)")
if deltas_whisper_duration:
    for i, d in enumerate(deltas_whisper_duration):
        print(f"   Buffer {i} : {d:.3f} s")
    print(f"   ► Moyenne : {avg(deltas_whisper_duration):.3f} s")
else:
    print("   Aucune donnée appariée.")

print("\n" + "=" * 60)
