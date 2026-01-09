# MLCoursesTree
Explore a decision tree to pick Machine Learning Courses @MIT 

https://shenshen.mit.edu/tree

The tree visualization is quickly cobbled together; need to clean up the code to port it here. Setting the repo up for bug tracking first.

## How to contribute?
- Edit the `tree.md` file, in standard markdown syntax.
- Run the build script:
```bash
python scripts/build.py
```

### Updating course data
The tree includes filter toggles for Fall/Spring semesters and Undergrad/Grad levels.
Course metadata is scraped from MIT's Fireroad API. To refresh the data:
```bash
python scripts/scrape_courses.py  # Fetches latest course offerings
python scripts/build.py           # Rebuilds tree.html with filters
```

### Manual build (without filters)
```bash
npx ./markmap/packages/markmap-cli tree.md --no-toolbar
```

## Credits:

Inspired by [Leslie Kaelbling](https://people.csail.mit.edu/lpk/)'s [slides](https://github.com/shensquared/MLTree/blob/master/lpk.pdf) shared with 6.390[6.036] students in Spring21, from .