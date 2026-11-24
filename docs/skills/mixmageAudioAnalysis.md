# Skill: Mixmage Audio Analysis

> How an agent that cannot hear judges sound: amplitude, five frequency bands, loudness, tempo and
> bass drop-outs, key, a song's bar-by-bar form, where it is sung, every beat of a live band, whether
> added drums land on the band, whether additions stay subtle, and how to lay a record's own sound
> under a video, measured with ffmpeg and small Node scripts from
> [awizardxch/MixMage](https://github.com/awizardxch/MixMage) (`scripts/analyze-mix.js`,
> `study-mix.js`, `key.js`, `bars.js`, `vocals.js`, `beats.js` with `src/beats.js`, `sync-check.js`,
> `compare-mix.js`, `beat-phase.js`, `original-audio.js`, read at `315c40e`). The methods are
> written out here, so the skill works without the scripts; fetch them for the exact output.
> Companion: `mixmageVideoProduction.md` (picture, captions, the producer workflow).

---

## The rule

You cannot listen. Never say a piece "sounds good", "is balanced" or "is on beat". Say what you
measured, give the number, and name what is left for a human ear (always: how it actually sounds,
and whether two kicks land together). Measure before explaining: when a number looks wrong, check
what produced it (the window, the source, a fade) before inventing a cause.

---

## Toolkit

Any ffmpeg works. In a Node project, `ffmpeg-static` gives a path (`require('ffmpeg-static')`),
which is what the MixMage scripts use. All commands below take audio or video files.

| Question | Command |
| --- | --- |
| How loud overall, does it clip? | `ffmpeg -hide_banner -i f.mp4 -af volumedetect -vn -f null -` (read `mean_volume`, `max_volume`; `max_volume` at 0.0 dB means clipping) |
| How loud for streaming (LUFS)? | `ffmpeg -hide_banner -i f.mp4 -af loudnorm=print_format=json -vn -f null -` (read `input_i` integrated LUFS, `input_tp` true peak, `input_lra` loudness range) |
| How loud over time? | `ffmpeg -v error -i f.mp4 -af "asetnsamples=n=22050,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-" -vn -f null -` (one RMS value per `n` samples; set `n` to the sample rate times the window in seconds) |
| How loud in one stretch? | Add `-ss <start> -t <seconds>` before `-i` to any command above |
| How much bass? | `-af "lowpass=f=120,volumedetect"` against plain `volumedetect`: the difference is the bass share |
| Master to a target | `-af loudnorm=I=-14:TP=-1.5:LRA=9` (what Mixmage does to every render: -14 LUFS, peaks under -1.5 dB) |
| Raw samples for your own analysis | `ffmpeg -v error -i f.mp4 -vn -ac 1 -ar 22050 -f s16le pipe:1` (mono 16-bit PCM on stdout) |

---

## Five bands per half-second (`analyze-mix.js`)

The stand-in for listening to balance. Usage: `node scripts/analyze-mix.js <file> [more files]`.

Method, so you can reproduce it anywhere:

1. Decode to mono 22,050 Hz PCM (the last row of the toolkit).
2. FFT frames of 2048 samples, Hann window, hop 1024. Sum the power in five bands:
   `sub` 20-120 Hz, `low` 120-500, `mid` 500-2000, `high` 2000-6000, `air` 6000-11000.
3. Average frames into half-second blocks. Per block: the total level in dB, and each band's
   share in dB of that block's total.
4. Ignore blocks more than 20 dB under the median total (fades and silence).
5. Flag a block when its total is more than 4 dB from the median total, or a band's share is more
   than 7 dB from that band's median share (and the band is not negligible, above -25 dB of total).

It prints the piece's balance (median share per band) and every flagged half-second, for example
`12.5s high +9 dB` or `20.0s level -5.2 dB, sub -14 dB`.

How to read the flags:

- Flags in the first and last second or two are the fade in and fade out. Expected.
- A **single** flagged half-second in the middle is almost always something you added (a stab, a
  cut, a pad hit at the wrong gain).
- A **run** of flags with `sub -10 dB` or lower in the middle is usually the song's own breakdown.
  Compare the same song in another render before "fixing" it.
- A deliberate bass cut shows as `sub -14 dB` or lower for exactly the bars you cut.
- A correct long blend measures flat except one short dip at the bass swap.

Measured facts worth knowing before you mix:

- **Cartoon and sound-effect stabs sit about 10 dB hot in the 2-6 kHz band** against a full music
  track at matched loudness. Play them at gain around 0.4, not 1.
