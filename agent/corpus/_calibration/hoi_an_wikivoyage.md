# Chunk boundaries — hoi-an-travel-guide-at-wikivoyage.md

Source: `corpus/da_nang_hoi_an/hoi-an-travel-guide-at-wikivoyage.md`

| # | Section path | Lines | Note |
|---|---|---|---|
| 1 | Intro | 9 | Standalone one-paragraph overview. |
| 2 | Understand + Orientation | 11–29 | Merged: Orientation (26–29) is 2 sentences, too small to stand alone, and is topically continuous with Understand. |
| 3 | Get in > By plane | 34–39 | |
| 4 | Get in > By train | 41–48 | |
| 5 | Get in > By bus > From Da Nang | 52–60 | Split by origin — a query like "bus from Da Nang to Hoi An" shouldn't retrieve Hue/other-origin logistics. |
| 6 | Get in > By bus > From Hue | 62–65 | |
| 7 | Get in > By bus > Other destinations | 67–76 | |
| 8 | Get in > By taxi | 78–85 | |
| 9 | Get around > On foot | 90–95 | |
| 10 | Get around > By bicycle | 97–104 | |
| 11 | Get around > By boat | 106–109 | |
| 12 | Get around > By motorbike | 111–122 | Long (safety disclaimers + rental info) but left whole — single topic, splitting would strand the safety warning from the rental advice it qualifies. |
| 13 | Get around > By shuttle bus + By taxi | 124–134 | Merged: both 1–3 sentences, same "get around" query intent. |
| 14 | See > Old Town + coupon system | 138–144 | |
| 15 | See > Landmarks | 146–152 | List kept as one chunk — bullets share the "landmarks" query intent; splitting per-bullet loses the shared framing. |
| 16 | See > Museums | 154–160 | |
| 17 | See > Traditional old houses | 162–170 | |
| 18 | See > Congregation halls | 172–183 | |
| 19 | See > Performances | 185–191 | |
| 20 | Do | 193–201 | |
| 21 | Do > Day trips | 203–219 | Kept whole despite length — internally it's one query intent ("day trips from Hoi An"); reranking/top-k can still surface it for narrower asks. |
| 22 | Buy > Money | 224–229 | |
| 23 | Buy > Shopping + Markets | 231–245 | Merged: "Shopping" intro bullets (2 items) too small alone, continuous with Markets list. |
| 24 | Buy > Bespoke clothing | 247–267 | Kept whole: the risk-mitigation advice (250–258) is meaningless without the tailor list it's warning about, and vice versa. |
| 25 | Eat > What | 272–281 | Dish descriptions. |
| 26 | Eat > Where (general) | 283–291 | |
| 27 | Eat > Budget | 293–303 | |
| 28 | Eat > Mid-range | 305–315 | |
| 29 | Eat > Splurge | 317–320 | |
| 30 | Drink | 322–330 | |
| 31 | Sleep (general) | 332–339 | |
| 32 | Sleep > Budget | 341–346 | |
| 33 | Sleep > Mid-range | 348–354 | |
| 34 | Sleep > Splurge | 356–363 | |
| 35 | Stay safe > November flooding | 365–373 | |
| 36 | Connect | 375–378 | |
| 37 | Go next > North | 380–390 | |
| 38 | Go next > South | 392–398 | |
| 39 | Go next > Laos | 400–403 | |

39 chunks from one doc. Confirms: for a heavily-sectioned source,
headers are ~80% of the answer — the manual work is almost entirely
deciding which *adjacent* small sections to merge, not where to split
big ones.
