FROM python:3.12-slim-trixie
RUN apt-get update && apt-get install -y --no-install-recommends git gh ca-certificates && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir uv
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
COPY skills ./skills
# GH_TOKEN (repo-scoped) lets gh push/PR and acts as git credential helper over https.
CMD ["sh", "-c", "[ -n \"$GH_TOKEN\" ] && gh auth setup-git; exec python worker.py"]
