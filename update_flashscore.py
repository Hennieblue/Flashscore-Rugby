import json,re,time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URLS=["https://www.flashscore.co.za/rugby-union/"]
OUT=Path(__file__).with_name("data.json")
SA=ZoneInfo("Africa/Johannesburg")
# GitHub Actions runs this script again every 5 minutes.
def clean(v): return re.sub(r"\s+"," ",v or "").strip()
def driver():
 o=webdriver.ChromeOptions()
 for a in ("--headless=new","--window-size=1920,1080","--disable-notifications","--disable-popup-blocking","--disable-gpu","--no-sandbox","--disable-dev-shm-usage","--lang=en-ZA"): o.add_argument(a)
 d=webdriver.Chrome(options=o);d.set_page_load_timeout(20);return d
def cookie(d):
 for sel in ("#onetrust-accept-btn-handler","button[id*='accept']","button[class*='accept']"):
  try:
   for b in d.find_elements(By.CSS_SELECTOR,sel):
    if b.is_displayed(): d.execute_script("arguments[0].click()",b);return
  except Exception: pass
def scroll(d):
    quiet=0
    last_height=0
    for _ in range(12):
        clicked=0
        for sel in ("div.event__more","[class*='event__more']","[data-testid*='show-more']"):
            try:
                for b in d.find_elements(By.CSS_SELECTOR,sel):
                    if b.is_displayed():
                        d.execute_script("arguments[0].scrollIntoView({block:'center'});",b)
                        d.execute_script("arguments[0].click();",b)
                        clicked+=1
                        time.sleep(.3)
            except Exception: pass
        try:
            for b in d.find_elements(By.XPATH,
                "//*[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'show more matches')]"):
                if b.is_displayed():
                    d.execute_script("arguments[0].scrollIntoView({block:'center'});",b)
                    d.execute_script("arguments[0].click();",b)
                    clicked+=1
                    time.sleep(.3)
        except Exception: pass
        d.execute_script("window.scrollBy(0,1200)")
        time.sleep(.4)
        try: h=d.execute_script("return document.body.scrollHeight")
        except Exception: h=last_height
        quiet = quiet+1 if h==last_height and clicked==0 else 0
        last_height=h
        if quiet>=3: break
    d.execute_script("window.scrollTo(0,0)")
    time.sleep(.4)

def text(row,selectors):
 for s in selectors:
  try:
   for e in row.find_elements(By.CSS_SELECTOR,s):
    v=clean(e.text)
    if v:return v
  except Exception:pass
 return ""
def participants(row):
 found=[]
 for s in (".event__homeParticipant",".event__awayParticipant",".event__participant","[data-testid='wcl-matchRow-participant']","[class*='event__participant']"):
  try:
   for e in row.find_elements(By.CSS_SELECTOR,s):
    v=clean(e.text)
    if v and v not in found:found.append(v)
  except Exception:pass
 return found[:2]
def rows(d):
 result=[]
 for s in ("div.event__match","div[class*='event__match']","[data-testid='wcl-matchRow']"):
  try:
   for e in d.find_elements(By.CSS_SELECTOR,s):
    if e not in result:result.append(e)
  except Exception:pass
 return result
def href(row):
 for s in ("a.eventRowLink","a[href*='/match/']"):
  try:
   for a in row.find_elements(By.CSS_SELECTOR,s):
    u=a.get_attribute("href")
    if u:return u
  except Exception:pass
 return ""
def status_from(value,has_score):
 low=value.lower()
 if low=="ft" or any(x in low for x in ("finished","after extra time","after penalties")):return "FINISHED"
 if any(x in low for x in ("postponed","cancelled","walkover")):return value.upper()
 if re.search(r"\d{1,3}\s*'",value) or any(x in low for x in ("1st half","2nd half","half time","break")):return "LIVE"
 if re.fullmatch(r"\d{1,2}:\d{2}",value.strip()):return "UPCOMING"
 # Flashscore finished rows sometimes contain a score but leave the time blank.
 if has_score and not value.strip():return "FINISHED"
 return "LIVE" if has_score else "UPCOMING"
