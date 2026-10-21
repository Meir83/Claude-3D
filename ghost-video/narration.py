#!/usr/bin/env python3
"""Hebrew narration for the "MCP for Mainframe" pitch.

Each sentence has (caption, tts): the caption is what appears on screen,
tts is a phonetic Hebrew spelling of the same sentence (Latin acronyms
don't read well), used as TTS input only.
Running this module renders the voice-over and writes timeline.json,
script_he.md and captions_he.srt next to it.

Engine (env TTS_ENGINE or --engine):
  espeak    robotic, offline fallback (default)
  phonikud  neural: phonikud-onnx adds nikud, phonikud + Piper ONNX voice
  mms       neural: facebook/mms-tts-heb via transformers (no nikud)
Neural engines need huggingface.co; see requirements-tts.txt.
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LEAD, GAP, TAIL, MIN_DUR = 0.9, 0.5, 1.3, 4.5

SLIDES = [
    ("Intro", [
        ("היי, אני רוח הרפאים של פרויקט MCP למיינפריים.",
         "היי, אני רוח הרפאים של פרויקט אם סי פי למיינפריים."),
        ("בקשה קטנה: תנו לנו את הקול שלכם.",
         "בקשה קטנה: תנו לנו את הקול שלכם."),
    ]),
    ("The Problem", [
        ("כדי לעבוד מול המיינפריים צריך מסכים ירוקים, פקודות סודיות וידע שנמצא אצל מעט מאוד אנשים.",
         "כדי לעבוד מול המיינפריים צריך מסכים ירוקים, פקודות סודיות, וידע שנמצא אצל מעט מאוד אנשים."),
        ("כל שגיאה כזו עולה זמן ותסכול.",
         "כל שגיאה כזו עולה זמן ותסכול."),
    ]),
    ("Target Audience", [
        ("הפרויקט מיועד לצוותי תשתיות, מסדי נתונים ופיתוח, שעובדים מול z/OS, Db2 ו-CICS.",
         "הפרויקט מיועד לצוותי תשתיות, מסדי נתונים ופיתוח, שעובדים מול זד או אס, די בי טו וסי איי סי אס."),
        ("וגם למפתחים חדשים שלא גדלו על קובול.",
         "וגם למפתחים חדשים שלא גדלו על קובול."),
    ]),
    ("The Vision", [
        ("MCP הוא תקן פתוח שמחבר עוזרי בינה מלאכותית למערכות ארגוניות.",
         "אם סי פי הוא תקן פתוח שמחבר עוזרי בינה מלאכותית למערכות ארגוניות."),
        ("במקום מסך ירוק, המפתח שואל בצ'אט בתוך ה-IDE, והעוזר מגיע למיינפריים בשבילו.",
         "במקום מסך ירוק, המפתח שואל בצאט בתוך איי די אי, והעוזר מגיע למיינפריים בשבילו."),
    ]),
    ("Business Value", [
        ("פחות זמן חיפוש וחקירה, קליטה מהירה של מפתחים חדשים ופחות תלות במומחים בודדים.",
         "פחות זמן חיפוש וחקירה, קליטה מהירה של מפתחים חדשים, ופחות תלות במומחים בודדים."),
        ("כך משפרים יעילות ומעלים את החזר ההשקעה.",
         "כך משפרים יעילות ומעלים את החזר ההשקעה."),
    ]),
    ("Security", [
        ("הגישה עוברת דרך שרת MCP מאובטח, עם הרשאות לפי משתמש ובלי לעקוף את בקרות האבטחה הקיימות.",
         "הגישה עוברת דרך שרת אם סי פי מאובטח, עם הרשאות לפי משתמש, ובלי לעקוף את בקרות האבטחה הקיימות."),
        ("כל פעולה נרשמת ביומן, ואפשר להתחיל עם גישת קריאה בלבד.",
         "כל פעולה נרשמת ביומן, ואפשר להתחיל עם גישת קריאה בלבד."),
    ]),
    ("Minimal Pilot", [
        ("מתחילים בפיילוט מינימלי: חיבור אחד, פעולות קריאה בלבד וקבוצת מפתחים קטנה.",
         "מתחילים בפיילוט מינימלי: חיבור אחד, פעולות קריאה בלבד, וקבוצת מפתחים קטנה."),
        ("מחברים כבל אחד, בודקים, ולומדים.",
         "מחברים כבל אחד, בודקים, ולומדים."),
    ]),
    ("Success Metrics", [
        ("נמדוד הצלחה במדדים ברורים: זמן לביצוע משימה, מספר שגיאות ושביעות רצון המפתחים.",
         "נמדוד הצלחה במדדים ברורים: זמן לביצוע משימה, מספר שגיאות, ושביעות רצון המפתחים."),
        ("עמדנו ביעד? מרחיבים. תודה, ובבקשה: הצביעו בעדי!",
         "עמדנו ביעד? מרחיבים. תודה, ובבקשה: הצביעו בעדי!"),
    ]),
]


def write_wav(path, samples, sr):
    pcm = (np.clip(np.asarray(samples, dtype=np.float32).reshape(-1), -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sr))
        w.writeframes(pcm.tobytes())


def hf_file(repo, name):
    from huggingface_hub import hf_hub_download
    return hf_hub_download(repo, name)


def make_espeak():
    def synth(text, path):
        subprocess.run(["espeak-ng", "-v", "he", "-s", "165", "-p", "45", "-g", "4", "-w", path, text], check=True)
    return synth


def make_phonikud():
    # UNTESTED against the real models: written without network access.
    # Repos/filenames are overridable; check them against the phonikud-tts README.
    from phonikud_onnx import Phonikud
    from phonikud import phonemize
    from piper_onnx import Piper
    nikud = Phonikud(hf_file(os.environ.get("PHONIKUD_REPO", "thewh1teagle/phonikud-onnx"),
                             os.environ.get("PHONIKUD_FILE", "phonikud-1.0.int8.onnx")))
    voice_repo = os.environ.get("PHONIKUD_TTS_REPO", "thewh1teagle/phonikud-tts-checkpoints")
    piper = Piper(hf_file(voice_repo, os.environ.get("PHONIKUD_TTS_MODEL", "model.onnx")),
                  hf_file(voice_repo, os.environ.get("PHONIKUD_TTS_CONFIG", "model.config.json")))

    def synth(text, path):
        phonemes = phonemize(nikud.add_diacritics(text))
        samples, sr = piper.create(phonemes, is_phonemes=True)
        write_wav(path, samples, sr)
    return synth


def make_mms():
    import torch
    from transformers import AutoTokenizer, VitsModel
    tok = AutoTokenizer.from_pretrained("facebook/mms-tts-heb")
    model = VitsModel.from_pretrained("facebook/mms-tts-heb").eval()

    def synth(text, path):
        with torch.no_grad():
            wav = model(**tok(text, return_tensors="pt")).waveform[0].numpy()
        write_wav(path, wav, model.config.sampling_rate)
    return synth


ENGINES = {"espeak": make_espeak, "phonikud": make_phonikud, "mms": make_mms}


def wav_len(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def srt_ts(x):
    ms = int(round(x * 1000))
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def build(workdir, engine=None):
    engine = engine or os.environ.get("TTS_ENGINE", "espeak")
    synth = ENGINES[engine]()
    os.makedirs(workdir, exist_ok=True)
    slides, start = [], 0.0
    for si, (title, sents) in enumerate(SLIDES):
        items, t = [], LEAD
        for k, (cap, tts) in enumerate(sents):
            p = os.path.join(workdir, "s%d_%d.wav" % (si + 1, k + 1))
            synth(tts, p)
            d = wav_len(p)
            items.append({"caption": cap, "wav": p, "t0": t, "t1": t + d})
            t += d + GAP
        dur = max(MIN_DUR, t - GAP + TAIL)
        slides.append({"title": title, "start": start, "dur": dur, "sentences": items})
        start += dur
    tl = {"slides": slides, "total": start}
    with open(os.path.join(HERE, "timeline.json"), "w") as f:
        json.dump(tl, f, ensure_ascii=False, indent=1)
    with open(os.path.join(HERE, "script_he.md"), "w") as f:
        f.write("# תסריט קריינות — MCP למיינפריים\n\n")
        for si, s in enumerate(slides):
            f.write("## סלייד %d — %s (%.1f ש')\n\n" % (si + 1, s["title"], s["dur"]))
            for it in s["sentences"]:
                f.write("- %s\n" % it["caption"])
            f.write("\n")
    with open(os.path.join(HERE, "captions_he.srt"), "w") as f:
        n = 1
        for s in slides:
            for it in s["sentences"]:
                f.write("%d\n%s --> %s\n%s\n\n" % (n, srt_ts(s["start"] + it["t0"]), srt_ts(s["start"] + it["t1"]), it["caption"]))
                n += 1
    return tl


if __name__ == "__main__":
    eng = sys.argv[sys.argv.index("--engine") + 1] if "--engine" in sys.argv else None
    out = build(os.path.join(HERE, "_tts"), eng)
    print("total %.1fs" % out["total"], [round(s["dur"], 1) for s in out["slides"]])
