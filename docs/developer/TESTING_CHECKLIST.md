# CX-505 Live Test Procedure Checklist

This checklist guides the transition from the simulation bench harness to a live CX-505 capture rehearsal. The objective is to verify telemetry integrity, watchdog responsiveness, and logging completeness prior to the production run.

## 1. Pre-Test Preparation
- [ ] Ensure the bench harness simulation run has been performed and reviewed (see `docs/CX505_BENCH_HARNESS.md`).
- [ ] Install required Python dependencies and verify `py -3 -m pytest` completes successfully.
- [ ] Validate protocol registry with the live profile: `python validate_protocols.py config/protocols.toml` (expect no errors).
- [ ] Confirm capture database location (default `data/live_rehearsal.sqlite` or operator-defined path).
- [ ] Identify CX-505 device serial/index and ensure FTDI drivers are installed.

## 2. Hardware Setup
- [ ] Connect CX-505 to the bench PC via USB and allow FTDI drivers to enumerate.
- [ ] Run `python cx505_capture_service.py --list-devices` and record device index/serial.
- [ ] Inspect cables, buffer solutions, and ensure the sensor is immersed in the appropriate calibration solution (e.g., pH 7 buffer) for telemetry sanity checks.

## 3. Harness Configuration (Transition from Simulation)
- [ ] Update `config/bench_harness.toml` (or copy to `config/live_rehearsal.toml`) to include:
  - `device.serial` or `device.index` set to the live instrument.
  - `device.transport = "ftdi"`.
  - `device.use_profile_defaults = true` (unless customizing serial parameters).
  - `acquisition.startup_commands` populated with required calibration/heartbeat commands.
- [ ] Ensure `config/protocols.toml` selects the live profile (`cx505`) instead of `cx505_sim`.
- [ ] Optional: create a dated database path (e.g., `data/live_rehearsal_YYYYMMDD.sqlite`).

## 4. Launching the Live Harness
- [ ] Execute:
  ```bash
  python scripts/run_bench_harness.py \
      --config config/live_rehearsal.toml \
      --protocols config/protocols.toml \
      --database data/live_rehearsal.sqlite \
      --health-port 8052 \
      --watchdog-timeout 10 \
      --window 2 --idle 1 \
      --extra-args --device-serial <SERIAL>
  ```
- [ ] Observe stdout for startup logs, command execution traces, and ensure no immediate errors.
- [ ] Confirm health API availability: `http://127.0.0.1:8052/health` (check frames, command metrics, response times).
- [ ] If `--health-log` is enabled, verify watchdog events print to console.

## 5. Telemetry & Watchdog Verification
- [ ] Allow the harness to run for at least 5 capture windows.
- [ ] Verify database entries via sqlite CLI or a quick inspection script:
  - Measurements inserted with realistic values.
  - Raw frames present and non-zero.
- [ ] Confirm watchdog does not emit timeouts under normal operation (unless intentionally tested).
- [ ] Trigger a fault scenario (optional, if feasible) to ensure watchdog alerts/health API reflects the event.

## 6. Acceptance Criteria
- [ ] No unhandled exceptions or fatal errors in harness output during the run.
- [ ] Health API shows `state = "running"` and frames incrementing.
- [ ] Database contains expected measurement count (aligned with run duration and window settings).
- [ ] Watchdog alert status remains clear (or recovers if intentionally triggered).
- [ ] Session metadata logs device profile, serial, and configuration details.
- [ ] Checklist signed off by engineer (record date, operator, instrument serial).

## 7. Post-Test Actions
- [ ] Archive the rehearsal database, logs, and health API snapshots for audit.
- [ ] Reset harness configuration to simulation defaults if further testing without hardware is required.
- [ ] Document any anomalies or observations in the test log.

## References
- Simulation harness workflow: `docs/CX505_BENCH_HARNESS.md`
- Harness runner: `scripts/run_bench_harness.py`
- Protocol validation CLI: `validate_protocols.py`
- Health API documentation: `docs/UI_MVP_SCOPE.md` (service health section)
