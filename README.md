# ps2-fix2

`ps2-fix2` collects practical compatibility fixes and workaround presets for iPSX2 issues.  The upstream iPSX2 repository currently publishes only a README in the public code tree, so this repository keeps the fixes data-driven until emulator source files are available to patch directly.

## What is fixed here

The first compatibility pack targets the recurring open issues reported against `otti83/iPSX2`:

| Area | Upstream issues | Added profile |
| --- | --- | --- |
| Aspect ratio not applying and virtual pad misses touches in landscape/iPad layouts | #39, #40 | `ui-aspect-pad-landscape` |
| EE Core JIT instability when Interpreter works but is slow | #38, #36 | `ee-core-jit-stability` |
| Need for Speed games missing audio and Carbon loading freezes | #43, #44 | `nfs-audio-and-carbon-loading` |
| Midnight Club 3 Remix infinite garage loading | #46 | `midnight-club-3-garage-streaming` |
| God of War hit-effect flicker | #42 | `god-of-war-hit-flicker` |
| Spinning models, broken geometry, and animation glitches | #39, #41 | `geometry-animation-vu-accuracy` |

Each profile includes affected games, symptoms, safe settings, user-facing steps, and implementation notes for future native emulator patches.

## Repository layout

- `compatibility/presets.json` - structured compatibility profile database.
- `compatibility/graphics_fixes.json` - graphics-focused fix plan database for flicker, black-screen, scrambled-screen, geometry, animation, and viewport issues.
- `tools/compatibility.py` - CLI for validating, listing, showing, and searching profiles and graphics fixes.
- `tests/test_compatibility.py` - regression tests ensuring the databases remain valid and cover the reviewed issues.

## Usage

Validate the profile database:

```bash
python3 tools/compatibility.py validate
```

List all profiles:

```bash
python3 tools/compatibility.py list
```

Filter by upstream issue number:

```bash
python3 tools/compatibility.py list --issue 46
```

Show a full workaround profile:

```bash
python3 tools/compatibility.py show midnight-club-3-garage-streaming
```

Search by game, symptom, or setting text:

```bash
python3 tools/compatibility.py search "Need for Speed"
```

List graphics-specific fixes:

```bash
python3 tools/compatibility.py graphics-list
```

Show the God of War flicker fix plan:

```bash
python3 tools/compatibility.py graphics-show gow-hit-flash-framebuffer-feedback
```

Search visual symptoms such as black screens or scrambled output:

```bash
python3 tools/compatibility.py graphics-search "black screen"
```

## Graphics bug fixes

The graphics fix database adds targeted renderer/accuracy plans for these issue reports:

| Graphics issue | Upstream issue | Added graphics fix | Key action |
| --- | --- | --- | --- |
| God of War flickers for a few seconds when hits occur | #42 | `gow-hit-flash-framebuffer-feedback` | Force accurate framebuffer feedback, destination alpha, and texture-barrier/framebuffer-fetch behavior at Native 1x. |
| Silent Hill 2 shows gameplay as a black screen after the first cutscene | #50 | `silent-hill-2-black-screen-depth-fog` | Disable unsafe hacks and require accurate depth/fog/readback behavior for gameplay scenes. |
| Scarface boots but the screen is scrambled | #49 | `scarface-scrambled-screen-target-resolve` | Increase texture-cache precision and resolve aliased render targets before presentation. |
| Dark Cloud 2 / Odin Sphere have spinning models or broken geometry | #41 | `vu-geometry-spinning-models` | Treat the visual symptom as VU transform accuracy: disable unsafe VU speedhacks and use VU interpreters. |
| Crash Twinsanity has animation glitches and iPad aspect scaling problems | #39 | `crash-twinsanity-animation-and-ipad-scaling` | Recompute iPad viewport/scissor state and add a VU fallback for animation glitches. |

## Applying these fixes in an emulator build

Until source code is available, apply the `settings`, `renderer_actions`, and `user_steps` in the matching profile manually.  When the emulator source is imported, the `implementation_notes` and `implementation_patch_plan` fields identify the native changes to prioritize, such as recalculating Metal viewports and touch hitboxes on orientation changes, adding per-game JIT/VU fallbacks, tightening CDVD/SPU2 timing for stream-heavy games, and adding accurate Metal render-target resolves for framebuffer-feedback effects.
