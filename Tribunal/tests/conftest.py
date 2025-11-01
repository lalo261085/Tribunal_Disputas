from __future__ import annotations

import pytest

from tribunal import Settings, create_application


@pytest.fixture()
def settings(tmp_path):
    return Settings(
        data_dir=tmp_path,
        api_token=None,
        forbidden_words=("insulto1", "insulto2"),
    )


@pytest.fixture()
def app(settings):
    app = create_application(settings)
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()
