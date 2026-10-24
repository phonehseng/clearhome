"""Pull housing records from public open-data APIs into a review queue.

Nothing fetched here is shown to users until a teammate approves it with
backend/review.py. All sources are official open-data services that need no key.

Run:  python backend/sources.py            # refresh every source (skips ones refreshed in the last 24 hours)
      python backend/sources.py --force    # refresh now
"""
import argparse
import json
import re
import threading
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
CANDIDATES_PATH = DATA / "candidates.json"
RESOURCES_PATH = DATA / "resources.json"
MAX_AGE = timedelta(hours=24)
_lock = threading.Lock()

HUD = "https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/{}/FeatureServer/0"
# Northern Virginia county/city FIPS codes. The LIHTC layer drops the leading zero
# for Fairfax County and Arlington, so both spellings are included.
NOVA_FIPS = {
    "059": "Fairfax County", "59": "Fairfax County", "600": "Fairfax City", "610": "Falls Church City",
    "013": "Arlington County", "13": "Arlington County", "510": "Alexandria City", "107": "Loudoun County",
    "153": "Prince William County", "683": "Manassas City", "685": "Manassas Park City",
}
HUD_WHERE = "STATE2KX='51' AND CNTY2KX IN ({})".format(",".join(f"'{c}'" for c in NOVA_FIPS))

SOURCES = {
    "hud_lihtc": {
        "label": "HUD Low-Income Housing Tax Credit database",
        "layer": HUD.format("LIHTC"),
        "where": HUD_WHERE,
    },
    "hud_multifamily": {
        "label": "HUD Multifamily Assisted Properties",
        "layer": HUD.format("MULTIFAMILY_PROPERTIES_ASSISTED"),
        "where": HUD_WHERE,
    },
    "hud_pha": {
        "label": "HUD Public Housing Authorities",
        "layer": HUD.format("Public_Housing_Authorities"),
        "where": HUD_WHERE,
    },
    "alexandria_affordable": {
        "label": "City of Alexandria Committed and Affordable Rentals",
        "layer": "https://services2.arcgis.com/ChYV69FhfjwkvRmy/arcgis/rest/services/Committed_and_Affordable_Rentals/FeatureServer/20",
        "where": "1=1",
    },
    "nvrc_shelters": {
        "label": "Northern Virginia Regional Commission homeless shelter map",
        "layer": "https://services5.arcgis.com/6MUPhDX27Ne3DNOw/arcgis/rest/services/NOVA_Homeless_Shelters/FeatureServer/1",
        "where": "1=1",
    },
}

CITY_TO_JURISDICTION = {
    "alexandria": "Alexandria City", "arlington": "Arlington County", "falls church": "Falls Church City",
    "fairfax": "Fairfax County", "manassas park": "Manassas Park City", "manassas": "Manassas City",
    "leesburg": "Loudoun County", "sterling": "Loudoun County", "ashburn": "Loudoun County",
    "woodbridge": "Prince William County", "dumfries": "Prince William County", "triangle": "Prince William County",
}


def _get_json(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "ClearHouse-hackathon/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _clean(value):
    """Strip padding and drop HUD's negative 'suppressed' codes."""
    if isinstance(value, str):
        value = re.sub(r"\s+", " ", value).strip()
        return value or None
    if isinstance(value, (int, float)) and value < 0:
        return None
    return value


def _title(value):
    value = _clean(value)
    return value.title() if value and value.isupper() else value


def _phone(value):
    digits = re.sub(r"\D", "", str(value or ""))
    return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}" if len(digits) == 10 else _clean(value)


def _slug(*parts):
    return re.sub(r"[^a-z0-9]+", "-", " ".join(str(p) for p in parts if p).lower()).strip("-")


def _data_as_of(layer):
    """The date the publisher last edited the layer, so users know how fresh it is."""
    try:
        ms = _get_json(layer, {"f": "json"}).get("editingInfo", {}).get("lastEditDate")
        return datetime.fromtimestamp(ms / 1000, timezone.utc).date().isoformat() if ms else None
    except Exception:
        return None


def _base(origin, name, as_of, query_url):
    src = SOURCES[origin]
    return {
        "name": name,
        "region": "Northern Virginia",
        "state": "VA",
        "accessible": None,
        "source_url": query_url,
        "sources": [{"url": src["layer"], "role": "government"}],
        "origin": origin,
        "data_as_of": as_of,
        "verified": False,
        "verification_method": f"Imported from the {src['label']} open-data API (data as of {as_of or 'unknown'}); not yet reviewed by the team.",
        "last_verified": None,
    }


