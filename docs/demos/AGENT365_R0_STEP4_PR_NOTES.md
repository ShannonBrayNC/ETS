# Step 4 review notes

Primary code: `ets/ranger/agent365_r0_evidence.py`

Primary tests: `tests/test_agent365_r0_evidence.py`

The verifier reparses retained canonical source bytes rather than trusting the live builder inputs. The Evidence Object is therefore checked against both its own integrity commitments and the retained authorization/Gateway/Ranger source bundle.
