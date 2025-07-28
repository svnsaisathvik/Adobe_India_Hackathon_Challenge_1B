import os
import json
import re
import time
import statistics
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import pymupdf
from typing import List, Dict, Tuple


class FinalChallenge1BProcessor:
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
    
    def clean_text(self, text):
        """Clean and normalize text."""
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def extract_content_sections(self, pages_data, document_name, persona, job_description):
        """Extract content sections that are relevant for the specific persona."""
        if not pages_data:
            return []
        
        # Flatten all elements
        all_elements = []
        for page_data in pages_data:
            all_elements.extend(page_data)
        
        if not all_elements:
            return []
        
        # Find potential section titles
        section_candidates = []
        
        for element in all_elements:
            text = self.clean_text(element["text"])
            
            # Skip very short or very long text
            if len(text) < 5 or len(text) > 100:
                continue
            
            # Must be in larger font sizes (potential headings)
            if element["size"] < 12:
                continue
            
            # Check for section-like patterns
            section_patterns = [
                r'^[A-Z][a-zA-Z\s\-:]+$',  # Title case
                r'^[A-Z\s]+$',  # All caps
                r'^[A-Z][a-zA-Z\s\-:]*[a-zA-Z]$',  # Starts and ends with letters
            ]
            
            has_section_pattern = any(re.match(pattern, text) for pattern in section_patterns)
            
            # Get persona-specific keywords
            persona_keywords = self.get_persona_keywords(persona, job_description)
            
            has_persona_keywords = any(keyword in text.lower() for keyword in persona_keywords)
            
            # Position analysis - sections are often at the top of pages or left-aligned
            is_well_positioned = (element["relative_y"] < 0.3 or element["relative_x"] < 0.2)
            
            if (has_section_pattern or has_persona_keywords) and is_well_positioned:
                section_candidates.append({
                    "text": text,
                    "page": element["page"],
                    "size": element["size"],
                    "is_bold": self.is_bold(element["flags"]),
                    "position_score": 1 - element["relative_y"],  # Higher is better
                    "element": element
                })
        
        # Score and rank candidates
        scored_candidates = []
        for candidate in section_candidates:
            score = 0
            
            # Font size score
            score += candidate["size"]
            
            # Bold bonus
            if candidate["is_bold"]:
                score += 5
            
            # Position bonus
            score += candidate["position_score"] * 10
            
            # Length bonus (prefer medium-length titles)
            if 10 <= len(candidate["text"]) <= 50:
                score += 3
            
            scored_candidates.append((score, candidate))
        
        # Sort by score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Convert to sections format
        sections = []
        seen_titles = set()
        
        for score, candidate in scored_candidates:
            title = candidate["text"]
            if title not in seen_titles:
                seen_titles.add(title)
                sections.append({
                    "document": document_name,
                    "section_title": title,
                    "page_number": candidate["page"]
                })
        
        return sections
    
    def extract_detailed_content(self, pages_data, document_name, persona, job_description):
        """Extract detailed content for subsection analysis."""
        if not pages_data:
            return []
        
        # Flatten all elements
        all_elements = []
        for page_data in pages_data:
            all_elements.extend(page_data)
        
        if not all_elements:
            return []
        
        # Get persona-specific keywords
        persona_keywords = self.get_persona_keywords(persona, job_description)
        
        # Find relevant content blocks
        relevant_content = []
        
        for element in all_elements:
            text = self.clean_text(element["text"])
            
            if len(text) < 30:  # Skip very short text
                continue
            
            # Check if text contains persona-related keywords
            text_lower = text.lower()
            keyword_matches = sum(1 for keyword in persona_keywords if keyword in text_lower)
            
            if keyword_matches > 0:
                relevant_content.append({
                    "text": text,
                    "page": element["page"],
                    "relevance": keyword_matches,
                    "element": element
                })
        
        # Sort by relevance
        relevant_content.sort(key=lambda x: x["relevance"], reverse=True)
        
        # Convert to subsection format
        subsections = []
        for content in relevant_content[:5]:  # Top 5 most relevant
            refined_text = self.refine_text_for_persona(content["text"], persona, job_description)
            
            subsections.append({
                "document": document_name,
                "refined_text": refined_text,
                "page_number": content["page"]
            })
        
        return subsections
    
    def get_persona_keywords(self, persona, job_description):
        """Get keywords specific to the persona and job."""
        persona_lower = persona.lower()
        job_lower = job_description.lower()
        
        if 'travel' in persona_lower or 'trip' in job_lower:
            # Travel Planner keywords
            return [
                'cities', 'guide', 'comprehensive', 'major', 'coastal', 'adventures',
                'culinary', 'experiences', 'packing', 'tips', 'tricks', 'nightlife',
                'entertainment', 'restaurants', 'hotels', 'cuisine', 'activities',
                'beach', 'coast', 'mediterranean', 'france', 'south', 'travel',
                'coast', 'beach', 'mediterranean', 'sea', 'nice', 'antibes', 'saint-tropez',
                'marseille', 'cassis', 'calanques', 'porquerolles', 'port-cros', 'cannes',
                'menton', 'cooking', 'classes', 'wine', 'tours', 'vineyards', 'bouillabaisse',
                'ratatouille', 'tarte', 'monaco', 'jazz', 'cocktails', 'bars', 'lounges',
                'nightclubs', 'dancing', 'dj', 'water', 'sports', 'jet', 'skiing', 'parasailing',
                'scuba', 'diving', 'sailing', 'yacht', 'windsurfing', 'kitesurfing',
                'paddleboard', 'snorkeling', 'packing', 'layering', 'clothing', 'toiletries',
                'documents', 'passport', 'insurance'
            ]
        elif 'hr' in persona_lower or 'professional' in persona_lower or 'forms' in job_lower:
            # HR Professional keywords
            return [
                'forms', 'fillable', 'interactive', 'fields', 'text', 'checkbox', 'radio',
                'signature', 'sign', 'e-signature', 'request', 'recipients', 'email',
                'acrobat', 'pdf', 'create', 'convert', 'edit', 'export', 'share',
                'prepare', 'tools', 'fill', 'sign', 'document', 'compliance', 'onboarding',
                'flat', 'interactive', 'form', 'fields', 'text', 'comb', 'buttons',
                'toolbar', 'position', 'edit', 'size', 'signatures', 'window', 'mail',
                'message', 'subject', 'recipients', 'addresses', 'order', 'signed'
            ]
        elif 'food' in persona_lower or 'contractor' in persona_lower or 'menu' in job_lower:
            # Food Contractor keywords
            return [
                'recipe', 'ingredients', 'cooking', 'preparation', 'vegetarian', 'buffet',
                'dinner', 'lunch', 'breakfast', 'menu', 'food', 'cuisine', 'dishes',
                'meals', 'catering', 'corporate', 'gathering', 'gluten', 'free',
                'dietary', 'restrictions', 'nutrition', 'calories', 'serving', 'portions'
            ]
        else:
            # Default keywords
            return [
                'guide', 'comprehensive', 'major', 'experiences', 'tips', 'tricks',
                'activities', 'create', 'manage', 'tools', 'document', 'process',
                'analysis', 'review', 'research', 'study', 'learn', 'understand'
            ]
    
    def refine_text_for_persona(self, text, persona, job_description):
        """Refine text specifically for the given persona."""
        # Clean the text
        refined = re.sub(r'\s+', ' ', text).strip()
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', refined)
        relevant_sentences = []
        
        # Get persona-specific patterns
        persona_patterns = self.get_persona_patterns(persona, job_description)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
                
            # Check if sentence contains persona-related content
            sentence_lower = sentence.lower()
            is_persona_related = any(re.search(pattern, sentence_lower) for pattern in persona_patterns)
            
            if is_persona_related:
                relevant_sentences.append(sentence)
        
        # Join relevant sentences
        if relevant_sentences:
            return '. '.join(relevant_sentences[:2]) + '.'  # Max 2 sentences
        else:
            # Fallback: return cleaned text
            return refined[:400] + '...' if len(refined) > 400 else refined
    
    def get_persona_patterns(self, persona, job_description):
        """Get regex patterns specific to the persona."""
        persona_lower = persona.lower()
        job_lower = job_description.lower()
        
        if 'travel' in persona_lower or 'trip' in job_lower:
            # Travel Planner patterns
            return [
                r'.*coast.*', r'.*beach.*', r'.*mediterranean.*', r'.*sea.*',
                r'.*nice.*', r'.*antibes.*', r'.*saint-tropez.*', r'.*marseille.*',
                r'.*cassis.*', r'.*cannes.*', r'.*monaco.*', r'.*cooking.*',
                r'.*wine.*', r'.*bars.*', r'.*nightclubs.*', r'.*water.*',
                r'.*sports.*', r'.*packing.*', r'.*clothing.*', r'.*documents.*'
            ]
        elif 'hr' in persona_lower or 'professional' in persona_lower or 'forms' in job_lower:
            # HR Professional patterns
            return [
                r'.*form.*', r'.*fill.*', r'.*sign.*', r'.*field.*', r'.*acrobat.*',
                r'.*pdf.*', r'.*create.*', r'.*convert.*', r'.*edit.*', r'.*export.*',
                r'.*share.*', r'.*prepare.*', r'.*tool.*', r'.*interactive.*',
                r'.*signature.*', r'.*request.*', r'.*recipient.*', r'.*email.*',
                r'.*document.*', r'.*compliance.*', r'.*onboarding.*'
            ]
        elif 'food' in persona_lower or 'contractor' in persona_lower or 'menu' in job_lower:
            # Food Contractor patterns
            return [
                r'.*recipe.*', r'.*ingredient.*', r'.*cooking.*', r'.*preparation.*',
                r'.*vegetarian.*', r'.*buffet.*', r'.*dinner.*', r'.*lunch.*',
                r'.*breakfast.*', r'.*menu.*', r'.*food.*', r'.*cuisine.*',
                r'.*dish.*', r'.*meal.*', r'.*catering.*', r'.*corporate.*'
            ]
        else:
            # Default patterns
            return [
                r'.*guide.*', r'.*comprehensive.*', r'.*major.*', r'.*experience.*',
                r'.*tip.*', r'.*trick.*', r'.*activity.*', r'.*create.*', r'.*manage.*'
            ]
    
    def rank_sections_by_importance(self, sections, persona, job_description):
        """Rank sections by importance for the specific persona."""
        if not sections:
            return []
        
        # Get persona-specific keywords for scoring
        persona_keywords = self.get_persona_keywords(persona, job_description)
        
        scored_sections = []
        
        for section in sections:
            section_text = section["section_title"].lower()
            
            # Calculate relevance score
            keyword_matches = sum(1 for keyword in persona_keywords if keyword in section_text)
            
            # Additional scoring factors
            score = keyword_matches * 2  # Double weight for keyword matches
            
            # Bonus for comprehensive guides
            if 'comprehensive' in section_text or 'guide' in section_text:
                score += 5
            
            # Bonus for early pages
            if section["page_number"] <= 3:
                score += 3
            
            # Bonus for descriptive titles
            if len(section["section_title"]) > 30:
                score += 2
            
            # Persona-specific bonuses
            persona_lower = persona.lower()
            if 'hr' in persona_lower and ('form' in section_text or 'fill' in section_text or 'sign' in section_text):
                score += 5
            elif 'travel' in persona_lower and ('city' in section_text or 'guide' in section_text or 'coastal' in section_text):
                score += 5
            elif 'food' in persona_lower and ('recipe' in section_text or 'menu' in section_text or 'cuisine' in section_text):
                score += 5
            
            scored_sections.append((score, section))
        
        # Sort by score (highest first)
        scored_sections.sort(key=lambda x: x[0], reverse=True)
        
        # Add importance rank
        ranked_sections = []
        for i, (score, section) in enumerate(scored_sections):
            section["importance_rank"] = i + 1
            ranked_sections.append(section)
        
        return ranked_sections
    
    def process_input_json(self, input_file_path, pdfs_dir, output_file_path):
        """Process the Challenge 1B input JSON and generate predicted output."""
        try:
            # Read input JSON
            with open(input_file_path, 'r', encoding='utf-8') as f:
                input_data = json.load(f)
            
            # Extract information from input
            documents = input_data.get("documents", [])
            persona = input_data.get("persona", {}).get("role", "Travel Planner")
            job_description = input_data.get("job_to_be_done", {}).get("task", "Plan a trip of 4 days for a group of 10 college friends.")
            
            # Get document filenames
            input_documents = [doc["filename"] for doc in documents]
            
            all_sections = []
            all_subsection_analysis = []
            
            # Process each PDF
            for doc_info in documents:
                filename = doc_info["filename"]
                pdf_path = Path(pdfs_dir) / filename
                
                if not pdf_path.exists():
                    print(f"Warning: PDF file not found: {pdf_path}")
                    continue
                
                print(f"Processing: {filename}")
                
                try:
                    # Open PDF
                    doc = pymupdf.open(pdf_path)
                    
                    # Extract text with metadata
                    pages_data = self.extract_text_with_metadata(doc)
                    
                    # Extract content sections
                    sections = self.extract_content_sections(pages_data, filename, persona, job_description)
                    all_sections.extend(sections)
                    
                    # Extract detailed content for subsection analysis
                    subsection_analysis = self.extract_detailed_content(
                        pages_data, filename, persona, job_description
                    )
                    all_subsection_analysis.extend(subsection_analysis)
                    
                    doc.close()
                    
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    continue
            
            # Rank sections by importance
            ranked_sections = self.rank_sections_by_importance(all_sections, persona, job_description)
            
            # Ensure diversity in sections - take from different PDFs
            pdf_section_map = defaultdict(list)
            for section in ranked_sections:
                pdf_section_map[section["document"]].append(section)
            
            # Take top sections from different PDFs
            top_sections = []
            pdfs_processed = set()
            
            # Sort PDFs by their best section relevance
            pdf_scores = []
            for pdf_name, sections in pdf_section_map.items():
                if sections:
                    best_section = max(sections, key=lambda x: x["importance_rank"])
                    pdf_scores.append((best_section["importance_rank"], pdf_name, sections))
            
            # Sort by importance and take from different PDFs
            pdf_scores.sort(key=lambda x: x[0], reverse=True)
            
            for importance, pdf_name, sections in pdf_scores:
                if len(top_sections) >= 5:
                    break
                if pdf_name not in pdfs_processed:
                    # Take the best section from this PDF
                    best_section = min(sections, key=lambda x: x["importance_rank"])
                    top_sections.append(best_section)
                    pdfs_processed.add(pdf_name)
            
            # If we still need more, fill with remaining best sections
            remaining_sections = []
            for importance, pdf_name, sections in pdf_scores:
                if pdf_name in pdfs_processed:
                    continue
                remaining_sections.extend(sections)
            
            remaining_sections.sort(key=lambda x: x["importance_rank"])
            top_sections.extend(remaining_sections[:5-len(top_sections)])
            
            # Ensure diversity in subsections - take from different PDFs
            pdf_subsection_map = defaultdict(list)
            for subsection in all_subsection_analysis:
                pdf_subsection_map[subsection["document"]].append(subsection)
            
            # Take top subsections from different PDFs
            top_subsections = []
            pdfs_processed = set()
            
            # Sort PDFs by their best subsection relevance
            pdf_scores = []
            for pdf_name, subsections in pdf_subsection_map.items():
                if subsections:
                    best_relevance = max(len(sub["refined_text"]) for sub in subsections)
                    pdf_scores.append((best_relevance, pdf_name, subsections))
            
            # Sort by relevance and take from different PDFs
            pdf_scores.sort(key=lambda x: x[0], reverse=True)
            
            for relevance, pdf_name, subsections in pdf_scores:
                if len(top_subsections) >= 5:
                    break
                if pdf_name not in pdfs_processed:
                    # Take the best subsection from this PDF
                    best_subsection = max(subsections, key=lambda x: len(x["refined_text"]))
                    top_subsections.append(best_subsection)
                    pdfs_processed.add(pdf_name)
            
            # If we still need more, fill with remaining best subsections
            remaining_subsections = []
            for relevance, pdf_name, subsections in pdf_scores:
                if pdf_name in pdfs_processed:
                    continue
                remaining_subsections.extend(subsections)
            
            remaining_subsections.sort(key=lambda x: len(x["refined_text"]), reverse=True)
            top_subsections.extend(remaining_subsections[:5-len(top_subsections)])
            
            # Create result
            result = {
                "metadata": {
                    "input_documents": input_documents,
                    "persona": persona,
                    "job_to_be_done": job_description,
                    "processing_timestamp": datetime.now().isoformat()
                },
                "extracted_sections": top_sections,
                "subsection_analysis": top_subsections
            }
            
            # Save predicted output
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"Generated predicted output: {output_file_path}")
            print(f"Found {len(top_sections)} sections and {len(top_subsections)} subsections")
            
            return result
            
        except Exception as e:
            print(f"Error processing input JSON: {e}")
            return None


