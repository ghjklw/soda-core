from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

from soda.contracts.helpers.data_source_test_helper import DataSourceTestHelper


@pytest.fixture(scope="function")
def env_vars() -> dict:
    original_env_vars = dict(os.environ)
    yield os.environ
    os.environ.clear()
    os.environ.update(original_env_vars)


@pytest.fixture(scope="session")
def dot_env(project_root_dir: str):
    load_dotenv(f"{project_root_dir}/.env", override=True)


@pytest.fixture(scope="session")
def project_root_dir() -> str:
    project_root_dir = __file__[: -len("/tests/helpers/test_fixtures.py")]
    yield project_root_dir


@pytest.fixture(scope="session")
def data_source_test_helper() -> DataSourceTestHelper:
    data_source_test_helper: DataSourceTestHelper = DataSourceTestHelper.create()
    data_source_test_helper.start_test_session()
    exception: Exception | None = None
    try:
        yield data_source_test_helper
    except Exception as e:
        exception = e
    finally:
        data_source_test_helper.end_test_session(exception=exception)
