from pipeline import pipeline
from pipeline.observability import service_logging as slog
from pipeline.observability import setup
from pipeline.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    stop = setup(settings, component="pathway")
    try:
        slog.get_logger().info(
            "pipeline starting", window=settings.window_seconds
        )
        pipeline.run(settings)
    except Exception as exc:
        slog.get_logger().exception("pipeline stopped", exc)
        raise
    finally:
        stop()
