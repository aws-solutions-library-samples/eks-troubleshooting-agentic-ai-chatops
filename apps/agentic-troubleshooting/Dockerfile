FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager for EKS MCP server
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY main.py .
COPY memory_agent_main.py .

# Create non-root user for security but keep uvx accessible
RUN useradd -m -u 1000 agent && \
    cp -r /root/.local /home/agent/ && \
    chown -R agent:agent /home/agent/.local && \
    chown -R agent:agent /app

# Switch to non-root user
USER agent

# Update PATH for the agent user
ENV PATH="/home/agent/.local/bin:$PATH"

# Expose port (if needed for health checks)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the application
CMD ["python", "main.py"]