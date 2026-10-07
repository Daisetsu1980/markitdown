#!/usr/bin/env python3
"""pptx の機械的な検査。

使い方: python3 scripts/check_pptx.py <file.pptx> [--min-pt 14]

拾うもの（[警告] は直す前提、[確認] は人の目で判断する）
  範囲外・重なり・文字のはみ出し（推定）・最小文字サイズ・コントラスト（明示色のみ）
  フッター／ページ番号・画像の代替テキスト・未導入フォント
  見出しの型（完結文・読点・分裂文）・箇条書きの文末の混在・発表者ノートの有無

文字のはみ出しは文字幅からの推定で、実際の描画とずれる。最終判断は描画画像で行う。
警告が1件でもあれば終了コード1。
"""
import argparse
import math
import re
import shutil
import subprocess
import sys
import unicodedata

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_COLOR_TYPE, MSO_FILL
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER

NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
EMU_PER_PT = 12700
DEFAULT_PT = 18.0

results = []  # (slide_no, level, message)


def add(n, level, msg):
    results.append((n, level, msg))


def walk(shapes):
    for sh in shapes:
        if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk(sh.shapes)
        else:
            yield sh


def box(sh):
    if None in (sh.left, sh.top, sh.width, sh.height):
        return None
    return (sh.left, sh.top, sh.left + sh.width, sh.top + sh.height)


def has_text(sh):
    return sh.has_text_frame and sh.text_frame.text.strip() != ""


def snippet(text, n=18):
    t = text.strip().replace("\n", " ")
    return t if len(t) <= n else t[:n] + "…"


def run_sizes(tf):
    return [r.font.size.pt for p in tf.paragraphs for r in p.runs if r.font.size]


def char_w(ch, size):
    return size if unicodedata.east_asian_width(ch) in ("F", "W", "A") else size * 0.55


def estimate_height(tf, width_pt):
    total = 0.0
    for p in tf.paragraphs:
        sizes = [r.font.size.pt for r in p.runs if r.font.size] or [DEFAULT_PT]
        size = max(sizes)
        text = "".join(r.text for r in p.runs)
        w = sum(char_w(c, size) for c in text)
        lines = max(1, math.ceil(w / max(width_pt, 1)))
        spacing = p.line_spacing if isinstance(p.line_spacing, float) else 1.2
        total += lines * size * spacing
    return total


