from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

RUNS_DIR = Path(__file__).resolve().parents[3] / "runs"
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


def fetch_file(file_key: str) -> dict:
    return request_json(f"{API_BASE}/files/{file_key}?branch_data=true")


def fetch_file_meta(file_key: str) -> dict:
    return request_json(f"{API_BASE}/files/{file_key}/meta")


def fetch_file_comments(file_key: str) -> dict:
    return request_json(f"{API_BASE}/files/{file_key}/comments")


def fetch_file_components(file_key: str) -> dict:
    return request_json(f"{API_BASE}/files/{file_key}/components")


def fetch_file_styles(file_key: str) -> dict:
    return request_json(f"{API_BASE}/files/{file_key}/styles")


def fetch_file_image_fills(file_key: str) -> dict:
    return request_json(f"{API_BASE}/files/{file_key}/images")


def fetch_file_versions(file_key: str) -> dict:
    pages: list[dict] = []
    payload = request_json(f"{API_BASE}/files/{file_key}/versions")
    pages.append(payload)
    next_page = (payload.get("pagination") or {}).get("next_page")
    while next_page:
        payload = request_json(next_page)
        pages.append(payload)
        next_page = (payload.get("pagination") or {}).get("next_page")
    return {"pages": pages}


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


def collect_text_snippets(node: dict) -> list[str]:
    snippets: list[str] = []
    text = str(node.get("characters", "")).strip()
    if text:
        snippets.append(text)
    for child in node.get("children", []):
        if isinstance(child, dict):
            snippets.extend(collect_text_snippets(child))
    return snippets


def build_requirement_summary(node: dict) -> list[str]:
    seen: set[str] = set()
    summary: list[str] = []
    for snippet in collect_text_snippets(node):
        if snippet not in seen:
            seen.add(snippet)
            summary.append(snippet)
    return summary


def build_prototype_markdown(kind: str, source_url: str, node: dict, dev_resources: dict | None) -> str:
    requirement_summary = build_requirement_summary(node)
    lines = [
        f"# {kind} Figma 资料",
        "",
        f"- 来源：{source_url}",
        f"- 名称：{node.get('name', '')}",
        f"- 类型：{node.get('type', '')}",
        f"- Node ID：{node.get('id', '')}",
        f"- 尺寸：{node.get('absoluteBoundingBox')}",
        "",
    ]
    if requirement_summary:
        lines.extend(["## 需求信息", "", *[f"- {item}" for item in requirement_summary], ""])
    lines.extend([
        "## 结构摘要",
        "",
        *summarize_node(node),
        "",
    ])
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
        "requirements": build_requirement_summary(node),
        "image": image_url,
        "dev_resources": dev_resources,
    }


def write_json_file(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
            file_payload = fetch_file(file_key)
            file_meta = fetch_file_meta(file_key)
            file_comments = fetch_file_comments(file_key)
            file_components = fetch_file_components(file_key)
            file_styles = fetch_file_styles(file_key)
            file_image_fills = fetch_file_image_fills(file_key)
            file_versions = fetch_file_versions(file_key)
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
            write_json_file(node_dir / "file.json", file_payload)
            write_json_file(node_dir / "file_meta.json", file_meta)
            write_json_file(node_dir / "comments.json", file_comments)
            write_json_file(node_dir / "components.json", file_components)
            write_json_file(node_dir / "styles.json", file_styles)
            write_json_file(node_dir / "image_fills.json", file_image_fills)
            write_json_file(node_dir / "versions.json", file_versions)
            write_json_file(node_dir / "node.json", node_payload)
            write_json_file(node_dir / "dev_resources.json", dev_resources)
            write_json_file(node_dir / "manifest.json", layout)
            (node_dir / "layout.md").write_text(build_prototype_markdown(kind, link, document, dev_resources), encoding="utf-8")
            manifests.append(layout)
        except Exception as error:
            error_payload = {"source_url": link, "error": str(error)}
            write_json_file(node_dir / "manifest.json", error_payload)
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
    print("main:start", flush=True)
    # 直接在这里手动填写即可
    project = "figma"
    kind = "高真设计"
    prototype_url = "https://www.figma.com/design/Wri0aaE2EIaesO0u2LTDAS/%E8%BF%AD%E4%BB%A3%E7%89%88%E7%A4%BE%E5%8C%BA?node-id=2099-215&m=dev&focus-id=2099-215"
    high_fidelity_urls = [
        "https://www.figma.com/design/W0M3jAZpdBP7OdWfZwrqJE/%E7%A4%BE%E5%8C%BA%EF%BC%88%E6%AF%8F%E5%91%A8%E6%9B%B4%E6%96%B0%E7%89%88%EF%BC%89?node-id=1280-4791&m=dev&focus-id=1280-4791",
        "https://www.figma.com/design/W0M3jAZpdBP7OdWfZwrqJE/%E7%A4%BE%E5%8C%BA%EF%BC%88%E6%AF%8F%E5%91%A8%E6%9B%B4%E6%96%B0%E7%89%88%EF%BC%89?node-id=1280-5041&m=dev&focus-id=1280-5041",
        "https://www.figma.com/design/W0M3jAZpdBP7OdWfZwrqJE/%E7%A4%BE%E5%8C%BA%EF%BC%88%E6%AF%8F%E5%91%A8%E6%9B%B4%E6%96%B0%E7%89%88%EF%BC%89?node-id=1280-5197&m=dev&focus-id=1280-5197",
        "https://www.figma.com/design/W0M3jAZpdBP7OdWfZwrqJE/%E7%A4%BE%E5%8C%BA%EF%BC%88%E6%AF%8F%E5%91%A8%E6%9B%B4%E6%96%B0%E7%89%88%EF%BC%89?node-id=1593-952&m=dev&focus-id=1593-952",
        "https://www.figma.com/design/W0M3jAZpdBP7OdWfZwrqJE/%E7%A4%BE%E5%8C%BA%EF%BC%88%E6%AF%8F%E5%91%A8%E6%9B%B4%E6%96%B0%E7%89%88%EF%BC%89?node-id=1593-1307&m=dev&focus-id=1593-1307",
    ]
    links = [prototype_url] if kind == "需求原生" else [prototype_url, *high_fidelity_urls]
    try:
        print(f"fetch:start kind={kind} links={len(links)}", flush=True)
        out_dir = fetch_figma_links(",".join(links), project, kind)
    except Exception as error:
        print(f"fetch:error {error}", flush=True)
        print(f"ERROR: {error}")
        return 1
    print("fetch:done", flush=True)
    print(f"Figma 阶段目录：{out_dir}")
    print(f"原型文档：{out_dir / 'prototype.md'}")
    print(f"布局信息：{out_dir / 'figma_layout.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
