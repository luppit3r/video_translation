from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Tuple, Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor


DEFAULT_YT_SIZE = (1280, 720)
DEFAULT_IG_SIZE = (1080, 1080)


def load_font(preferred_paths: list[Path], size: int) -> ImageFont.FreeTypeFont:
    for p in preferred_paths:
        try:
            if p.exists():
                return ImageFont.truetype(str(p), size=size)
        except Exception:
            continue
    # Fallback to PIL default bitmap font (limited)
    return ImageFont.load_default()


def fit_text(draw: ImageDraw.ImageDraw, text: str, font_paths: list[Path], max_width: int, base_size: int, min_size: int = 28) -> ImageFont.FreeTypeFont:
    size = base_size
    while size >= min_size:
        font = load_font(font_paths, size)
        w, _ = draw.textbbox((0, 0), text, font=font)[2:]
        if w <= max_width:
            return font
        size -= 2
    return load_font(font_paths, min_size)


def add_centered_text(
    img: Image.Image,
    text_lines: list[Tuple[str, Tuple[int, int, int]]],
    font_paths: list[Path],
    left_margin: int,
    top_y: int,
    max_width: int,
    line_spacing: int,
) -> None:
    draw = ImageDraw.Draw(img)
    y = top_y
    for text, color in text_lines:
        font = fit_text(draw, text, font_paths, max_width, base_size=88)
        text_w, text_h = draw.textbbox((0, 0), text, font=font)[2:]
        x = left_margin + (max_width - text_w) // 2
        # Outline for readability
        outline_color = (0, 0, 0)
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        draw.text((x, y), text, font=font, fill=color)
        y += text_h + line_spacing


def add_logo(img: Image.Image, logo_path: Optional[Path], max_width_ratio: float = 0.16, margin: int = 24, position: str = "bottom_right") -> None:
    if not logo_path:
        return
    if not logo_path.exists():
        return
    try:
        logo = Image.open(logo_path).convert("RGBA")
    except Exception:
        return
    W, H = img.size
    max_w = int(W * max_width_ratio)
    scale = max_w / logo.width
    new_size = (max(1, int(logo.width * scale)), max(1, int(logo.height * scale)))
    logo = logo.resize(new_size, Image.LANCZOS)

    if position == "bottom_right":
        x = W - margin - logo.width
        y = H - margin - logo.height
    elif position == "bottom_left":
        x = margin
        y = H - margin - logo.height
    elif position == "top_left":
        x = margin
        y = margin
    else:
        x = W - margin - logo.width
        y = margin

    img.alpha_composite(logo, (x, y))


def add_background(img: Image.Image, background_path: Optional[Path], blur: int = 0, darken: float = 0.0) -> None:
    if background_path and background_path.exists():
        try:
            bg = Image.open(background_path).convert("RGB").resize(img.size, Image.LANCZOS)
            if blur > 0:
                bg = bg.filter(ImageFilter.GaussianBlur(radius=blur))
        except Exception:
            bg = Image.new("RGB", img.size, (20, 22, 26))
    else:
        bg = Image.new("RGB", img.size, (20, 22, 26))

    overlay = Image.new("RGBA", img.size, (0, 0, 0, int(255 * darken)))
    base = Image.new("RGBA", img.size)
    base.paste(bg, (0, 0))
    base.alpha_composite(overlay)
    img.paste(base.convert("RGB"))


def draw_frame_border(img: Image.Image, color: Optional[str], thickness: int = 8) -> None:
    if not color:
        return
    color = color.strip()
    if color.lower() in {"none", "no", "off", "0"}:
        return
    try:
        rgb = ImageColor.getrgb(color)
    except Exception:
        # Try to parse #RRGGBB without '#'
        try:
            rgb = ImageColor.getrgb(f"#{color}")
        except Exception:
            return
    draw = ImageDraw.Draw(img)
    W, H = img.size
    # rectangle outline uses center of stroke, so inset by half thickness
    inset = max(1, thickness // 2)
    draw.rectangle([inset, inset, W - 1 - inset, H - 1 - inset], outline=rgb, width=thickness)


# ====== Helpers for wrapping and multiline drawing ======
def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for w in words[1:]:
        test = current + " " + w
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            lines.append(current)
            current = w
    lines.append(current)
    return lines


def draw_multiline_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    color: tuple[int, int, int],
    left_margin: int,
    top_y: int,
    max_width: int,
    line_gap: int,
    pseudo_bold: bool = False,
) -> int:
    lines = wrap_text(draw, text, font, max_width)
    y = top_y
    for line in lines:
        w, h = draw.textbbox((0, 0), line, font=font)[2:]
        x = left_margin + (max_width - w) // 2
        if pseudo_bold:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                draw.text((x + dx, y + dy), line, font=font, fill=color)
        draw.text((x, y), line, font=font, fill=color)
        y += h + line_gap
    return y - top_y


