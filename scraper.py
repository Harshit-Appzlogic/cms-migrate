import os
import time
import re
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
import json
from datetime import datetime

class HTMLScraper:
    def __init__(self, headless=False, timeout=30000):
        self.headless = headless
        self.timeout = timeout
        self.output_dir = Path("scrap")
        self.output_dir.mkdir(exist_ok=True)
        
    def sanitize_filename(self, url: str) -> str:
        """Create a safe filename from URL"""
        parsed = urlparse(url)
        filename = parsed.path.strip('/').replace('/', '_')
        
        # Clean up filename
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        filename = re.sub(r'_+', '_', filename)
        filename = filename.strip('_')
        
        # Add domain if filename is generic
        if not filename or len(filename) < 5:
            domain = parsed.netloc.replace('www.', '').split('.')[0]
            filename = f"{domain}_page"
            
        # Add timestamp to avoid duplicates
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename}_{timestamp}"
        
        return f"{filename}.html"
    
    def wait_for_content_load(self, page, wait_seconds=3):
        """Wait for dynamic content to load"""
        print("⏳ Waiting for page to fully load...")
        
        # Wait for network to be idle
        try:
            page.wait_for_load_state("networkidle", timeout=self.timeout)
        except:
            print("⚠️ Network idle timeout, continuing anyway")
        
        # Additional wait for JavaScript content
        time.sleep(wait_seconds)
        
        # Check for common loading indicators
        loading_selectors = [
            '[class*="loading"]',
            '[class*="spinner"]', 
            '.skeleton',
            '[aria-busy="true"]'
        ]
        
        for selector in loading_selectors:
            try:
                page.wait_for_selector(selector, state="detached", timeout=3000)
            except:
                pass  # Selector not found or still loading
    
    def handle_cookies_and_popups(self, page):
        """Handle common cookie banners and popups"""
        print("🍪 Handling cookies and popups...")
        
        # Common cookie/popup selectors
        popup_selectors = [
            'button:has-text("Accept")',
            'button:has-text("Accept All")',
            'button:has-text("Got it")',
            'button:has-text("OK")',
            '[id*="cookie"] button',
            '[class*="cookie"] button',
            '[data-dismiss="modal"]',
            '.modal-close',
            '[aria-label*="close"]'
        ]
        
        for selector in popup_selectors:
            try:
                element = page.query_selector(selector)
                if element and element.is_visible():
                    element.click()
                    print(f"✅ Clicked: {selector}")
                    time.sleep(1)
                    break
            except:
                continue
    
    def extract_page_metadata(self, page) -> dict:
        """Extract useful page metadata"""
        metadata = {
            "url": page.url,
            "title": page.title(),
            "timestamp": datetime.now().isoformat(),
        }
        
        # Try to get additional metadata
        try:
            metadata["description"] = page.get_attribute('meta[name="description"]', 'content') or ""
        except:
            metadata["description"] = ""
            
        try:
            # Check page type based on URL patterns
            url_lower = page.url.lower()
            if 'recipe' in url_lower:
                metadata["page_type"] = "recipe"
            elif 'article' in url_lower or 'story' in url_lower:
                metadata["page_type"] = "article"
            elif 'member' in url_lower:
                metadata["page_type"] = "member_content"
            elif 'connection' in url_lower:
                metadata["page_type"] = "costco_connection"
            else:
                metadata["page_type"] = "general"
        except:
            metadata["page_type"] = "unknown"
            
        return metadata
    
    def scrape_url(self, url: str, manual_intervention=True) -> str:
        """Scrape a single URL and return the saved filename"""
        print(f"\n🌐 Scraping: {url}")
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            
            try:
                page = context.new_page()
                
                # Navigate to URL
                print("📂 Loading page...")
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                
                # Handle popups and cookies
                self.handle_cookies_and_popups(page)
                
                # Wait for content to load
                self.wait_for_content_load(page)
                
                # Manual intervention if requested
                if manual_intervention:
                    print("\n" + "="*60)
                    print("🖱️  MANUAL INTERVENTION PHASE")
                    print("="*60)
                    print("Current URL:", page.url)
                    print("Page Title:", page.title())
                    print("\nYou can now:")
                    print("• Login if required")
                    print("• Navigate to specific content")
                    print("• Wait for dynamic content to load")
                    print("• Handle any captchas or verification")
                    print("\nPress Enter when ready to extract content...")
                    input()
                
                # Final content load wait
                self.wait_for_content_load(page, wait_seconds=2)
                
                # Extract content and metadata
                content = page.content()
                metadata = self.extract_page_metadata(page)
                
                # Generate filename and save
                filename = self.sanitize_filename(url)
                filepath = self.output_dir / filename
                
                # Save HTML content
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Save metadata
                metadata_file = filepath.with_suffix('.json')
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                
                print(f"✅ Saved: {filename}")
                print(f"📊 Metadata: {metadata_file.name}")
                print(f"📄 Content size: {len(content):,} characters")
                
                return str(filepath)
                
            except Exception as e:
                print(f"❌ Error scraping {url}: {e}")
                raise
            finally:
                browser.close()
    
    def scrape_multiple_urls(self, urls: list, manual_intervention=True) -> list:
        """Scrape multiple URLs"""
        results = []
        total = len(urls)
        
        print(f"\n🚀 Starting batch scrape of {total} URLs")
        print("="*60)
        
        for i, url in enumerate(urls, 1):
            print(f"\n📍 Progress: {i}/{total}")
            try:
                filepath = self.scrape_url(url.strip(), manual_intervention)
                results.append({"url": url, "file": filepath, "status": "success"})
            except Exception as e:
                print(f"❌ Failed to scrape {url}: {e}")
                results.append({"url": url, "file": None, "status": "failed", "error": str(e)})
                
                # Ask if user wants to continue on error
                if i < total:
                    continue_scraping = input(f"\nContinue with remaining {total - i} URLs? (y/n): ").lower()
                    if continue_scraping != 'y':
                        break
        
        return results



