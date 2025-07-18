### Components

- **`models.py`** - Simple data structures for everything we work with
- **`html_parser.py`** - Finds interesting content in HTML files
- **`ai_classifier.py`** - Uses AI to figure out what type of content each section is
- **`schema_creator.py`** - Creates CMS schemas from AI analysis
- **`database.py`** - Handles saving and loading data from MongoDB
- **`migration_system.py`** - The main system that coordinates everything

## Requirements

- Python 3.9+
- MongoDB
- A Cohere API key (sign up at [cohere.ai](https://dashboard.cohere.com/api-keys))

### Quick Setup

1. **Unzip the scrap files into /scrap**

2. **Clone**
   ```bash
   # clone this repository
   cd smart-cms-migration
   ```

3. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install required packages**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure your API key**
   ```bash
   cp .env.template .env
   # Edit .env and add your Cohere API key
   ```

6. **Start MongoDB**
   ```bash
   # Ubuntu/Debian
   sudo systemctl start mongod
   
   # macOS
   brew services start mongodb-community
   
   # Windows
   net start MongoDB
   ```

### Usage

```bash
# Analyze all HTML files in the scrap/ folder
python main.py
```

## Result

The system creates several useful files:

- **`content_schemas_*.json`** - Ready-to-use CMS schemas
- **`extracted_content_*.json`** - All your content in structured format
- **`migration_report_*.json`** - Complete analysis and summary

### Comp Schema

```json
{
  "title": "Headline",
  "uid": "headline",
  "schema": [
    {
      "uid": "headline_text",
      "data_type": "text",
      "display_name": "Headline Text",
      "mandatory": true,
      "field_metadata": {
        "multiline": false
      }
    },
    {
      "uid": "color",
      "data_type": "text",
      "display_name": "Color",
      "mandatory": false,
      "field_metadata": {
        "enum": [
          {
            "value": "black",
            "label": "Black"
          },
          {
            "value": "white",
            "label": "White"
          },
          {
            "value": "red",
            "label": "Red"
          },
          {
            "value": "blue",
            "label": "Blue"
          },
          {
            "value": "custom",
            "label": "Custom (enter hex)"
          }
        ]
      }
    }
  ],
  "options": {
    "singleton": false,
    "is_page": false,
    "title": "headline_text"
  },
  "description": "A simple component to define a styled headline.",
  "content_type_uid": "headline_component"
}
```

## Database

### Saved in MongoDB

- **`component_schemas`** - CMS schemas
- **`extracted_data`** - Extracted content
- **`component_types`** - Stats about content types
- **`page_types`** - Info about each type of HTML page analyzed(recipe, members and others)