def match_list(d,url):
    d.get(url)
    try:
        WebDriverWait(d,25).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR,"a.eventRowLink,div.event__match,[data-testid='wcl-matchRow']")))
    except Exception: pass
    time.sleep(1.5)
    cookie(d)
    scroll(d)
    out=[]; seen=set()
    for row in rows(d):
        try:
            u=href(row); names=participants(row)
            if "/match/" not in u or len(names)<2: continue
            key=u.split("#")[0]
            if key in seen: continue
            seen.add(key)
            tm=text(row,[".event__time","[class*='event__time']","[data-testid*='time']"])
            hs=text(row,[".event__score--home","[class*='event__score--home']"])
            aws=text(row,[".event__score--away","[class*='event__score--away']"])
            has_score=bool(re.fullmatch(r"\d{1,3}",hs) and re.fullmatch(r"\d{1,3}",aws))
            score=f"{int(hs)} - {int(aws)}" if has_score else "0 - 0"
            stage=text(row,[".event__stage--block",".event__stage","[class*='event__stage']"])
            status=status_from(stage or tm,has_score)
            out.append({"home":names[0],"away":names[1],"time":tm,"score":score,
                        "status":status,"url":u,"incidents":[]})
        except Exception: pass
    return out

def all_matches(d):
    allm=[]; seen=set()
    for url in URLS:
        try:
            for m in match_list(d,url):
                key=m["url"].split("#")[0]
                if key not in seen:
                    seen.add(key); allm.append(m)
        except Exception as e:
            print("Source error:",url,e)
    return allm

def match_detail(d,m):
    # Read the match-detail page.  The list page can still say 08:10/0-0
    # after a match has started, so the detail page is the source of truth.
    if m["status"] == "FINISHED":
        return
    try:
        d.get(m["url"])
        time.sleep(1.0)

        # Current score: use Flashscore's dedicated score elements first.
        hs = text(d, [
            ".detailScore__homeResult",
            ".detailScore__home",
            "[class*='detailScore__homeResult']",
            "[class*='detailScore__home']",
        ])
        aws = text(d, [
            ".detailScore__awayResult",
            ".detailScore__away",
            "[class*='detailScore__awayResult']",
            "[class*='detailScore__away']",
        ])
        if re.fullmatch(r"\d{1,3}", hs) and re.fullmatch(r"\d{1,3}", aws):
            m["score"] = f"{int(hs)} - {int(aws)}"

        # Current match status/minute from the detail page.
        detail_status = text(d, [
            ".detailScore__status",
            "[class*='detailScore__status']",
            ".detailScore__status span",
        ])
        if detail_status:
            low = detail_status.lower()
            if low == "ft" or "finished" in low or "after extra time" in low or "after penalties" in low:
                m["status"] = "FINISHED"
                m["time"] = detail_status
            elif re.search(r"\d{1,3}\s*'", detail_status) or any(x in low for x in ("1st half", "2nd half", "half time", "break")):
                m["status"] = "LIVE"
                m["time"] = detail_status
            else:
                # If a detail page exists and has a non-scheduled score/status,
                # keep it as live unless it is explicitly finished/upcoming.
                if m.get("score") != "0 - 0":
                    m["status"] = "LIVE"
                    m["time"] = detail_status

        # Incidents: tries, conversions, penalties, cards, substitutions, etc.
        seen = []
        for selector in (
            "div.smv__incident",
            "div[class*='smv__incident']",
            "[data-testid*='incident']",
        ):
            try:
                for e in d.find_elements(By.CSS_SELECTOR, selector):
                    value = clean(e.text)
                    if value and value not in {"-", "–", "—"} and len(value) > 1 and value not in seen:
                        seen.append(value)
            except Exception:
                pass
        m["incidents"] = seen[:100]

    except Exception as e:
        print("Detail error:", m.get("home"), "v", m.get("away"), e)


def refresh_nonfinished_details(d, matches):
    # Refresh every non-finished match from its own detail page.
    # This is intentionally broader than the old LIVE-only test because
    # the list page can incorrectly leave a just-started match at 0-0.
    for m in matches:
        if m["status"] != "FINISHED":
            match_detail(d, m)

def save_cycle(d):
    matches=all_matches(d)
    refresh_nonfinished_details(d, matches)
    OUT.write_text(
        json.dumps(
            {
                "updated":datetime.now(SA).strftime("%Y-%m-%d %H:%M:%S SAST"),
                "matches":matches
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )
    return len(matches)

def main():
    d=driver()
    try:
        count=save_cycle(d)
        print(datetime.now(SA).strftime("%H:%M:%S"), "Saved", count, "matches")
        print("Flashscore read completed. Exiting.")
    finally:
        d.quit()


if __name__=="__main__":main()
