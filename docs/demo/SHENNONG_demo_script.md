# SHENNONG demo video — narration script

**File:** `docs/demo/SHENNONG_demo.mp4` · **2:59** · 1600×900 · female neural voice (en-US-AvaMultilingualNeural,
rate −4 %, pitch +14 Hz for a softer delivery)

| # | in | text |
|---|---|---|
| 1 | 0:00 | Traditional medicine is the largest observational dataset humanity has. Hundreds of thousands of recorded treatments, centuries of clinical use. And it has never been queryable, for two reasons. The names don't survive the centuries. And nobody ever checked the chemistry. |
| 2 | 0:18 | Open the demo. I click 丹參, a sixteenth century Chinese drug name. In about a second it returns the modern botanical binomial, Salvia miltiorrhiza. Its names in six languages. Eight recorded uses. Four compound classes, and ten modern gene targets. That is the whole chain, from a name that is four hundred years old, to pharmacology today. |
| 3 | 0:44 | But a name is a lookup. Here is the real capability. I paste a classical formula: 甘草, 白朮, 茯苓, boiled in water. The extractor returns every drug with a character span and a confidence. Compound classes, and gene targets. And it maps the sixteenth century claim, 脾胃虛弱, to dyspepsia. Extraction is rule and lexicon based, so it cannot invent a span. Every item points at a character range in the text I just pasted. |
| 4 | 1:17 | And it runs at corpus scale. We mined two hundred and seventy three thousand formulas from one thousand and eighty two classical works. Seven hundred and forty four thousand drug mentions. Seven hundred and fourteen thousand drug indication pairs. In fifty two seconds, on a CPU. |
| 5 | 1:37 | Same idea, second track. I type a disease target: E G F R. Twenty three thousand plant compounds ranked by fingerprint similarity to known ChEMBL actives, then filtered by ADMET, preparation physics, and novelty. On H M G C R the top hit scores a Tanimoto of one point zero. The pipeline rediscovers a known active. That is our control that the method works. |
| 6 | 2:04 | But the part that matters most. We ran two hundred and three recorded preparation methods through a mass balance and heat stability check. Seventy eight are physically impossible. The compound decomposes at the temperature the text prescribes. And six of those had unanimous support from every text based check. The ancient record agreed. The tradition agreed. Physics said no. Ancient consensus is not evidence. Our system is built to argue with its own sources. |
| 7 | 2:36 | The model underneath is nine hundred and forty megabytes, and runs on a CPU. Forty nine percent, against thirty seven for its base model. We also trained a sparse mixture of experts. It lost, and we published it anyway. Everything is open. The contribution isn't a bigger model. It's a system that links eras, and then checks itself. |

**Scenes:** landing → resolve 丹參 → read a passage → corpus scale → screen EGFR → the arbiter → ask the model.