def lum(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def solid_rgb(fill):
    try:
        if fill.type == MSO_FILL.SOLID and fill.fore_color.type == MSO_COLOR_TYPE.RGB:
            c = fill.fore_color.rgb
            return (c[0], c[1], c[2])
    except Exception:
        pass
    return None


def installed_fonts():
    if not shutil.which("fc-list"):
        return None
    out = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    names = set()
    for line in out.splitlines():
        for part in line.split(","):
            names.add(part.strip().lower())
    return names


SENTENCE_END = re.compile(r"(です|ます|ました|でした|である|だ|だった|った|いる|ない|する|れる|せる|できる|ある)。?$")
PAGE_NO = re.compile(r"^\s*(p\.?\s*)?\d+\s*(/\s*\d+)?\s*$", re.I)
CLEFT = re.compile(r"は、.+(だった|である|というものだ|のだ|だ)。?$")


def check_title(n, slide):
    title = slide.shapes.title
    if title is None or not title.has_text_frame:
        return
    t = title.text_frame.text.strip().replace("\n", " ")
    if not t:
        return
    if t.endswith(("？", "?")) or t.endswith("か"):
        return  # 問いかけ型
    if SENTENCE_END.search(t):
        add(n, "警告", f"見出しが完結文の疑い: 「{t}」（体言止めが既定）")
    if CLEFT.search(t):
        add(n, "警告", f"見出しが「Xは、Yだ」型の疑い: 「{t}」")
    if "、" in t:
        add(n, "確認", f"見出しに読点: 「{t}」（列挙でなく、間を作るための読点なら削る）")


def check_bullets(n, sh):
    paras = [p for p in sh.text_frame.paragraphs if "".join(r.text for r in p.runs).strip()]
    if len(paras) < 3:
        return
    by_level = {}
    for p in paras:
        text = "".join(r.text for r in p.runs).strip()
        kind = "文" if (text.endswith("。") or SENTENCE_END.search(text)) else "体言"
        by_level.setdefault(p.level, set()).add(kind)
    if any(len(v) > 1 for v in by_level.values()):
        add(n, "確認", f"箇条書きの文末が体言止めと文で混在: 「{snippet(sh.text_frame.text)}」")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("--min-pt", type=float, default=14.0,
                    help="本文の最小文字サイズ(pt)。既定14。DADSスキルの値に合わせて変える")
    args = ap.parse_args()

    prs = Presentation(args.pptx)
    sw, sh_ = prs.slide_width, prs.slide_height
    fonts_seen = {}
    fonts_installed = installed_fonts()

    for n, slide in enumerate(prs.slides, start=1):
        shapes = list(walk(slide.shapes))
        check_title(n, slide)

        # 背景色（明示されたときだけ）
        bg = None
        try:
            bg = solid_rgb(slide.background.fill)
        except Exception:
            pass
        bg = bg or (255, 255, 255)

        text_boxes = []
        for s in shapes:
            b = box(s)

            # フッター・ページ番号
            if s.is_placeholder:
                pt = s.placeholder_format.type
                if pt in (PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.SLIDE_NUMBER, PP_PLACEHOLDER.DATE):
                    add(n, "警告", f"フッター系のプレースホルダー（{pt}）がある")
            if s.has_text_frame and s._element.xpath('.//a:fld[@type="slidenum"]'):
                add(n, "警告", "ページ番号のフィールドがある")
            if has_text(s) and b and b[1] > sh_ * 0.92 and len(s.text_frame.text.strip()) < 60:
                if PAGE_NO.match(s.text_frame.text):
                    add(n, "警告", f"ページ番号らしきテキスト「{snippet(s.text_frame.text)}」が下端にある")
                else:
                    add(n, "確認", f"下端にテキスト「{snippet(s.text_frame.text)}」（フッター帯なら削る。出典や注記なら残す）")

            # 範囲外
            if b:
                tol_x, tol_y = sw * 0.005, sh_ * 0.005
                if b[0] < -tol_x or b[1] < -tol_y or b[2] > sw + tol_x or b[3] > sh_ + tol_y:
                    add(n, "警告", f"スライドの範囲外にはみ出し: {s.name}")

            # 画像の代替テキスト
            if s.shape_type == MSO_SHAPE_TYPE.PICTURE:
                nv = s._element.xpath(".//p:cNvPr")
                descr = nv[0].get("descr") if nv else None
                if not descr:
                    add(n, "警告", f"画像に代替テキストがない: {s.name}")

            if not has_text(s):
                continue
            tf = s.text_frame
            text_boxes.append(s)

            # 最小文字サイズ
            small = [z for z in run_sizes(tf) if z < args.min_pt]
            if small:
                add(n, "警告", f"{min(small):g}pt の文字（最小 {args.min_pt:g}pt）: 「{snippet(tf.text)}」")

            # フォント
            for r in (r for p in tf.paragraphs for r in p.runs):
                rpr = r._r.find("a:rPr", NS)
                if rpr is None:
                    continue
                for tag in ("latin", "ea"):
                    el = rpr.find(f"a:{tag}", NS)
                    if el is not None and el.get("typeface") and not el.get("typeface").startswith("+"):
                        fonts_seen.setdefault(el.get("typeface"), set()).add(n)

            # 文字のはみ出し（推定）
            if b:
                width_pt = (s.width - tf.margin_left - tf.margin_right) / EMU_PER_PT
                height_pt = (s.height - tf.margin_top - tf.margin_bottom) / EMU_PER_PT
                if tf.word_wrap is False:
                    longest = max(
                        (sum(char_w(c, max(run_sizes(tf) or [DEFAULT_PT])) for c in p.text) for p in tf.paragraphs),
                        default=0,
                    )
                    if longest > width_pt * 1.02:
                        add(n, "警告", f"文字が枠の幅を超える疑い（推定）: 「{snippet(tf.text)}」")
                else:
                    need = estimate_height(tf, width_pt)
                    if need > height_pt * 1.05:
                        add(n, "警告", f"文字が枠の高さを超える疑い（推定 {need:.0f}pt > {height_pt:.0f}pt）: 「{snippet(tf.text)}」")

            # コントラスト（文字色と塗りの両方が明示されたときだけ）
            fg_colors = set()
            for p in tf.paragraphs:
                for r in p.runs:
                    try:
                        if r.font.color.type == MSO_COLOR_TYPE.RGB:
                            c = r.font.color.rgb
                            fg_colors.add((c[0], c[1], c[2]))
                    except Exception:
                        pass
            if fg_colors:
                back = None
                try:
                    back = solid_rgb(s.fill)
                except Exception:
                    pass
                back = back or bg
                for fg in fg_colors:
                    r_ = ratio(fg, back)
                    if r_ < 4.5:
                        add(n, "警告", f"コントラスト比 {r_:.1f}:1（4.5:1 未満）: 「{snippet(tf.text)}」")

            check_bullets(n, s)

        # 重なり（テキストを持つ図形どうし。包含は除く）
        for i in range(len(text_boxes)):
            for j in range(i + 1, len(text_boxes)):
                a, b = box(text_boxes[i]), box(text_boxes[j])
                if not a or not b:
                    continue
                ix = min(a[2], b[2]) - max(a[0], b[0])
                iy = min(a[3], b[3]) - max(a[1], b[1])
                if ix <= 0 or iy <= 0:
                    continue
                inter = ix * iy
                small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
                if small == 0:
                    continue
                if inter / small > 0.97:
                    continue  # 片方がもう片方に収まっている
                if inter / small > 0.1:
                    add(n, "警告", f"テキストの枠が重なる: 「{snippet(text_boxes[i].text_frame.text)}」と「{snippet(text_boxes[j].text_frame.text)}」")

        # 発表者ノート
        if not (slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip()):
            add(n, "確認", "発表者ノートが空")

    # 未導入フォント
    if fonts_installed is not None:
        for name, pages in sorted(fonts_seen.items()):
            if name.lower() not in fonts_installed:
                add(min(pages), "確認", f"フォント「{name}」がこの環境にない（描画では置換される。使用ページ: {sorted(pages)}）。PowerPoint側に入っているかは別に確かめる")

    # 出力
    results.sort(key=lambda r: (r[0], r[1] != "警告"))
    for n, level, msg in results:
        print(f"スライド{n} [{level}] {msg}")
    warns = sum(1 for r in results if r[1] == "警告")
    infos = len(results) - warns
    print(f"--- 警告 {warns} 件、確認 {infos} 件（{len(prs.slides)} 枚）")
    sys.exit(1 if warns else 0)


if __name__ == "__main__":
    main()
