#!/usr/bin/env python3
"""
LinkedIn Auto-Poster — קול קו
פורסם: ב/ד/ו בשעה 10:00 ישראל
"""

import os
import sys
import json
import datetime
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

# ─── CONFIG ───────────────────────────────────────
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
COMPANY_ID     = "80445615"
DIR            = Path(__file__).parent
STATE_FILE     = DIR / "storage_state.json"
LOG_FILE       = DIR / "log.json"
QUEUE_FILE     = DIR / "queue.json"

POST_URL = (
    f"https://www.linkedin.com/company/{COMPANY_ID}/admin/page-posts/published/"
    f"?share=true&shareActorType=ORGANIZATION"
    f"&shareOrganizationActor=urn%3Ali%3Afsd_company%3A{COMPANY_ID}"
)

# ─── POST PROMPTS (day: 0=Mon, 2=Wed, 4=Fri) ─────
PROMPTS = {
    0: [
        "כתוב פוסט מקצועי קצר בעברית ללינקדאין של קול קו - מרכזייה וירטואלית לעסקים. נושא: כיצד ניהול שיחות נכנסות חכם מגדיל פרודוקטיביות. 2-3 שורות. ללא אמוג'י. ללא האשטאגים. לסיים עם kolkav.com",
        "כתוב פוסט מקצועי קצר בעברית ללינקדאין של קול קו. נושא: כשהמרכזייה מטפלת בשיחות - אתה מתרכז בצמיחה. 2-3 שורות. ללא אמוג'י. ללא האשטאגים. לסיים עם kolkav.com",
        "כתוב פוסט מקצועי קצר בעברית ללינקדאין של קול קו. נושא: ניתוב שיחות אוטומטי חוסך שעות עבודה בשבוע. 2-3 שורות. ללא אמוג'י. ללא האשטאגים. לסיים עם kolkav.com",
    ],
    2: [
        "כתוב פוסט מקצועי קצר בעברית ללינקדאין של קול קו. נושא: כל לקוח שמתקשר ראוי לענה מיידית, גם בשעות העסק הכי עמוסות. 2-3 שורות. ללא אמוג'י. ללא האשטאגים. לסיים עם kolkav.com",
        "כתוב פוסט מקצועי קצר בעברית ללינקדאין של קול קו. נושא: חווית לקוח מתחילה מהרגע הראשון - ניתוב חכם לאיש הנכון. 2-3 שורות. ללא אמוג'י. ללא האשטאגים. לסיים עם kolkav.com",
        "כתוב פוסט מקצועי קצר בעברית ללינקדאין של קול קו. נושא: שיחה שלא נענית = לקוח שהולך למתחרה. 2-3 שורות. ללא אמוג'י. ללא האשטאגים. לסיים עם kolkav.com",
    ],
    4: [
        "כתוב פוסט מקצועי קצר בעברית ללינקדאין של קול קו. נושא: מרכזייה וירטואלית עולה פחות ממזכירה חצי משרה - ועובדת 24/7. 2-3 שורות. ללא אמוג'י. ללא האשטאגים. לסיים עם kolkav.com",
        "כתוב פוסט מקצועי קצר בעברית ללינקדאין של קול קו. נושא: ללא ציוד, ללא התקנה, ללא חוזה ארוך - מרכזייה מקצועית בתשלום חודשי קבוע. 2-3 שורות. ללא אמוג'י. ללא האשטאגים. לסיים עם kolkav.com",
        "כתוב פוסט מקצועי קצר בעברית ללינקדאין של קול קו. נושא: מה עסק קטן מרוויח ממרכזייה שעולה פחות מקפה ביום. 2-3 שורות. ללא אמוג'י. ללא האשטאגים. לסיים עם kolkav.com",
    ],
}


def generate_post(dow: int) -> str:
    import random
    pool = PROMPTS.get(dow, PROMPTS[0])

    # rotation נגד חזרה
    q = {}
    if QUEUE_FILE.exists():
        q = json.loads(QUEUE_FILE.read_text())
    last = q.get(str(dow), -1)
    idx = (last + 1) % len(pool)
    q[str(dow)] = idx
    QUEUE_FILE.write_text(json.dumps(q))

    prompt = pool[idx]
    data = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 250,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return resp['content'][0]['text'].strip()


