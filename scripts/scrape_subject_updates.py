#!/usr/bin/env python3
"""
Scrape subject updates from the MIT EECS website.

The subject-updates pages list special-topics subjects (6.S9xx and friends)
that the Fireroad API does not carry until they get a permanent number.
This parses the page for one term and writes the ML-relevant subset to
data/subject_updates_<term>.json in the same shape as course_data.json.
"""
import html
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

# Subject update URLs by semester.
# MIT term codes: Fall 2026 = 2027FA, Spring 2026 = 2026SP (academic-year naming).
SUBJECT_UPDATE_URLS = {
    "fall_2026": "https://eecsis.mit.edu/plugins/subj_2027FA.html",
    "spring_2026": "https://eecsis.mit.edu/plugins/subj_2026SP.html",
}

# Term to scrape, and the file suffix it is written under.
TERM = "fall_2026"
TERM_SUFFIX = "fa26"

# Words that mark a subject as ML-relevant enough for the tree.
ML_KEYWORDS = [
    "machine learning",
    "machine-learning",
    "deep learning",
    "neural network",
    "reinforcement learning",
    "artificial intelligence",
    "generative ai",
    "large language model",
    "llm",
    "foundation model",
    "transformer",
    "computer vision",
    "natural language",
    "statistical learning",
    "learning agents",
    "learning-theoretic",
    "learning through human feedback",
]

# Subjects that trip the keyword filter but are not ML subjects.
EXCLUDE = {
    "6.S964",  # Electric Energy Markets; mentions ML/AI only in passing
}

# Subjects to keep even if the keyword filter misses them.
INCLUDE = set()


