"""Create monthly synthetic review fixtures without running a translation model.

Run ``python3 backend/seed_reviews.py`` from any directory. The English fixture
and offline browser fixture contain 15 demo reviews for every month of 2026,
including future months. The persisted store is only topped up to 15 per month;
existing reviews, including months already above that target, are preserved.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
from tempfile import NamedTemporaryFile


YEAR = 2026
REVIEWS_PER_MONTH = 15
ROOT = Path(__file__).resolve().parent.parent

# Pretranslated Kiswahili counterparts for the original English sample set.
# These are fixtures, so seeding needs neither the model nor network access.
TRANSLATIONS = {
    "The guide was friendly and very knowledgeable.": (
        "Mwongoza watalii alikuwa mwenye urafiki na maarifa mengi.",
        "Ziara ingeweza kujumuisha mapumziko mafupi.",
    ),
    "I loved learning about the history of the old town.": (
        "Nilifurahia kujifunza historia ya mji wa kale.",
        "Kundi lilikuwa kubwa kidogo.",
    ),
    "The views from the lookout were incredible.": (
        "Mandhari kutoka sehemu ya kutazamia yalikuwa ya kuvutia sana.",
        "Muda zaidi wa kupiga picha ungekuwa mzuri.",
    ),
    "The local food tasting was delicious.": (
        "Vyakula vya wenyeji tulivyoonja vilikuwa vitamu.",
        "Sehemu ya kukutana ilikuwa ngumu kuipata.",
    ),
    "The guide shared fascinating stories about the community.": (
        "Mwongoza watalii alisimulia hadithi za kuvutia kuhusu jamii.",
        "Ziara inapaswa kuanza mapema kidogo.",
    ),
    "The walking route showed us places we would not have found alone.": (
        "Njia ya matembezi ilituonyesha maeneo ambayo tusingeyapata wenyewe.",
        "Tafadhali tupatie maelezo ya njia kabla ya ziara.",
    ),
    "I enjoyed meeting local artists at the market.": (
        "Nilifurahia kukutana na wasanii wa eneo hilo sokoni.",
        "Sauti ya mfumo wa sauti ingeweza kuongezwa.",
    ),
    "The museum collection was interesting.": (
        "Vitu vilivyoonyeshwa katika jumba la makumbusho vilivutia.",
        "Ziara iliharakishwa na ilianza kuchelewa.",
    ),
    "Our guide made the entire experience fun for the children.": (
        "Mwongoza watalii wetu aliifanya ziara nzima iwafurahishe watoto.",
        "Punguzo kwa familia lingependeza.",
    ),
    "The sunset over the river was beautiful.": (
        "Mandhari ya jua likitua juu ya mto yalikuwa mazuri.",
        "Maelekezo kuhusu sehemu ya kuchukuliwa na usafiri yawe wazi zaidi.",
    ),
    "The cooking demonstration was personal and engaging.": (
        "Onyesho la upishi lilitushirikisha na lilivutia.",
        "Ningependa kupewa maelekezo ya mapishi yaliyochapishwa.",
    ),
    "The cultural explanations were thoughtful.": (
        "Maelezo kuhusu utamaduni yalitolewa kwa makini.",
        "Kunapaswa kuwa na sehemu zaidi za kukaa njiani.",
    ),
    "The wildlife walk gave us several great sightings.": (
        "Matembezi ya kutazama wanyamapori yalituwezesha kuona wanyama wengi.",
        "Kila mgeni anapaswa kupewa darubini.",
    ),
    "The guide answered every question with patience.": (
        "Mwongoza watalii alijibu kila swali kwa uvumilivu.",
        "Hakuna jambo kubwa linalohitaji kuboreshwa.",
    ),
    "The architecture tour was informative and well organized.": (
        "Ziara ya majengo ilikuwa na maelezo mengi na ilipangwa vizuri.",
        "Ramani ya njia ingekuwa na manufaa.",
    ),
    "The waterfall hike was challenging but rewarding.": (
        "Matembezi ya kuelekea maporomoko ya maji yalikuwa magumu lakini yalifurahisha.",
        "Tafadhali elezeni kwa uwazi zaidi kiwango cha ugumu wa matembezi.",
    ),
    "I enjoyed the visit to the community garden.": (
        "Nilifurahia kutembelea bustani ya jamii.",
        "Ziara ilihitaji mpangilio bora kati ya vituo.",
    ),
    "The music performance was the highlight of our evening.": (
        "Onyesho la muziki lilikuwa jambo bora zaidi jioni yetu.",
        "Mpangilio wa viti ungeweza kuwa wa kustarehesha zaidi.",
    ),
    "The guide was welcoming and made us feel safe.": (
        "Mwongoza watalii alitukaribisha vizuri na alitufanya tujisikie salama.",
        "Maelezo mafupi kuhusu usalama mwanzoni yangesaidia.",
    ),
    "The market tour gave us a great taste of local life.": (
        "Ziara ya soko ilitupa nafasi nzuri ya kujionea maisha ya wenyeji.",
        "Chaguo zaidi za vyakula visivyo na nyama zingekuwa nzuri.",
    ),
    "The photography stops were perfectly chosen.": (
        "Sehemu za kusimama kupiga picha zilichaguliwa vizuri sana.",
        "Ziara ingeweza kutoa huduma ya mpiga picha mtaalamu.",
    ),
    "The historic building was impressive.": (
        "Jengo la kihistoria lilivutia sana.",
        "Mwongoza watalii anapaswa kuzungumza polepole na kutumia kipaza sauti.",
    ),
    "I appreciated the small group size.": (
        "Nilipenda jinsi kundi letu lilivyokuwa dogo.",
        "Barua pepe ya uthibitisho inapaswa kujumuisha maelezo ya maegesho.",
    ),
    "The river cruise was relaxing and scenic.": (
        "Safari ya mashua mtoni ilikuwa ya kustarehesha na yenye mandhari mazuri.",
        "Sehemu zaidi za kivuli kwenye mashua zingesaidia.",
    ),
    "The craft workshop was creative and enjoyable.": (
        "Warsha ya ufundi ilikuwa ya ubunifu na ya kufurahisha.",
        "Vifaa viliisha kabla ya kila mtu kumaliza.",
    ),
    "The neighborhood history was presented in an engaging way.": (
        "Historia ya eneo hilo ilisimuliwa kwa njia ya kuvutia.",
        "Ziara inapaswa kujumuisha picha zaidi za kihistoria.",
    ),
    "The beach was peaceful and the guide was excellent.": (
        "Ufukwe ulikuwa mtulivu na mwongoza watalii alikuwa bora sana.",
        "Tafadhali toeni chupa za maji zinazoweza kutumika tena.",
    ),
    "The botanical garden had an amazing variety of plants.": (
        "Bustani ya mimea ilikuwa na aina nyingi za mimea ya kuvutia.",
        "Majina ya mimea yangeweza kuonyeshwa kwa uwazi zaidi.",
    ),
    "The storytelling made the legends feel alive.": (
        "Usimulizi wa hadithi ulifanya masimulizi ya kale yaonekane halisi.",
        "Kijitabu kifupi cha hadithi kingekuwa kumbukumbu nzuri.",
    ),
    "The local snacks were my favorite part.": (
        "Vitafunio vya wenyeji vilikuwa sehemu niliyoipenda zaidi.",
        "Ziara inapaswa kutoa muda zaidi katika vituo vya chakula.",
    ),
    "The cycling route was scenic and enjoyable.": (
        "Njia ya baiskeli ilikuwa na mandhari mazuri na ilifurahisha.",
        "Baiskeli zinahitaji viti vya kustarehesha zaidi.",
    ),
    "The guide gave excellent recommendations for the rest of our trip.": (
        "Mwongoza watalii alitupa mapendekezo mazuri kwa sehemu iliyobaki ya safari yetu.",
        "Orodha ya mapendekezo baada ya ziara ingekuwa na manufaa.",
    ),
    "The small historical sites were hidden gems.": (
        "Maeneo madogo ya kihistoria yalikuwa hazina zilizofichika.",
        "Njia inapaswa kujumuisha mapumziko zaidi ya kutumia vyoo.",
    ),
    "The final viewpoint was beautiful.": (
        "Mandhari katika kituo cha mwisho cha kutazamia yalikuwa mazuri.",
        "Ziara ilifutwa dakika za mwisho na ile mbadala ilipangwa vibaya.",
    ),
    "The community members were generous and welcoming.": (
        "Wanajamii walikuwa wakarimu na wenye ukarimu kwa wageni.",
        "Ningefurahia mazungumzo marefu zaidi na wenyeji.",
    ),
    "The sunset photography session was memorable.": (
        "Kipindi cha kupiga picha wakati wa machweo kilikuwa cha kukumbukwa.",
        "Tafadhali tutumieni taarifa za hali ya hewa kabla ya kipindi hicho.",
    ),
    "The guide had a great sense of humor.": (
        "Mwongoza watalii alikuwa mcheshi sana.",
        "Ratiba ya safari inapaswa kuelezwa mwanzoni.",
    ),
    "The tour gave us a meaningful connection to the local culture.": (
        "Ziara ilitupa uhusiano wa maana na utamaduni wa wenyeji.",
        "Tafadhali pangeni ziara hii katika siku zaidi.",
    ),
    "The forest walk was calm and beautiful.": (
        "Matembezi msituni yalikuwa ya utulivu na yenye mandhari mazuri.",
        "Maelezo zaidi kuhusu mimea ya eneo hilo yangependeza.",
    ),
    "The guide remembered everyone's name and made the group feel connected.": (
        "Mwongoza watalii alikumbuka jina la kila mtu na aliunganisha kundi vizuri.",
        "Utaratibu wa kujiandikisha ungeweza kuwa wa haraka zaidi.",
    ),
    "The traditional dance performance was vibrant and exciting.": (
        "Onyesho la ngoma za jadi lilikuwa lenye nguvu na la kusisimua.",
        "Mwonekano kutoka sehemu ya nyuma ya ukumbi ungeweza kuboreshwa.",
    ),
    "The boat ride offered a different view of the city.": (
        "Safari ya mashua ilitupa mandhari tofauti ya jiji.",
        "Injini ya mashua ilikuwa na kelele wakati maelezo yalipotolewa.",
    ),
    "The tour was accessible and the staff were considerate.": (
        "Ziara ilikuwa rahisi kufikiwa na wafanyakazi walijali mahitaji yetu.",
        "Tafadhali chapisheni maelezo ya ufikivu mapema.",
    ),
    "The handmade souvenir was a lovely reminder of the visit.": (
        "Zawadi iliyotengenezwa kwa mikono ilikuwa kumbukumbu nzuri ya ziara.",
        "Miundo zaidi ya zawadi za kumbukumbu ingependeza.",
    ),
    "Every stop was interesting and the pacing was excellent.": (
        "Kila kituo kilivutia na kasi ya ziara ilikuwa nzuri sana.",
        "Ziara ilikuwa nzuri sana ilivyokuwa.",
    ),
    "The guide explained the traditions respectfully.": (
        "Mwongoza watalii alieleza mila kwa heshima.",
        "Kipeperushi chenye tafsiri kingewasaidia wageni wa kimataifa.",
    ),
    "The evening atmosphere and live music were wonderful.": (
        "Mazingira ya jioni na muziki wa moja kwa moja vilikuwa vizuri sana.",
        "Hafla ingeweza kuwa na meza zaidi.",
    ),
    "The destination itself was worth visiting.": (
        "Eneo tulilofika lilistahili kutembelewa.",
        "Ratiba ilibadilishwa bila taarifa ya kutosha.",
    ),
    "The guide gave us a detailed explanation of the local ecosystem.": (
        "Mwongoza watalii alitupa maelezo ya kina kuhusu mfumo wa ikolojia wa eneo hilo.",
        "Njia ingeweza kuwa na alama zilizo wazi zaidi.",
    ),
    "The experience felt authentic rather than touristy.": (
        "Ziara ilitupa uzoefu halisi wa maisha ya wenyeji.",
        "Ningependa chaguo la kundi dogo zaidi.",
    ),
}


def build_demo_reviews(source: list[dict]) -> tuple[list[dict], list[dict]]:
    """Preserve the English samples and fill each month with deterministic demos."""
    expanded = list(source)
    templates = {review["favorite"]: review for review in source}
    missing = TRANSLATIONS.keys() - templates.keys()
    if missing:
        raise ValueError(f"Original sample reviews are missing: {sorted(missing)}")
    templates = [templates[text] for text in TRANSLATIONS]
    counts = Counter(review["date"][:7] for review in source)
    for month in range(1, 13):
        prefix = f"{YEAR}-{month:02d}"
        used_dates = {review["date"] for review in expanded if review["date"].startswith(prefix)}
        # Use spaced days first; all these dates are valid even in February.
        days = list(range(1, 29, 2)) + list(range(2, 29, 2))
        available_days = [day for day in days if f"{prefix}-{day:02d}" not in used_dates]
        for slot in range(max(0, REVIEWS_PER_MONTH - counts[prefix])):
            template = templates[((month - 1) * 13 + slot * 7) % len(templates)]
            expanded.append({
                "rating": template["rating"],
                "language": "en",
                "date": date(YEAR, month, available_days[slot]).isoformat(),
                "favorite": template["favorite"],
                "improvement": template["improvement"],
                "is_demo": True,
            })

    translated = []
    for review in expanded:
        favorite, improvement = TRANSLATIONS[review["favorite"]]
        translated.append({
            "rating": review["rating"],
            "language": "sw",
            "date": review["date"],
            "favorite": favorite,
            "improvement": improvement,
            "original_favorite": review["favorite"],
            "original_improvement": review["improvement"],
            "is_demo": True,
        })
    return expanded, translated


def review_key(review: dict) -> tuple:
    """Match seeds by their original content, date and rating, ignoring metadata."""
    return (
        review["date"], review["rating"],
        review.get("original_favorite") or review["favorite"],
        review.get("original_improvement") or review["improvement"],
    )


def top_up_store(stored: list[dict], demos: list[dict]) -> list[dict]:
    """Append only enough new demos to reach the monthly minimum."""
    result = list(stored)
    counts = Counter(review["date"][:7] for review in stored)
    seen = {review_key(review) for review in stored}
    for review in demos:
        month = review["date"][:7]
        key = review_key(review)
        if counts[month] < REVIEWS_PER_MONTH and key not in seen:
            result.append(review)
            seen.add(key)
            counts[month] += 1
    return result


def json_text(value: list[dict]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
        file.write(content)
        temporary_path = Path(file.name)
    temporary_path.replace(path)
    return True


def seed_reviews(source_path: Path, storage_path: Path, frontend_path: Path, *, check: bool = False) -> dict:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    stored = json.loads(storage_path.read_text(encoding="utf-8")) if storage_path.exists() else []
    expanded, demos = build_demo_reviews(source)
    updated = top_up_store(stored, demos)
    frontend = (
        "// Generated by backend/seed_reviews.py. Synthetic examples for every month of 2026,\n"
        "// including future months. Only used until a populated backend store is available.\n"
        "const DEMO_REVIEWS = " + json_text(demos).rstrip() + ";\n"
    )
    outputs = {
        source_path: json_text(expanded),
        storage_path: json_text(updated),
        frontend_path: frontend,
    }
    if check:
        stale = [str(path) for path, content in outputs.items()
                 if not path.exists() or path.read_text(encoding="utf-8") != content]
        if stale:
            raise ValueError(f"Run backend/seed_reviews.py to update: {', '.join(stale)}")
    else:
        for path, content in outputs.items():
            write_if_changed(path, content)
    return {
        "demo_reviews": len(demos),
        "stored_reviews": len(updated),
        "added_to_store": len(updated) - len(stored),
        "stored_months": dict(sorted(Counter(review["date"][:7] for review in updated).items())),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate fixtures without writing files.")
    args = parser.parse_args()
    result = seed_reviews(
        ROOT / "backend" / "reviews.json",
        ROOT / "backend" / "translated_reviews.json",
        ROOT / "frontend" / "demo-reviews.js",
        check=args.check,
    )
    print(json.dumps(result, indent=2))
