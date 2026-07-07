#!/usr/bin/env python3
"""
Scrape subject updates from MIT EECS website.

This fetches course information from the EECS subject updates pages,
which contain special topics courses not always in the Fireroad API.
"""
import json
import re
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path

# Subject update URLs by semester.
# MIT term codes: Fall 2026 = 2027FA, Spring 2026 = 2026SP (academic-year naming).
SUBJECT_UPDATE_URLS = {
    "fall_2026": "https://eecsis.mit.edu/plugins/subj_2027FA.html",
    "spring_2026": "https://eecsis.mit.edu/plugins/subj_2026SP.html",
}


class SubjectUpdateParser(HTMLParser):
    """Parse the EECS subject updates HTML."""

    def __init__(self):
        super().__init__()
        self.courses = []
        self.current_course = None
        self.in_course_header = False
        self.in_instructor = False
        self.in_description = False
        self.current_text = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Course headers are typically in h3 or strong tags with course numbers
        if tag in ("h3", "h4", "strong", "b"):
            self.in_course_header = True
            self.current_text = ""

        # Look for instructor info
        if tag == "p" or tag == "div":
            class_name = attrs_dict.get("class", "")
            if "instructor" in class_name.lower():
                self.in_instructor = True
                self.current_text = ""

    def handle_endtag(self, tag):
        if tag in ("h3", "h4", "strong", "b") and self.in_course_header:
            self.in_course_header = False
            # Check if this looks like a course header
            text = self.current_text.strip()
            course_match = re.match(r"^([\d.]+[A-Z]?\d*(?:\s*/\s*[\d.]+[A-Z]?\d*)*)\s*[-–—]\s*(.+)$", text)
            if course_match:
                # Save previous course if exists
                if self.current_course:
                    self.courses.append(self.current_course)

                course_nums = course_match.group(1)
                title = course_match.group(2).strip()

                self.current_course = {
                    "course_numbers": [n.strip() for n in re.split(r"\s*/\s*", course_nums)],
                    "title": title,
                    "instructors": "",
                    "description": "",
                }

        if tag == "p" and self.in_instructor:
            self.in_instructor = False

    def handle_data(self, data):
        if self.in_course_header:
            self.current_text += data

        # Try to capture instructor and description from text
        if self.current_course:
            text = data.strip()

            # Look for instructor patterns
            instructor_match = re.match(r"^(?:Instructor[s]?|Taught by|Faculty):\s*(.+)$", text, re.IGNORECASE)
            if instructor_match:
                self.current_course["instructors"] = instructor_match.group(1).strip()
            elif text and not self.current_course["description"]:
                # Accumulate description
                if len(text) > 50:  # Likely a description
                    self.current_course["description"] = text

    def get_courses(self):
        # Don't forget the last course
        if self.current_course:
            self.courses.append(self.current_course)
        return self.courses


def fetch_subject_updates(url: str) -> str:
    """Fetch HTML content from subject updates page."""
    print(f"Fetching from {url}...")

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MLCoursesTree/1.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"Error fetching data: {e}")
        return ""


def parse_subject_updates_simple(html: str) -> list:
    """
    Simple regex-based parser for subject updates HTML.

    The HTML structure varies, so we use flexible patterns.
    """
    courses = []

    # Pattern to find course entries
    # Look for course numbers like 6.S051, 6.S891/6.S893, etc.
    course_pattern = re.compile(
        r'<(?:h[234]|strong|b)[^>]*>.*?'
        r'((?:\d+\.S?\d+(?:\s*/\s*\d+\.S?\d+)*)'  # Course number(s)
        r'(?:\s*\([^)]+\))?)'  # Optional cross-listing in parens
        r'\s*[-–—:]\s*'  # Separator
        r'([^<]+)'  # Title
        r'</(?:h[234]|strong|b)>',
        re.IGNORECASE | re.DOTALL
    )

    # Find all course headers
    for match in course_pattern.finditer(html):
        course_nums_raw = match.group(1).strip()
        title = match.group(2).strip()

        # Extract individual course numbers
        course_nums = re.findall(r'(\d+\.S?\d+)', course_nums_raw)

        if course_nums and title:
            courses.append({
                "course_numbers": course_nums,
                "title": title,
                "instructors": "",
                "description": "",
            })

    return courses


