# P0 Step 3 implementation scope

Branch: `demo/p0-ranger-r0-motion-boundary`

This slice implements only the Ranger-side receipt/motion boundary required by the frozen
Agent 365 + M365 + Ranger R0 demonstration. It consumes the exact Gateway command introduced by
P0 Step 2 and does not introduce a second mission format.

Implemented artifacts:

- `ets/ranger/agent365_r0_motion.py` — executable robot-side state machine and durable retry
  deduplication boundary;
- `tests/test_agent365_r0_ranger_motion.py` — positive and negative qualification cases;
- `docs/demos/AGENT365_R0_RANGER_MOTION_BOUNDARY.md` — operator/architecture contract;
- `docs/demos/AGENT365_R0_RANGER_MOTION_RESEARCH.md` — external engineering research boundary;
- `docs/demos/AGENT365_R0_RANGER_MOTION_ACCEPTANCE.md` — frozen acceptance matrix.

Not included:

- generalized autonomous navigation;
- ROS 2 dependency or hardware driver selection;
- machinery-safety certification;
- Ranger Decision Event projection;
- Evidence Object projection;
- independent-verifier packaging;
- physical qualification run results.
