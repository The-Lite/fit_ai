from __future__ import annotations

from sqlalchemy import Engine, bindparam, text
from sqlalchemy.exc import SQLAlchemyError

from fit_ai.domain.errors import RepositoryError
from fit_ai.domain.stores import StoreLocation


class StoreRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def list_locations(
        self, stores: tuple[str, ...] | None = None
    ) -> tuple[StoreLocation, ...]:
        sql = """SELECT store_location_id, store_brand AS store, store_name,
                        latitude, longitude
                 FROM public.store_locations"""
        parameters: dict[str, object] = {}
        statement = text(sql)
        if stores:
            statement = text(sql + " WHERE store_brand IN :stores").bindparams(
                bindparam("stores", expanding=True)
            )
            parameters["stores"] = tuple(sorted(set(stores)))
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(statement, parameters).mappings().all()
        except SQLAlchemyError as exc:
            raise RepositoryError("Store locations could not be read") from exc
        return tuple(
            StoreLocation.model_validate(dict(row))
            for row in sorted(
                rows, key=lambda item: (item["store"], item["store_location_id"])
            )
        )
