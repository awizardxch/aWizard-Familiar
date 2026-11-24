# Skill: Mixmage Video Production

> How an agent that cannot watch reads video and produces finished music videos, DJ-style sets and
> promos with **Mixmage** ([awizardxch/MixMage](https://github.com/awizardxch/MixMage), read at
> `315c40e`; formerly Video Sampler). Mixmage is an Electron sampler and two-deck mixer for audio and
> video: MIDI pads with pages and auto cut, two decks with BPM sync and a bass control, a beat
> tracker and a synthesized beat box that follows it, one viewer with a stack of music-video effects,
> output recording with titles, YouTube search through yt-dlp. The repo carries the full producer
> skill at `.claude/skills/mixmage-producer/SKILL.md`; this file holds what an agent needs inline.
> Companion: `mixmageAudioAnalysis.md` (every sound measurement referred to here).

---

## The rule

You cannot watch or hear. Read pictures as images and words as captions; measure the sound and the
picture. Tell the user which judgments are measured and which are theirs to make by eye and ear.

Let the song and the user lead. The user's own music is the record; other videos are the crate.
The work must have flow, not be a tour of the app's buttons. You never edit video by hand with
ffmpeg: the app plays real clips on real decks and pads and records its own output, so every piece
is something that could have been played live.

---

## Reading video without watching

| Instead of | Do this |
| --- | --- |
| Watching a render | A contact sheet, Read as an image; then `check-video.js` (below) |
| Checking a source's clips | `clip-sheet.js`: three labeled frames per clip |
| Hearing the words | Fetch the captions with times |
| Listening | `mixmageAudioAnalysis.md` (bands, loudness, tempo, beats, sync, balance) |

**Contact sheet of a render.** For a 30-second render, 16 frames in one strip:

```
ffmpeg -v error -y -i in.mp4 -vf "fps=1/1.85,scale=160:-2,tile=16x1" -frames:v 1 sheet.png
```

For other lengths use `fps=16/<seconds>`, or a grid (`tile=8x6`, `fps=48/<seconds>`). Read every
sheet you make. Bugs found this way so far: a black opening, credit frames, title cards used as
picture, the same clips in every video, clips that had not loaded (black), a song's cover art
flashing between cuts, banners inside newsreel clips.

**Contact sheet of a source's clips** (to choose what to leave out): `node scripts/clip-sheet.js
<library> <source id> <out.jpg>` puts three frames per clip (at 15%, 50% and 85%), each labeled with
the clip's index. Use three frames, never only the first: text that appears partway through a clip
("EVERY JULY" banners in a rodeo newsreel), narrator captions, subtitles and faces deeper into a
vlog clip never show on its first frame, and all four reached renders that way. Without the script:
one `ffmpeg -ss <t> -i src -frames:v 1` per point, tiled.

**Checking a render's picture without watching:** `node scripts/check-video.js <video>` reads every
frame (30 a second, 64x36 gray) and reports DARK stretches (average under 7% for 1 s or more),
WASHED (over 85% for 0.5 s), FROZEN (no change for 3 s) and the worst FLASHES per second (a jump of
10% of full brightness and back is one flash). Over 3 flashes in any second fails the broadcast
photosensitive-epilepsy line (Ofcom, the Harding test) and must be fixed before posting. Dark
night footage shows as short DARK runs; fine if the footage is meant to be dark.

Other helpers: `blackdetect=d=0.3:pix_th=0.1` prints black stretches; `select='gt(scene,0.3)',showinfo`
prints each cut's time; `-ss <t> -frames:v 1` grabs one frame.

**Captions.** MixMage's `node scripts/captions.js <id or url> [from] [to]` prints `m:ss.s  text`
per line and caches it. With yt-dlp alone:

```
yt-dlp --js-runtimes node --no-playlist --skip-download --write-subs --write-auto-subs \
  --sub-langs "en.*,en" --sub-format json3 -o "captions/%(id)s" "https://www.youtube.com/watch?v=<id>"
```

Each `.json3` event has `tStartMs`, `dDurationMs` and `segs[].utf8`. Many music uploads have none;
a failure with `ERROR` is a rate limit worth retrying later; "no captions" is final.

**What not to use as picture:** credits, logos, title cards, banners, narrator captions,
subtitles, watermarks (stock-footage sites stamp every frame), brand signs (soda, beer brands),
private people's faces (vlogs), near-black frames. Exclude them by index from the clip sheets.

---

## Fetching sources

- Always pass `--js-runtimes node` to yt-dlp, or YouTube answers "video not available".
- Look up first: `yt-dlp --js-runtimes node --no-playlist --print "%(id)s | %(title)s | %(duration)s" <url>`.
- Search by topic: `ytsearch10:<words>` with `--flat-playlist`, or the app's own search box.
- Download in the app's format: `-S "vcodec:h264,res:720,acodec:m4a" --merge-output-format mp4`;
  over about 8 minutes add `--download-sections "*<from>-<to>"`.
- Prefer archival home movies, public-domain films and amateur footage. Skip official league and
  network channels (aggressive takedowns) and stock sites (watermarks). A character still owned as a
  trademark (a famous mouse in a 1930 cartoon) is a risk even when the film is public domain.

Third-party footage in public posts invites takedowns. Say so once, briefly; do not repeat it.

---

## Protect the user's library

- **Never write to the live library** (`Videos\Video Sampler`, the app's original name, kept on
  purpose). The app is usually open on it. Demo mode opens it read-only.
- New pieces and sources go into a separate demo library (`demo/extra-library` in the repo).
- Test the app only against synthetic videos (ffmpeg `lavfi`: `testsrc` plus a gated `sine`), or the
  real library through `READONLY_LIBRARY=1`.
- Do not write code containing backslashes through bash heredocs or `node -e` strings; use
  file-writing tools.

---

## The producer workflow

Run from the MixMage repo root (`npm install` also fetches yt-dlp into `bin/`).

**1. Add a source.** Download into `demo/extra-library/library/<id>.mp4`, add it to `sources` in
`demo/extra-library/state.json` (id, title, duration, file, url), then cut it by running the app on
that library with a small script (`SMOKE_ROOT=demo/extra-library SMOKE_JS=<script> npx electron .
--smoke`): `setSource`, set `$('autoMode').value` (`hits` for songs, `equal` for picture, `sounds`
for one-shots) and `$('autoLen').value` (`1` = whole song in one-bar clips, `0` = one page), `await
autoCut()`, `await window.api.save(state)`. Then `clip-sheet.js` and choose the indexes to keep.

**2. Find out what the song is about** (the user's words, the lyrics, captions) and its form
(`vocals.js` and `bars.js` in `mixmageAudioAnalysis.md`). **Picture tells the song**: for a
get-back-up rodeo song you'd play in an old truck or a dive bar, that was the bar and the arena
lights for the intro, a truck in the mud as the band comes in, riders thrown in the dirt for the
breakdown, getting up for the build, the ride for the big parts, the open road for the outro.
Effects are seasoning, not the subject.

**3. Write the performance** in `scripts/demo-performance.js`, a new entry in `variants`.

- For a DJ set of several songs, `djSet(L, parts, options)`: `parts` `[{ id, bars, still?, skip?,
  mix? }]` play song sections from alternating decks, starting at the loudest four bars (`skip`
  shifts); by default the outgoing song's last bar is loop-rolled and the next drops on the
  downbeat; `mix: <bars>` blends instead (incoming bass cut, crossfader over the overlap, bass swapped
  half-way). `still: true` cuts picture in from `options.pictures` every `options.cut` bars.
  `options.bpm` one master tempo; `options.extra(at)` timed events. Titles: `titled(LIST, bars)`.
- For one record played by a live band (tempo that moves), play it from **one deck started at bar
  0**, track its beats and give the piece `timeOf(bar)` (milliseconds from the start, from the
  tracked bars) so every event lands on the band's bars, not on a fixed clock. `trackChips` and
  `rodeoVideo` in the repo are the worked example; `picturePlan(pools)` deals picture clips by
  section and **only clips at least as long as their cut** (a one-shot that ends early leaves the
  viewer on the deck's own picture, for a record its cover art).
- In events, the app's functions: `hit(pad)`, `stop(pad, quick?)`, `setBlend(s)`,
  `setDeckPlaying(deck, on)`, `setDeckBass(deck, 0..1.5)`, `setDeckLowCut(0..1, s)`, `fade(0..1)`,
  `setOutputTitle({ title, sub, center? })`, and the effect calls below. Per pad: `mode`, `gain`,
  `pitch`, `trim`, `loop`; `rt[i].pin = true` for pads hit faster than once a bar (or the video is
  not loaded and the picture goes black); `rt[i].noPic = true` for heard-but-not-shown.

**4. Render.** One at a time; the window comes to the front:

```
DEMO_VARIANT=<name> DEMO_JS=scripts/demo-performance.js DEMO_OUT=demo DEMO_EXTRA=demo/extra-library npx electron .
```

Writes `demo/<name>-output.mp4` (mastered to -14 LUFS) and `demo/<name>-app.mp4` (the app being
played). For anything over about two minutes add `DEMO_NO_APP=1`: filming the app holds every frame
in memory. Read `DEMO_PREPARE`, `DEMO_RUN`, `DEMO_ERROR` and any `[renderer:3]` (a script error).

**5. If the sound must be the record itself** (a music video of the song): the app's output passes
its limiter, which squashes a mastered record. Replace it: `node scripts/original-audio.js
demo/<name>-output.mp4 <original file> <out.mp4> [originalTimeAtStart]` cross-correlates the two
soundtracks and lays the original in, to the millisecond. Give the 4th argument (roughly) when the
render starts partway into the record, and check it prints a match strength well above 0.3. A
shorter cut of a finished video is an ffmpeg stretch with fades and a drawn title, not a re-edit.

**6. Check.** Contact sheet, Read it; `check-video.js`; for added sound, the band, sync and balance
checks in `mixmageAudioAnalysis.md`. Fix, re-render.

**7. Report.** Lead with the files. Then what each piece is, what you measured, what you could not
judge (always: how it sounds), anything excluded or changed on your own. Short.

After any change to the app's own source, `SMOKE_SRC=<synthetic mp4> npx electron . --smoke` must
end with `SMOKE_DONE errors 0` (the earlier `SMOKE ... errors` line prints before most checks run).

---

## Effects: what is available and how to choose

All in `src/renderer/fx.js`; the user picks the same from the FX menu under the viewer (presets) and
"Effects ▾" (tick single effects). Nothing is applied unless chosen. The `fxSampler` variant shows
every preset in turn, named on screen. Effects show in the viewer and record into the output, and
fill the frame (crop, no letterbox) while on.

**Presets** (`fxPreset(name)`), by mood:

| Preset | What it is | Suits |
| --- | --- | --- |
| `shroom`, `shroomMirror` | Rainbow color wash in the canvas `color` blend (colors black-and-white footage too), trails; with a kaleidoscope | psychedelic, EDM |
| `rodeo` | Light shroom color, film, zoom punch | country, archival Americana |
| `archival` | Film (grain, scratches, flicker, weave, fade) and sepia | old footage, documentary |
| `vhsParty` | VHS tracking, bleed, scanlines, PLAY stamp; shake; zoom punch | 80s/90s throwback, lo-fi |
| `neonClub` | Neon grade, zoom punch, strobe every 4 beats, trails | club, house, EDM |
| `comic` | Halftone print dots, zoom punch | cartoons, pop |
| `heat` | Thermal-camera colors, shake | dark, heavy, a breakdown |
| `nightVision` | Green phosphor, noise, vignette | night footage, tension |
| `noir` | High-contrast black and white, film | drama, a quiet section |
| `brand` | Duotone (`dark`, `light` settable to brand colors) | promos |
| `splitBeat` | Four panes of recent clips trading places every two beats | montage, call and response |
| `dream` | Double exposure, trails, warm grade | intros, ballads |

**Single effects** (`fxUse([...])`, `fxAdd(name, settings)`, `fxSet`, `fxRemove`; each has an
`amount` 0..1; defaults in `FX_CATALOG`):

- On the beat (`every` is in beats): `zoomPunch`, `shake`, `strobe` {color 'white'|'black'},
  `stutter` {every 0.25 = the picture steps in quarter beats}.
- Looks: `film` {grain, scratches, flicker, weave, fade}, `vhs` {stamp}, `grade` {look: sepia,
  noir, warm, cold, tealOrange, neon}, `duotone` {dark, light}, `halftone` {cell}, `thermal`,
  `nightVision`, `mirror`, `trails`.
- Compose, using the clips shown just before the current one (the viewer always remembers the last
  four): `split` {panes 2|4}, `pip` {size, corner 'tl'|'tr'|'bl'|'br'}, `double`, `chroma`
  {key '#00ff00', tolerance}.
- Text: `fxText(text, { style: 'caption'|'pop'|'type'|'slide', where: 'bottom'|'center'|'top',
  every, hold })`; `pop` brings one word per `every` beats. `fxText(null)` clears.
- `fxFreeze(seconds)` holds the picture. Freeze a moment after a cut, never on it: on the cut the
  old clip has stopped and the new one has not drawn, so the freeze holds the deck's cover art.

Timing: set `fx.follow = { deck, beats }` with tracked beats so every hit lands on a live band's
beat (or `fx.bpm` and `fx.t0` for a steady tempo). Section by section: `fxSections(at, [[0,
'intro'], [8, 'verse'], [32, 'build'], [40, 'chorus'], [72, 'breakdown'], ...])` scales every
effect (intro 0.45, verse 0.6, build 0.85, chorus and drop 1, breakdown 0.35, outro 0.4); switch
presets on section changes. Lyrics: `lyricsAt(at, [[bar, 'words', { style: 'pop' }], ...])`, with
words from the user or captions, never invented.

**Choosing.** Match the footage (archival film on archival footage, comic on cartoons), keep one
look per section rather than changing every bar, save the strongest for the biggest parts. Stacking
several looks turns to mud; one look plus one beat effect is usually enough.

**Safety.** Every full-frame flash (strobe, `fxFlash`) passes one limiter: at most 3 a second,
whatever a script asks (a test asking for 16 a second gets 3). Still run `check-video.js` before
anything is posted.

---

## Adding drums to a record (the beat box)

Built and measured; the user preferred the original song for the music video in the end, so treat
a dance version as an option to offer, not the default.

- **Beat box** (`src/renderer/beat.js`; the Beat button in the mixer): a synthesized 909-style kit
  (kick, clap on 2 and 4, open and closed hats, an optional off-beat bass, snare roll, noise riser)
  into the output limiter. `startBeat({ bpm, parts, duck, follow })`, `setBeatParts({...})`,
  `beat.roll = { from, to }`, `riser(ctxTime, s)`, `stopBeat()`.
- **Follow the record's own beats, never a fixed grid.** A live band drifts (one record moved
  138-142 BPM phrase to phrase); a fixed grid, even re-locked to the deck every two bars, measured
  52 ms late in one section and 26 ms early in another, and the user heard it. Track the beats and
  start in follow mode: `startBeat({ follow: { deck, beats, down, offset: 0 } })`, `down` = the index
  of the beat that starts bar 0. Measured afterwards with `sync-check.js`: within 2 ms.
- **Known fault:** a deck started partway through a piece is heard about 37 ms after the position it
  reports (the fault moved with the late start when the decks' roles were swapped). Play from one
  deck started at bar 0, or measure and set `beat.follow.offset` (+0.037). A listening lock that
  correlated the deck's live sound with the beats wandered by tens of milliseconds on a dense band
  record and was removed.
- **Levels: an addition, not a takeover.** At beat-bus 0.9, pump depths 0.45-0.6 and the record's
  bass up 4 dB, the record's mids (voice, guitars) lost 5 dB of their share and the user heard the
  added bass overwhelming the song. Now: beat bus 0.5, pump (`beat.duck`) 0.12-0.3, the record's own
  bass about +1 dB (`setDeckBass(deck, 1.08)`); verse bands land within 1 dB of the original. Check
  with `compare-mix.js`.
- **No synth bass under a band record unless the roots are certain.** Two root analyses agreed on
  only half the bars of a live country-rock record; a wrong note sounds out of time even on time.
  Boost the record's own bass instead.
- **Build and drop** on instrumental bars only: `setDeckLowCut` rising, kick out four bars before,
  roll and riser, one beat of silence, everything on the one. On sung bars keep the low cut open.

---

## What makes it a DJ and not a demo

- One master tempo (or the record's own tracked beats); change songs only on bar lines, preferably
  every 4 or 8 bars.
- Let whole song sections play; chopping every bar into pads sounds like a demo.
- Samples are seasoning: off-beats, bar ends, answers to the beat, at gain around 0.4 (they measure
  about 10 dB hot at 2-6 kHz). Gains are not portable between sources; measure each.
- Two traditions, never mixed in one short piece: the **roll-and-drop** (80s cut style) and the
  **long blend** (house-set style: tempo within about 1.5%, level within 1 dB, a bass swap in a
  minute-long blend, or cutting the low end for 2-16 bars and bringing it back on the one). The
  measured sets are in `mixmageAudioAnalysis.md`.

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
- Adding a YouTube video or song; choosing or changing picture clips, titles or lyrics on screen.
- Choosing, adding or tuning video effects (looks, beat effects, split screens, text, presets).
- Remixing a record (beat box, build and drop), or making a music video of a song as recorded.
- Checking how a rendered video looks (and, with `mixmageAudioAnalysis.md`, how it measures).
