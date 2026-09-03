import json, re, sys, hashlib
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparse

ROOT = Path(__file__).resolve().parents[1]
UA = "Mozilla/5.0 (compatible; SouthFloridaEventsRadar/1.0; +GitHubActions)"

def load_json(path, default):
    p=ROOT/path
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def save_json(path, data):
    (ROOT/path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def flatten_jsonld(obj):
    if isinstance(obj, list):
        for x in obj: yield from flatten_jsonld(x)
    elif isinstance(obj, dict):
        if "@graph" in obj: yield from flatten_jsonld(obj["@graph"])
        yield obj

def text(v):
    if isinstance(v, dict):
        return v.get("name") or v.get("@value") or ""
    return str(v or "")

def parse_when(v):
    if not v: return None
    try: return dtparse.parse(str(v))
    except Exception: return None

def normalize_event(raw, source, page_url, county):
    typ=raw.get("@type")
    types=typ if isinstance(typ,list) else [typ]
    if not any(str(t).lower()=="event" or str(t).lower().endswith("event") for t in types):
        return None
    name=text(raw.get("name")).strip()
    start=parse_when(raw.get("startDate"))
    if not name or not start: return None

    loc=raw.get("location") or {}
    venue=""
    city=source.get("default_city","")
    if isinstance(loc,dict):
        venue=text(loc.get("name")).strip()
        addr=loc.get("address") or {}
        if isinstance(addr,dict):
            city=text(addr.get("addressLocality")).strip() or city

    offers=raw.get("offers")
    cost="Check source"
    url=raw.get("url") or page_url
    if isinstance(offers,list) and offers:
        offers=offers[0]
    if isinstance(offers,dict):
        price=offers.get("price")
        cur=offers.get("priceCurrency","USD")
        url=offers.get("url") or url
        if price not in (None,""):
            cost=f"{cur} {price}"
        elif str(offers.get("availability","")).lower().find("free")>=0:
            cost="Free"

    desc=text(raw.get("description"))
    category="Event"
    low=(name+" "+desc).lower()
    categories=[
      ("Comedy","comedy"),("Sports","sport"),("Concert / Music","concert"),
      ("Concert / Music","music"),("Nightlife / Party","nightclub"),
      ("Nightlife / Party","party"),("Festival","festival"),("Food / Dining","food"),
      ("Art / Museum","museum"),("Art / Museum","art"),("Family","family"),
      ("Market","market")
    ]
    for label,needle in categories:
        if needle in low:
            category=label; break

    return {
      "date": start.strftime("%Y-%m-%d"),
      "time": start.strftime("%-I:%M %p") if sys.platform != "win32" else start.strftime("%I:%M %p").lstrip("0"),
      "name": name,
      "venue": venue or source["name"],
      "city": city,
      "category": category,
      "cost": cost,
      "url": urljoin(page_url, str(url)),
      "source": source["name"],
      "age": "",
      "featured": False,
      "new": True
    }

def scrape_source(source, county, target_year, target_month):
    try:
        r=requests.get(source["url"],headers={"User-Agent":UA},timeout=25)
        r.raise_for_status()
    except Exception as e:
        print(f"WARN {source['name']}: {e}")
        return []
    soup=BeautifulSoup(r.text,"html.parser")
    found=[]
    for tag in soup.find_all("script",{"type":"application/ld+json"}):
        try: data=json.loads(tag.string or tag.get_text() or "{}")
        except Exception: continue
        for obj in flatten_jsonld(data):
            ev=normalize_event(obj,source,source["url"],county)
            if not ev: continue
            d=parse_when(ev["date"])
            if d and d.year==target_year and d.month==target_month:
                found.append(ev)
    print(f"{source['name']}: {len(found)} structured events")
    return found

def key(e):
    def n(s): return re.sub(r"\W+","",str(s).lower())
    return (e.get("date",""), n(e.get("name","")), n(e.get("venue","")))

def merge(existing, discovered):
    out={key(e):e for e in existing}
    for e in discovered:
        k=key(e)
        if k in out:
            old=out[k]
            # Preserve hand-curated richer fields, but refresh URL/time/cost when discovered.
            for field in ["time","url","cost","source","city","venue"]:
                if e.get(field) and e[field] not in ("Check source",""):
                    old[field]=e[field]
            old["new"]=False
        else:
            out[k]=e
    return sorted(out.values(),key=lambda e:(e.get("date",""),e.get("time",""),e.get("name","")))

def main():
    now=datetime.now()
    year,month=now.year,now.month
    sources=load_json("sources.json",{})
    for county, srcs in sources.items():
        filename="broward-events.json" if county=="broward" else "miami-events.json"
        existing=load_json(filename,[])
        discovered=[]
        for s in srcs:
            discovered.extend(scrape_source(s,county,year,month))
        merged=merge(existing,discovered)
        save_json(filename,merged)
        print(f"{county}: {len(existing)} -> {len(merged)} events")

if __name__=="__main__":
    main()
