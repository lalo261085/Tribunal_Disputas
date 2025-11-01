from __future__ import annotations

import pytest

from tribunal import Settings, create_application


@pytest.fixture()
def settings(tmp_path):
    return Settings(
        ipfs_enabled=False,
        auto_start_ipfs_daemon=False,
        enable_pubsub_listener=False,
        state_dir=tmp_path,
    )


@pytest.fixture()
def app(settings):
    app, _ = create_application(settings)
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()
