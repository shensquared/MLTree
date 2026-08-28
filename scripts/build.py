#!/usr/bin/env python3
"""
Build script for MLCoursesTree

This script:
1. Generates tree.html from tree.md using markmap-cli
2. Injects course metadata and filtering UI into the generated HTML
"""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_markmap():
    """Generate base tree.html using markmap-cli."""
    print("Running markmap-cli to generate tree.html...")

    result = subprocess.run(
        ["npx", "./markmap/packages/markmap-cli", "tree.md", "--no-toolbar"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error running markmap-cli:")
        print(result.stderr)
        sys.exit(1)

    print("Base tree.html generated successfully")


def load_course_data() -> dict:
    """
    Load scraped course metadata from all sources.

    Special-topics numbers get reused across terms, so 6.S951 in Fireroad and
    6.S951 on the subject-updates page can be different courses. Each number
    maps to a list of candidate entries; the page picks among them by title.
    """
    data = {}

    def add(entries: dict):
        for number, entry in entries.items():
            candidates = data.setdefault(number, [])
            if entry not in candidates:
                candidates.append(entry)

    # Load main Fireroad course data
    main_data_path = PROJECT_ROOT / "data" / "course_data.json"
    if main_data_path.exists():
        with open(main_data_path) as f:
            add(json.load(f))
    else:
        print(f"Warning: {main_data_path} not found")
        print("Run 'python scripts/scrape_courses.py' first to fetch course data")

    # Load subject updates (special topics courses)
    subject_updates_dir = PROJECT_ROOT / "data"
    for updates_file in subject_updates_dir.glob("subject_updates_*.json"):
        print(f"Loading subject updates from {updates_file.name}...")
        with open(updates_file) as f:
            add(json.load(f))

    return data


def get_toggle_ui() -> str:
    """Return the HTML for the toggle UI."""
    return '''
<div id="filter-controls">
  <div class="filter-group">
    <span class="filter-label">Semester:</span>
    <button class="filter-btn active" data-type="semester" data-value="all" onclick="setFilter('semester', 'all')">All</button>
    <button class="filter-btn" data-type="semester" data-value="fall" onclick="setFilter('semester', 'fall')">Fall</button>
    <button class="filter-btn" data-type="semester" data-value="spring" onclick="setFilter('semester', 'spring')">Spring</button>
  </div>
  <div class="filter-group">
    <span class="filter-label">Level:</span>
    <button class="filter-btn active" data-type="level" data-value="all" onclick="setFilter('level', 'all')">All</button>
    <button class="filter-btn" data-type="level" data-value="undergrad" onclick="setFilter('level', 'undergrad')">Undergrad</button>
    <button class="filter-btn" data-type="level" data-value="grad" onclick="setFilter('level', 'grad')">Grad</button>
  </div>
  <div class="filter-hint">Click nodes to expand; hover course number for details</div>
</div>

<style>
#filter-controls {
  position: fixed;
  top: 10px;
  right: 10px;
  z-index: 1000;
  background: white;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.15);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  font-size: 13px;
}

.filter-group {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.filter-group:last-child {
  margin-bottom: 0;
}

.filter-hint {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #eee;
  font-size: 12px;
  color: #0066cc;
  text-align: center;
  font-weight: 500;
}

.filter-label {
  font-weight: 600;
  margin-right: 10px;
  min-width: 70px;
  color: #333;
}

.filter-btn {
  padding: 5px 12px;
  margin: 0 3px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #f8f8f8;
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 13px;
  color: #555;
}

.filter-btn:hover {
  background: #e8e8e8;
  border-color: #ccc;
}

.filter-btn.active {
  background: #0066cc;
  color: white;
  border-color: #0055aa;
}

/* Dimmed state for filtered-out nodes */
.markmap-node.filtered-out {
  opacity: 0.25 !important;
  transition: opacity 0.2s ease;
}

.markmap-node.filtered-out text {
  fill: #999 !important;
}

.markmap-node.filtered-out circle {
  stroke: #ccc !important;
  fill: #f5f5f5 !important;
}

/* Dim connecting lines to filtered nodes */
path.markmap-link.filtered-out {
  stroke-opacity: 0.2 !important;
  transition: stroke-opacity 0.2s ease;
}

/* Course link styling */
.course-link {
  color: inherit;
  text-decoration: none;
  border-bottom: 1px dotted currentColor;
  cursor: pointer;
}

.course-link:hover {
  border-bottom-style: solid;
}

/* Tippy tooltip styling */
.tippy-box[data-theme~='course'] {
  background-color: #fff;
  color: #333;
  border: 1px solid #ddd;
  box-shadow: 0 4px 14px rgba(0,0,0,0.15);
  font-size: 13px;
  max-width: 350px;
}

.tippy-box[data-theme~='course'] .tippy-content {
  padding: 12px 14px;
}

.tippy-box[data-theme~='course'] .tippy-arrow {
  color: #fff;
}

.tippy-box[data-theme~='course'] .tippy-arrow::before {
  border-top-color: #ddd;
}

.course-tooltip-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 6px;
  color: #222;
}

.course-tooltip-meta {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.course-tooltip-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.course-tooltip-desc {
  font-size: 12px;
  line-height: 1.5;
  color: #444;
}

.course-tooltip-links {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #eee;
  font-size: 12px;
}

.course-tooltip-links a {
  color: #0066cc;
  text-decoration: none;
  margin-right: 12px;
}

.course-tooltip-links a:hover {
  text-decoration: underline;
}
</style>
'''


def get_filter_script(course_data: dict) -> str:
    """Return the JavaScript for filtering logic."""
    return f'''
<script>
(function() {{
  // Course metadata from Fireroad API
  const COURSE_DATA = {json.dumps(course_data)};

  // Filter state
  const filters = {{
    semester: 'all', // 'all', 'fall', 'spring'
    level: 'all'     // 'all', 'undergrad', 'grad'
  }};

  // Extract course numbers from node content
  // Handles formats like:
  //   "6.390 [6.036] Intro to ML"
  //   "6.C01 Modeling..."
  //   "6.S042/6.5820 Computer Networks"
  function extractCourseNumbers(content) {{
    const numbers = [];

    // Match course numbers: dept.number (e.g., 6.390, 18.05, 6.C01, 6.S951, 21M.589)
    // Dept may include a letter suffix (21M, 21W); number may be alphanumeric (C01, S951).
    const pattern = /(\\d+[A-Za-z]*\\.[A-Za-z]?\\d*[A-Za-z]*\\d*)/g;
    let match;

    while ((match = pattern.exec(content)) !== null) {{
      numbers.push(match[1]);
    }}

    return numbers;
  }}

  // Words too common to tell one course title from another
  const TITLE_STOPWORDS = new Set([
    'a', 'an', 'and', 'the', 'to', 'of', 'for', 'in', 'with', 'from', 'on',
    'introduction', 'intro', 'topics', 'special', 'subject', 'studies'
  ]);

  function titleWords(text) {{
    return (text || '').toLowerCase().match(/[a-z0-9]+/g) || [];
  }}

  // How much of a course title shows up in the node's own text, 0 to 1.
  // Generic catalog titles ("Special Subject in EECS") score near 0, which is
  // what we want: they make no claim about the topic.
  function titleScore(title, nodeWords) {{
    const words = titleWords(title)
      .filter(w => w.length > 2 && !TITLE_STOPWORDS.has(w));
    if (words.length === 0) return 0;

    return words.filter(w => nodeWords.has(w)).length / words.length;
  }}

  // Special-topics numbers get reused, so one number can hold several entries
  // (e.g. 6.S951 is both Modern Mathematical Statistics and AI for Science).
  // Pick the entry whose title actually shows up in the node's own text.
  function lookupCourse(courseId, content) {{
    const candidates = COURSE_DATA[courseId];
    if (!candidates || candidates.length === 0) return null;
    if (candidates.length === 1) return candidates[0];

    const nodeWords = new Set(titleWords(content));
    let best = candidates[0];
    let bestScore = 0;

    candidates.forEach(candidate => {{
      const score = titleScore(candidate.title, nodeWords);
      if (score > bestScore) {{
        bestScore = score;
        best = candidate;
      }}
    }});

    // Nothing matched, so fall back to the first entry, the catalog's own.
    return best;
  }}

  // Pick the entry to describe a node that may carry several numbers, such as
  // "6.S042/6.5820 Computer Networks". The best title match wins, so a
  // cross-listing with a real catalog title beats a bare special-subject shell.
  function selectCourse(courseNumbers, content) {{
    const nodeWords = new Set(titleWords(content));
    let best = null;
    let bestScore = -1;

    for (const courseId of courseNumbers) {{
      const data = lookupCourse(courseId, content);
      if (!data) continue;

      const score = titleScore(data.title, nodeWords);
      if (score > bestScore) {{
        bestScore = score;
        best = {{ courseId, data }};
      }}
    }}

    return best;
  }}

  // Check if any of the course numbers pass current filters
  function coursePassesFilters(courseNumbers, content) {{
    if (courseNumbers.length === 0) return true; // Non-course nodes pass

    // Check if ANY of the course numbers pass (for cross-listed courses)
    for (const courseId of courseNumbers) {{
      const data = lookupCourse(courseId, content);
      if (!data) continue; // Unknown courses - keep checking others

      // Check semester filter
      let semesterOk = true;
      if (filters.semester === 'fall') semesterOk = data.offered_fall;
      if (filters.semester === 'spring') semesterOk = data.offered_spring;

      // Check level filter
      let levelOk = true;
      if (filters.level === 'undergrad') levelOk = data.level === 'U';
      if (filters.level === 'grad') levelOk = data.level === 'G';

      if (semesterOk && levelOk) return true;
    }}

    // If we found course numbers but none passed, check if any were unknown
    const hasKnownCourse = courseNumbers.some(id => lookupCourse(id, content));
    if (!hasKnownCourse) return true; // All unknown = pass through

    return false;
  }}

  // Apply filters to all tree nodes
  function applyFilters() {{
    const svg = document.querySelector('#mindmap');
    if (!svg) return;

    // Get all node groups
    const nodes = svg.querySelectorAll('g.markmap-node');

    nodes.forEach(node => {{
      // Find the text content
      const foreignObj = node.querySelector('foreignObject');
      if (!foreignObj) return;

      const content = foreignObj.textContent || '';
      const courseNumbers = extractCourseNumbers(content);

      // Skip category nodes (no course numbers)
      if (courseNumbers.length === 0) {{
        node.classList.remove('filtered-out');
        return;
      }}

      const passes = coursePassesFilters(courseNumbers, content);
      node.classList.toggle('filtered-out', !passes);

      // Also handle the connecting line
      const path = node.dataset.path;
      if (path) {{
        const link = svg.querySelector(`path.markmap-link[data-path="${{path}}"]`);
        if (link) {{
          link.classList.toggle('filtered-out', !passes);
        }}
      }}
    }});
  }}

  // Update filter and re-apply
  window.setFilter = function(type, value) {{
    filters[type] = value;

    // Update button states
    document.querySelectorAll(`.filter-btn[data-type="${{type}}"]`).forEach(btn => {{
      btn.classList.toggle('active', btn.dataset.value === value);
    }});

    applyFilters();
  }};

  // Watch for tree changes (expand/collapse) and reapply filters
  function setupObserver() {{
    const svg = document.querySelector('#mindmap');
    if (!svg) {{
      setTimeout(setupObserver, 100);
      return;
    }}

    const observer = new MutationObserver(() => {{
      // Debounce to avoid excessive calls during animations
      clearTimeout(window._filterTimeout);
      window._filterTimeout = setTimeout(() => {{
        applyFilters();
        initializeTooltips(); // Re-init tooltips for newly rendered nodes
      }}, 50);
    }});

    observer.observe(svg, {{
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class', 'transform']
    }});

    // Initial application
    applyFilters();

    // Initialize tooltips and links
    initializeTooltips();
  }}

  // Build tooltip HTML content
  function buildTooltipContent(courseId, data) {{
    const semesters = [];
    if (data.offered_fall) semesters.push('Fall');
    if (data.offered_spring) semesters.push('Spring');
    if (data.offered_IAP) semesters.push('IAP');
    const semesterStr = semesters.length > 0 ? semesters.join(', ') : 'Not offered';

    const levelStr = data.level === 'G' ? 'Graduate' : 'Undergraduate';
    const unitsStr = data.units ? data.units + ' units' : '';

    let html = `<div class="course-tooltip-title">${{data.title || courseId}}</div>`;

    html += `<div class="course-tooltip-meta">`;
    html += `<span>${{levelStr}}</span>`;
    if (unitsStr) html += `<span>${{unitsStr}}</span>`;
    html += `<span>${{semesterStr}}</span>`;
    html += `</div>`;

    if (data.instructors) {{
      html += `<div class="course-tooltip-meta"><span>Instructor: ${{data.instructors}}</span></div>`;
    }}

    if (data.description) {{
      html += `<div class="course-tooltip-desc">${{data.description}}</div>`;
    }}

    html += `<div class="course-tooltip-links">`;
    html += `<a href="${{data.catalog_url}}" target="_blank">MIT Catalog</a>`;
    if (data.course_url) {{
      html += `<a href="${{data.course_url}}" target="_blank">Course Website</a>`;
    }}
    html += `</div>`;

    return html;
  }}

  // Initialize tooltips for course nodes
  function initializeTooltips() {{
    const svg = document.querySelector('#mindmap');
    if (!svg || typeof tippy === 'undefined') return;

    // Find all foreignObject elements (where course text is rendered)
    const foreignObjects = svg.querySelectorAll('foreignObject');

    foreignObjects.forEach(fo => {{
      // Skip if already has tooltip
      if (fo._tippy) return;

      const content = fo.textContent || '';
      const courseNumbers = extractCourseNumbers(content);

      if (courseNumbers.length === 0) return;

      // Find the entry that best describes this node
      const selected = selectCourse(courseNumbers, content);
      if (!selected) return;

      const primaryCourse = selected.courseId;
      const primaryData = selected.data;

      // Create tooltip on the foreignObject element
      tippy(fo, {{
        content: buildTooltipContent(primaryCourse, primaryData),
        allowHTML: true,
        theme: 'course',
        placement: 'right',
        interactive: true,
        appendTo: document.body,
        maxWidth: 350,
        delay: [150, 0],
        trigger: 'mouseenter',
      }});
    }});
  }}

  // Wait for Tippy to be available
  function waitForTippy(callback, attempts = 0) {{
    if (typeof tippy !== 'undefined') {{
      callback();
    }} else if (attempts < 50) {{
      setTimeout(() => waitForTippy(callback, attempts + 1), 100);
    }} else {{
      console.warn('Tippy.js not loaded, tooltips disabled');
      callback();
    }}
  }}

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', () => {{
      waitForTippy(setupObserver);
    }});
  }} else {{
    // Wait for markmap to render and Tippy to load
    setTimeout(() => waitForTippy(setupObserver), 300);
  }}
}})();
</script>
'''


def get_tippy_scripts() -> str:
    """Return Tippy.js script tags to inject in head."""
    return '''
<!-- Tippy.js for course tooltips -->
<script src="https://unpkg.com/@popperjs/core@2"></script>
<script src="https://unpkg.com/tippy.js@6"></script>
'''


def inject_filtering(html: str, course_data: dict) -> str:
    """Inject course data and filtering UI into HTML."""
    toggle_ui = get_toggle_ui()
    filter_script = get_filter_script(course_data)
    tippy_scripts = get_tippy_scripts()

    # Inject Tippy.js in head (before </head>)
    html = html.replace('</head>', tippy_scripts + '\n</head>')

    # Inject UI after <body>
    html = html.replace('<body>', '<body>\n' + toggle_ui)

    # Inject script before </body>
    html = html.replace('</body>', filter_script + '\n</body>')

    return html


def main():
    print("=" * 60)
    print("MLCoursesTree - Build Script")
    print("=" * 60)

    # Step 1: Generate base HTML
    run_markmap()

    # Step 2: Load course data
    course_data = load_course_data()
    print(f"Loaded metadata for {len(course_data)} course entries")

    # Step 3: Read generated HTML
    html_path = PROJECT_ROOT / "tree.html"
    with open(html_path) as f:
        html = f.read()

    # Step 4: Inject filtering
    html = inject_filtering(html, course_data)

    # Step 5: Write back
    with open(html_path, "w") as f:
        f.write(html)

    print(f"\nDone! tree.html updated with semester/level filter toggles")
    print(f"Open tree.html in a browser to test the filters")


if __name__ == "__main__":
    main()
