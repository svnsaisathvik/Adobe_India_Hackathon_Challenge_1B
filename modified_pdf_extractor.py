import os
import json
import re
import time
import statistics
from pathlib import Path
from collections import defaultdict, Counter
import pymupdf


class ModifiedPDFOutlineExtractor:
    def __init__(self):
        self.debug = False
        
    def extract_text_with_metadata(self, doc):
        """Extract text with comprehensive metadata for each page."""
        pages_data = []
        
        for page_num, page in enumerate(doc):
            # Get page dimensions for position analysis
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            blocks = page.get_text("dict", flags=11)["blocks"]
            text_elements = []
            
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        line_bbox = line["bbox"]
                        line_y = line_bbox[1]  # y-coordinate for vertical position
                        
                        for span in line["spans"]:
                            if span["text"].strip():
                                bbox = span["bbox"]
                                text_elements.append({
                                    "text": span["text"].strip(),
                                    "font": span["font"],
                                    "size": span["size"],
                                    "flags": span["flags"],
                                    "page": page_num + 1,
                                    "bbox": bbox,
                                    "x": bbox[0],
                                    "y": bbox[1],
                                    "width": bbox[2] - bbox[0],
                                    "height": bbox[3] - bbox[1],
                                    "page_width": page_width,
                                    "page_height": page_height,
                                    "relative_x": bbox[0] / page_width,
                                    "relative_y": bbox[1] / page_height,
                                    "line_y": line_y
                                })
            
            pages_data.append(text_elements)
        
        return pages_data
    
    def is_bold(self, flags):
        """Check if text is bold."""
        return bool(flags & 2 ** 4)
    
    def is_italic(self, flags):
        """Check if text is italic."""
        return bool(flags & 2 ** 6)
    
    def clean_text(self, text):
        """Clean and normalize text."""
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def analyze_font_distribution(self, all_elements):
        """Analyze font size distribution to identify heading sizes."""
        font_sizes = [elem["size"] for elem in all_elements]
        
        if not font_sizes:
            return []
        
        # Calculate statistics
        mean_size = statistics.mean(font_sizes)
        median_size = statistics.median(font_sizes)
        
        # Count occurrences of each size
        size_counts = Counter(font_sizes)
        
        # Find sizes significantly larger than average
        significant_sizes = []
        for size, count in size_counts.items():
            # Consider as potential heading if:
            # 1. Size is larger than median + some threshold
            # 2. Not too many occurrences (not body text)
            # 3. Not too few occurrences (not noise)
            if (size > median_size + 2 and 
                count > 1 and 
                count < len(all_elements) * 0.1):
                significant_sizes.append(size)
        
        # Sort by size (largest first)
        significant_sizes.sort(reverse=True)
        
        return significant_sizes[:3]  # Top 3 sizes for H1, H2, H3
    
    def is_title_candidate(self, element, is_first_page=False):
        """Check if an element could be a title."""
        text = self.clean_text(element["text"])
        
        # Basic length check
        if len(text) < 5 or len(text) > 150:
            return False
        
        # Position check - titles are usually in upper portion
        if element["relative_y"] > 0.3:  # Not in top 30% of page
            return False
        
        # Content analysis
        # Titles usually don't end with periods
        if text.endswith('.') and not text.endswith('...'):
            return False
        
        # Check for title-like patterns
        title_patterns = [
            r'^[A-Z][a-zA-Z\s\-:]+$',  # Starts with capital, mostly letters
            r'^[A-Z][a-zA-Z\s\-:]*[a-zA-Z]$',  # Starts and ends with letters
        ]
        
        has_title_pattern = any(re.match(pattern, text) for pattern in title_patterns)
        
        # Scoring factors
        score = 0
        
        # Size factor
        if element["size"] > 16:
            score += 3
        elif element["size"] > 14:
            score += 2
        elif element["size"] > 12:
            score += 1
        
        # Position factor (higher = better for title)
        if element["relative_y"] < 0.15:
            score += 3
        elif element["relative_y"] < 0.25:
            score += 2
        
        # Formatting factor
        if self.is_bold(element["flags"]):
            score += 2
        
        # Content factor
        if has_title_pattern:
            score += 2
        
        # Centering factor (titles are often centered)
        center_x = element["relative_x"] + (element["width"] / element["page_width"]) / 2
        if 0.3 < center_x < 0.7:  # Roughly centered
            score += 1
        
        # First page bonus
        if is_first_page:
            score += 1
        
        return score >= 4
    
    def extract_title(self, pages_data, pdf_metadata=None):
        """Extract title using multiple strategies."""
        title_candidates = []
        
        # Strategy 1: Check PDF metadata
        if pdf_metadata and pdf_metadata.get("title"):
            metadata_title = pdf_metadata["title"].strip()
            if metadata_title and len(metadata_title) > 3:
                return metadata_title
        
        # Strategy 2: Analyze first page elements
        if pages_data:
            first_page = pages_data[0]
            
            for element in first_page:
                if self.is_title_candidate(element, is_first_page=True):
                    text = self.clean_text(element["text"])
                    
                    # Calculate title score
                    score = 0
                    score += element["size"]  # Font size
                    score += (1 - element["relative_y"]) * 10  # Position (top is better)
                    
                    if self.is_bold(element["flags"]):
                        score += 5
                    
                    title_candidates.append((score, text, element))
        
        # Strategy 3: Look for isolated large text
        if not title_candidates and len(pages_data) > 0:
            all_first_page = pages_data[0]
            
            # Find largest font sizes
            sizes = [elem["size"] for elem in all_first_page]
            if sizes:
                max_size = max(sizes)
                large_texts = [elem for elem in all_first_page 
                             if elem["size"] >= max_size - 1 and 
                             elem["relative_y"] < 0.4]
                
                for elem in large_texts:
                    text = self.clean_text(elem["text"])
                    if 5 <= len(text) <= 150:
                        title_candidates.append((elem["size"], text, elem))
        
        # Select best title candidate
        if title_candidates:
            title_candidates.sort(key=lambda x: x[0], reverse=True)
            return title_candidates[0][1]
        
        return None
    
    def is_heading_candidate(self, element, significant_sizes, body_text_size):
        """Check if an element could be a heading."""
        text = self.clean_text(element["text"])
        
        # Basic checks
        if len(text) < 3 or len(text) > 200:
            return False
        
        # Must be in significant sizes or bold with reasonable size
        is_significant_size = element["size"] in significant_sizes
        is_bold_and_large = (self.is_bold(element["flags"]) and 
                           element["size"] > body_text_size)
        
        if not (is_significant_size or is_bold_and_large):
            return False
        
        # Content analysis
        # Skip pure numbers or punctuation
        if re.match(r'^[\d\s\.\-\(\)]+$', text):
            return False
        
        # Must contain letters
        if not re.search(r'[a-zA-Z]', text):
            return False
        
        # Skip very common words that might be formatted differently
        common_words = {'page', 'chapter', 'section', 'figure', 'table', 'appendix'}
        if text.lower() in common_words:
            return False
        
        # Check for heading-like patterns
        heading_patterns = [
            r'^\d+\.?\s+[A-Z]',  # Numbered headings
            r'^[A-Z][a-zA-Z\s\-:]+$',  # Title case
            r'^[A-Z\s]+$',  # All caps
            r'^\d+\.\d+\.?\s+',  # Subsection numbers
        ]
        
        has_heading_pattern = any(re.match(pattern, text) for pattern in heading_patterns)
        
        # Position analysis - headings are often left-aligned or have specific indentation
        is_left_aligned = element["relative_x"] < 0.2
        
        return has_heading_pattern or is_left_aligned
    
    def classify_heading_levels(self, heading_candidates, significant_sizes):
        """Classify headings into H1, H2, H3 levels."""
        if not heading_candidates or not significant_sizes:
            return []
        
        # Create size to level mapping
        size_to_level = {}
        for i, size in enumerate(significant_sizes[:3]):
            size_to_level[size] = f"H{i+1}"
        
        classified_headings = []
        
        for candidate in heading_candidates:
            size = candidate["size"]
            text = self.clean_text(candidate["text"])
            
            # Find closest significant size
            closest_size = min(significant_sizes, key=lambda x: abs(x - size))
            
            # Assign level based on closest size
            if closest_size in size_to_level:
                level = size_to_level[closest_size]
            else:
                # Fallback: larger sizes are higher levels
                if size >= significant_sizes[0]:
                    level = "H1"
                elif len(significant_sizes) > 1 and size >= significant_sizes[1]:
                    level = "H2"
                else:
                    level = "H3"
            
            classified_headings.append({
                "level": level,
                "text": text,
                "page": candidate["page"],
                "size": size,
                "element": candidate
            })
        
        return classified_headings
    
    def extract_headings(self, pages_data, title_text=None):
        """Extract headings using improved multi-factor analysis."""
        if not pages_data:
            return []
        
        # Flatten all elements
        all_elements = []
        for page_data in pages_data:
            all_elements.extend(page_data)
        
        if not all_elements:
            return []
        
        # Analyze font distribution
        significant_sizes = self.analyze_font_distribution(all_elements)
        
        # Estimate body text size
        all_sizes = [elem["size"] for elem in all_elements]
        body_text_size = statistics.mode(all_sizes) if all_sizes else 12
        
        # Find heading candidates
        heading_candidates = []
        
        for element in all_elements:
            if self.is_heading_candidate(element, significant_sizes, body_text_size):
                text = self.clean_text(element["text"])
                
                # Skip if it's the title
                if title_text and text == title_text:
                    continue
                
                heading_candidates.append(element)
        
        # Classify heading levels
        classified_headings = self.classify_heading_levels(heading_candidates, significant_sizes)
        
        # Separate H1 headings to include in title
        h1_headings = []
        other_headings = []
        
        for heading in classified_headings:
            if heading["level"] == "H1":
                h1_headings.append(heading)
            else:
                other_headings.append(heading)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_headings = []
        
        for heading in other_headings:
            key = (heading["level"], heading["text"])
            if key not in seen:
                seen.add(key)
                # Shift heading levels: H2 -> H1, H3 -> H2, etc.
                if heading["level"] == "H2":
                    new_level = "H1"
                elif heading["level"] == "H3":
                    new_level = "H2"
                elif heading["level"] == "H4":
                    new_level = "H3"
                else:
                    new_level = heading["level"]  # Keep as is for other levels
                
                unique_headings.append({
                    "level": new_level,
                    "text": heading["text"],
                    "page": heading["page"]
                })
        
        return unique_headings, h1_headings
    
    def process_pdf(self, pdf_path):
        """Process a single PDF file and extract outline."""
        try:
            start_time = time.time()
            
            # Open PDF
            doc = pymupdf.open(pdf_path)
            
            # Extract metadata
            metadata = doc.metadata
            
            # Extract text with metadata
            pages_data = self.extract_text_with_metadata(doc)
            
            # Extract title
            title = self.extract_title(pages_data, metadata)
            
            # Extract headings
            headings, h1_headings = self.extract_headings(pages_data, title)
            
            doc.close()
            
            # Use filename as fallback title
            if not title:
                title = Path(pdf_path).stem.replace('_', ' ').replace('-', ' ').title()
            
            # Include H1 headings in the title
            if h1_headings:
                h1_texts = [h["text"] for h in h1_headings]
                if title:
                    title = f"{title} - {' | '.join(h1_texts)}"
                else:
                    title = ' | '.join(h1_texts)
            
            processing_time = time.time() - start_time
            
            result = {
                "title": title,
                "outline": headings
            }
            
            if self.debug:
                result["processing_time"] = processing_time
                result["metadata"] = metadata
                result["h1_headings_included_in_title"] = [h["text"] for h in h1_headings]
            
            return result, processing_time
            
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            return {
                "title": Path(pdf_path).stem.replace('_', ' ').replace('-', ' ').title(),
                "outline": []
            }, 0
    
    def process_directory(self, input_dir="input", output_dir="Output1"):
        """Process all PDFs in input directory."""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Get all PDF files
        pdf_files = list(input_path.glob("*.pdf"))
        
        total_time = 0
        
        for pdf_file in pdf_files:
            result, processing_time = self.process_pdf(pdf_file)
            total_time += processing_time
            
            # Create output JSON file
            output_file = output_path / f"{pdf_file.stem}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"Processed {pdf_file.name} -> {output_file.name} ({processing_time:.2f}s)")
        
        print(f"Total processing time: {total_time:.2f}s")
        return total_time


def main():
    extractor = ModifiedPDFOutlineExtractor()
    
    # Check if running in Docker environment
    if os.path.exists("/app/input"):
        print("Running in Docker environment - processing /app/input directory")
        extractor.process_directory("/app/input", "/app/output")
    else:
        # Try to process any local directory as fallback
        if Path("input").exists():
            print("Processing local input directory")
            extractor.process_directory("input", "Output1")
        else:
            print("No input directory found. Please create an 'input' directory with PDF files.")


if __name__ == "__main__":
    main() 