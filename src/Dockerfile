# 1. Use an official Python runtime as a parent image
FROM python:3.13.5-slim-bookworm

# 2. Set DEBIAN_FRONTEND to noninteractive to avoid prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# 3. Set timezone to Berlin
ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 4. Install system dependencies and Google Chrome in a single layer for a smaller image
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    unzip \
    tzdata \
    # Required Chrome dependencies
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 && \
    # Add Google's official GPG key
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome-keyring.gpg && \
    # Set up the repository
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    # Update apt and install Chrome from the repository
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    # Clean up to keep the image size down
    rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/apt/sources.list.d/google-chrome.list

# 5. Create a non-root user for better security
RUN useradd --create-home dockie
USER dockie
WORKDIR /home/dockie/

ENV PATH="/home/dockie/.local/bin:${PATH}"

# 6. Install UV package manager in user space
RUN pip install --user --no-cache-dir uv

# 7. Copy requirements first to leverage Docker layer caching
COPY --chown=dockie:dockie pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# 8. Copy the application files  
COPY --chown=dockie:dockie . ./

# 9. Install the correct chromedriver for the installed Chrome version
# This will be installed in the user's home directory, and seleniumbase will find it.
RUN uv run seleniumbase install chromedriver

# 10. Default command - shows help, can be overridden
CMD ["uv", "run", "python", "-m", "src.scrapers.main", "--help"]