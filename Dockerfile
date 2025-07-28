# Use a lightweight Python base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy source code and input folder
COPY final_challenge1b_processor.py modified_pdf_extractor.py ./
COPY input ./input
COPY requirements.txt ./

# Install system dependencies for pymupdf
RUN apt-get update && \
    apt-get install -y build-essential libmupdf-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt


# Default command: process Collection 1 as an example
CMD ["python", "final_challenge1b_processor.py"]
