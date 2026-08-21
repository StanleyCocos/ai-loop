from __future__ import annotations

from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

from src.core.inputs.figma import build_prototype_markdown, fetch_figma_links, main


class FigmaInputsTestCase(unittest.TestCase):
    def test_build_prototype_markdown_includes_requirement_summary_from_text_nodes(self) -> None:
        node = {
            "name": "需求原型",
            "type": "FRAME",
            "id": "1",
            "children": [
                {"name": "标题", "type": "TEXT", "id": "1:1", "characters": "发布帖子"},
                {"name": "说明", "type": "TEXT", "id": "1:2", "characters": "支持图片和视频"},
            ],
        }

        markdown = build_prototype_markdown("需求原生", "https://example.com", node, None)

        self.assertIn("## 需求信息", markdown)
        self.assertIn("发布帖子", markdown)
        self.assertIn("支持图片和视频", markdown)

    def test_main_fetches_prototype_doc_before_high_fidelity_nodes(self) -> None:
        captured: list[str] = []

        def fake_fetch_figma_links(raw_links: str, project: str, kind: str) -> Path:
            captured.append(raw_links)
            return Path("/tmp/out")

        with (
            patch("src.core.inputs.figma.fetch_figma_links", side_effect=fake_fetch_figma_links),
            patch("src.core.inputs.figma.parse_figma_links", side_effect=lambda raw: [item for item in raw.split(",") if item]),
            patch("builtins.print"),
        ):
            self.assertEqual(main(), 0)

        links = captured[0].split(",")
        self.assertTrue(links[0].startswith("https://www.figma.com/design/Wri0aaE2EIaesO0u2LTDAS/"))

    def test_fetch_figma_links_persists_raw_figma_responses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            def fake_request_json(url: str) -> dict:
                if "/nodes?" in url:
                    return {"nodes": {"1:2": {"document": {"name": "页面", "id": "1:2"}}}}
                if "/dev_resources" in url:
                    return {"dev_resources": [{"url": "https://example.com"}]}
                if "/images/" in url:
                    return {"images": {"1:2": "https://example.com/image.png"}}
                if url.startswith("https://api.figma.com/v1/files/file_key?branch_data=true"):
                    return {"name": "完整文件"}
                if url.endswith("/files/file_key/meta"):
                    return {"file": {"name": "文件元信息"}}
                if url.endswith("/files/file_key/comments"):
                    return {"comments": [{"id": "c1"}]}
                if url.endswith("/files/file_key/components"):
                    return {"status": 200, "meta": {"components": []}}
                if url.endswith("/files/file_key/styles"):
                    return {"status": 200, "meta": {"styles": []}}
                if url.endswith("/files/file_key/images"):
                    return {"images": {"r1": "https://example.com/fill.png"}}
                if url.endswith("/files/file_key/versions"):
                    return {"versions": [{"id": "v1"}], "pagination": {}}
                raise AssertionError(url)

            class FakeResponse:
                def read(self) -> bytes:
                    return b"png"

            with (
                patch("src.core.inputs.figma.create_run_dir", return_value=temp_path),
                patch("src.core.inputs.figma.parse_figma_url", return_value=("file_key", "1:2")),
                patch("src.core.inputs.figma.request_json", side_effect=fake_request_json),
                patch("src.core.inputs.figma.urllib.request.urlopen", return_value=FakeResponse()),
            ):
                out_dir = fetch_figma_links("https://www.figma.com/design/file_key/test?node-id=1-2", "demo", "高真设计")

            node_dir = out_dir / "node_1"
            self.assertTrue((node_dir / "file.json").exists())
            self.assertTrue((node_dir / "file_meta.json").exists())
            self.assertTrue((node_dir / "comments.json").exists())
            self.assertTrue((node_dir / "components.json").exists())
            self.assertTrue((node_dir / "styles.json").exists())
            self.assertTrue((node_dir / "image_fills.json").exists())
            self.assertTrue((node_dir / "versions.json").exists())
