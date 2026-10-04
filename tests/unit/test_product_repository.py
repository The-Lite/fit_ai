from datetime import date

import pytest

from fit_ai.config.food_catalog import CANDIDATE_LIMIT
from fit_ai.repositories.product_repository import ProductRepository


class Rows:
    def scalar_one_or_none(self):
        return date(2026, 9, 13)

    def mappings(self):
        return self

    def all(self):
        return []


class Connection:
    def __init__(self):
        self.calls = []
        self.options = {}

    def execution_options(self, **kwargs):
        self.options = kwargs
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, statement, parameters=None):
        self.calls.append((str(statement), parameters))
        return Rows()


class Engine:
    def __init__(self):
        self.connection = Connection()

    def connect(self):
        return self.connection


def test_repository_filters_snapshot_and_bounds_candidates_before_python():
    engine = Engine()
    repository = ProductRepository(engine)
    snapshot, groups = repository.search_batch(("chiken", "rice"), ("maxi",))
    assert snapshot == date(2026, 9, 13) and groups == ((), ())
    assert engine.connection.options == {"isolation_level": "REPEATABLE READ"}
    assert engine.connection.calls[0][0] == "SET TRANSACTION READ ONLY"
    selects = [
        (sql, params) for sql, params in engine.connection.calls if "LIMIT" in sql
    ]
    assert len(selects) == 2
    for sql, params in selects:
        assert "updated::date = (SELECT MAX(updated::date)" in sql
        assert "LIMIT :limit" in sql and params["limit"] == CANDIDATE_LIMIT
        assert "ORDER BY price" not in sql
        assert params["stores"] == ("maxi",)
    assert "% chicken %" in selects[0][1].values()
    assert "% poulet %" in selects[0][1].values()


def test_candidate_limit_cannot_be_overridden_to_scan_all_products():
    with pytest.raises(ValueError, match="candidate_limit"):
        ProductRepository(Engine()).search_current("rice", limit=68330)


def test_untrusted_search_text_is_bound_and_wildcards_are_normalized():
    engine = Engine()
    ProductRepository(engine).search_current("%; DROP TABLE products; --")
    sql, params = engine.connection.calls[-1]
    assert "DROP TABLE" not in sql
    assert not any(";" in str(value) for value in params.values())
