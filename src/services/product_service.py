"""
Product service for managing products in Qdrant.

Handles product upload, deletion, and statistics for multi-tenant
product catalogs stored entirely in Qdrant vector collections.
"""

import logging
from typing import Any, Dict, List

from src.modules.module2_recommendation.embeddings import (
    EmbeddingService,
    get_embedding_service,
)
from src.modules.module2_recommendation.vector_store import (
    MultiTenantVectorStore,
    get_vector_store,
)

logger = logging.getLogger(__name__)


class ProductService:
    """
    Service for managing products in Qdrant.

    Products are stored entirely in Qdrant payloads with their
    vector embeddings. No PostgreSQL product table is involved.
    """

    def __init__(
        self,
        vector_store: MultiTenantVectorStore | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        self.vectors = vector_store or get_vector_store()
        self.embeddings = embedding_service or get_embedding_service()

    async def upload_products(
        self,
        tenant_id: str,
        products: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Validate, vectorize, and upload products to the tenant's Qdrant collection.

        Each product dict must have:
            - product_id: str
            - description: str
            - metadata: dict (optional custom fields for scoring)

        Args:
            tenant_id: External tenant identifier.
            products: List of product dicts.

        Returns:
            Dict with upload statistics.
        """
        if not products:
            return {"tenant_id": tenant_id, "uploaded": 0, "errors": 0}

        logger.info(
            "Uploading %d products for tenant %s", len(products), tenant_id
        )

        # Validate products
        valid_products = []
        errors = []
        for i, product in enumerate(products):
            if not product.get("product_id"):
                errors.append(f"Product at index {i} missing 'product_id'")
                continue
            if not product.get("description"):
                errors.append(
                    f"Product '{product.get('product_id', i)}' missing 'description'"
                )
                continue
            valid_products.append(product)

        if errors:
            logger.warning(
                "Product validation errors for tenant %s: %s",
                tenant_id,
                errors,
            )

        if not valid_products:
            return {
                "tenant_id": tenant_id,
                "uploaded": 0,
                "errors": len(errors),
                "error_details": errors,
            }

        # Generate embeddings for all descriptions
        descriptions = [p["description"] for p in valid_products]
        vectors = self.embeddings.encode_batch_for_qdrant(descriptions)

        # Prepare product dicts with vectors
        products_with_vectors = []
        for product, vector in zip(valid_products, vectors):
            products_with_vectors.append(
                {
                    "product_id": product["product_id"],
                    "description": product["description"],
                    "vector": vector,
                    "metadata": product.get("metadata", {}),
                }
            )

        # Upsert into Qdrant
        count = self.vectors.add_products(tenant_id, products_with_vectors)

        logger.info(
            "Upload complete for tenant %s: %d products uploaded, %d errors",
            tenant_id,
            count,
            len(errors),
        )

        result = {
            "tenant_id": tenant_id,
            "uploaded": count,
            "errors": len(errors),
        }
        if errors:
            result["error_details"] = errors
        return result

    async def delete_product(
        self, tenant_id: str, product_id: str
    ) -> Dict[str, Any]:
        """
        Delete a product from the tenant's Qdrant collection.

        Args:
            tenant_id: External tenant identifier.
            product_id: Product ID to delete.

        Returns:
            Dict with deletion status.
        """
        success = self.vectors.delete_product(tenant_id, product_id)

        if success:
            logger.info(
                "Product %s deleted from tenant %s", product_id, tenant_id
            )
        else:
            logger.error(
                "Failed to delete product %s from tenant %s",
                product_id,
                tenant_id,
            )

        return {
            "tenant_id": tenant_id,
            "product_id": product_id,
            "deleted": success,
        }

    async def get_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get collection statistics for a tenant.

        Args:
            tenant_id: External tenant identifier.

        Returns:
            Dict with collection statistics.
        """
        return self.vectors.get_collection_stats(tenant_id)
