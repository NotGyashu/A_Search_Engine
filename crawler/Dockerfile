# Crawler Dockerfile
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    gcc \
    g++ \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy crawler source
COPY crawler/ ./crawler/
COPY data_pipeline/ ./data_pipeline/

# Build crawler
RUN cd crawler && \
    mkdir -p build && \
    cd build && \
    cmake .. && \
    make

# Install Python dependencies for data processing
RUN pip3 install pandas sqlite3 json

# Create output directory
RUN mkdir -p /app/data

# Copy scripts
COPY crawler/scripts/ ./scripts/

# Make scripts executable
RUN chmod +x ./scripts/*.sh

# Default command
CMD ["./scripts/crawl_and_process.sh"]
