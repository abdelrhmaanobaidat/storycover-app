from storycover import gemini, storage


def _fake_cover(*_args, **_kwargs):
    return b"generated-image-bytes", "image/png"


def test_generate_happy_path(client, monkeypatch):
    monkeypatch.setattr(gemini, "generate_cover", _fake_cover)
    monkeypatch.setattr(storage, "upload_cover", lambda *_: "https://signed.example/cover")

    resp = client.post(
        "/api/generate",
        data={"title": "The Brave Little Cat"},
        files={"photo": ("cat.png", b"rawbytes", "image/png")},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "The Brave Little Cat"
    assert body["url"] == "https://signed.example/cover"
    assert body["object"].startswith("covers/")


def test_generate_rejects_non_image(client):
    resp = client.post(
        "/api/generate",
        data={"title": "x"},
        files={"photo": ("note.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_generate_requires_title(client):
    resp = client.post(
        "/api/generate",
        files={"photo": ("cat.png", b"rawbytes", "image/png")},
    )
    assert resp.status_code == 422


def test_generate_surfaces_model_failure(client, monkeypatch):
    def _boom(*_args, **_kwargs):
        raise gemini.CoverGenerationError("no image")

    monkeypatch.setattr(gemini, "generate_cover", _boom)
    resp = client.post(
        "/api/generate",
        data={"title": "x"},
        files={"photo": ("cat.png", b"rawbytes", "image/png")},
    )
    assert resp.status_code == 502
