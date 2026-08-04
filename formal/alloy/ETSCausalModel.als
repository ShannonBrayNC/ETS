module ETSCausalModel

// This model is structural and causal. It supports reasoning about modeled
// event relationships, tenant/workspace association, append-only uniqueness,
// and omission relative to an external expected set.
// It does not prove real-world truth, legal sufficiency, election correctness,
// cryptographic hash security, hosted identity correctness, or completeness
// without an external expected-event policy and observation process.
sig Event {
  id: one EventId,
  previous: lone Event,
  tenant: one Tenant,
  workspace: one Workspace
}

sig EventId {}
sig Tenant {}
sig Workspace {}

sig Log {
  entries: seq Event
}

sig ExpectedSet {
  expected: set EventId
}

pred appendOnly[l: Log] {
  all i, j: l.entries.inds |
    i < j implies l.entries[i] != l.entries[j]
}

pred tenantScoped[l: Log] {
  all i, j: l.entries.inds |
    l.entries[i].tenant != l.entries[j].tenant implies
      l.entries[i].workspace != l.entries[j].workspace or
      l.entries[i].id != l.entries[j].id
}

fun observedIds[l: Log]: set EventId {
  l.entries.elems.id
}

pred omitted[e: ExpectedSet, l: Log, missing: EventId] {
  missing in e.expected
  missing not in observedIds[l]
}

assert NoDuplicateEventsInAppendOnlyLog {
  all l: Log |
    appendOnly[l] implies no disj i, j: l.entries.inds |
      l.entries[i] = l.entries[j]
}

assert OmissionRequiresExternalExpectation {
  all e: ExpectedSet, l: Log, missing: EventId |
    omitted[e, l, missing] implies missing in e.expected
}

check NoDuplicateEventsInAppendOnlyLog for 5
check OmissionRequiresExternalExpectation for 5