def fetch_subject_updates(url: str) -> str:
    """Fetch HTML content from a subject updates page."""
    print(f"Fetching from {url}...")

    req = urllib.request.Request(url, headers={"User-Agent": "MLCoursesTree/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"Error fetching data: {e}")
        return ""


def clean(text: str) -> str:
    """Unescape entities and collapse whitespace."""
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def parse_heading(heading: str) -> tuple:
    """
    Split a subject heading into course numbers and title.

    Headings look like "6.S951 AI for Science: ..." or
    "NEW 6.3930/2  AI and Decision Making in Medicine: ... (was 6.S043/6.S983)".
    A trailing "/N" is shorthand for a sibling number sharing the same stem.
    """
    heading = re.sub(r"^\s*NEW\s+", "", heading)

    match = re.match(r"^(\d+[A-Z]*\.[A-Z]?\d+(?:\s*/\s*[A-Z]?\d+)*)\s+(.+)$", heading)
    if not match:
        return [], ""

    numbers_raw, title = match.group(1), match.group(2).strip()
    parts = [p.strip() for p in numbers_raw.split("/")]
    primary = parts[0]
    stem = primary[: primary.rindex(".") + 1]

    numbers = [primary]
    for part in parts[1:]:
        # "6.3930/2" means 6.3932: the suffix replaces the primary's tail.
        if "." in part:
            numbers.append(part)
        else:
            base = primary.split(".", 1)[1]
            numbers.append(stem + base[: len(base) - len(part)] + part)

    return numbers, title


def parse_units(units_raw: str) -> int:
    """Turn "3-0-9", "12 units (3-1.5-7.5)", or "12" into a total unit count."""
    triple = re.search(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", units_raw)
    if triple:
        return round(sum(float(g) for g in triple.groups()))

    plain = re.search(r"\d+", units_raw)
    return int(plain.group(0)) if plain else 12


def parse_page(page_html: str) -> list:
    """Parse a subject updates page into a list of course dicts."""
    courses = []

    # Each subject is a block introduced by a wp-block-separator rule.
    blocks = re.split(r'<hr class="wp-block-separator[^>]*/>', page_html)[1:]

    for block in blocks:
        heading_match = re.search(r"<h6[^>]*>(.*?)<a href", block, re.DOTALL)
        if not heading_match:
            continue

        numbers, title = parse_heading(clean(heading_match.group(1)))
        if not numbers:
            continue

        fields = {
            clean(key): clean(value)
            for key, value in re.findall(r"<td>([^<]*?):</td>\s*<td[^>]*>(.*?)</td>", block, re.DOTALL)
        }

        desc_match = re.search(r'<div style="white-space: pre-line;">(.*?)</div>', block, re.DOTALL)
        description = clean(desc_match.group(1)) if desc_match else ""

        # "Undergraduate and Graduate" subjects are listed as U, matching Fireroad.
        level = "U" if fields.get("Level", "").startswith("Undergraduate") else "G"

        courses.append({
            "course_numbers": numbers,
            "title": title,
            "description": description,
            "instructors": fields.get("Instructors", ""),
            "level": level,
            "units": parse_units(fields.get("Units", "")),
        })

    return courses


def is_ml_relevant(course: dict) -> bool:
    """Keep subjects whose title or description reads as machine learning."""
    if any(num in EXCLUDE for num in course["course_numbers"]):
        return False
    if any(num in INCLUDE for num in course["course_numbers"]):
        return True

    text = (course["title"] + " " + course["description"]).lower()
    return any(keyword in text for keyword in ML_KEYWORDS)


def clean_instructors(raw: str) -> str:
    """Drop the department parentheticals and normalize separators."""
    # A parenthetical marks the end of a name, so turn it into a separator.
    names = re.split(r"\s*[,;]\s*", re.sub(r"\s*\([^)]*\)", ";", raw))
    return ", ".join(name.strip() for name in names if name.strip())


def build_course_data(courses: list, term: str) -> dict:
    """Convert a course list to the lookup dict the build script expects."""
    result = {}

    for course in courses:
        description = course["description"]
        if len(description) > 300:
            description = description[:300] + "..."

        course_data = {
            "level": course["level"],
            "offered_fall": term.startswith("fall"),
            "offered_spring": term.startswith("spring"),
            "offered_IAP": False,
            "offered_summer": False,
            "title": course["title"],
            "description": description,
            "catalog_url": f"http://student.mit.edu/catalog/search.cgi?search={course['course_numbers'][0]}",
            "course_url": "",
            "units": course["units"],
            "instructors": clean_instructors(course["instructors"]),
        }

        for num in course["course_numbers"]:
            result[num] = course_data

    return result


def main():
    print("=" * 60)
    print("MLCoursesTree - Subject Updates Scraper")
    print("=" * 60)

    page_html = fetch_subject_updates(SUBJECT_UPDATE_URLS[TERM])
    if not page_html:
        print("No HTML fetched; leaving existing data in place.")
        return

    all_courses = parse_page(page_html)
    courses = [c for c in all_courses if is_ml_relevant(c)]

    print(f"Parsed {len(all_courses)} subjects, kept {len(courses)} as ML-relevant")
    for course in courses:
        print(f"  {'/'.join(course['course_numbers']):22s} {course['title']}")

    skipped = [c for c in all_courses if c not in courses]
    if skipped:
        print("\nSkipped:")
        for course in skipped:
            print(f"  {'/'.join(course['course_numbers']):22s} {course['title']}")

    course_data = build_course_data(courses, TERM)

    output_path = Path(__file__).parent.parent / "data" / f"subject_updates_{TERM_SUFFIX}.json"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(course_data, f, indent=2, sort_keys=True)

    print(f"\nWritten to {output_path}")

    undergrad = sum(1 for c in courses if c["level"] == "U")
    grad = sum(1 for c in courses if c["level"] == "G")

    print(f"\nSummary:")
    print(f"  Total courses: {len(courses)}")
    print(f"  Undergrad (U): {undergrad}")
    print(f"  Graduate (G):  {grad}")
    print(f"  Total entries: {len(course_data)} (including cross-listings)")


if __name__ == "__main__":
    main()
