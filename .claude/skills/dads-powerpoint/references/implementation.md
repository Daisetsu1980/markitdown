# 実装メモ

現在のPresentationsスキルの実装手順を読んでから使う。`dads-theme.mjs` はArtifact Toolを自前でロードせず、呼出し元の `Presentation` を受け取る。環境指定のランタイムとモジュール解決を、書込み可能な一時ビルドディレクトリで準備する。スキルの保存先に `node_modules` を作らない。

## 最小例

以下はES moduleの例。`DADS_SKILL_DIR` は、現在読み込んでいるこのスキルの絶対パスに設定する。スキルのインストール後にディレクトリ名が変わるため、作成時のフォルダ名やユーザー固有のパスを固定しない。

```js
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';
const { createDadsTheme } = await import(pathToFileURL(
  path.join(process.env.DADS_SKILL_DIR, 'scripts/dads-theme.mjs')
).href);

const d = createDadsTheme(Presentation, { font: 'Noto Sans JP' });
const slide = d.baseSlide({ title: '伝える主題を一つに絞る', footer: '説明資料', page: 1 });
d.text(slide, 'ここに対象読者に伝える説明を書く。',
  { left: 64, top: 192, width: 1152, height: 120 });
d.sources(slide, [], 'このページの出典・補足説明を記入する。');
// 必要なページを追加し、最終ページか資料情報欄に出典・加工表示を置く。
// 全ページをレンダリングして確認してから納品する。
const output = await PresentationFile.exportPptx(d.presentation);
await output.save(process.env.FINAL_PPTX);
```

`font` は利用可能な書体を確認してから渡す。ライブラリのフォント指定は、ファイルの導入・埋め込みを意味しない。

## ヘルパーの範囲

| API | 用途 |
| --- | --- |
| `createDadsTheme(Presentation, {font, colors, width, height})` | プレゼンテーションと色テーマを作成。`colors` は役割名からHEXへの上書き |
| `text(slide, value, position, {pt, bold, color, background, lineHeight, align, font})` | 編集可能なテキスト。サイズはpt、位置はpx |
| `rule(slide, position, color)` | 単純な区切り。画像・イラスト用の描画APIではない |
| `footer(slide, label, page)` | 資料名とページ番号 |
| `baseSlide({title, footer, page, titleLines})` | 標準見出し。2行指定では本文開始位置を呼出し側で下げる |
| `table(slide, values, position, {columnWidths, pt, numericColumns})` | 見出し行のある編集可能な表 |
| `sources(slide, entries, notes)` | 発表者ノートの出典。既存ノートを維持する場合は引き継いで渡す |
| `contrastRatio(fg, bg)` / `assertContrast(fg, bg, minimum)` | 不透明HEX二色のコントラスト計算。既定4.5 |

`position` は `{left, top, width, height}`。本文の周囲に面を置く場合は、`text` の `background` に実際の背景色を渡す。これは検査用であり、背景図形自体は別に作成する。レイヤー・透過・画像上の文字や、表の独自色の最終組合せは別途確認する。

ヘルパーは本文の字数・行の高さを自動調整しない。境界チェックは画面外だけを検出し、文字のはみ出しや要素同士の重なりを保証しない。必ずレンダリングを確認する。

グラフ、画像、図解は現在のArtifact Tool APIで追加し、ヘルパーの配色と文字サイズを適用する。色の数を増やすだけで系列を区別せず、直接ラベルやマーカーも使う。ユーザーの別配色・別比率を指定する場合は、応用設定の上書きと各要素の再配置を行う。