def _lihtc(a, as_of, url):
    name = _title(a.get("PROJECT"))
    targets = [label for key, label in (("TRGT_ELD", "seniors"), ("TRGT_DIS", "people with disabilities"), ("TRGT_HML", "people experiencing homelessness")) if str(a.get(key) or "").strip() in ("1", "Y")]
    beds = ", ".join(f"{a[k]} {label}" for k, label in (("N_0BR", "studio"), ("N_1BR", "1BR"), ("N_2BR", "2BR"), ("N_3BR", "3BR"), ("N_4BR", "4BR")) if _clean(a.get(k)))
    return {
        **_base("hud_lihtc", name, as_of, url),
        "id": "hud-lihtc-" + _slug(name, a.get("PROJ_ZIP")),
        "type": "affordable_property",
        "address": ", ".join(x for x in (_title(a.get("PROJ_ADD")), _title(a.get("PROJ_CTY")), "VA " + str(_clean(a.get("PROJ_ZIP")) or "")) if x).strip(", "),
        "city": _title(a.get("PROJ_CTY")),
        "jurisdiction": NOVA_FIPS.get(str(_clean(a.get("CNTY2KX")))) or _clean(a.get("CNTY_NM2KX")),
        "phone": _phone(a.get("CO_TEL")),
        "website": None,
        "who_it_serves": "Income-restricted apartments under the federal tax credit program"
                         + (f" ({_clean(a.get('LI_UNITS'))} of {_clean(a.get('N_UNITS'))} units)" if _clean(a.get("LI_UNITS")) else "")
                         + (f"; targets {', '.join(targets)}" if targets else "") + ".",
        "unit_mix": beds or None,
        "cost": None,
        "requirements": "Household income must be under the property's limit, usually 50-60% of area median income.",
        "how_to_apply": "1. Call the property or search its name to find the leasing office. 2. Ask if they have openings or a waitlist for income-restricted units. 3. Have proof of income and ID ready.",
        "notes": "Federal database record. The address can be outdated or list the owner's office; confirm before visiting.",
    }


def _multifamily(a, as_of, url):
    name = _title(a.get("PROPERTY_NAME_TEXT"))
    wait = _clean(a.get("MONTHS_WAITING"))
    return {
        **_base("hud_multifamily", name, as_of, url),
        "id": "hud-mf-" + _slug(name, a.get("STD_ZIP5")),
        "type": "affordable_property",
        "address": ", ".join(x for x in (_title(a.get("ADDRESS_LINE1_TEXT")), _title(a.get("PLACED_BASE_CITY_NAME_TEXT")), "VA " + str(_clean(a.get("STD_ZIP5")) or "")) if x),
        "city": _title(a.get("PLACED_BASE_CITY_NAME_TEXT")),
        "jurisdiction": NOVA_FIPS.get(str(_clean(a.get("CNTY2KX")))) or _clean(a.get("CNTY_NM2KX")),
        "phone": _phone(a.get("PROPERTY_ON_SITE_PHONE_NUMBER") or a.get("MGMT_CONTACT_MAIN_PHN_NBR")),
        "website": None,
        "who_it_serves": "HUD-subsidized apartments; rent is usually based on income"
                         + (f" ({_clean(a.get('TOTAL_ASSISTED_UNIT_COUNT'))} assisted units)" if _clean(a.get("TOTAL_ASSISTED_UNIT_COUNT")) else "")
                         + (f"; for {_clean(a.get('CLIENT_GROUP_NAME')).lower()}" if _clean(a.get("CLIENT_GROUP_NAME")) else "") + ".",
        "cost": "Usually about 30% of household income for assisted units.",
        "requirements": "Income limits apply; some properties serve only seniors or people with disabilities.",
        "how_to_apply": "1. Call the property's management office. 2. Ask to join the waitlist for an assisted unit. 3. Have proof of income and ID ready."
                        + (f" HUD reports an average wait of about {wait} months." if wait else ""),
        "notes": f"Managed by {_clean(a.get('MGMT_AGENT_ORG_NAME'))}." if _clean(a.get("MGMT_AGENT_ORG_NAME")) else None,
    }


def _pha(a, as_of, url):
    name = _title(a.get("FORMAL_PARTICIPANT_NAME"))
    return {
        **_base("hud_pha", name, as_of, url),
        "id": "hud-pha-" + _slug(a.get("PARTICIPANT_CODE") or name),
        "type": "housing_authority",
        "address": ", ".join(x for x in (_clean(a.get("STD_ADDR")), _clean(a.get("STD_CITY")), "VA " + str(_clean(a.get("STD_ZIP5")) or "")) if x),
        "city": _clean(a.get("STD_CITY")),
        "jurisdiction": NOVA_FIPS.get(str(_clean(a.get("CNTY2KX")))) or _clean(a.get("CNTY_NM2KX")),
        "phone": _phone(a.get("HA_PHN_NUM")),  # HUD lists a named staff email; deliberately not imported
        "website": None,
        "who_it_serves": "Runs Housing Choice Vouchers (Section 8)"
                         + (f" ({_clean(a.get('SECTION8_UNITS_CNT'))} vouchers)" if _clean(a.get("SECTION8_UNITS_CNT")) else "")
                         + " and other assistance for low-income households.",
        "cost": None,
        "requirements": "Income limits apply. Voucher waitlists open and close; check the authority's website for current status.",
        "how_to_apply": "1. Check the housing authority's website or call to ask whether the voucher waitlist is open. 2. Apply online or in person when it is. 3. Keep your contact details updated so you don't lose your place.",
        "notes": None,
    }


