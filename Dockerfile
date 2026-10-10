FROM python:3.12-slim AS build

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install .

FROM python:3.12-slim

ENV PATH="/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=build /venv /venv

# Run as a non-root, no-shell user; rootfs can be mounted read-only.
RUN useradd --system --no-create-home --uid 10001 app
USER 10001

EXPOSE 8080
CMD ["uvicorn", "storycover.main:app", "--host", "0.0.0.0", "--port", "8080"]