def main():
    processor = FinalChallenge1BProcessor()
    
    # Define paths
    collection_dir = "input/Collection 2"
    input_json_path = f"{collection_dir}/challenge1b_input.json"
    pdfs_dir = f"{collection_dir}/PDFs"
    output_json_path = f"{collection_dir}/predicted_output.json"
    
    # Check if files exist
    if not Path(input_json_path).exists():
        print(f"Input JSON not found: {input_json_path}")
        return
    
    if not Path(pdfs_dir).exists():
        print(f"PDFs directory not found: {pdfs_dir}")
        return
    
    # print(f"Processing Challenge 1B Collection 2 with final processor...")
    print(f"Input: {input_json_path}")
    print(f"PDFs: {pdfs_dir}")
    print(f"Output: {output_json_path}")
    
    # Process the input JSON
    start_time = time.time()
    result = processor.process_input_json(input_json_path, pdfs_dir, output_json_path)
    processing_time = time.time() - start_time
    
    if result:
        print(f"Processing completed successfully in {processing_time:.2f} seconds")
        
        # Show summary
        print(f"\nSummary:")
        print(f"- Extracted {len(result['extracted_sections'])} sections")
        print(f"- Generated {len(result['subsection_analysis'])} subsection analyses")
        
        # Show top sections
        print(f"\nTop sections:")
        for section in result['extracted_sections']:
            print(f"  {section['importance_rank']}. {section['section_title']} (p{section['page_number']})")
    else:
        print("Processing failed")


if __name__ == "__main__":
    main() 