# ====== Optional corners ======
def _draw_corners(draw: ImageDraw.ImageDraw, W: int, H: int, length: int = 170, thickness: int = 12, color=(255, 255, 255)) -> None:
    # Top-left
    draw.rectangle([ (36, 36), (36 + length, 36 + thickness) ], fill=color)
    draw.rectangle([ (36, 36), (36 + thickness, 36 + length) ], fill=color)
    # Top-right
    draw.rectangle([ (W - 36 - length, 36), (W - 36, 36 + thickness) ], fill=color)
    draw.rectangle([ (W - 36 - thickness, 36), (W - 36, 36 + length) ], fill=color)
    # Bottom-left
    draw.rectangle([ (36, H - 36 - thickness), (36 + length, H - 36) ], fill=color)
    draw.rectangle([ (36, H - 36 - length), (36 + thickness, H - 36) ], fill=color)
    # Bottom-right
    draw.rectangle([ (W - 36 - length, H - 36 - thickness), (W - 36, H - 36) ], fill=color)
    draw.rectangle([ (W - 36 - thickness, H - 36 - length), (W - 36, H - 36) ], fill=color)


def _draw_rec(draw: ImageDraw.ImageDraw, W: int, top_y: int, font_paths: list[Path]) -> None:
    # Wyłączone: nie rysujemy REC – placeholder pozostaje dla kompatybilności
    return


