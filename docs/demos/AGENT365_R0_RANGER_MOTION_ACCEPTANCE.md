# P0 Step 3 acceptance matrix

The Ranger receipt/motion boundary is accepted only when repository tests establish the matrix
below. This is a software-boundary qualification, not a physical safety certification.

| Gate | Required behavior |
| --- | --- |
| Gateway binding | Ranger rejects a Gateway egress commitment that does not match the exact robot command. |
| Correlation | Every main-path Ranger event retains the original canonical UUIDv4 `mission_id`. |
| Chain continuity | The first Ranger event chains to Gateway egress; each later event chains to its predecessor. |
| Exactly-once execution | A correctly linked transport retry is durably retained but returns `execute=false`. |
| Local interlock | Hardware E-stop or local-not-ready denies motion after Gateway authorization. |
| Start boundary | Motion start may not exceed the authorized forward-speed ceiling. |
| Stop observation | The STOP decision cannot precede an observed bounded stop condition. |
| Obstacle bound | An obstacle outside `stop_distance_m` cannot satisfy the frozen obstacle-stop trigger. |
| Actuation boundary | A stop-controller acknowledgement does not transition directly to completed result. |
| Result boundary | Completion requires a later, non-actuator observer with stationary measurements. |
| Contradiction retention | A post-stop observation showing continued motion produces `FAILED_OBSERVATION`. |
| Ordering | Local monotonic event time must strictly increase along the main mission chain. |
| Scope freeze | No turning, rerouting, obstacle avoidance, path planning, payload action, or multi-step mission is added. |

The two positive acceptance paths are the same frozen behavior with different stop triggers:

```text
marked-stop:
Gateway -> receipt -> authorize -> forward start -> marked-stop observation
        -> STOP decision -> stop actuation -> stationary result observation

obstacle-stop:
Gateway -> receipt -> authorize -> forward start -> obstacle <= stop_distance_m
        -> STOP decision -> stop actuation -> stationary result observation
```
