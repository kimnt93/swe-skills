FROM python:3.12-slim AS build
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv pip install --system --no-cache .
COPY src ./src

FROM python:3.12-slim
RUN useradd --uid 10001 --no-create-home app && mkdir -p /var/lib/pw-state \
    && chown app /var/lib/pw-state
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /app/src /app/src
ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1
USER app
VOLUME /var/lib/pw-state
CMD ["python", "-m", "pipeline"]
