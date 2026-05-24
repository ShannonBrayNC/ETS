export const electionDemo = {
  milestone: 'pre_election',
  jurisdiction: 'Fictional County',
  root: {
    treeSize: 3,
    merkleRoot: '26d51f841c272ed6b07ac13b0041da33c9729c374a4a9a3bd28a98a43f1cb521',
    generatedAt: '2026-05-04T12:00:00Z',
  },
  timeline: [
    {
      eventId: 'elx_evt_0001',
      label: 'Election setup package',
      type: 'election_config_registered',
      privacyClass: 'public',
      status: 'included',
      timestamp: '2026-05-04T09:00:00Z',
    },
    {
      eventId: 'elx_evt_0002',
      label: 'Logic and accuracy evidence',
      type: 'logic_accuracy_test_registered',
      privacyClass: 'restricted',
      status: 'verified',
      timestamp: '2026-05-04T10:30:00Z',
    },
    {
      eventId: 'elx_evt_0003',
      label: 'Ballot batch custody transfer',
      type: 'ballot_batch_custody_transferred',
      privacyClass: 'internal',
      status: 'included',
      timestamp: '2026-05-04T11:45:00Z',
    },
  ],
  proof: {
    eventId: 'elx_evt_0002',
    eventHash: '2291c9035340786e966ffc9f4905c2932547f8f6466148aee537a4c9c66f06ee',
    leafHash: '4775ca6f90e3796e6667af8a068178680914ec3749c0c418ac3db98741afa7c0',
    payloadHash: '2222222222222222222222222222222222222222222222222222222222222222',
    auditPath: [
      {
        position: 'left',
        hash: '77f320aa42d4d46367620fe206810e6fb2b2bad91845e8f55ba0c9c57d722a7f',
      },
      {
        position: 'right',
        hash: '67784be331eb322659e9412509c9892e2671e49d12be6d7ca40b3e3ed5c1ad42',
      },
    ],
  },
  validVerification: {
    valid: true,
    reason: 'ok',
  },
  tamperVerification: {
    valid: false,
    reason: 'leaf hash does not match event hash',
    tamperedLeafHash: '0000000000000000000000000000000000000000000000000000000000000000',
  },
}