def generate_edupanda(
    output_path: Path,
    title: str,
    highlight: str,
    subtitle: str,
    size: Tuple[int, int],
    logo_path: Optional[Path],
    background_path: Optional[Path],
    show_for_beginners: bool = False,
    show_rec: bool = True,
    font_paths: Optional[list[Path]] = None,
    size1: int = 132,
    size2: int = 112,
    size3: int = 88,
    show_corners: bool = False,
    left_pct: int = 8,
    right_pct: int = 8,
    top_pct: int = 32,
    bottom_pct: int = 18,
    line_gap_pct: int = 2,
    darken: float = 0.0,
    highlight_bold: bool = True,
    subtitle_bold: bool = False,
    highlight_underline: bool = False,
    subtitle_underline: bool = True,
) -> Path:
    W, H = size
    img = Image.new("RGBA", (W, H))
    add_background(img, background_path, blur=0, darken=darken)

    if font_paths is None:
        font_paths = [
            Path("C:/Windows/Fonts/SegoeUI-Bold.ttf"),
            Path("C:/Windows/Fonts/Arial.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
            Path("/Library/Fonts/Arial Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ]

    draw = ImageDraw.Draw(img)
    if show_corners:
        _draw_corners(draw, W, H)
    # Nie rysujemy REC ani brandu, bo używasz gotowego tła z brandingiem

    # Nie doklejamy logo ani napisu EduPanda – tło ma branding

    # FOR BEGINNERS
    if show_for_beginners:
        fb_font = load_font(font_paths, 78)
        fb_text = "FOR BEGINNERS"
        ftw, fth = draw.textbbox((0, 0), fb_text, font=fb_font)[2:]
        draw.text(((W - ftw) // 2, int(H * 0.30)), fb_text, font=fb_font, fill=(220, 18, 28))

    # Obszar tekstu i czcionki
    left_margin = int(W * (left_pct / 100.0))
    right_margin = int(W * (right_pct / 100.0))
    max_width = W - left_margin - right_margin
    area_top = int(H * (top_pct / 100.0))
    area_bottom = int(H * (1.0 - bottom_pct / 100.0))
    line_gap = int(H * (line_gap_pct / 100.0))

    title_font = load_font(font_paths, size1)
    hl_font = load_font(font_paths, size2)
    sub_font = load_font(font_paths, size3)

    # Pomiar wysokości linii (wrap-aware) do wyśrodkowania pionowego
    meter = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    h1 = draw_multiline_centered(meter, title, title_font, (0,0,0), 0, 0, max_width, line_gap)
    h2 = draw_multiline_centered(meter, highlight, hl_font, (0,0,0), 0, 0, max_width, line_gap)
    h3 = draw_multiline_centered(meter, subtitle, sub_font, (0,0,0), 0, 0, max_width, line_gap)
    total_h = h1 + h2 + h3 + 2 * line_gap
    start_y = max(area_top, area_top + (area_bottom - area_top - total_h) // 2)

    y = start_y
    y += draw_multiline_centered(draw, title, title_font, (240, 248, 255), left_margin, y, max_width, line_gap)
    y += line_gap
    y += draw_multiline_centered(draw, highlight, hl_font, (255, 255, 255), left_margin, y, max_width, line_gap, pseudo_bold=bool(highlight_bold))
    # Opcjonalne podkreślenie linii 2
    if highlight_underline and highlight.strip():
        last_line_hl = wrap_text(draw, highlight, hl_font, max_width)[-1]
        lhw, lhh = draw.textbbox((0, 0), last_line_hl, font=hl_font)[2:]
        hlx = left_margin + (max_width - lhw) // 2
        hly = y - lhh  # y wskazuje już po narysowaniu; cofnij wysokość linii
        draw.rectangle([(hlx, hly + lhh + 6), (hlx + lhw, hly + lhh + 10)], fill=(255, 255, 255))
    y += line_gap
    before = y
    used = draw_multiline_centered(draw, subtitle, sub_font, (0, 191, 255), left_margin, y, max_width, line_gap, pseudo_bold=bool(subtitle_bold))
    # Opcjonalne podkreślenie linii 3
    if subtitle_underline and subtitle.strip():
        last_line = wrap_text(draw, subtitle, sub_font, max_width)[-1]
        lw, lh = draw.textbbox((0, 0), last_line, font=sub_font)[2:]
        lx = left_margin + (max_width - lw) // 2
        ly = before + used - lh
        draw.rectangle([(lx, ly + lh + 6), (lx + lw, ly + lh + 10)], fill=(0, 191, 255))

    # Frame at the end to be on top
    # Note: frame is applied by caller via draw_frame_border
    img = img.convert("RGB")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="JPEG", quality=95)
    return output_path


def generate_thumbnail(
    output_path: Path,
    subject: str,
    section: str,
    topic: str,
    size: Tuple[int, int] = DEFAULT_YT_SIZE,
    background_path: Optional[Path] = None,
    logo_path: Optional[Path] = None,
    font_paths: Optional[list[Path]] = None,
    palette: Optional[dict] = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    W, H = size
    img = Image.new("RGBA", (W, H))
    add_background(img, background_path, blur=6, darken=0.42)

    # Defaults
    if font_paths is None:
        font_paths = [
            Path("C:/Windows/Fonts/SegoeUI-Bold.ttf"),
            Path("C:/Windows/Fonts/Arial.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
            Path("/Library/Fonts/Arial Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ]
    if palette is None:
        palette = {
            "subject": (255, 215, 0),      # złoty
            "section": (135, 206, 250),     # jasny niebieski
            "topic": (255, 255, 255),       # biały
        }

    # Text block area
    left_margin = int(W * 0.08)
    right_margin = int(W * 0.08)
    max_width = W - left_margin - right_margin
    top_y = int(H * 0.18)
    line_spacing = int(H * 0.03)

    lines = [
        (subject.strip(), palette["subject"]),
        (section.strip(), palette["section"]),
        (topic.strip(), palette["topic"]),
    ]
    add_centered_text(img, lines, font_paths, left_margin, top_y, max_width, line_spacing)

    # Logo
    add_logo(img, logo_path, max_width_ratio=0.14, margin=22, position="bottom_right")

    # Save
    img = img.convert("RGB")
    img.save(output_path, format="JPEG", quality=92)
    return output_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate YouTube/Instagram thumbnails from text fields.")
    p.add_argument("--subject", help="Nazwa przedmiotu (tryb klasyczny)")
    p.add_argument("--section", help="Nazwa działu (tryb klasyczny)")
    p.add_argument("--topic", help="Konkretne zagadnienie (tryb klasyczny)")
    p.add_argument("--output", required=True, help="Ścieżka wyjściowa .jpg")
    p.add_argument("--platform", choices=["youtube", "instagram"], default="youtube")
    p.add_argument("--background", help="Opcjonalny obraz tła")
    p.add_argument("--logo", help="Opcjonalne logo (np. logo.png)")
    p.add_argument("--palette", help="Opcjonalny JSON {subject:[r,g,b], section:[r,g,b], topic:[r,g,b]}")
    p.add_argument("--font", action="append", help="Ścieżka do czcionki .ttf (możesz podać wiele)")
    p.add_argument("--frame_color", help="Kolor ramki np. #FFFFFF lub 'cyan' (opcjonalnie)")
    p.add_argument("--frame_size", type=int, default=8, help="Grubość ramki w px (domyślnie 8)")
    # Preset EduPanda
    p.add_argument("--preset", choices=["edupanda"], help="Użyj gotowego preset'u (edupanda)")
    p.add_argument("--title", help="Preset: duży tytuł (np. INTERNAL FORCES)")
    p.add_argument("--highlight", help="Preset: wyróżnione słowo (np. IN BEAMS / IN TRUSS)")
    p.add_argument("--subtitle", help="Preset: podtytuł (np. EXAMPLE 1 / Node equilibrium method)")
    p.add_argument("--for_beginners", action="store_true", help="Preset: pokaż napis FOR BEGINNERS (czerwony)")
    p.add_argument("--no_rec", action="store_true", help="Preset: ukryj znacznik REC")
    # optional font sizes for 1/2/3 lines
    p.add_argument("--title_size", type=int, help="Rozmiar czcionki linii 1")
    p.add_argument("--highlight_size", type=int, help="Rozmiar czcionki linii 2")
    p.add_argument("--subtitle_size", type=int, help="Rozmiar czcionki linii 3")
    # padding and corners
    p.add_argument("--show_corners", action="store_true", help="Rysuj rogi L")
    p.add_argument("--left_pct", type=int, default=8, help="Lewy margines [% szerokości]")
    p.add_argument("--right_pct", type=int, default=8, help="Prawy margines [% szerokości]")
    p.add_argument("--top_pct", type=int, default=32, help="Górny obszar tekstu [% wysokości]")
    p.add_argument("--bottom_pct", type=int, default=18, help="Dolny margines obszaru tekstu [% wysokości]")
    p.add_argument("--line_gap_pct", type=int, default=2, help="Odstęp między liniami [% wysokości]")
    p.add_argument("--darken", type=float, default=0.0, help="Przyciemnienie tła 0..0.8")
    # style flags
    p.add_argument("--highlight_bold", choices=["true","false"], help="Czy linia 2 ma być pogrubiona")
    p.add_argument("--subtitle_bold", choices=["true","false"], help="Czy linia 3 ma być pogrubiona")
    p.add_argument("--highlight_underline", choices=["true","false"], help="Czy linia 2 ma być podkreślona")
    p.add_argument("--subtitle_underline", choices=["true","false"], help="Czy linia 3 ma być podkreślona")
    return p.parse_args()


def main():
    args = parse_args()
    size = DEFAULT_YT_SIZE if args.platform == "youtube" else DEFAULT_IG_SIZE
    background = Path(args.background) if args.background else None
    logo = Path(args.logo) if args.logo else None
    fonts = [Path(f) for f in args.font] if args.font else None
    out = Path(args.output)

    if args.preset == "edupanda":
        if not (args.title and args.highlight and args.subtitle):
            raise SystemExit("Dla preset'u edupanda podaj --title --highlight --subtitle")
        def _to_bool(val, default):
            if val is None:
                return default
            return str(val).lower() == "true"
        result = generate_edupanda(
            output_path=out,
            title=args.title,
            highlight=args.highlight,
            subtitle=args.subtitle,
            size=size,
            logo_path=logo,
            background_path=background,
            show_for_beginners=bool(args.for_beginners),
            show_rec=not bool(args.no_rec),
            font_paths=fonts,
            size1=args.title_size or 132,
            size2=args.highlight_size or 112,
            size3=args.subtitle_size or 88,
            show_corners=bool(args.show_corners),
            left_pct=args.left_pct,
            right_pct=args.right_pct,
            top_pct=args.top_pct,
            bottom_pct=args.bottom_pct,
            line_gap_pct=args.line_gap_pct,
            darken=max(0.0, min(0.8, args.darken)),
            highlight_bold=_to_bool(args.highlight_bold, True),
            subtitle_bold=_to_bool(args.subtitle_bold, False),
            highlight_underline=_to_bool(args.highlight_underline, False),
            subtitle_underline=_to_bool(args.subtitle_underline, True),
        )
        # Draw frame if requested
        if args.frame_color:
            img = Image.open(out).convert("RGB")
            draw_frame_border(img, args.frame_color, max(1, args.frame_size))
            img.save(out, format="JPEG", quality=95)
    else:
        palette = None
        if args.palette:
            try:
                raw = json.loads(args.palette)
                palette = {
                    k: tuple(int(c) for c in raw[k]) for k in ["subject", "section", "topic"] if k in raw
                }
            except Exception:
                pass
        result = generate_thumbnail(
            output_path=out,
            subject=args.subject or "",
            section=args.section or "",
            topic=args.topic or "",
            size=size,
            background_path=background,
            logo_path=logo,
            font_paths=fonts,
            palette=palette,
        )
        if args.frame_color:
            img = Image.open(out).convert("RGB")
            draw_frame_border(img, args.frame_color, max(1, args.frame_size))
            img.save(out, format="JPEG", quality=95)
    print(str(out.resolve()))


if __name__ == "__main__":
    main()


