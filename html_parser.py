from pathlib import Path
import re
from bs4 import BeautifulSoup, Tag


def find_content_sections(html_file: Path) -> list:
    """Find interesting content in an HTML file with hierarchical detection"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        sections = []
        
        # Step 1: Find top-level containers
        top_level_selectors = ['nav', 'form', 'header', 'footer', 'aside']
        
        for selector in top_level_selectors:
            elements = soup.select(selector)
            for element in elements:
                if looks_like_content(element):
                    sections.append(element)
        
        # Step 2: Hierarchical content extraction from main content areas
        main_areas = soup.select('main, article, section, div.content, [id*="content"]')
        
        for main_area in main_areas:
            if main_area and len(main_area.get_text(strip=True)) > 200:
                # Extract nested components from main content
                nested_sections = extract_nested_components(main_area)
                sections.extend(nested_sections)
        
        # Step 3: If still not enough, look for standalone content divs
        if len(sections) < 5:
            content_divs = soup.find_all('div')
            for div in content_divs:
                if looks_like_standalone_content(div) and div not in sections:
                    sections.append(div)
        
        # Remove duplicates and limit results
        unique_sections = []
        seen_elements = set()
        
        for section in sections:
            element_id = id(section)
            if element_id not in seen_elements:
                unique_sections.append(section)
                seen_elements.add(element_id)
        
        return unique_sections[:20]  # Increased limit for more component diversity
        
    except Exception as e:
        print(f"Couldn't read {html_file}: {e}")
        return []


def extract_nested_components(main_area) -> list:
    """Extract individual components from within main content areas"""
    components = []
    
    # Look for semantic content patterns
    content_patterns = {
        'headline_sections': ['h1', 'h2', 'h3', '.headline', '[class*="title"]', '[class*="header"]'],
        'article_sections': ['article', '.article', '[class*="story"]', '[class*="post"]'],
        'recipe_sections': ['[class*="recipe"]', '[data-recipe]', '[id*="recipe"]'],
        'member_sections': ['[class*="member"]', '[id*="member"]', '[class*="user"]'],
        'banner_sections': ['[class*="banner"]', '[class*="promo"]', '[class*="hero"]'],
        'card_sections': ['[class*="card"]', '[class*="tile"]', '[class*="item"]'],
        'list_sections': ['ul', 'ol', '[class*="list"]']
    }
    
    # Extract components by pattern
    for pattern_type, selectors in content_patterns.items():
        for selector in selectors:
            elements = main_area.select(selector)
            for element in elements:
                if looks_like_component(element):
                    components.append(element)
    
    # Look for content blocks - divs with substantial content
    content_divs = main_area.find_all('div', recursive=True)
    for div in content_divs:
        if looks_like_content_block(div) and div not in components:
            components.append(div)
    
    return components[:15]  # Limit nested components per main area


def looks_like_component(element) -> bool:
    """Check if element looks like a reusable component"""
    if not element or not hasattr(element, 'get_text'):
        return False
    
    text = element.get_text(strip=True)
    
    # Component size filters
    if len(text) < 20 or len(text) > 2000:
        return False
    
    words = text.split()
    if len(words) < 3:
        return False
    
    # Component indicators
    classes = element.get('class', [])
    element_id = element.get('id', '')
    
    # Has meaningful classes or ID
    if classes or element_id:
        return True
    
    # Has semantic content
    if element.find(['h1', 'h2', 'h3', 'h4', 'img', 'a', 'button']):
        return True
    
    # Has structured content
    if len(element.find_all(['p', 'li', 'span'])) >= 2:
        return True
    
    return False


def looks_like_content_block(element) -> bool:
    """Check if div looks like a meaningful content block"""
    if not element or element.name != 'div':
        return False
    
    text = element.get_text(strip=True)
    
    # Content block filters
    if len(text) < 50 or len(text) > 1500:
        return False
    
    words = text.split()
    if len(words) < 8 or len(words) > 300:
        return False
    
    # Skip navigation-like content
    text_lower = text.lower()
    nav_words = ['menu', 'navigation', 'footer', 'copyright', 'privacy', 'cookie']
    if any(word in text_lower for word in nav_words):
        return False
    
    # Must have some structure
    children = element.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img', 'a', 'button', 'span'], recursive=False)
    if len(children) < 2:
        return False
    
    return True


def looks_like_standalone_content(element) -> bool:
    """Check if element is standalone content worth extracting"""
    if not element or not hasattr(element, 'get_text'):
        return False
    
    text = element.get_text(strip=True)
    
    # Size filters
    if len(text) < 100 or len(text) > 3000:
        return False
    
    words = text.split()
    if len(words) < 15:
        return False
    
    # Skip obvious utility content
    text_lower = text.lower()
    skip_patterns = ['cookie', 'privacy', 'terms', 'copyright', 'all rights reserved']
    if any(pattern in text_lower for pattern in skip_patterns):
        return False
    
    return True


def looks_like_content(element: Tag) -> bool:
    """Does this look like real content?"""
    text = element.get_text(strip=True)
    
    # Too short or too long isn't useful
    if len(text) < 50 or len(text) > 3000:
        return False
    
    # Need enough words
    words = text.split()
    if len(words) < 10:
        return False
    
    # Skip obvious junk (but allow navigation content)
    text_lower = text.lower()
    skip_words = ['footer', 'copyright', 'login', 'cookie policy', 'privacy policy']
    if any(word in text_lower for word in skip_words):
        return False
    
    return True


def get_fallback_text(section: Tag, field_name: str) -> str:
    """Simple fallback if AI doesn't find field value"""
    field_name = field_name.lower()
    
    # Title-like fields
    if field_name in ['title', 'heading', 'name']:
        for tag in ['h1', 'h2', 'h3', '.title']:
            element = section.find(tag) if tag.startswith('h') else section.select_one(tag)
            if element:
                return element.get_text(strip=True)
    
    # Just return some text
    return section.get_text(strip=True)[:200]