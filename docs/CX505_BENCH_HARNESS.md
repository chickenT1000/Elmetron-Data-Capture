# CX-505 Bench Harness (Simulation Mode)

This checklist describes the preparatory bench harness for CX-505 when hardware is not yet connected. It provides simulated telemetry and watchdog monitoring to ensure that acquisition, logging, and health API flows are ready before the live meter is attached.

## Prerequisites
- Python 3.11+
- Repository dependencies installed (`pip install -r requirements.txt` if applicable)
- No CX-505 hardware connected (simulation mode enabled)

## Simulation Profiles and Config
- `config/bench_harness.toml` provides acquisition settings for the harness (transport set to `sim`).
- `config/protocols.toml` includes the `cx505_sim` profile used for simulated windows (transport `sim`).

## Running the Harness
```bash
python scripts/run_bench_harness.py \
  --config config/bench_harness.toml \
  --protocols config/protocols.toml \
  --database data/bench_harness.sqlite \
  --health-port 8051 \
  --watchdog-timeout 10 \
  --window 2 --idle 1
```

This command:
- launches acquisition in simulated profile mode
- records telemetry into `data/bench_harness.sqlite`
- exposes health API on `http://127.0.0.1:8051/health`
- enables watchdog monitoring with 10-second timeout

## Validating Outputs
1. Visit `http://127.0.0.1:8051/health` to inspect telemetry snapshot (frames, command metrics, response times).
2. Observe stdout for watchdog events if `--health-log` flag is added.
3. Use `validate_protocols.py config/protocols.toml` to ensure the simulation profile remains valid.

## Transition to Live CX-505
Once the meter is connected:
- Remove `--profile cx505_sim` override (or set to actual profile such as `cx505`).
- Provide real device index/serial using `--device-index` or `--device-serial` flags in `scripts/run_bench_harness.py`.
- Re-run harness, confirm telemetry reflects live frames, and document run as part of CX-505 verification.