- **Gains are not portable between sources.** A gain that fixed one sample made another 5 dB too
  loud. Level-match first, set gains near 1, render, then adjust from the measurement.
- **A quiet intro is short of highs**, so even soft hats added over it stood 8 dB out. Keep hats
  over a quiet intro at about 0.2 of their normal level.
- **A noise riser at full level stood 17 dB out in the air band** at its peak; a peak gain of 0.16
  (against 0.35) sits right.
- **Added drums under a full band record must stay small.** A kit at 0.9 with a deep sidechain pump
  (0.45-0.6) and the record's bass up 4 dB took 5 dB of share from its mids; a kit at 0.5, pump
  0.12-0.3 and bass +1 dB left every band within 1-2 dB (`compare-mix.js`).

---

## Tempo

The estimator in `study-mix.js`, at 11,025 Hz mono:

1. Onset envelope: frames of 128 samples; per frame `log1p(100 * rms)`; keep only rises
   (`max(0, env - previous)`).
2. Autocorrelate the onset curve over lags for 100-140 BPM; take the best lag.
3. Refine around it in steps of 0.02 frames, scoring `ac(lag) + ac(2*lag) + ac(4*lag)` (beat, half
   bar, bar), so the estimate locks to the bar and not a stray hit.
4. BPM = `60 * (11025 / 128) / lag`.

Measure 40 seconds from the middle of a track. Readings that jump to about 98-105 in a house set
are the estimator slipping to a 4:5 ratio in a breakdown, not a real change; ignore isolated ones.
Narrow the lag range for other genres (100-140 BPM suits house and most pop).

---

## Key (`key.js`)

`node scripts/key.js <file> [fromSeconds] [toSeconds]`, so added bass lines, stabs and pitched
samples fit the song. Method, at 11,025 Hz mono:

1. FFT frames of 8192 samples, Hann window, half-overlapped. Map every bin from 55 Hz to 2 kHz to
   its pitch class (`round(12 * log2(f / 440))`, A = 9) and sum magnitudes per class. Normalize each
   frame to sum 1, so loud and quiet frames count once each; add the frames into a chromagram.
2. Correlate the chromagram with the Krumhansl-Kessler profiles rotated to all 12 tonics:
   major `6.35 2.23 3.48 2.33 4.38 4.09 2.52 5.19 2.39 3.66 2.29 2.88`,
   minor `6.33 2.68 3.52 5.38 2.60 3.53 2.54 4.75 3.98 2.69 3.34 3.17` (index 0 = the tonic).
3. Rank the 24 keys by correlation. A winner well clear of the runner-up is a confident reading.
   Relative pairs (C major / A minor share notes) can score close: break the tie with the bass
   notes, the strongest pitch classes below 220 Hz, which it also prints.

## A song's form, bar by bar (`bars.js`)

`node scripts/bars.js <library folder> <source id>` reads the one-bar clips the app's auto cut made
(`hits` mode, whole song in one-bar clips), so the bars are the app's own grid. Per bar: the
strongest bass pitch class (the chord root, from the chromagram above restricted to the low end),
the level in dB against the loudest bar, and a `_` mark where the low end (one-pole 120 Hz
low-pass) is 6 dB or more under the song's median (an intro, a break). Rows of 8 bars, so sections
and chord cycles show up as repeating rows.

Use it to pick sections (a pre-chorus that runs into the chorus is a build and drop with no edit at
all). `--roots` prints just the roots, one per bar. **Treat roots of a live band record as
uncertain**: a bass line that moves within the bar has no single root, and two methods (this one,
and the drum-free one in `beats.js` below) agreed on only half the bars of a country-rock record. A
synth bass on uncertain roots sounds out of time even when it is on time; prefer the record's own
bass.

Without the app's clips the same works on any fixed grid: cut the file into bars of `240 / bpm`
seconds from a known downbeat and run the same per-bar measurement.

## Where it is sung (`vocals.js`)

`node scripts/vocals.js <library> <source id>`. The lead vocal is mixed dead center; double-tracked
guitars and keys sit wide. So per bar, after a 250-3500 Hz band-pass, compare the energy of the
center `(L+R)/2` with the sides `(L-R)/2`, in dB against the song's median: 3 dB or more above is
sung (V), 1.5 dB is a maybe (v). The signal is rough (about ±3 dB): read runs of bars alongside
`bars.js`, never single bars; a centered lead guitar or a mono recording will fool it. Use it to
put builds, silences and big moments on instrumental bars, and when the lyrics must survive,
**never cut the record**: play it whole and arrange around it, so a wrong guess costs nothing.