# Manually curated Spring 2026 subject updates
# (Since the HTML parsing is complex, we include the data directly)
SPRING_2026_COURSES = [
    {
        "course_numbers": ["6.S051", "17.S917"],
        "title": "AI Alignment: Moral, Political, and Computational Foundations",
        "description": "Explores moral, political, and computational foundations of AI alignment by drawing on political theory and computer science. Examines how individual and collective values are elicited and embedded in AI systems, covering topics like decision-making rules, value concepts, fairness objectives, pluralism, and technical methods for capturing judgments.",
        "level": "U",
        "offered_spring": True,
        "offered_fall": False,
    },
    {
        "course_numbers": ["6.S056"],
        "title": "Hack Yourself: Data-Driven Learning and Wellbeing",
        "description": "Teaches students to design daily choices for improved wellbeing using data science approaches. Covers over 60 sustainable habits with tools including generative AI, vibe coding, and statistical analysis applied to leadership and innovation domains.",
        "level": "U",
        "offered_spring": True,
        "offered_fall": False,
    },
    {
        "course_numbers": ["6.S058"],
        "title": "Introduction to Computer Vision",
        "description": "Covers early to high-level vision topics including image analysis, edge detection, transformations, 3D reconstruction, and motion tracking. Also presents machine learning fundamentals, convolutional neural networks, and transformers for classification, detection, and segmentation tasks.",
        "level": "U",
        "offered_spring": True,
        "offered_fall": False,
    },
    {
        "course_numbers": ["6.S080", "16.S690"],
        "title": "Introduction to Autonomy",
        "description": "Introduces computational principles underlying autonomous robots and vehicles, covering state-space planning, probabilistic belief estimation, constraint programming, and reinforcement learning for optimal decision-making policies.",
        "level": "U",
        "offered_spring": True,
        "offered_fall": False,
    },
    {
        "course_numbers": ["6.S891", "6.S893", "12.S992"],
        "title": "AI for Climate Action",
        "description": "Examines AI and machine learning applications to climate change mitigation, adaptation, and monitoring. Includes merged lectures on climate fundamentals followed by domain-specific sections on physics-informed learning, data assimilation, and uncertainty quantification.",
        "level": "G",
        "offered_spring": True,
        "offered_fall": False,
    },
    {
        "course_numbers": ["6.S899"],
        "title": "Learning Time Series With Interventions",
        "description": "Provides foundations for understanding, predicting, and intervening in time series processes. Addresses modeling evolving processes affected by noise for prediction and intervention applications.",
        "level": "G",
        "offered_spring": True,
        "offered_fall": False,
    },
    {
        "course_numbers": ["6.S955"],
        "title": "Machine Learning for Signal Processing",
        "description": "Covers machine learning and signal processing for understanding complex real-world signals including speech, images, and music. Includes decomposition, analysis, classification, detection, and consolidation techniques with practical applications.",
        "level": "G",
        "offered_spring": True,
        "offered_fall": False,
    },
    {
        "course_numbers": ["6.S976", "18.S996"],
        "title": "Cryptography and Machine Learning: Foundations and Frontiers",
        "description": "Applies cryptographic tools to modern machine learning, studying privacy-preserving algorithms, interactive proofs, and verification methods. Addresses privacy, verifiability, reliability, robustness, and alignment across discriminative and generative models.",
        "level": "G",
        "offered_spring": True,
        "offered_fall": False,
    },
    {
        "course_numbers": ["6.S977"],
        "title": "Ethical Machine Learning in Human Systems",
        "description": "Focuses on human-centered considerations for machine learning in healthcare, employment, and education. Combines lectures and homework with a central project on ethical ML deployment, covering robustness, fairness, privacy, and practical challenges.",
        "level": "G",
        "offered_spring": True,
        "offered_fall": False,
    },
    {
        "course_numbers": ["6.S985"],
        "title": "Modeling: Multimodal Approaches",
        "description": "Introduces principles of multimodal AI processing many data types simultaneously. Covers representation, fusion, alignment, multi-step reasoning, content generation, knowledge transfer, and ethical deployment of systems integrating vision, audio, sensors, and other modalities.",
        "level": "G",
        "offered_spring": True,
        "offered_fall": False,
    },
    {
        "course_numbers": ["6.S986"],
        "title": "Uncertainty Quantification with AI",
        "description": "Advanced graduate investigation of algorithms and theory for uncertainty quantification. Covers deep ensembles, calibration, conformal prediction, and recent research literature, intended for PhD students in statistics and machine learning.",
        "level": "G",
        "offered_spring": True,
        "offered_fall": False,
    },
]


