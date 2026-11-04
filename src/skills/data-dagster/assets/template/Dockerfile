FROM python:3.12-slim AS build
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv pip install --system --no-cache .
COPY src ./src

FROM python:3.12-slim
RUN useradd --uid 10001 --create-home app \
    && mkdir -p /opt/dagster/home /var/lib/dagster-output \
    && chown -R app /opt/dagster/home /var/lib/dagster-output
COPY --from=build /usr/local /usr/local
COPY --from=build /app/src /app/src
COPY dagster.yaml workspace.yaml /opt/dagster/home/
ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1 DAGSTER_HOME=/opt/dagster/home
USER app
WORKDIR /opt/dagster/home
EXPOSE 3000
# webserver: dagster-webserver -h 0.0.0.0 -p 3000 -w workspace.yaml
# daemon:    dagster-daemon run -w workspace.yaml
CMD ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000", "-w", "workspace.yaml"]