def interactive_scraper():
    """Interactive scraper with user prompts"""
    print("🕷️  HTML Scraper for CMS Migration")
    print("="*40)
    
    # Configuration
    print("\n⚙️ Configuration:")
    manual_mode = 'y'
    
    scraper = HTMLScraper(headless=False, timeout=30000)
    
    # URL input options
    print("\n📝 URL Input Options:")
    print("1. Single URL")
    print("2. Multiple URLs (one per line)")
    print("3. Load URLs from file")
    
    choice = input("Choose option (1-3): ").strip()
    urls = []
    
    if choice == "1":
        url = input("\n🌐 Enter URL: ").strip()
        if url:
            urls = [url]
    
    elif choice == "2":
        print("\n🌐 Enter URLs (one per line, empty line to finish):")
        while True:
            url = input().strip()
            if not url:
                break
            urls.append(url)
    
    elif choice == "3":
        file_path = input("\n📁 Enter file path: ").strip()
        try:
            with open(file_path, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return
    
    if not urls:
        print("❌ No URLs provided")
        return
    
    # Start scraping
    try:
        if len(urls) == 1:
            scraper.scrape_url(urls[0], manual_mode)
        else:
            results = scraper.scrape_multiple_urls(urls, manual_mode)
            
            # Summary
            successful = sum(1 for r in results if r["status"] == "success")
            failed = len(results) - successful
            
            print(f"\n📊 Scraping Summary:")
            print(f"✅ Successful: {successful}/{len(results)}")
            print(f"❌ Failed: {failed}/{len(results)}")
            
            if failed > 0:
                print("\n❌ Failed URLs:")
                for result in results:
                    if result["status"] == "failed":
                        print(f"  • {result['url']}: {result['error']}")

        # ✅ START MIGRATION PIPELINE
        print("\n🚀 Starting migration process on scraped HTMLs...\n")
        system = MigrationSystem()
        results = system.migrate_content("scrap")

        console = Console()
        console.print(f"\n{results.summary()}", style="bold green")
        console.print("\n📁 Output files:")
        for name, path in results.output_files.items():
            console.print(f"  • {name}: {path}")

    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    interactive_scraper()