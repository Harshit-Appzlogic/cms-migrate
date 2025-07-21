## Project Structure Overview

| File/Folder                     | Description                                    |
| ------------------------------- | ---------------------------------------------- |
| `scraper.py`                    | Interactive Playwright-based scraper with head navigation for now.           |
| `scrap/`                        | Folder where HTML and metadata are saved       |
| `migration_system.py`           | Orchestrates the migration pipeline            |
| `ai_classifier.py`              | AI logic for classifying HTML sections         |
| `schema_creator.py`             | Generates component schema from field data     |
| `html_parser.py`                | Parses meaningful HTML content blocks          |
| `enhanced_content_detection.py` | Detects patterns before AI prompt              |
| `component_patterns.py`         | Finds reusable design/component patterns       |
| `smart_parser.py`               | Extracts structured, semantic HTML data        |
| `database.py`                   | MongoDB persistence for all entities           |
| `main.py`                       | Main entry point for full migration            |
| `migration_outputs/`            | Final JSON outputs (schemas, content, reports) |

---

## Prerequisites

* Python 3.9+
* [Playwright](https://playwright.dev/python/docs/intro)
* MongoDB installed locally or via Atlas
* OpenAI API key (uses GPT-4o-mini)

---

## Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/smart-cms-migration.git
cd smart-cms-migration
```

### 2. Create Python Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
playwright install
```

### 4. Set Environment Variables

```bash
cp .env.template .env
# Open .env and set:
OPENAI_API_KEY=your_key_here
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=cms_migration
```

---

### Scraper

```bash
python scraper.py
```

* Choose single URL, multiple URLs, or a file of URLs
* Paste your URL
* Wait for page to load completely
* Press enter in terminal

---

## Full Migration Pipeline

Once the `scrap/` folder contains HTML files:

```bash
python main.py
```

This will:

1. Analyze each HTML file
2. Run AI classification per content block
3. Generate CMS schemas for all content types
4. Extract structured content into a normalized format
5. Detect reusable component patterns
6. Save output in `migration_outputs/`

---

## Output Files

| File                                   | Description                     |
| -------------------------------------- | ------------------------------- |
| `content_schemas_<timestamp>.json`     | Component schemas for CMS       |
| `extracted_content_<timestamp>.json`   | Structured content extracted    |
| `reusable_components_<timestamp>.json` | Identified reusable UI patterns |
| `migration_report_<timestamp>.json`    | Full summary of migration run   |

---

## MongoDB Collections

| Collection          | Data                                     |
| ------------------- | ---------------------------------------- |
| `component_schemas` | Saved schemas                            |
| `extracted_data`    | Structured blocks with confidence scores |
| `component_types`   | Discovered types with metadata           |
| `page_types`        | Per-page analysis summary                |

---


## Sample Component Schema Output

```json
{
  "title": "Headline",
  "uid": "headline_component",
  "schema": [
    {
      "uid": "headline_text",
      "data_type": "text",
      "display_name": "Headline Text",
      "mandatory": true
    }
  ],
  "options": {
    "singleton": false,
    "is_page": false,
    "title": "headline_text"
  },
  "description": "A styled headline component."
}