# Manually curated Fall 2026 subject updates (ML-relevant subset of the EECS
# subject-updates page; non-ML topics like Verified Software Engineering,
# Error-Correcting Codes, and Quantum Error Correction are omitted).
FALL_2026_COURSES = [
    {
        "course_numbers": ["6.S951"],
        "title": "AI for Science: Generative AI for Scientific Discovery",
        "description": "Project-based course on emerging opportunities for generative AI in scientific research. Draws on recent literature covering representation and grounding of scientific knowledge, generative approaches, inverse design, closed-loop discovery, and agentic approaches to scientific discovery.",
        "level": "G",
        "instructors": "Tommi S. Jaakkola",
        "offered_fall": True,
        "offered_spring": False,
    },
    {
        "course_numbers": ["6.S978"],
        "title": "Engineering AI Systems and Agents",
        "description": "Principles, abstractions, algorithms, and processes for building, evaluating, and optimizing stochastic AI software systems that invoke pre-trained foundation models. Covers structured generation, evaluation and security of agentic apps, retrieval-augmented generation, tool use and agent harnesses, prompt optimization, fine-tuning, RL, and distillation.",
        "level": "G",
        "instructors": "Omar Khattab",
        "offered_fall": True,
        "offered_spring": False,
    },
    {
        "course_numbers": ["6.S979"],
        "title": "Introduction to LLM Inference Systems",
        "description": "Examines large language model inference as a systems problem, emphasizing low-latency execution, memory-intensive workloads, and deployment across heterogeneous hardware. Covers batching and scheduling, KV-cache management, kernel and compiler co-design, distributed inference, quantization, sparsity, and speculative decoding.",
        "level": "G",
        "instructors": "Nir Shavit, Alex Matveev",
        "offered_fall": True,
        "offered_spring": False,
    },
    {
        "course_numbers": ["6.7980"],
        "title": "Topics in Multiagent Learning (was 6.S890)",
        "description": "Foundations of multi-agent systems from a combined game-theoretic, optimization, and learning-theoretic perspective. Covers matrix games, stochastic games, imperfect-information games, equilibrium concepts and computation, and applications including multi-agent reinforcement learning, adversarial learning, and game-playing agents.",
        "level": "G",
        "instructors": "Gabriele Farina, Costis Daskalakis",
        "offered_fall": True,
        "offered_spring": False,
    },
    {
        "course_numbers": ["6.3930", "6.3932"],
        "title": "AI and Decision Making in Medicine: From Disease to Therapy (was 6.S043/6.S983)",
        "description": "Fundamental principles and applications of AI in medicine and medical research. Introduces machine learning for clinical decision support, personalized medicine, and computational methods for drug optimization and protein folding, stressing clinical reasoning, risk stratification, and the design of novel therapeutics.",
        "level": "U",
        "instructors": "Regina Barzilay, Collin Stultz",
        "offered_fall": True,
        "offered_spring": False,
    },
    {
        "course_numbers": ["21M.589"],
        "title": "Audio Computing: Processing Sound in Engineering, Science, and the Arts",
        "description": "Computational tools for sound and vibration analysis, including basic signal processing, machine learning audio, microphone and speaker arrays, signal enhancement and restoration, and psychoacoustics. Applications include sound-event classifiers, speech recognition, denoising, and source separation.",
        "level": "G",
        "instructors": "Paris Smaragdis, Mark Rau",
        "offered_fall": True,
        "offered_spring": False,
    },
]


def build_course_data(courses: list) -> dict:
    """Convert course list to lookup dict matching existing format."""
    result = {}

    for course in courses:
        course_data = {
            "level": course.get("level", "U"),
            "offered_fall": course.get("offered_fall", False),
            "offered_spring": course.get("offered_spring", True),
            "offered_IAP": course.get("offered_IAP", False),
            "offered_summer": course.get("offered_summer", False),
            "title": course["title"],
            "description": course.get("description", "")[:300] + "..." if len(course.get("description", "")) > 300 else course.get("description", ""),
            "catalog_url": f"http://student.mit.edu/catalog/search.cgi?search={course['course_numbers'][0]}",
            "course_url": "",
            "units": course.get("units", 12),
            "instructors": course.get("instructors", ""),
        }

        # Store under all course numbers
        for num in course["course_numbers"]:
            result[num] = course_data

    return result


def main():
    print("=" * 60)
    print("MLCoursesTree - Subject Updates Scraper")
    print("=" * 60)

    # Use the manually curated data for Fall 2026
    courses = FALL_2026_COURSES
    print(f"Processing {len(courses)} Fall 2026 subject updates")

    # Build course data dict
    course_data = build_course_data(courses)

    # Write output
    output_path = Path(__file__).parent.parent / "data" / "subject_updates_fa26.json"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(course_data, f, indent=2, sort_keys=True)

    print(f"\nWritten to {output_path}")

    # Print summary
    undergrad = sum(1 for c in courses if c.get("level") == "U")
    grad = sum(1 for c in courses if c.get("level") == "G")

    print(f"\nSummary:")
    print(f"  Total courses: {len(courses)}")
    print(f"  Undergrad (U): {undergrad}")
    print(f"  Graduate (G):  {grad}")
    print(f"  Total entries: {len(course_data)} (including cross-listings)")


if __name__ == "__main__":
    main()
