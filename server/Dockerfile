FROM python:3.13-slim

# uv installs the Python packages listed in pyproject.toml / uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv

# Show print() output in `docker compose logs` right away.
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked
COPY . .

CMD ["uv", "run", "--locked", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
