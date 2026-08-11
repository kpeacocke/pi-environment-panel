from __future__ import annotations

from pathlib import Path


def render_png(plan, output: str):
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("1", (800, 600), 1)
    draw = ImageDraw.Draw(image)

    def font(size):
        candidates = [
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if size >= 48 else ''}.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for candidate in candidates:
            if Path(candidate).exists():
                return ImageFont.truetype(candidate, max(12, int(size * 0.75)))
        return ImageFont.load_default()

    for op in plan.operations:
        if op.kind == "text":
            draw.text((op.x1, op.y1), op.text, fill=0, font=font(op.size))
        elif op.kind == "line":
            draw.line((op.x1, op.y1, op.x2, op.y2), fill=0, width=2)
        elif op.kind == "fill_rect":
            draw.rectangle((op.x1, op.y1, op.x2, op.y2), fill=0)

    image.save(output)
