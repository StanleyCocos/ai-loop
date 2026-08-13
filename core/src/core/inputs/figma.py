from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

RUNS_DIR = Path(__file__).resolve().parents[5] / "runs"
API_BASE = "https://api.figma.com/v1"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "_", text).strip("_")
    return slug or "project"


def create_run_dir(project_name: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return RUNS_DIR / f"{timestamp}_{slugify(project_name)}"


def parse_figma_links(raw: str) -> list[str]:
    return [normalize_figma_url(link.strip()) for link in raw.split(",") if link.strip()]


def normalize_figma_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    if "node-id" not in query and "focus-id" in query:
        query["node-id"] = query["focus-id"]
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query, doseq=True)))


def parse_figma_url(url: str) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    file_key = ""
    for index, part in enumerate(parts):
        if part in {"design", "file"} and index + 1 < len(parts):
            file_key = parts[index + 1]
            break
    if not file_key:
        raise ValueError(f"无法从链接解析 file key: {url}")
    query = urllib.parse.parse_qs(parsed.query)
    node_id = (query.get("node-id") or query.get("focus-id") or [""])[0].replace("-", ":")
    if not node_id:
        raise ValueError(f"无法从链接解析 node-id: {url}")
    return file_key, node_id


def request_json(url: str) -> dict:
    token = os.environ.get("FIGMA_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("请先设置环境变量：export FIGMA_ACCESS_TOKEN='你的 Figma token'")
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Figma API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Figma API request failed: {exc.reason}") from exc


def fetch_file_node(file_key: str, node_id: str) -> dict:
    url = (
        f"{API_BASE}/files/{file_key}/nodes?ids={urllib.parse.quote(node_id, safe='')}"
        f"&geometry=paths&depth=20"
    )
    payload = request_json(url)
    return payload.get("nodes", {}).get(node_id, {})


def fetch_dev_resources(file_key: str, node_id: str) -> dict:
    url = f"{API_BASE}/files/{file_key}/dev_resources?node_ids={urllib.parse.quote(node_id, safe='')}"
    return request_json(url)


def fetch_image_url(file_key: str, node_id: str) -> str | None:
    url = f"{API_BASE}/images/{file_key}?ids={urllib.parse.quote(node_id, safe='')}&format=png&scale=2"
    payload = request_json(url)
    return (payload.get("images", {}) or {}).get(node_id)


def compact_node(node: dict) -> dict:
    result = {
        "id": node.get("id"),
        "name": node.get("name"),
        "type": node.get("type"),
        "visible": node.get("visible"),
        "absoluteBoundingBox": node.get("absoluteBoundingBox"),
        "absoluteRenderBounds": node.get("absoluteRenderBounds"),
        "layoutMode": node.get("layoutMode"),
        "primaryAxisAlignItems": node.get("primaryAxisAlignItems"),
        "counterAxisAlignItems": node.get("counterAxisAlignItems"),
        "primaryAxisSizingMode": node.get("primaryAxisSizingMode"),
        "counterAxisSizingMode": node.get("counterAxisSizingMode"),
        "paddingLeft": node.get("paddingLeft"),
        "paddingRight": node.get("paddingRight"),
        "paddingTop": node.get("paddingTop"),
        "paddingBottom": node.get("paddingBottom"),
        "itemSpacing": node.get("itemSpacing"),
        "fills": node.get("fills"),
        "strokes": node.get("strokes"),
        "strokeWeight": node.get("strokeWeight"),
        "cornerRadius": node.get("cornerRadius"),
        "characters": node.get("characters"),
        "style": node.get("style"),
        "effects": node.get("effects"),
        "constraints": node.get("constraints"),
        "componentId": node.get("componentId"),
        "componentProperties": node.get("componentProperties"),
        "children": [compact_node(child) for child in node.get("children", []) if isinstance(child, dict)],
    }
    return {key: value for key, value in result.items() if value not in (None, [], {}, "")}


def summarize_node(node: dict, level: int = 0) -> list[str]:
    pad = "  " * level
    lines = [f"{pad}- {node.get('name', '')} [{node.get('type', '')}] {node.get('id', '')}"]
    box = node.get("absoluteBoundingBox") or {}
    if box:
        lines.append(f"{pad}  pos=({box.get('x')}, {box.get('y')}), size=({box.get('width')} x {box.get('height')})")
    if node.get("layoutMode"):
        lines.append(
            f"{pad}  layout={node.get('layoutMode')}, spacing={node.get('itemSpacing')}, "
            f"padding=({node.get('paddingTop')}, {node.get('paddingRight')}, {node.get('paddingBottom')}, {node.get('paddingLeft')})"
        )
    if node.get("characters"):
        lines.append(f"{pad}  text={node.get('characters')}")
    for child in node.get("children", []):
        lines.extend(summarize_node(child, level + 1))
    return lines


def build_prototype_markdown(kind: str, source_url: str, node: dict, dev_resources: dict | None) -> str:
    lines = [
        f"# {kind} Figma 资料",
        "",
        f"- 来源：{source_url}",
        f"- 名称：{node.get('name', '')}",
        f"- 类型：{node.get('type', '')}",
        f"- Node ID：{node.get('id', '')}",
        f"- 尺寸：{node.get('absoluteBoundingBox')}",
        "",
        "## 结构摘要",
        "",
        *summarize_node(node),
        "",
    ]
    if dev_resources:
        lines.extend(["## Dev Resources", "", json.dumps(dev_resources, ensure_ascii=False, indent=2), ""])
    return "\n".join(lines)


def build_layout_payload(kind: str, source_url: str, file_key: str, node_id: str, node: dict, image_url: str | None, dev_resources: dict | None) -> dict:
    return {
        "kind": kind,
        "source_url": source_url,
        "file_key": file_key,
        "node_id": node_id,
        "node": compact_node(node),
        "image": image_url,
        "dev_resources": dev_resources,
    }


def fetch_figma_links(raw_links: str, project: str, kind: str) -> Path:
    links = parse_figma_links(raw_links)
    if not links:
        raise ValueError("请传入 Figma 链接，多个链接用英文逗号分割。")

    out_dir = create_run_dir(project) / slugify(kind)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifests: list[dict] = []

    for index, link in enumerate(links, start=1):
        node_dir = out_dir / f"node_{index}"
        node_dir.mkdir(parents=True, exist_ok=True)
        try:
            file_key, node_id = parse_figma_url(link)
            node_payload = fetch_file_node(file_key, node_id)
            document = node_payload.get("document", {}) if isinstance(node_payload, dict) else {}
            try:
                dev_resources = fetch_dev_resources(file_key, node_id)
            except Exception as error:
                dev_resources = {"error": str(error)}

            image_url = None
            try:
                image_url = fetch_image_url(file_key, node_id)
            except Exception as error:
                image_url = None
                dev_resources = dev_resources or {}
                dev_resources["image_error"] = str(error)

            image_path = None
            if image_url:
                raw_dir = node_dir / "raw"
                raw_dir.mkdir(parents=True, exist_ok=True)
                file_name = f"{slugify(document.get('name') or node_id)}.png"
                image_path = str(raw_dir / file_name)
                (raw_dir / file_name).write_bytes(urllib.request.urlopen(urllib.request.Request(image_url), timeout=60).read())

            layout = build_layout_payload(kind, link, file_key, node_id, document, image_path, dev_resources)
            (node_dir / "node.json").write_text(json.dumps(node_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            (node_dir / "dev_resources.json").write_text(json.dumps(dev_resources, ensure_ascii=False, indent=2), encoding="utf-8")
            (node_dir / "manifest.json").write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
            (node_dir / "layout.md").write_text(
                build_prototype_markdown(kind, link, document, dev_resources),
                encoding="utf-8",
            )
            manifests.append(layout)
        except Exception as error:
            error_payload = {"source_url": link, "error": str(error)}
            (node_dir / "manifest.json").write_text(json.dumps(error_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            manifests.append(error_payload)

    (out_dir / "input.json").write_text(
        json.dumps({"project": project, "kind": kind, "links": links}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "figma_layout.json").write_text(json.dumps(manifests, ensure_ascii=False, indent=2), encoding="utf-8")
    if manifests and "node" in manifests[0]:
        first_node = manifests[0]["node"]
        (out_dir / "prototype.md").write_text(
            build_prototype_markdown(kind, links[0], first_node, manifests[0].get("dev_resources")),
            encoding="utf-8",
        )
    else:
        (out_dir / "prototype.md").write_text(f"# {kind} Figma 资料\n\n无可用节点。\n", encoding="utf-8")
    return out_dir


def main() -> int:
    kind = input("请输入类型（需求原生/高真设计，默认高真设计）：").strip() or "高真设计"
    links = input(f"请输入 {kind} Figma 链接，多个用英文逗号分割：").strip()
    project = input("请输入项目名（直接回车默认 figma）：").strip() or "figma"
    try:
        out_dir = fetch_figma_links(links, project, kind)
    except Exception as error:
        print(f"ERROR: {error}")
        return 1
    print(f"Figma 阶段目录：{out_dir}")
    print(f"原型文档：{out_dir / 'prototype.md'}")
    print(f"布局信息：{out_dir / 'figma_layout.json'}")
    return 0