def _alexandria(a, as_of, url):
    name = _title(a.get("PROJECT_NAME"))
    ami = _clean(a.get("AMILEVELOFAFFORDABILITY"))
    website = _clean(a.get("Website"))
    return {
        **_base("alexandria_affordable", name, as_of, url),
        "id": "alx-" + _slug(name),
        "type": "affordable_property",
        "address": ", ".join(x for x in (_clean(a.get("ADDRESS")), "Alexandria, VA") if x),
        "city": "Alexandria",
        "jurisdiction": "Alexandria City",
        "phone": None,
        "website": website if website and website.startswith("https://") else None,
        "who_it_serves": "Committed affordable rentals"
                         + (f" ({_clean(a.get('COMMITTAFFORDABLE_COUNT'))} affordable units)" if _clean(a.get("COMMITTAFFORDABLE_COUNT")) else "")
                         + (f" for households at {ami} of area median income" if ami else "")
                         + ("; seniors only" if str(_clean(a.get("SENIORONLY")) or "").lower() in ("yes", "y", "1", "true") else "") + ".",
        "cost": None,
        "requirements": f"Income at or below {ami} of area median income." if ami else "Income limits apply.",
        "how_to_apply": "1. Visit the property website or the City of Alexandria's affordable rental list. 2. Ask the leasing office about openings or a waitlist for affordable units. 3. Have proof of income and ID ready.",
        "notes": f"City status: {_clean(a.get('STATUS'))}." if _clean(a.get("STATUS")) else None,
    }


def _nvrc_shelter(a, as_of, url):
    name = _clean(a.get("Name"))
    address = _clean(a.get("Full_Address"))
    city = next((j for c, j in CITY_TO_JURISDICTION.items() if address and c in address.lower()), None)
    website = _clean(a.get("Website"))
    return {
        **_base("nvrc_shelters", name, as_of, url),
        "id": "nvrc-" + _slug(name),
        "type": "emergency_shelter",
        "address": address,
        "city": None,
        "jurisdiction": city or "Northern Virginia",
        "phone": _phone(a.get("Phone")),
        "website": website if website and website.startswith("https://") else None,
        "who_it_serves": _clean(a.get("Populations_Served")) or "People experiencing homelessness.",
        "beds": _clean(a.get("Number_Beds")),
        "cost": "Free",
        "requirements": _clean(a.get("Minimum_Requirements")),
        "how_to_apply": _clean(a.get("Mean_of_Referral")) or "Call the local homeless services intake line first; most beds are assigned through it.",
        "notes": f"From a regional map last updated {as_of or 'on an unknown date'}. Call ahead: details may have changed.",
    }


BUILDERS = {"hud_lihtc": _lihtc, "hud_multifamily": _multifamily, "hud_pha": _pha,
            "alexandria_affordable": _alexandria, "nvrc_shelters": _nvrc_shelter}


def fetch(origin):
    src = SOURCES[origin]
    params = {"where": src["where"], "outFields": "*", "returnGeometry": "false", "f": "json"}
    url = src["layer"] + "/query?" + urllib.parse.urlencode(params)
    features = _get_json(url).get("features", [])
    as_of = _data_as_of(src["layer"])
    records = [BUILDERS[origin](f.get("attributes", {}), as_of, url) for f in features]
    return [r for r in records if r.get("name")]


def _load_queue():
    if CANDIDATES_PATH.exists():
        return json.loads(CANDIDATES_PATH.read_text())
    return {"refreshed": {}, "rejected": [], "candidates": []}


def refresh(force=False, origins=None):
    """Fetch sources older than MAX_AGE and add new records to the queue. Returns {origin: added}."""
    with _lock:
        queue = _load_queue()
        known = {r["id"] for r in queue["candidates"]} | set(queue["rejected"])
        live = json.loads(RESOURCES_PATH.read_text())
        known |= {r.get("id") for r in live}
        live_names = {str(r.get("name", "")).casefold() for r in live}
        added = {}
        now = datetime.now(timezone.utc)
        for origin in origins or SOURCES:
            last = queue["refreshed"].get(origin)
            if not force and last and now - datetime.fromisoformat(last) < MAX_AGE:
                continue
            try:
                records = fetch(origin)
            except Exception as e:
                added[origin] = f"failed: {e}"
                continue
            count = 0
            for r in records:
                if r["id"] in known:
                    continue
                if r["name"].casefold() in live_names:
                    r["notes"] = ((r.get("notes") or "") + " Possible duplicate of a record already in the catalog.").strip()
                queue["candidates"].append(r)
                known.add(r["id"])
                count += 1
            queue["refreshed"][origin] = now.isoformat()
            added[origin] = count
        CANDIDATES_PATH.write_text(json.dumps(queue, indent=2) + "\n")
        return added


def refresh_in_background():
    """Called on each search. Cheap when everything was refreshed recently."""
    threading.Thread(target=refresh, daemon=True).start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="refresh even if fetched in the last 24 hours")
    args = parser.parse_args()
    for origin, result in refresh(force=args.force).items():
        print(f"{origin}: {result}")
    print(f"Queue: {len(_load_queue()['candidates'])} candidates waiting for review in {CANDIDATES_PATH.name}")
