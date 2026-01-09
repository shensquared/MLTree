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
    """Load scraped course metadata."""
    data_path = PROJECT_ROOT / "data" / "course_data.json"

    if not data_path.exists():
        print(f"Warning: {data_path} not found")
        print("Run 'python scripts/scrape_courses.py' first to fetch course data")
        return {}

    with open(data_path) as f:
        return json.load(f)


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

    // Match course numbers: digits.alphanumerics (e.g., 6.390, 18.05, 6.C01, 6.S951)
    const pattern = /(\\d+\\.[A-Za-z]?\\d*[A-Za-z]*\\d*)/g;
    let match;

    while ((match = pattern.exec(content)) !== null) {{
      numbers.push(match[1]);
    }}

    return numbers;
  }}

  // Check if any of the course numbers pass current filters
  function coursePassesFilters(courseNumbers) {{
    if (courseNumbers.length === 0) return true; // Non-course nodes pass

    // Check if ANY of the course numbers pass (for cross-listed courses)
    for (const courseId of courseNumbers) {{
      const data = COURSE_DATA[courseId];
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
    const hasKnownCourse = courseNumbers.some(id => COURSE_DATA[id]);
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

      const passes = coursePassesFilters(courseNumbers);
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
      window._filterTimeout = setTimeout(applyFilters, 50);
    }});

    observer.observe(svg, {{
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class', 'transform']
    }});

    // Initial application
    applyFilters();
  }}

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', setupObserver);
  }} else {{
    // Small delay to ensure markmap has rendered
    setTimeout(setupObserver, 200);
  }}
}})();
</script>
'''


def inject_filtering(html: str, course_data: dict) -> str:
    """Inject course data and filtering UI into HTML."""
    toggle_ui = get_toggle_ui()
    filter_script = get_filter_script(course_data)

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
