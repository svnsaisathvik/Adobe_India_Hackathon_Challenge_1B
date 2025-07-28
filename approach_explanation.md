# Approach Explanation: Intelligent Document Analyst for Persona-based Section Extraction

## Overview
This solution is designed to act as an intelligent document analyst that extracts and prioritizes the most relevant sections from a collection of PDFs, tailored to a specific persona and their job-to-be-done. The methodology is generic and robust, allowing it to generalize across diverse document types (research papers, textbooks, reports, etc.), personas (researcher, student, analyst, etc.), and tasks.

## Methodology

### 1. Input Handling
- The script reads an input JSON file (e.g., `challenge1b_input.json`) that specifies the document collection, persona, and job-to-be-done.
- The input directory and collection can be changed by modifying the `collection_dir` variable in `final_challenge1b_processor.py` (see the `main()` function). By default, it is set to `input/Collection 2`.

### 2. PDF Parsing and Metadata Extraction
- Each PDF is opened using the `pymupdf` library, which allows for detailed extraction of text, font size, style, and position for every text span on every page.
- The script builds a rich metadata structure for each page, capturing not just the text but also its formatting and layout context.

### 3. Section and Subsection Identification
- **Section Extraction:**
  - The script identifies potential section titles by looking for text spans with large font sizes, bold formatting, and specific positional heuristics (e.g., top of the page, left-aligned).
  - It uses regex patterns to match typical section title formats and checks for the presence of persona/job-specific keywords.
  - Each candidate is scored based on font size, boldness, position, and length, and the top candidates are selected as sections.
- **Subsection Analysis:**
  - The script searches for content blocks containing persona/job-specific keywords, prioritizing longer and more relevant text spans.
  - It further refines these blocks by extracting sentences that match persona-specific patterns, ensuring the output is concise and relevant.

### 4. Persona and Task Adaptation
- The script dynamically generates keyword and pattern lists based on the persona and job description, allowing it to adapt its extraction logic to different domains and user needs.
- This ensures that, for example, a "PhD Researcher" looking for "methodologies" will get different sections than a "Student" looking for "key concepts."

### 5. Ranking and Diversity
- Extracted sections are ranked by importance using a scoring system that considers keyword matches, comprehensiveness, page number, and title descriptiveness.
- The script ensures diversity by selecting top sections and subsections from different PDFs, not just the highest-scoring ones overall.

### 6. Output Generation
- The final output is a JSON file (e.g., `predicted_output.json`) containing:
  - Metadata (input documents, persona, job, timestamp)
  - Extracted sections (with document, page, title, and importance rank)
  - Subsection analysis (with document, refined text, and page number)
- **Output Location:** The predicted output is saved in the same collection directory as the input JSON (e.g., `input/Collection 2/predicted_output.json`).

## Customization
- **Change Input Directory:**
  - Edit the `collection_dir` variable in the `main()` function of `final_challenge1b_processor.py` to point to your desired input collection (e.g., `input/Collection 1`).
- **View Predicted Output:**
  - The output JSON will be written to the same collection directory as the input, named `predicted_output.json`.

## Summary
This approach leverages a combination of text extraction, formatting analysis, persona-driven keyword matching, and ranking heuristics to deliver a flexible, domain-agnostic solution for extracting the most relevant document sections for any user and task. The code is modular and can be easily extended to support new personas, document types, or extraction strategies as needed.
