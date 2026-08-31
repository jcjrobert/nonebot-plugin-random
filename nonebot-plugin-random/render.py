from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Sequence

import jinja2
from nonebot_plugin_htmlrender import html_to_pic

from .models import PoolView


template_path = Path(__file__).parent / "templates"
env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(template_path),
    enable_async=True,
    autoescape=jinja2.select_autoescape(["html", "xml"]),
)


async def render_pool_manager(
    title: str,
    pools: List[PoolView],
    detailed: bool,
    help_sections: Sequence[Dict[str, Any]],
) -> bytes:
    template = env.get_template("pool_manager.html")
    content = await template.render_async(
        title=title,
        pools=pools,
        detailed=detailed,
        help_sections=help_sections,
    )
    return await html_to_pic(
        content,
        wait=0,
        viewport={"width": 1000, "height": 200},
        template_path=f"file://{template_path.absolute()}",
    )