## Every beat of a live band (`beats.js`, `src/beats.js`)

`node scripts/beats.js <file> <bpm hint> [--json out.json]`; in the app, `window.api.beats({ file,
bpm })` runs the same in a background thread. It takes the best-proven parts of the open-source
analysis tools:

1. **Onset strength** (librosa): spectral flux over 40 log-spaced bands from 30 Hz to 8 kHz,
   log-compressed, averaged; 22,050 Hz, FFT 1024, hop 128 (5.8 ms). A local average over about a
   second is subtracted, so loud passages do not outweigh quiet ones.
2. **More views** (aubio, Essentia): high-frequency content (snare and hats) and low-band flux
   under 150 Hz (kicks), each a separate onset curve.
3. **Tempo** near the hint: autocorrelation of the onset curve within 8% of it, scoring beat, half
   bar and bar lags together.
4. **Beat tracking** (librosa, Ellis 2007): dynamic programming over frames, `score(t) = onset(t) +
   max over p in [t-2P, t-P/2] of score(p) - 100 * log((t-p)/P)^2`, P the period; backtrack from the
   best score in the last period. The tempo may wander; a sudden skip may not.
5. **Agreement** (Essentia's multi-feature tracker): track each onset view separately and keep the
   sequence the others agree with most (F-measure within 50 ms).
6. **Peak picking** (aubio): move each beat onto the strongest combined onset within 3 frames, with
   parabolic interpolation; then pull each a quarter of the way toward its neighbors' midpoint.
7. **Downbeats**: chords change on the one and the kick lands on 1 and 3; the phase (which of every
   four beats starts a bar) with the most bass-chroma change plus kick weight wins.
8. **Bass roots** (librosa HPSS, a KeyFinder-style chroma as in Mixxx): median-filter the low end
   (FFT 8192) along time and along frequency; keep bins where the time view wins (the harmonic
   part, drums removed); strongest pitch class per bar, with a confidence (top over runner-up, sure
   at 1.25 or more).

Measured on a live country-rock record: 139.7 BPM overall, 138.0-141.9 from one 8-bar stretch to the
next, beat-to-beat 134.7-145.8 (5th-95th percentile, after the agreement and peak steps; 134.7-152
before). The tracked bars landed within a few ms of the app's own bar clips.

## Is the added kick on the band? (`sync-check.js`)

`node scripts/sync-check.js <render> <song> <beats.json> <from> <to> [songTimeAtFrom]`. First it
finds where the song sits in that stretch of the render (cross-correlating 1-2.5 kHz envelopes; give
the last argument when the song repeats itself, or it can match the wrong chorus). Then, because
the beat box's kick is a known sound (a sine falling 160 to 48 to 40 Hz), it finds each kick with a
**matched filter**, correlating the render's low end with that waveform within 80 ms of every
tracked beat, keeps the better-matching half, and reports the median offset, the spread and the
share within 15 ms. In sync: median within about 5 ms, most beats within 15 ms. (Measuring the low
end's onsets instead does not work on a band record: the bass guitar's notes are onsets too; the
original alone scored only 30% within 15 ms.)

Measured: a fixed grid at the record's average tempo drifted to 52 ms late and 26 ms early; the beat
box following the tracked beats landed at a median of -2 ms, every beat within 15 ms.

## Do additions stay subtle? (`compare-mix.js`)

`node scripts/compare-mix.js <remix> <original> <from> <to> [originalTimeAtFrom]`. Over the same
music in both, each band's share of the total: sub (under 60 Hz), bass (60-150), low-mid (150-500),
mid (500-2000), presence (2-6 kHz), air (over 6 kHz). Shares, not levels, because the remix is
mastered to a different loudness. Subtle: the low bands within about +2 dB of the original, the rest
within 1.5 dB. **Mids losing share means the added beat buries the voice and guitars** (measured
-5 dB, and the user heard it; after lowering the kit and the pump, within 1-2 dB).

## Laying a record's own sound under a video (`original-audio.js`)

`node scripts/original-audio.js <render> <original> <out> [originalTimeAtStart]`. Onset envelopes of
both soundtracks are cross-correlated, coarse at 10 ms over ±5 s, then fine at 1 ms over ±20 ms; the
picture is copied and the original's audio laid in at the found offset (`-itsoffset`, or `-ss` when
the render starts partway into the record; then give the 4th argument, roughly, and the search stays
within 5 s of it). It prints a match strength: a true match is well above 0.3 (0.6-0.9 measured);
near 0 means the wrong place. Use it whenever the sound must be the record as released: a renderer's
output limiter squashes a mastered record.

