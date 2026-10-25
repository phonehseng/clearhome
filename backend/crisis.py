"""Crisis lines before anything else: someone who writes about suicide or self-harm, or about abuse at home, gets the
right hotline at once, with no AI and no waiting, plus buttons to call or text it.

Numbers were checked on 2026-10-25 against each line's own site: 988lifeline.org (call or text 988),
vsdvalliance.org/hotlines (Virginia Family Violence & Sexual Assault Hotline, also listed on dss.virginia.gov) and
thehotline.org (National Domestic Violence Hotline).
"""
import re

from advisor import Instant, area_for
from catalog import filter_catalog, load_catalog

SELF_HARM = re.compile(r"\b(?:suicid\w*|kill(?:ing)? my ?self|end(?:ing)? my (?:own )?life|end(?:ing)? it all|take my (?:own )?life|"
                       r"(?:want|wanna|going) to die|wish i (?:was|were) dead|better off dead|no reason to (?:live|go on)|"
                       r"self[- ]?harm\w*|hurt(?:ing)? my ?self|cut(?:ting)? my ?self)\b", re.I)
# Abuse by a person: a partner, family member or anyone at home. Not "substance abuse" or "drug abuse".
ABUSE = re.compile(r"\b(?:domestic (?:violence|abuse)|abusive(?! (?:landlord|property|manager|management|boss|employer))|abuser|being abused|abuses (?:me|us)|(?<!substance )(?<!drug )(?<!alcohol )abused|"
                   r"sexual(?:ly)? assault\w*|raped|stalk(?:ing|er|s me|ed)|(?:restraining|protective) order|"
                   r"(?:beat|beats|beating|hit|hits|hitting|hurts|chok\w+|punch\w*|slap\w*|threaten\w*) (?:me|us|my (?:kids?|children|baby|son|daughter))(?! (?:up|with|back|to it))|"
                   r"(?:afraid|scared|terrified) of (?:him|her|my (?:partner|boyfriend|girlfriend|husband|wife|spouse|ex|dad|mom|father|mother|parents?))|"
                   r"fle(?:e|eing|d) (?:from )?(?:him|her|abuse|violence|my (?:partner|boyfriend|girlfriend|husband|wife|spouse|ex|abuser)))\b", re.I)

LIFELINE = [{"label": "Call 988", "href": "tel:988"}, {"label": "Text 988", "href": "sms:988"}, {"label": "Emergency: 911", "href": "tel:911"}]
ABUSE_LINES = [{"label": "Call the Virginia hotline", "href": "tel:+18008388238"}, {"label": "Text 804-793-9999", "href": "sms:+18047939999"},
               {"label": "Call 1-800-799-7233", "href": "tel:+18007997233"}, {"label": "Emergency: 911", "href": "tel:911"}]

SELF_HARM_TEXT = ("I'm really glad you told me. You don't have to go through this alone. Call or text **988**, the Suicide & Crisis "
                  "Lifeline: it's free, confidential and open any time. If you might act on these thoughts right now, call **911**.\n\n"
                  "When you're ready, I can also help you find a safe place to stay.")
ABUSE_TEXT = ("You deserve to be safe. If you're in danger right now, call **911**.\n\n"
              "For confidential help any time, the **Virginia Family Violence & Sexual Assault Hotline** is free and open 24/7: "
              "call 1-800-838-8238 or text 804-793-9999. The **National Domestic Violence Hotline** is 1-800-799-7233, or text START to 88788.\n\n"
              "They can connect you with a domestic violence shelter (those keep their addresses private, so the hotline is the way in) "
              "and help you plan how to leave safely. If someone checks your phone or computer, a private browsing window keeps this page "
              "out of your history.")
ASK_WHERE = "When you're ready, tell me the city or county and I'll show housing help there."


class Lifeline(Instant):
    """A crisis answer: the hotline text plus the call and text buttons the page shows under it."""
    engine = "Clear Home safety lines (instant, no AI)"
    lines = ()


def local_line(area):
    """The county or city's own 24-hour domestic violence hotline from our verified list (Fairfax, Arlington, Alexandria), or None."""
    return next((r for r in filter_catalog(load_catalog()) if r.get("jurisdiction") == area and r.get("phone")
                 and re.search(r"domestic", r.get("name") or "", re.I) and re.search(r"hotline", r.get("name") or "", re.I)), None)


def answer(text, location=None):
    """The crisis answer for these words (self-harm first, then abuse, or both), or None. A county or city named in the
    message (or the find form's location) adds that area's own hotline, and the answer doesn't ask where again."""
    harm, abuse = bool(SELF_HARM.search(text or "")), bool(ABUSE.search(text or ""))
    if not (harm or abuse):
        return None
    parts, buttons = [], []
    if harm:
        parts.append(SELF_HARM_TEXT)
        buttons += LIFELINE[:2]
    if abuse:
        area = next((a for a in (area_for(text), location and area_for(location)) if a and a != "Northern Virginia"), None)
        local = local_line(area) if area else None
        digits = re.sub(r"\D", "", local["phone"]) if local else ""
        parts.append(ABUSE_TEXT)
        if local:
            parts.append(f"In {area}, the local 24-hour line is **{local['name']}**: {local['phone']}.")
        parts.append(f"When you're ready, I can show housing help in {area} too." if area else ASK_WHERE)
        buttons += ABUSE_LINES[:1] + ([{"label": f"Call {local['phone']}", "href": f"tel:+1{digits}"}] if len(digits) == 10 else []) + ABUSE_LINES[1:3]
    reply = Lifeline("\n\n".join(parts))
    reply.lines = buttons + [LIFELINE[2]]
    return reply
