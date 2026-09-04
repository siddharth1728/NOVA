"""Controlled computer vision fallback targeting with stale screen protection."""

from datetime import datetime, timezone
import logging

from nova.control.automation.models import VisionTarget
from nova.errors import StaleVisionTargetError, VisionConfidenceError

logger = logging.getLogger("nova.control.automation.vision")


class VisionFallbackTargeter:
    """Validates vision-proposed targets against confidence and staleness constraints."""

    def __init__(
        self,
        min_confidence: float = 0.80,
        max_age_seconds: float = 6.0,
    ) -> None:
        self.min_confidence = min_confidence
        self.max_age_seconds = max_age_seconds

    def validate_and_resolve(self, target: VisionTarget) -> tuple[int, int]:
        """Validate candidate vision target and return center coordinates.

        Raises:
            VisionConfidenceError: When model confidence is below required threshold.
            StaleVisionTargetError: When screenshot timestamp is older than max permitted age.
        """
        # 1. Confidence threshold check
        if target.confidence < self.min_confidence:
            raise VisionConfidenceError(
                f"Vision candidate '{target.description}' rejected: confidence {target.confidence:.2f} "
                f"below required threshold {self.min_confidence:.2f}",
                details={
                    "confidence": target.confidence,
                    "threshold": self.min_confidence,
                    "target": target.model_dump(),
                },
            )

        # 2. Stale screen check
        try:
            cap_dt = datetime.fromisoformat(target.capture_timestamp)
            if cap_dt.tzinfo is None:
                cap_dt = cap_dt.replace(tzinfo=timezone.utc)
            now_dt = datetime.now(timezone.utc)
            age = (now_dt - cap_dt).total_seconds()

            if age > self.max_age_seconds:
                raise StaleVisionTargetError(
                    f"Vision target rejected: observation frame is stale ({age:.1f}s old, max permitted: {self.max_age_seconds:.1f}s)",
                    details={
                        "frame_age_seconds": age,
                        "max_permitted_age": self.max_age_seconds,
                        "screen_id": target.screen_id,
                    },
                )
        except (ValueError, TypeError) as ex:
            logger.warning("Could not parse vision target timestamp: %s", ex)

        logger.info(
            "Vision candidate approved: '%s' at (%d, %d) with confidence %.2f",
            target.description, target.x, target.y, target.confidence
        )
        return (target.x, target.y)

    validate_target = validate_and_resolve

