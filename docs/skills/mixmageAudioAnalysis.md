# Skill: Mixmage Audio Analysis

> How an agent that cannot hear judges sound: amplitude, five frequency bands, loudness, tempo and
> bass drop-outs, measured with ffmpeg and three small Node scripts from
> [awizardxch/MixMage](https://github.com/awizardxch/MixMage) (`scripts/analyze-mix.js`,
> `scripts/study-mix.js`, read at `4e4987e`). The methods are written out here, so the skill works
> without the scripts; fetch the scripts when you want the exact output format.
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

Pair with `mixmageVideoProduction.md` when the file has picture, or when the job is to make a video.
