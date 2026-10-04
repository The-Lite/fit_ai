from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Engine, bindparam, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from fit_ai.config.food_catalog import CANDIDATE_LIMIT
from fit_ai.domain.errors import RepositoryError
from fit_ai.domain.food_matching import query_aliases
from fit_ai.domain.products import Product

PRODUCT_COLUMNS = """id AS product_id, name, brand, size, unit_price, image,
category_id, price, store, discounted, prices, link, url, category_name,
updated, loaded_at"""


def normalized_sql(column: str) -> str:
    # Only constant column names. No database extension is required.
    return (
        "trim(regexp_replace(translate(replace(lower(coalesce("
        + column
        + ", '')), 'œ', 'oe'), "
        "'àáâäãåçèéêëìíîïñòóôöõùúûüýÿ', 'aaaaaaceeeeiiiinooooouuuuyy'), "
        "'[^a-z0-9]+', ' ', 'g'))"
    )


class ProductRepository:
    """Read verified fields from a consistent repository-selected snapshot."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_current_snapshot_date(self) -> date | None:
        try:
            with self._engine.connect() as connection:
                return self._snapshot(connection)
        except SQLAlchemyError as exc:
            raise RepositoryError("Current product snapshot could not be read") from exc

    @staticmethod
    def _snapshot(connection: Connection) -> date | None:
        return connection.execute(
            text("SELECT MAX(updated::date) FROM public.epiceries_products")
        ).scalar_one_or_none()

    def search_batch(
        self,
        queries: tuple[str, ...],
        stores: tuple[str, ...] | None = None,
        limit: int = CANDIDATE_LIMIT,
    ) -> tuple[date | None, tuple[tuple[Product, ...], ...]]:
        if not 1 <= limit <= CANDIDATE_LIMIT:
            raise ValueError("candidate_limit_out_of_range")
        try:
            with self._engine.connect().execution_options(
                isolation_level="REPEATABLE READ"
            ) as connection:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                snapshot = self._snapshot(connection)
                groups = tuple(
                    self._search(connection, query, stores, limit) for query in queries
                )
                return snapshot, groups
        except SQLAlchemyError as exc:
            raise RepositoryError("Current products could not be searched") from exc

    def search_current(
        self,
        query: str,
        stores: tuple[str, ...] | None = None,
        limit: int = 20,
    ) -> tuple[Product, ...]:
        return self.search_batch((query,), stores, limit)[1][0]

    def _search(
        self,
        connection: Connection,
        query: str,
        stores: tuple[str, ...] | None,
        limit: int,
    ) -> tuple[Product, ...]:
        _, aliases = query_aliases(query)
        if not aliases:
            return ()
        params: dict[str, object] = {"limit": limit}
        clauses, ranks = [], []
        for index, alias in enumerate(aliases):
            params[f"a{index}"] = f"% {alias} %"
            tokens = [
                token for token in alias.split() if token not in {"de", "d", "the"}
            ]
            token_clauses = []
            for token_index, token in enumerate(tokens):
                key = f"t{index}_{token_index}"
                params[key] = f"% {token} %"
                token_clauses.append(f"(' ' || normalized_name || ' ') LIKE :{key}")
            name_match = " AND ".join(token_clauses) or "FALSE"
            category_match = f"(' ' || normalized_category || ' ') LIKE :a{index}"
            brand_match = f"(' ' || normalized_brand || ' ') LIKE :a{index}"
            clauses.append(f"(({name_match}) OR {category_match} OR {brand_match})")
            ranks.append(
                f"CASE WHEN (' ' || normalized_name || ' ') LIKE :a{index} THEN 3 "
                f"WHEN ({name_match}) THEN 2 WHEN {category_match} THEN 1 ELSE 0 END"
            )
        sql = f"""WITH current_products AS (
            SELECT {PRODUCT_COLUMNS},
                   {normalized_sql("name")} AS normalized_name,
                   {normalized_sql("category_name")} AS normalized_category,
                   {normalized_sql("brand")} AS normalized_brand
            FROM public.epiceries_products
            WHERE updated::date = (SELECT MAX(updated::date) FROM public.epiceries_products)
        ) SELECT * FROM current_products WHERE ({" OR ".join(clauses)})"""
        if stores is not None:
            sql += " AND store IN :stores"
            params["stores"] = tuple(sorted(set(stores)))
        sql += f" ORDER BY GREATEST({', '.join(ranks)}) DESC, product_id LIMIT :limit"
        statement = text(sql)
        if stores is not None:
            statement = statement.bindparams(bindparam("stores", expanding=True))
        rows = connection.execute(statement, params).mappings().all()
        return tuple(self._map_product(dict(row)) for row in rows)

    def current_by_ids(
        self, ids: tuple[str, ...]
    ) -> tuple[date | None, tuple[Product, ...]]:
        """Rehydrate tool references; supplied prices/dates are not authoritative."""
        if len(ids) > 3000:
            raise ValueError("too_many_product_references")
        statement = text(f"""SELECT {PRODUCT_COLUMNS} FROM public.epiceries_products
            WHERE id IN :ids AND updated::date = (
                SELECT MAX(updated::date) FROM public.epiceries_products
            ) ORDER BY id""").bindparams(bindparam("ids", expanding=True))
        try:
            with self._engine.connect().execution_options(
                isolation_level="REPEATABLE READ"
            ) as connection:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                snapshot = self._snapshot(connection)
                rows = connection.execute(statement, {"ids": ids}).mappings().all()
                return snapshot, tuple(self._map_product(dict(row)) for row in rows)
        except SQLAlchemyError as exc:
            raise RepositoryError(
                "Current product references could not be read"
            ) from exc

    @staticmethod
    def _map_product(row: dict[str, object]) -> Product:
        for key in ("normalized_name", "normalized_category", "normalized_brand"):
            row.pop(key, None)
        if row.get("price") is not None:
            row["price"] = Decimal(str(row["price"]))
        return Product.model_validate(row)
