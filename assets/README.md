# assets/

Pitch assets for SHENNONG. Everything is hand-written SVG — no binaries, no font files, no build
step — so it diffs cleanly in git and stays editable with a text editor.

| File | Size | Used by | Notes |
|---|---|---|---|
| `logo.svg` | 620×180 | README, Devpost, slides | Seal mark (鼎 + 禾 + benzene ring) and wordmark. The mark alone is also `app/static/favicon.svg`, redrawn simpler so it survives 16–32 px. |
| `og-image.svg` | 1280×640 | Devpost social card | Dark ground, mark, tagline, three claims. |
| `architecture.svg` | 1320×880 | README, docs/ARCHITECTURE, slide 5 | Four planes with the file contract on every arrow. |
| `pipeline.svg` | 1280×470 | slide 6, docs/METHODOLOGY | 采 Cǎi → 制 Zhì → 配 Pèi → 使 Shǐ. |
| `corpus_tiers.svg` | 1120×700 | slide 4, docs/METHODOLOGY | Tier structure. Deliberately **no baked-in counts** — live counts come from the registry at runtime (Workbench → Corpus). |

## Palette

Alchemical-manuscript-on-a-lab-bench: warm parchment, ink, one cinnabar accent, verdigris, brass.

| Token | Hex | Where |
|---|---|---|
| parchment | `#F6F0E3` | page ground |
| parchment light | `#FCF8F0` | cards |
| ink | `#1B1815` | text, 鼎 |
| cinnabar 朱 | `#A8362A` | the single accent: 禾, seals, falsification blocks |
| verdigris 石綠 | `#2C6B5C` | evidence, success, grounded |
| brass 金 | `#8A6420` | caution, warnings |
| indigo | `#2B4A6F` | novelty axis, structure |
| night | `#17140F` | knowledge-graph canvas, og-image |

The same tokens are the CSS custom properties at the top of `app/static/app.css`, so the UI and the
figures cannot drift apart.

## Fonts

No webfonts (the demo runs offline). The house stack is a system serif for display, system sans for
UI, and a monospace for data:

```
serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia,
       "Songti SC", "Noto Serif CJK SC", "Source Han Serif SC", serif
sans:  system-ui, -apple-system, "Segoe UI", "PingFang SC", "Hiragino Sans GB", sans-serif
mono:  ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace
```

Classical Chinese and Sanskrit render in whatever CJK/Devanagari serif the machine has. If a machine
has none, the text still renders in the fallback serif — never in tofu boxes, because every SVG that
contains CJK also carries it as `<text>`, not as a path.

## Rules for editing

1. **No fabricated numbers.** Figures carry structure and labels, never statistics. Anything measured
   is pulled from the artefacts at runtime (Workbench) or quoted from `eval/report.json` in text.
2. **Keep the palette.** One accent (cinnabar) does the work; verdigris and brass are semantic, not
   decorative.
3. **Text stays text.** Do not convert labels to outlines — a judge grepping the repo should find
   "采" in the source.
4. **Contrast.** Body text on parchment ≥ 7:1; the cinnabar accent is used at ≥ 4.5:1 for large/bold
   text only.

## Regenerating the raster social card

Devpost wants a raster image. Convert locally (not in CI):

```bash
# macOS
qlmanage -t -s 1280 -o /tmp assets/og-image.svg   # → /tmp/og-image.svg.png
# or
rsvg-convert -w 1280 -h 640 assets/og-image.svg -o assets/og-image.png
```

`og-image.png` is intentionally **not** committed: it is a derived binary, and the repo policy is that
every tracked artefact is either source or a hashed pipeline output.
