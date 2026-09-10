# 出典と参照先

このスキルの設計ガイドは、デジタル庁デザインシステムウェブサイト <https://design.digital.go.jp/dads/> のコンテンツをもとに、PowerPoint用に編集・加工して作成した。デジタル庁が作成・公認したPowerPointテンプレートではない。

## 同梱資料

利用者が提供した `dads-markdown-20260819.zip` から、以下の14文書を原文のまま抽出した。`source-manifest.json` に入力ZIPと各文書のSHA-256を記録した。

| 確認したい事項 | 同梱原文 |
| --- | --- |
| 色の役割、コントラスト、色覚多様性 | [カラー](dads/foundations/color/index.md) |
| 書体、サイズ、太さ、行間 | [タイポグラフィ](dads/foundations/typography/index.md) |
| 列、ガター、読み順 | [レイアウト](dads/foundations/layout/index.md) |
| 余白の規則、情報のまとまり | [余白](dads/foundations/spacing/index.md) |
| 角丸の調整 | [角の形状](dads/foundations/corner-shapes/index.md) |
| アイコンの用途 | [アイコン](dads/foundations/icon/index.md) |
| 見出しの構造・表現 | [見出し](dads/components/heading/index.md) |
| 並列項目、順序リスト | [箇条書きリスト](dads/components/list/index.md) |
| 表の構造と視認性 | [テーブル](dads/components/table/index.md) |
| 境界と区切り | [ディバイダー](dads/components/divider/index.md) |
| 画像の役割 | [画像](dads/components/image/index.md) |
| アクセシビリティの位置づけと限界 | [アクセシビリティ](dads/guidance/accessibility/index.md) |
| 個別用途向けのカスタマイズ | [スタイルガイド](dads/guidance/style-guides/index.md) |
| 出典・加工表示・素材の条件 | [利用上の注意事項](dads/introduction/notices/index.md) |

画像、Figmaファイル、Web UIの実装、フォントファイルは同梱していない。原文中の更新履歴・他コンポーネントへの相対リンクの一部は未収録である。必要なときは各文書冒頭の `source_url` から公式サイトを参照する。キャプションを根拠に未取得の図版の細部を断定しない。

## 数値カラーの補完

添付Markdownのカラー図は外部画像リンクであり、全HEX値を含まない。そのため機械可読の25色は以下の公式リソースで補った。

- [デジタル庁 design-tokens v2.0.1](https://github.com/digital-go-jp/design-tokens/blob/v2.0.1/figma/tokens.json)
- 確認日：2026年9月7日
- 選択した値と元のトークン名：`../assets/dads-slide-tokens.json` の `officialPrimitives`
- 利用条件：[MIT License原文](design-tokens-LICENSE.txt)

パッケージv2.0.1を、Webサイトや添付ZIPの版番号と取り違えない。公式の色値に対する「本文」「主色」などのスライド役割の割当ては、このスキルの独自設定である。

## 成果物への表示

最終ページや資料情報欄で、例えば次のように記載する。

> デザイン：デジタル庁デザインシステムの資料をもとに、スライド用に編集・加工
> https://design.digital.go.jp/dads/

各ページの発表者ノートには参照した設計資料と、そのページの主張・データ・画像の出典を `[Sources]` ブロックで残す。公式サイト文書の利用と、加工済みFigma部品やコードスニペットの出典条件は異なるため、必要なら「利用上の注意事項」の該当節で確認する。
