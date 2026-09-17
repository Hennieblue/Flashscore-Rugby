import json,re,time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL="https://www.flashscore.co.za/rugby-union/"; OUT=Path(__file__).with_name("data.json"); SA=ZoneInfo("Africa/Johannesburg")
def clean(v): return re.sub(r"\s+"," ",v or "").strip()
def driver():
 o=webdriver.ChromeOptions()
 for a in ("--headless=new","--window-size=1920,1080","--disable-notifications","--disable-popup-blocking","--disable-gpu","--no-sandbox","--disable-dev-shm-usage","--lang=en-ZA"): o.add_argument(a)
 d=webdriver.Chrome(options=o);d.set_page_load_timeout(60);return d
def cookie(d):
 for sel in ("#onetrust-accept-btn-handler","button[id*='accept']","button[class*='accept']"):
  try:
   for b in d.find_elements(By.CSS_SELECTOR,sel):
    if b.is_displayed(): d.execute_script("arguments[0].click()",b);return
  except Exception: pass
def scroll(d):
 for _ in range(12): d.execute_script("window.scrollBy(0,900)");time.sleep(.35)
 d.execute_script("window.scrollTo(0,0)")
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
def status_from(value,score):
 low=value.lower()
 if low=="ft" or any(x in low for x in ("finished","after extra time","after penalties")):return "FINISHED"
 if any(x in low for x in ("postponed","cancelled","walkover")):return value.upper()
 if re.search(r"\d{1,3}\s*'",value) or any(x in low for x in ("1st half","2nd half","half time","break")):return "LIVE"
 return "UPCOMING" if not score else "LIVE"
def match_list(d):
 d.get(URL)
 try:WebDriverWait(d,25).until(EC.presence_of_element_located((By.CSS_SELECTOR,"a.eventRowLink,div.event__match,[data-testid='wcl-matchRow']")))
 except Exception:pass
 time.sleep(2);cookie(d);scroll(d);out=[];seen=set()
 for row in rows(d):
  try:
   u=href(row);names=participants(row)
   if "/match/" not in u or len(names)<2 or u.split("#")[0] in seen:continue
   seen.add(u.split("#")[0]);tm=text(row,[".event__time","[class*='event__time']","[data-testid*='time']"])
   hs=text(row,[".event__score--home","[class*='event__score--home']"]);aws=text(row,[".event__score--away","[class*='event__score--away']"])
   score=f"{hs} - {aws}" if hs and aws else "0 - 0";status=status_from(tm,score if hs and aws else "")
   out.append({"home":names[0],"away":names[1],"time":tm,"score":score,"status":status,"url":u,"incidents":[]})
  except Exception:pass
 return out
def live_detail(d,m):
 if m["status"]!="LIVE":return
 try:
  d.get(m["url"]);time.sleep(2);seen=[]
  for s in ("div.smv__incident","[class*='smv__incident']","[data-testid*='incident']"):
   for e in d.find_elements(By.CSS_SELECTOR,s):
    v=clean(e.text)
    if v and v not in seen:seen.append(v)
  m["incidents"]=seen[:100]
  detail=text(d,[".detailScore__wrapper","[class*='detailScore__wrapper']"])
  nums=re.findall(r"\b\d{1,3}\b",detail)
  if len(nums)>=2:m["score"]=f"{nums[0]} - {nums[1]}"
 except Exception:pass
def main():
 d=driver()
 try:
  matches=match_list(d)
  for m in matches:live_detail(d,m)
  OUT.write_text(json.dumps({"updated":datetime.now(SA).strftime("%Y-%m-%d %H:%M:%S SAST"),"matches":matches},ensure_ascii=False,indent=2),encoding="utf-8")
  print(f"Saved {len(matches)} matches")
 finally:d.quit()
if __name__=="__main__":main()
