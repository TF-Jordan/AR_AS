"""
Scoring configuration service for the multi-tenant RaaS platform.

Manages per-tenant dynamic scoring criteria with versioning.
Each update creates a new version while deactivating the previous one.
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models_multitenant import ScoringConfig
from src.api.schemas_multitenant import ScoringCriterion

logger = logging.getLogger(__name__)


class ScoringConfigService:
    """Service for managing tenant scoring configurations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_config(
        self,
        tenant_id: str,
        criteria: List[ScoringCriterion],
        created_by: Optional[str] = None,
    ) -> ScoringConfig:
        """
        Create a new scoring configuration for a tenant.

        If an active config already exists, it is deactivated and
        the new config receives an incremented version number.

        Args:
            tenant_id: External tenant identifier.
            criteria: List of scoring criteria (weights must sum to 1.0).
            created_by: Optional admin username.

        Returns:
            The newly created ``ScoringConfig`` instance.

        Raises:
            ValueError: If criteria validation fails.
        """
        self.validate_criteria([c.model_dump() for c in criteria])

        # Determine next version and deactivate current active config
        current = await self.get_active_config(tenant_id)
        next_version = (current.version + 1) if current else 1

        if current:
            await self._deactivate_config(current.id)

        config = ScoringConfig(
            tenant_id=tenant_id,
            scoring_criteria=[c.model_dump() for c in criteria],
            version=next_version,
            is_active=True,
            created_by=created_by,
        )
        self.db.add(config)
        await self.db.flush()

        logger.info(
            "Scoring config created for tenant %s (version=%d, by=%s)",
            tenant_id,
            next_version,
            created_by or "system",
        )
        return config

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_active_config(self, tenant_id: str) -> Optional[ScoringConfig]:
        """
        Get the currently active scoring config for a tenant.

        Args:
            tenant_id: External tenant identifier.

        Returns:
            The active ``ScoringConfig``, or None if none exists.
        """
        stmt = (
            select(ScoringConfig)
            .where(
                ScoringConfig.tenant_id == tenant_id,
                ScoringConfig.is_active.is_(True),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_config_history(self, tenant_id: str) -> List[ScoringConfig]:
        """
        Get all scoring config versions for a tenant, newest first.

        Args:
            tenant_id: External tenant identifier.

        Returns:
            List of all ``ScoringConfig`` versions ordered by version descending.
        """
        stmt = (
            select(ScoringConfig)
            .where(ScoringConfig.tenant_id == tenant_id)
            .order_by(ScoringConfig.version.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_config(
        self,
        tenant_id: str,
        criteria: List[ScoringCriterion],
        created_by: Optional[str] = None,
    ) -> ScoringConfig:
        """
        Update the scoring config by creating a new version.

        The old active config is deactivated; a new config is created
        with an incremented version number.

        Args:
            tenant_id: External tenant identifier.
            criteria: New list of scoring criteria.
            created_by: Optional admin username.

        Returns:
            The newly created ``ScoringConfig`` version.

        Raises:
            ValueError: If criteria validation fails.
        """
        return await self.create_config(tenant_id, criteria, created_by)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_criteria(criteria: List[Dict]) -> bool:
        """
        Validate a list of scoring criteria dictionaries.

        Checks:
        - At least one criterion exists.
        - Each criterion has ``name``, ``weight``, and ``type`` fields.
        - ``type`` is either ``"system"`` or ``"custom"``.
        - Weights sum to 1.0 (with 0.01 tolerance).

        Args:
            criteria: List of criterion dictionaries.

        Returns:
            True if valid.

        Raises:
            ValueError: If any validation check fails.
        """
        if not criteria:
            raise ValueError("At least one scoring criterion is required")

        valid_types = {"system", "custom"}
        total_weight = 0.0

        for i, criterion in enumerate(criteria):
            # Required fields
            for field in ("name", "weight", "type"):
                if field not in criterion:
                    raise ValueError(
                        f"Criterion at index {i} is missing required field '{field}'"
                    )

            # Type validation
            if criterion["type"] not in valid_types:
                raise ValueError(
                    f"Criterion '{criterion['name']}' has invalid type "
                    f"'{criterion['type']}' (must be 'system' or 'custom')"
                )

            # Weight bounds
            weight = criterion["weight"]
            if not isinstance(weight, (int, float)) or weight < 0 or weight > 1:
                raise ValueError(
                    f"Criterion '{criterion['name']}' has invalid weight {weight} "
                    f"(must be between 0.0 and 1.0)"
                )

            total_weight += weight

        # Sum check
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(
                f"Scoring criteria weights must sum to 1.0 (got {total_weight:.4f})"
            )

        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _deactivate_config(self, config_id) -> None:
        """Deactivate a scoring config by its primary key."""
        stmt = (
            update(ScoringConfig)
            .where(ScoringConfig.id == config_id)
            .values(is_active=False)
        )
        await self.db.execute(stmt)
        await self.db.flush()
