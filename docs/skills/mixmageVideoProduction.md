# Skill: Mixmage Video Production

> How an agent that cannot watch reads video and produces finished music videos, DJ-style sets and
> promos with **Mixmage** ([awizardxch/MixMage](https://github.com/awizardxch/MixMage), read at
> `4e4987e`; formerly Video Sampler). Mixmage is an Electron sampler and two-deck mixer for audio and
> video: MIDI pads with pages and auto cut, two decks with BPM sync and a bass control, one viewer,
> output recording with titles, YouTube search through yt-dlp. The repo carries the full producer
> skill at `.claude/skills/mixmage-producer/SKILL.md`; this file holds what an agent needs inline.
> Companion: `mixmageAudioAnalysis.md` (every sound measurement referred to here).

---

## The rule

You cannot watch or hear. Read pictures as images and words as captions; measure the sound. Tell
the user which judgments are measured and which are theirs to make by eye and ear.

The style the pieces aim for: the digital, AI-era take on 1980s turntable mixing and sampling. The
user's own music is the record; cartoons and other videos are the crate of samples. It must be
DJ-quality music with flow, not a tour of the app's buttons. You never edit video by hand with
ffmpeg: the app plays real clips on real decks and pads and records its own output, so every piece
is something that could have been played live.

---

## Reading video without watching

| Instead of | Do this |
| --- | --- |
| Watching | Build a contact sheet and Read it as an image |
| Hearing the words | Fetch the captions with times |
| Listening | `mixmageAudioAnalysis.md` (bands, loudness, tempo) |

**Contact sheet.** For a 30-second render, 16 frames in one strip:

```
ffmpeg -v error -y -i in.mp4 -vf "fps=1/1.85,scale=160:-2,tile=16x1" -frames:v 1 sheet.png
```

For other lengths use `fps=16/<seconds>`, or a grid (`tile=8x4`, `fps=32/<seconds>`) for long
sources. Read every sheet you make. Bugs found this way so far: a black opening, credit frames,
title cards used as picture, the same clips in every video, clips that had not loaded (black).

Helpers that answer "where" without reading every frame:

- Black frames: `ffmpeg -hide_banner -i in.mp4 -vf "blackdetect=d=0.3:pix_th=0.1" -an -f null -`
  (prints `black_start`/`black_end`).
- Scene changes: `-vf "select='gt(scene,0.3)',showinfo"` prints a line per cut with `pts_time`.
- A frame at a time: `ffmpeg -ss <t> -i in.mp4 -frames:v 1 frame.png`.

**Captions** (match words to clips and titles). MixMage's `node scripts/captions.js <id or url>
[from] [to]` prints `m:ss.s  text` per line and caches the result. The same with yt-dlp alone:

```
yt-dlp --js-runtimes node --no-playlist --skip-download --write-subs --write-auto-subs \
  --sub-langs "en.*,en" --sub-format json3 -o "captions/%(id)s" "https://www.youtube.com/watch?v=<id>"
```

In the `.json3`, each event has `tStartMs`, `dDurationMs` and `segs[].utf8`; join the segments for
the line. Many music uploads have no captions. YouTube rate-limits caption requests: a failure with
`ERROR` is worth retrying later; "no captions" is final.

**Avoid credits and title frames as picture.** Opening logos, title cards, end credits and
near-black frames are not footage. Build a contact sheet of the candidate clips' thumbnails,
note the ones to exclude by eye, and keep them out of every reel.

---

## Fetching sources

- Always pass `--js-runtimes node` to yt-dlp, or YouTube answers "video not available".
- Look up first: `yt-dlp --js-runtimes node --no-playlist --print "%(id)s | %(title)s | %(duration)s" <url>`.
- Search by topic: `ytsearch10:<words>` as the URL with `--flat-playlist`, or the app's own search box.
- Download in the app's format: `-S "vcodec:h264,res:720,acodec:m4a" --merge-output-format mp4`.
  For anything over about 8 minutes add `--download-sections "*<from>-<to>"`.
- Tracklists and descriptions: `--print "%(description)s"`.

Third-party footage in public posts invites takedowns. Say so once, briefly; do not repeat it.

---

## Protect the user's library

- **Never write to the live library** (`Videos\Video Sampler`, the app's original name, kept on
  purpose). The app is usually open on it; anything written there is lost or orphaned. Demo mode
  opens it read-only.
- New pieces and new sources go into a separate demo library (`demo/extra-library` in the repo).
- Test the app only against synthetic videos (ffmpeg `lavfi`: `testsrc` plus a gated `sine`), or
  the real library through `READONLY_LIBRARY=1`.
- Do not write code containing backslashes through bash heredocs or `node -e` strings; they are
  silently mangled. Use file-writing tools.

---

## The producer workflow

Run from the MixMage repo root (`npm install` also fetches yt-dlp into `bin/`).

**1. Add a source.** Download into `demo/extra-library/library/<id>.mp4`, add it to `sources` in
`demo/extra-library/state.json` (id, title, duration, file, url), then cut it by running the app on
that library with a small script:

```
SMOKE_ROOT=demo/extra-library SMOKE_JS=<script> npx electron . --smoke
```

In the script: `setSource`, set `$('autoMode').value` (`hits` for songs, `equal` for picture,
`sounds` for one-shots) and `$('autoLen').value` (`1` = whole song in one-bar clips, `0` = fill one
page), `await autoCut()`, then `await window.api.save(state)`. Name picture clips so they can be
found. Then contact-sheet the new clips' `.jpg` thumbnails and exclude the bad ones (the `drop(...)`
list in `reelFor`).

**2. Write the performance** in `scripts/demo-performance.js`, as a new entry in `variants`.
Almost everything is `djSet(L, parts, options)`:

- `parts`: `[{ id, bars, still?, skip?, mix? }]`. Each part plays a song section from a deck,
  starting at its loudest four bars (`skip` shifts by bars). Parts alternate decks. By default the
  outgoing song's last bar is loop-rolled (halves, quarters, eighths) and the next drops on the
  downbeat. `mix: <bars>` instead blends into the next part: the incoming deck enters with its bass
  cut, the crossfader travels over the overlap, the bass is swapped half-way, the outgoing deck
  leaves (8 bars in a 30-second piece; 16 or 32 in anything longer).
- `still: true`: the song's own video is only a cover image, so picture is cut in from
  `options.pictures`, one clip per `options.cut` bars (default 1; 0.5 for fast cutting).
- `options.bpm`: one master tempo, the main song's own (`bpmOf(id)`), so it is not shifted.
- `options.extra(at)`: timed events; `at(bars, fn)` runs `fn` at that bar.
- Titles: `extra: titled(LIST, bars)`, entries `[bar, { title, sub, center? }]` written for 16
  bars and stretched; `center: true` is a full card (first and last).
- In events, the app's own functions: `hit(pad)`, `stop(pad, quick?)`, `playNote(pad, note, vel)`,
  `stopNote(note)`, `setBlend(s)`, `setPitch(semitones)`, `setDeckPlaying(deck, on)`,
  `setDeckBass(deck, 0..1)`, `fade(0..1)` (crossfader), `setOutputTitle({...})`. Per pad:
  `state.pads[i].mode` (`oneshot`/`gate`/`loop`), `gain`, `pitch`, `trim`, `loop`.
- `rt[i].pin = true` for any pad hit faster than once a bar, or its video will not have loaded and
  the picture goes black. `rt[i].noPic = true` for a pad to be heard but never shown.
- Every video gets its own picture: `reelFor(L, slot, count)` deals each source's clips to six
  slots; give each video a different slot.
- `cut80s(L, { id, pictures, stabs, tone, titles })` is the 80s routine (half-bar cuts,
  transformer, beat juggle, stabs, scratch wobble, echo-out). Read it before writing anything
  rhythmic: it shows sixteenth-note scheduling, gating a deck, juggling a bar and the echo-out.

**3. Render.** One at a time; the window pops up for about a minute:

```
DEMO_VARIANT=<name> DEMO_JS=scripts/demo-performance.js DEMO_OUT=demo DEMO_EXTRA=demo/extra-library npx electron .
```

It writes `demo/<name>-output.mp4` (the piece, mastered to -14 LUFS) and `demo/<name>-app.mp4`
(the app being played). Read the log lines `DEMO_PREPARE`, `DEMO_RUN`, `DEMO_ERROR` and any
`[renderer:3]` (a script error).

**4. Check.** Contact sheet, Read it. Band analysis (`analyze-mix.js`), loudness. Fix, re-render.

**5. Report.** Lead with the files. Then what each piece is, what you measured, what you could not
judge (always: how it sounds), and anything you excluded or changed on your own. Short: the user
reads on a phone between takes.

After any change to the app's own source, `SMOKE_SRC=<synthetic mp4> npx electron . --smoke` must
end with `errors 0`.

---

## What makes it a DJ and not a demo

- One master tempo; change songs only on bar lines, preferably every 4 or 8 bars.
- Let whole song sections play. Chopping every bar of a song into pads sounds like a demo.
- Samples are seasoning: off-beats, bar ends, answers to the beat, at gain around 0.4 (they
  measure about 10 dB hot at 2-6 kHz). Gains are not portable between sources; measure each.
- Two traditions, never mixed in one short piece: the **roll-and-drop** (80s cut style, the
  default) and the **long blend** (house-set style: one tempo within about 1.5%, level within 1 dB,
  a bass swap in a minute-long blend, or the bass-play move of cutting the low end for 2-16 bars and
  bringing it back on the one). The measured sets behind these numbers are in
  `mixmageAudioAnalysis.md`.
- A sampled cold open (an archival clip before the first record) is a real DJ move; `djSet` calls
  it `opener`.

---

## Promos

Promo wording comes only from the owner's own published sources (for Forge: forge.awizard.dev/docs,
public talk titles, the project's public bio). Do not invent claims about a financial product. The
Forge end card is exactly: title `Enter the Beta`, sub `at Forge.aWizard.dev`. No credits, logos or
title cards as picture.

---

## When to load

- Any request for a promo, post, set, mix, music video or a new variant of one, even if Mixmage is
  not named.
- Adding a YouTube video or song to a mix; changing titles or picture clips.
- Checking how a rendered video looks (and, with `mixmageAudioAnalysis.md`, how it measures).