def post_to_linkedin(text: str, headless: bool = True) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--no-sandbox"],
        )

        # טעינת session קיים
        ctx_args = {"viewport": {"width": 1280, "height": 800}}
        if STATE_FILE.exists():
            ctx_args["storage_state"] = str(STATE_FILE)

        context = browser.new_context(**ctx_args)
        page = context.new_page()

        # פתיחת דיאלוג פרסום
        page.goto(POST_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(6000)

        # בדיקת login
        if "login" in page.url or "authwall" in page.url:
            browser.close()
            return {"status": "NEED_LOGIN", "error": "Not logged in. Run with --setup first."}

        # המתנה לעורך - אם הדיאלוג לא נפתח אוטומטית, לחץ על Start a post
        try:
            page.wait_for_selector('[contenteditable="true"]', timeout=5000)
        except Exception:
            # נסה ללחוץ על כפתור Start a post / Create post
            try:
                btn = page.locator('button:has-text("Start a post"), button:has-text("Create a post")')
                if btn.count() > 0:
                    btn.first.click()
                    page.wait_for_timeout(3000)
                page.wait_for_selector('[contenteditable="true"]', timeout=8000)
            except Exception as e2:
                browser.close()
                return {"status": "FAILED", "error": f"Post editor not found: {e2}"}

        editor = page.locator('[contenteditable="true"]').first
        editor.click()
        page.wait_for_timeout(300)
        editor.type(text, delay=8)
        page.wait_for_timeout(600)

        # כפתור Post
        post_btn = page.locator("button.share-actions__primary-action")
        if not post_btn.is_visible():
            browser.close()
            return {"status": "FAILED", "error": "Post button not visible"}

        post_btn.click()
        page.wait_for_timeout(4000)

        # שמירת session מעודכן
        context.storage_state(path=str(STATE_FILE))

        # בדיקת הצלחה
        success = "share=true" not in page.url
        browser.close()

        if success:
            return {"status": "OK", "text": text}
        return {"status": "FAILED", "error": "Page did not change after clicking Post"}


def log_result(status: str, text: str, error: str = ""):
    log = []
    if LOG_FILE.exists():
        try:
            log = json.loads(LOG_FILE.read_text())
        except Exception:
            pass
    log.append({
        "time":   datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "text":   text[:120],
        "error":  error,
    })
    if len(log) > 300:
        log = log[-300:]
    LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2))


def setup_mode():
    """פותח דפדפן גלוי להתחברות ידנית ושמירת session - ממתין אוטומטית עד להתחברות"""
    print("=== SETUP MODE ===")
    print("יפתח דפדפן. התחבר ל-LinkedIn - הסקריפט ישמור session אוטומטית.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        page.goto("https://www.linkedin.com/login")
        print("ממתין להתחברות (5 דקות מקסימום)...")
        import time
        deadline = time.time() + 300
        logged_in = False
        while time.time() < deadline:
            time.sleep(3)
            url = page.url
            if "login" not in url and "authwall" not in url and "linkedin.com" in url:
                page.wait_for_timeout(2000)
                logged_in = True
                break
        if not logged_in:
            print("timeout - שומר session כמו שהוא")
        context.storage_state(path=str(STATE_FILE))
        browser.close()

    print(f"✅ Session נשמר ב-{STATE_FILE}")


def main():
    force  = "--force"  in sys.argv
    headed = "--headed" in sys.argv
    setup  = "--setup"  in sys.argv

    if setup:
        setup_mode()
        return

    dow = datetime.datetime.now().weekday()  # 0=Mon, 2=Wed, 4=Fri

    if not force and dow not in [0, 2, 4]:
        print(f"לא יום פרסום (weekday={dow}). יוצא.")
        sys.exit(0)

    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] מייצר פוסט ליום {dow}...")

    try:
        text = generate_post(dow)
        print(f"טקסט: {text[:100]}...")
    except Exception as e:
        print(f"שגיאה בייצור טקסט: {e}")
        log_result("FAILED", "", str(e))
        sys.exit(1)

    result = post_to_linkedin(text, headless=not headed)
    log_result(result["status"], text, result.get("error", ""))

    print(f"תוצאה: {result['status']}")
    if result.get("error"):
        print(f"שגיאה: {result['error']}")
        sys.exit(1)

    print("✅ פוסט פורסם בהצלחה!")


if __name__ == "__main__":
    main()
