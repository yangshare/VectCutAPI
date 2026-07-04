import json

from PIL import Image


def _write_minimal_draft(draft_root, draft_id="draft_1"):
    draft_dir = draft_root / draft_id
    draft_dir.mkdir(parents=True)
    (draft_dir / "draft_info.json").write_text(
        json.dumps({"cover": None, "materials": {"drafts": []}}, ensure_ascii=False),
        encoding="utf-8",
    )
    return draft_dir


def _write_image(path, color, size=(32, 48)):
    Image.new("RGB", size, color).save(path)
    return path


def _load_info(draft_dir):
    return json.loads((draft_dir / "draft_info.json").read_text(encoding="utf-8"))


def test_add_cover_to_draft_imports_and_injects_local_cover(tmp_path):
    from vectcut.features.draft._cover_engine import add_cover_to_draft

    draft_dir = _write_minimal_draft(tmp_path)
    cover = _write_image(tmp_path / "cover.png", (10, 20, 30), size=(24, 36))

    add_cover_to_draft("draft_1", str(cover), draft_folder=str(tmp_path))

    info = _load_info(draft_dir)
    assert info["cover"]["cover_draft_id"].endswith("_material")
    assert len(info["materials"]["drafts"]) == 1

    cover_material = info["materials"]["drafts"][0]
    assert info["cover"]["cover_draft_id"] == cover_material["id"]
    video = cover_material["draft"]["materials"]["videos"][0]
    assert video["width"] == 24
    assert video["height"] == 36
    assert "{{" not in json.dumps(cover_material, ensure_ascii=False)
    assert (draft_dir / "draft_cover.jpg").is_file()
    assert (draft_dir / "Resources" / "cover" / f'{video["path"].rsplit("/", 1)[-1]}').is_file()


def test_add_cover_to_draft_draws_cover_text_into_preview(tmp_path):
    from vectcut.features.draft._cover_engine import add_cover_to_draft

    draft_dir = _write_minimal_draft(tmp_path)
    cover = _write_image(tmp_path / "white.png", (255, 255, 255), size=(240, 320))

    add_cover_to_draft("draft_1", str(cover), cover_text="Cover", draft_folder=str(tmp_path))

    preview = Image.open(draft_dir / "draft_cover.jpg").convert("RGB")
    dark_pixels = sum(1 for pixel in preview.getdata() if min(pixel) < 80)
    assert dark_pixels > 0


def test_add_cover_to_draft_replaces_previous_cover_material(tmp_path):
    from vectcut.features.draft._cover_engine import add_cover_to_draft

    draft_dir = _write_minimal_draft(tmp_path)
    first = _write_image(tmp_path / "first.png", (255, 0, 0))
    second = _write_image(tmp_path / "second.png", (0, 255, 0))

    add_cover_to_draft("draft_1", str(first), draft_folder=str(tmp_path))
    first_info = _load_info(draft_dir)
    first_cover_id = first_info["cover"]["cover_draft_id"]

    add_cover_to_draft("draft_1", str(second), draft_folder=str(tmp_path))

    info = _load_info(draft_dir)
    cover_ids = [item["id"] for item in info["materials"]["drafts"]]
    assert len(cover_ids) == 1
    assert cover_ids[0] == info["cover"]["cover_draft_id"]
    assert cover_ids[0] != first_cover_id