## Do added drums land with the song? (`beat-phase.js`)

`node scripts/beat-phase.js <file> <bpm> <from> <to> [bandHz=150]`. It low-passes at the band (one
pole), takes a 1 ms energy envelope, keeps rises against a short running average (so slow swells do
not count), and folds them over the beat period into 40 slots, printed as a bar chart with the
strongest slot and the next peak away from it.

- **One peak**: everything hits together.
- **Two peaks** a few to a few tens of milliseconds apart: two grids, a flam.

Run it on the original song over the section you used and on the render over the same music. For a
render the phase is relative to the render's start, so compare the shape, not the slot. It assumes
a steady tempo: on a live band whose tempo moves, use `sync-check.js` against tracked beats instead.
Measured: a beat started on the same event as a video `play()` lands about 20 ms early (the video
starts a little late); following tracked beats through the deck's position removes that, except on
a deck started partway through a piece, which plays about 37 ms behind its reported position.

---

## Bass and level through a DJ set (`study-mix.js`)

Two modes:

- `node scripts/study-mix.js <file> <t1,t2,...>`: give it the transition times in seconds (from the
  video's tracklist: `yt-dlp --js-runtimes node --print "%(description)s" <url>`). It prints each
  track's tempo, then for each transition the bass and the level in 4-second steps from 96 s before
  to 96 s after, against that window's median, with `|` at the listed time.
- `node scripts/study-mix.js <file> scan`: for a set with no tracklist. Tempo per minute, how much
  of the set is within 1.5 dB and 3 dB of its norm, and every bass drop-out.

Its band split is a one-pole low-pass at 120 Hz (`a = exp(-2*pi*120/rate)`, `lp = a*lp + (1-a)*x`):
bass is the energy of `lp`, the rest is the energy of `x - lp`. Cheap and good enough for "is the
bass there". A **bass drop-out** is a 4-second step more than 6 dB under the median bass of the
surrounding two minutes (so a quieter record is not mistaken for one), while the overall level is
still playing; neighboring steps join into one drop-out.

How to read a transition: bass that dips and returns is a bass swap; the span over which two
records are both audible is the blend length; `bass never drops 6 dB` means the low end was carried
straight through.

---

## What two house sets measured

Use these as targets when building a DJ-style piece, and as a reference for reading other sets.

**A soulful deep house block-party set, 35 minutes with a tracklist (the smooth style):**

- One tempo, creeping upward: 121.6, then 123.0, then 123.8 BPM across eight records; never more
  than about 1 BPM (1.2%) between neighbors. Pick records within about 1.5% of each other.
- Level within 1 dB through every change. A change is not an event in the level.
- Long blends with a bass swap: two records run together for about a minute; the bass drops out
  for 2-4 bars near the start of the blend, or sits 5 dB down for the whole overlap, then returns.
  No hard cuts. One bass drop-out every 3.1 minutes; 67% of the set within 1.5 dB of its norm.

**A 62-minute radio house set, no tracklist, read with `scan` (the bass-play style):**

- The same slow creep: 122.3 to 124.5 BPM over the hour.
- A much more hands-on low end: 43 bass drop-outs, one every 1.4 minutes, mostly 4-16 bars long
  and 13-23 dB deep. Cuts run 2-16 bars. Level looser: 39% within 1.5 dB of its norm.
- The move: cut the low end for a phrase, bring it back on the one as a drop.

Those are two traditions. In a short piece pick one; do not mix them.

---

## Reporting

Lead with the numbers that answer the question (LUFS and peak, flagged seconds, tempo per track,
bass drop-outs). Then say plainly which judgments are measured and which belong to a listener.
Keep it short.

---

## When to load

- Checking a render, a mix or any audio file you cannot hear.
- Studying a DJ set or a song to copy its tempo, blend or bass style.
- Choosing gains or levels for samples against a track.
- Finding a song's key, its sections and chord roots, or where it is sung.
- Tracking every beat of a live-played record; checking that added drums land on the band and stay
  subtle; putting a record's own sound under a video.

Pair with `mixmageVideoProduction.md` when the file has picture, or when the job is to make a video.
