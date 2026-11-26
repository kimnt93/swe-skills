# How a step is judged, and the evidence

## Verdicts

| Verdict | Meaning |
|---|---|
| `PASS` | every expected result seen, in budget, with no failed or unanswered request and no console error |
| `FAIL` | the app did not do what was expected; the reasons say how |
| `NOT RUN` | the step was refused, held back by the guard, or its evidence could not be made. Not a pass, not a bug |

| Reason starts with | What the browser saw |
|---|---|
| `no response:` | a click sent no request and changed no text: a dead control |
| `expected result not seen` | something happened, or nothing visible did, but not what was expected |
| `missing response:` | a request still had no answer at the timeout |
| `failed request:` | status 400 or higher that was not expected, or a connection that broke |
| `console error:` | the page logged an error or threw |
| `slow:` | the result came, after the budget |
| `control not found`, `ambiguous:` | check your plan first, then the app |
| `the expected result was there before the action` | the expectation proves nothing: rewrite it |
| `the page showed a secret` | the app displays a credential; that step's screenshot and video were deleted |

A failure that may be the guard's own doing (it held a request to an unlisted host or a socket message) is `NOT RUN`.
So is a page that left the allowed hosts. `favicon.ico` is not judged.

## Evidence, per function

```text
<out>/report.md                    pass or fail per function, evidence paths, bugs ready to file
<out>/results.json                 every step: input, expected, observed, requests, console, timing
<out>/<function>/03-click.png      the page after the step (the whole page when it did not pass)
<out>/<function>/03-click.webm     from just before the click until the answer arrived, or the timeout
<out>/<function>/03-click.analysis.md    timeline after the click, and the frames
<out>/<function>/03-click-frames/  t004320ms.png: the frame 4320 ms into the video; frames.json
```

## Reading a video without playing it

The runner decodes each whole video, so a video listed as `opens` did decode. It keeps the first frame, the last, the
frame at the answer (or at giving up) and frames where the picture changed, at most 10. Each name is its time in the
video; `analysis.md` also gives the time after the click.

Open the frames in order and check:

1. before the click: the inputs are the ones in the plan;
2. just after: the page reacted (a pressed button, a spinner) or did not;
3. at the answer: the expected result is really on screen, not covered, cut off or beside an error;
4. the last: it stayed.

The verdict comes from text, requests and console. Frames show what those miss: a result off screen, an overlay, a
layout that broke. Report that as a failure you saw, with the frame.

Several runs, merged into one report with one row per function (a failure in any run stays a failure):

```bash
python3 <this skill>/scripts/testkit.py report --out <out>/report.md <run-1>/results.json <run-2>/results.json
```
