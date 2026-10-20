#!/usr/bin/env python3
"""Hebrew narration for the "MCP for Mainframe" pitch.

Each sentence has (caption, tts): the caption is what appears on screen,
tts is a phonetic spelling for espeak-ng (Latin acronyms don't read well).
Running this module renders the voice-over and writes timeline.json,
script_he.md and captions_he.srt next to it.
"""
import json
import os
import subprocess
import wave

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
         "הפרויקט מיועד לצוותי תשתיות, מסדי נתונים ופיתוח, שעובדים מול זד או אס, די בי טו, וסיקס."),
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


def wav_len(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def srt_ts(x):
    ms = int(round(x * 1000))
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def build(workdir):
    os.makedirs(workdir, exist_ok=True)
    slides, start = [], 0.0
    for si, (title, sents) in enumerate(SLIDES):
        items, t = [], LEAD
        for k, (cap, tts) in enumerate(sents):
            p = os.path.join(workdir, "s%d_%d.wav" % (si + 1, k + 1))
            subprocess.run(["espeak-ng", "-v", "he", "-s", "165", "-p", "45", "-g", "4", "-w", p, tts], check=True)
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
    out = build(os.path.join(HERE, "_tts"))
    print("total %.1fs" % out["total"], [round(s["dur"], 1) for s in out["slides"]])
