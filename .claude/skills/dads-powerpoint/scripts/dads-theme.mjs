// DADS values are from assets/dads-slide-tokens.json; slide roles are adaptations.
// This module does not import Artifact Tool or install runtime dependencies.
import { readFileSync } from 'node:fs';

export const tokens = JSON.parse(readFileSync(new URL('../assets/dads-slide-tokens.json', import.meta.url), 'utf8'));
export const ptToPx = (pt) => pt * 96 / 72;

function rgb(hex) {
  if (!/^#[0-9a-f]{6}$/i.test(hex)) throw new Error(`Expected opaque #RRGGBB, got ${hex}`);
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
}

export function contrastRatio(foreground, background) {
  const luminance = (hex) => rgb(hex).map((v) => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
    .reduce((s, v, i) => s + v * [0.2126, 0.7152, 0.0722][i], 0);
  const a = luminance(foreground), b = luminance(background);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

export function assertContrast(foreground, background, minimum = 4.5) {
  const ratio = contrastRatio(foreground, background);
  if (ratio < minimum) throw new Error(`Contrast ${ratio.toFixed(2)}:1 < ${minimum}:1 (${foreground} / ${background})`);
  return ratio;
}

export function createDadsTheme(Presentation, options = {}) {
  const spec = tokens.slideAdaptation;
  const colors = Object.fromEntries(Object.entries(spec.roles).map(([role, key]) => [role, tokens.officialPrimitives[key].value]));
  Object.assign(colors, options.colors ?? {});
  Object.values(colors).forEach(rgb);
  const font = options.font ?? spec.font.preferred;
  const width = options.width ?? spec.canvasPx.width;
  const height = options.height ?? spec.canvasPx.height;
  const presentation = Presentation.create({ slideSize: { width, height } });
  presentation.theme.colorScheme = {
    name: 'DADS slide adaptation',
    themeColors: {
      accent1: colors.primary, accent2: colors.series2, accent3: colors.series3,
      accent4: colors.series4, accent5: colors.error, accent6: colors.warning,
      bg1: colors.background, bg2: colors.surface, tx1: colors.text, tx2: colors.muted,
      dk1: '#000000', dk2: colors.text, lt1: colors.background, lt2: colors.surface,
      hlink: colors.primary, folHlink: colors.series3,
    },
  };
  for (const [a, b] of [['text', 'background'], ['muted', 'background'], ['primary', 'background'],
    ['text', 'surface'], ['primary', 'primarySurface'], ['success', 'successSurface'],
    ['error', 'errorSurface'], ['warning', 'warningSurface']]) assertContrast(colors[a], colors[b]);

  const checkBounds = ({ left, top, width: w, height: h }) => {
    if (![left, top, w, h].every(Number.isFinite) || w <= 0 || h <= 0 || left < 0 || top < 0 || left + w > width + 0.01 || top + h > height + 0.01) {
      throw new Error(`Invalid slide bounds: ${JSON.stringify({ left, top, width: w, height: h })}`);
    }
  };
  const text = (slide, value, position, style = {}) => {
    checkBounds(position);
    const size = style.pt ?? spec.fontPt.body;
    const foreground = style.color ?? colors.text;
    const background = style.background ?? colors.background;
    assertContrast(foreground, background);
    const shape = slide.shapes.add({
      geometry: 'textbox', name: style.name ?? 'text', position,
      fill: 'none', line: { fill: 'none', width: 0, style: 'solid' },
    });
    shape.text = value;
    shape.text.style = {
      typeface: style.font ?? font, fontSize: ptToPx(size), bold: style.bold ?? false,
      color: foreground, alignment: style.align ?? 'left', verticalAlignment: 'top',
      lineSpacing: style.lineHeight ?? spec.lineHeight.body, autoFit: 'none',
      wrap: style.wrap ?? 'square', insets: { top: 0, right: 0, bottom: 0, left: 0 },
    };
    return shape;
  };
  const rule = (slide, position, color = colors.primary) => {
    checkBounds(position);
    return slide.shapes.add({ geometry: 'rect', name: 'divider', position, fill: color,
      line: { fill: 'none', width: 0, style: 'solid' } });
  };
  const footer = (slide, label = '', page) => {
    const top = height - 56;
    if (label) text(slide, label, { left: 64, top, width: width - 240, height: 28 },
      { pt: spec.fontPt.footer, color: colors.muted, lineHeight: 1.2, name: 'footer' });
    if (page !== undefined) text(slide, String(page), { left: width - 128, top, width: 64, height: 28 },
      { pt: spec.fontPt.footer, color: colors.muted, lineHeight: 1.2, align: 'right', name: 'page-number' });
  };
  const baseSlide = ({ title, footer: footerText = '', page, titleLines = 1 } = {}) => {
    const slide = presentation.slides.add();
    slide.background.fill = colors.background;
    if (title) {
      if (titleLines === 1 && title.includes('\n')) throw new Error('Use titleLines: 2 for an intentional two-line title');
      text(slide, title, { left: 64, top: 48, width: width - 128, height: 72 * titleLines },
        { pt: spec.fontPt.title, bold: true, lineHeight: spec.lineHeight.title, name: 'slide-title' });
      rule(slide, { left: 64, top: 140 + (titleLines - 1) * 72, width: 64, height: 4 });
    }
    footer(slide, footerText, page);
    return slide;
  };
  const table = (slide, values, position, tableOptions = {}) => {
    checkBounds(position);
    if (!values.length || !values[0].length || values.some((row) => row.length !== values[0].length)) throw new Error('Table values must be a nonempty rectangular matrix');
    const rows = values.length, columns = values[0].length;
    const tab = slide.tables.add({ rows, columns, ...position, values,
      ...(tableOptions.columnWidths ? { columnWidths: tableOptions.columnWidths } : {}) });
    tab.styleOptions = { headerRow: true, bandedRows: false };
    tab.borders.assign({ style: 'solid', fill: colors.rule, width: 1 });
    for (let r = 0; r < rows; r++) {
      tab.rows[r].height = position.height / rows;
      for (let c = 0; c < columns; c++) {
        const cell = tab.getCell(r, c);
        cell.fill = r === 0 ? colors.primarySurface : colors.background;
        cell.text.style = { typeface: font, fontSize: ptToPx(tableOptions.pt ?? spec.fontPt.table),
          bold: r === 0, color: colors.text, lineSpacing: 1.3,
          alignment: tableOptions.numericColumns?.includes(c) && r > 0 ? 'right' : 'left',
          verticalAlignment: 'middle', autoFit: 'none',
          insets: { top: 12, right: 16, bottom: 12, left: 16 } };
      }
    }
    return tab;
  };
  const sources = (slide, entries = [], notes = '') => {
    const urls = [...new Set([
      'https://design.digital.go.jp/dads/guidance/style-guides/',
      'https://design.digital.go.jp/dads/foundations/color/',
      'https://design.digital.go.jp/dads/foundations/typography/',
      tokens.provenance.tokenSource, ...entries,
    ])];
    slide.speakerNotes.textFrame.setText(`${notes}\n\nデザイン：デジタル庁デザインシステムの資料をもとに、スライド用に編集・加工。\n[Sources]\n${urls.join('\n')}\n[/Sources]`);
  };
  return { presentation, colors, font, text, rule, footer, baseSlide, table, sources, width, height };
}
