# Agent 365 R0 Step 4 verification checklist

- [x] SharePoint authorization retained as canonical source bytes
- [x] Gateway ingress/decision/egress digest chain retained
- [x] Gateway robot command retained and bound to authorization material
- [x] Ranger motion and stop directives retained
- [x] Seven Ranger receipt/motion/stop/result records retained in frozen order
- [x] Ranger receipt anchored to Gateway egress digest
- [x] Independent result observer required to differ from motion controller
- [x] `STOP_ACTUATED` kept distinct from `RESULT_OBSERVED`
- [x] Ranger Decision Event generated with source-evidence digests
- [x] ETS Evidence Object v1 generated and reverse verified
- [x] Source artifact bytes reverse verified
- [x] SharePoint completion references generated without changing authorization material
- [x] Separate actuator acknowledgement/response left `NOT_OBSERVED` rather than inferred
