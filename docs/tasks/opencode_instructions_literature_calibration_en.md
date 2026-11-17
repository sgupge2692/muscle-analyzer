# Instruction: Implement the Literature-Calibration Pipeline

You are working in the `backend/src/anatomy/` directory of the muscle-analyzer repository. Before starting, read `GUARDRAILS.md` in this same folder/root and follow it strictly.

**Write all commit messages, code comments, and your final report in Japanese.** This instruction is written in English only so the plan is unambiguous to you; the output you produce for the human should be in Japanese.

## Background
`muscle_activation.py` currently combines a static per-exercise base weight (`EXERCISE_BASE_WEIGHTS`) with `_compute_dynamic_modifier`, which only reacts to joint angle *velocity*. It does not account for joint angle *position* (e.g., quadriceps activation during a squat peaks around 90° knee flexion). This task adds that missing piece, grounded in published EMG literature.

## Task 1: Create the literature EMG curve data file
Create `backend/src/anatomy/literature_emg_curves.json` with this structure:

```json
{
  "Squats": {
    "Quadriceps": {"peak_angle_deg": 90, "width_deg": 35, "source": "Marchetti et al. 2016"},
    "Gluteus": {"peak_angle_deg": 90, "width_deg": 50, "source": "Marchetti et al. 2016"}
  },
  "Deadlift": {
    "Hamstring": {"peak_angle_deg": null, "width_deg": null, "note": "Angle-dependence is small per literature; non-monotonic correction not applied", "source": "Marchetti et al. 2016"}
  }
}
```
Every value must be grounded in an actual cited paper. For any muscle/exercise combination where the literature is unclear, use `null` rather than guessing. Scope is limited to Squats and Deadlift, and to Quadriceps / Gluteus / Hamstring / Erector Spinae only.

## Task 2: Implement the angle-position modifier
Add this function to `muscle_activation.py`:

```python
def _angle_position_modifier(angle_deg: float, peak_angle_deg: float, width_deg: float) -> float:
    """Returns a Gaussian-shaped weight (0-1) centered on the literature-reported peak angle."""
    import math
    return math.exp(-((angle_deg - peak_angle_deg) ** 2) / (2 * width_deg ** 2))
```
- Apply this only for muscle/exercise pairs that have an entry in `literature_emg_curves.json`.
- For everything else, fall back to the existing `_compute_dynamic_modifier` logic unchanged (do not break backward compatibility).
- Confirm any existing tests still pass; if there are none, add at least one minimal unit test.

## Task 3: Fix the inconsistency in EXERCISE_BASE_WEIGHTS
The `Deadlift` entry currently has no `Quadriceps` weight, even though EMG literature reports meaningful quadriceps activation during deadlifts. Add a reasonable weight (consistent in magnitude with the other listed muscles for that exercise, roughly 0.15–0.20 as a starting point) and document the reasoning in `docs/muscle_mapping_review.md`.

## Task 4: Validation script
Create `backend/scripts/literature_validation.py`:
- For each entry in `literature_emg_curves.json`, compute the system's estimated activation across a 0–180° angle sweep and compare it against the literature curve (the Gaussian function from Task 2).
- Compute Pearson's r using `scipy.stats.pearsonr`, printing results and writing them to a CSV.
- Use only the existing virtual environment and requirements.txt dependencies; ask before adding anything new.

## Definition of done
- [ ] `literature_emg_curves.json` created, with sources cited for every non-null value
- [ ] `_angle_position_modifier` implemented, without changing the `/analyze` API response shape
- [ ] Deadlift weight fix made and documented
- [ ] `literature_validation.py` runs and outputs correlation coefficients
- [ ] Existing functionality (WebSocket real-time analysis, rep detection) confirmed still working

## How to proceed
Commit each task separately, not all at once. Write each commit message in Japanese, stating what changed and why. When all tasks are done, report a summary of changes in Japanese. If you're unsure about anything — especially how to interpret a literature value — stop and ask before proceeding.
