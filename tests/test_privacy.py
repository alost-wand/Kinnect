import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.main import app
import backend.utils.auth as auth_mod
import ai_privacy.pipeline as pipeline_mod


@pytest.fixture(autouse=True)
def override_deps():
    """Override authentication dependency for tests and restore after."""
    original = app.dependency_overrides.get(auth_mod.require_family)
    app.dependency_overrides[auth_mod.require_family] = lambda: {"family_id": "test-family", "sub": "tester"}
    yield
    # restore
    if original is None:
        app.dependency_overrides.pop(auth_mod.require_family, None)
    else:
        app.dependency_overrides[auth_mod.require_family] = original


def make_jpeg_bytes(color=(64, 128, 192)):
    img = Image.new("RGB", (64, 64), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_privacy_protect_endpoint(monkeypatch):
    # Monkeypatch the heavy pipeline to a lightweight identity that returns JPEG bytes
    def fake_process_image(img_bytes, blur_targets=True, adversarial_noise=True, use_pgd=False, fmt="JPEG"):
        # Ensure we received bytes and return a valid JPEG (identity)
        return img_bytes

    monkeypatch.setattr(pipeline_mod, "process_image", fake_process_image)

    client = TestClient(app)

    files = {"file": ("test.jpg", make_jpeg_bytes(), "image/jpeg")}
    data = {"blur_targets": "true", "adversarial_noise": "true", "use_pgd": "false"}

    resp = client.post("/privacy/protect", files=files, data=data)

    assert resp.status_code == 200, resp.text
    assert resp.headers.get("content-type") == "image/jpeg"
    assert resp.content is not None and len(resp.content) > 0
