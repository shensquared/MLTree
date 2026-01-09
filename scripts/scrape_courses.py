#!/usr/bin/env python3
"""
Scrape course metadata from Fireroad API and generate course_data.json

This fetches course information (level, semester offerings) from MIT's Fireroad API,
similar to how Hydrant does it, and outputs a JSON file for use in the tree filter UI.
"""
import json
import re
import urllib.request
import urllib.error
from pathlib import Path

FIREROAD_API = "https://fireroad.mit.edu/courses/all?full=true"

# Course numbers from tree.md (including old numbers in brackets)
# Format: new_number or old_number
COURSES_IN_TREE = [
    # General
    "6.390", "6.036",  # Intro to ML
    "6.C01",           # Modeling with ML
    "6.796",           # Deep Learning (also 6.7960)
    "6.790", "6.867",  # Machine Learning
    # Statistics
    "18.05",           # Intro Probability and Statistics
    "18.650",          # Fundamentals of Statistics
    "6.372", "6.401",  # Intro Statistical Data Analysis
    "6.S951",          # Modern Mathematical Statistics
    # Inference
    "6.3700", "6.041", # Intro to Probability
    "6.3800", "6.008", # Intro to Inference
    "6.7700", "6.436", # Fundamentals of Probability
    "6.7800", "6.437", # Inference and Information
    "6.7810", "6.438", # Algorithms for Inference
    "6.7830", "6.435", # Bayesian Modeling and Inference
    # Theory
    "6.7910", "6.860", # Statistical Learning Theory
    "6.7940", "6.231", # Dynamic Programming and RL
    "6.7950", "6.246", # RL: Foundations and Methods
    "6.7900",          # Machine Learning (grad)
    # Systems
    "6.5931", "6.812", # Hardware Architecture for DL
    "6.S079",          # Software Systems for Data Science
    "6.S965",          # TinyML
    "6.S981",          # Program Synthesis
    "6.S042", "6.5820",# Computer Networks
    # Society
    "6.3950", "6.404", # AI, Decision Making, and Society
    "6.4590", "6.805", # Foundations of Information Policy
    "6.C40", "24.C40", # Ethics of Computing
    # Cognition
    "6.4120", "6.804", # Computational Cognitive Science
    "6.S899",          # Brain Algorithms
    "6.S978",          # Tissue vs Silicon in ML
    # Applications
    "6.C011", "6.C511",# Modeling with ML for CS
    "6.3730",          # Statistics, Computation and Applications
    "6.7930", "6.871", # ML for Healthcare
    "6.8200", "6.484", # Sensorimotor Learning
    "6.4300",          # Intro to Computer Vision
    "6.8301", "6.819", # Advances in Computer Vision
    "6.4610",          # NLP
    "6.8711", "6.802", # Computational Systems Biology
    "6.S980",          # ML for Inverse Graphics
    "6.S982",          # Clinical Data Learning
    # Fall 2025 Special
    "6.S044",          # AI and Rationality
    "6.S890",          # Topics in Multiagent Learning
    "6.S894",          # Accelerated Computing
    "6.S896",          # Algorithmic Statistics
]


def fetch_course_data() -> list:
    """Fetch all courses from Fireroad API."""
    print(f"Fetching from {FIREROAD_API}...")

    req = urllib.request.Request(
        FIREROAD_API,
        headers={"User-Agent": "MLCoursesTree/1.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except urllib.error.URLError as e:
        print(f"Error fetching data: {e}")
        return []


def normalize_course_number(num: str) -> str:
    """Normalize course number for matching (remove leading zeros, etc.)."""
    # Remove any whitespace
    num = num.strip()
    # Standardize format
    return num


def extract_relevant_courses(all_courses: list) -> dict:
    """Extract only courses in our tree, building a lookup with all variants."""
    # Build lookup by subject_id
    lookup = {}
    for course in all_courses:
        subject_id = course.get("subject_id", "")
        if subject_id:
            lookup[subject_id] = course

    # Also check for old_id field and create reverse mappings
    old_to_new = {}
    for course in all_courses:
        subject_id = course.get("subject_id", "")
        old_id = course.get("old_id", "")
        if old_id and subject_id:
            old_to_new[old_id] = subject_id

    # Manual aliases for courses where tree.md uses a different format than Fireroad
    # (e.g., tree.md uses "6.390" but Fireroad has "6.3900")
    MANUAL_ALIASES = {
        "6.390": "6.3900",   # Intro to ML
        "6.790": "6.7900",   # Machine Learning (grad)
        "6.796": "6.7960",   # Deep Learning
        "6.372": "6.3720",   # Intro Statistical Data Analysis
    }
    for alias, canonical in MANUAL_ALIASES.items():
        if canonical in lookup:
            old_to_new[alias] = canonical

    result = {}
    matched = set()

    for course_id in COURSES_IN_TREE:
        # Try direct lookup
        course = lookup.get(course_id)

        # If not found, check if it's an old number
        if not course and course_id in old_to_new:
            new_id = old_to_new[course_id]
            course = lookup.get(new_id)

        if course:
            # Extract the fields we need
            course_data = {
                "level": course.get("level", "U"),  # "U" or "G"
                "offered_fall": course.get("offered_fall", False),
                "offered_spring": course.get("offered_spring", False),
                "offered_IAP": course.get("offered_IAP", False),
                "offered_summer": course.get("offered_summer", False),
                "title": course.get("title", ""),
            }

            # Store under the ID we searched for
            result[course_id] = course_data
            matched.add(course_id)

            # Also store under subject_id if different
            subject_id = course.get("subject_id", "")
            if subject_id and subject_id != course_id:
                result[subject_id] = course_data
                matched.add(subject_id)

            # Also store under old_id if present
            old_id = course.get("old_id", "")
            if old_id and old_id != course_id:
                result[old_id] = course_data
                matched.add(old_id)

    return result, matched


def main():
    print("=" * 60)
    print("MLCoursesTree - Course Data Scraper")
    print("=" * 60)

    # Fetch all courses
    all_courses = fetch_course_data()
    if not all_courses:
        print("Failed to fetch course data. Using cached data if available.")
        return

    print(f"Total courses in Fireroad API: {len(all_courses)}")

    # Extract relevant courses
    course_data, matched = extract_relevant_courses(all_courses)

    print(f"Matched {len(matched)} course numbers from tree")

    # Report unmatched courses
    unmatched = set(COURSES_IN_TREE) - matched
    if unmatched:
        print(f"\nCourses not found in API ({len(unmatched)}):")
        for c in sorted(unmatched):
            print(f"  - {c}")
        print("(These will pass through all filters)")

    # Write output
    output_path = Path(__file__).parent.parent / "data" / "course_data.json"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(course_data, f, indent=2, sort_keys=True)

    print(f"\nWritten to {output_path}")

    # Print summary stats
    undergrad = sum(1 for c in course_data.values() if c["level"] == "U")
    grad = sum(1 for c in course_data.values() if c["level"] == "G")
    fall = sum(1 for c in course_data.values() if c["offered_fall"])
    spring = sum(1 for c in course_data.values() if c["offered_spring"])

    print(f"\nSummary:")
    print(f"  Undergrad (U): {undergrad}")
    print(f"  Graduate (G):  {grad}")
    print(f"  Offered Fall:   {fall}")
    print(f"  Offered Spring: {spring}")


if __name__ == "__main__":
    main()
