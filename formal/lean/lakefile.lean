import Lake
open Lake DSL

package etsProofs where
  version := v!"0.1.0"
  keywords := #["ETS", "formal-methods", "temporal-liveness", "evidence"]

lean_lib ETSProofs where
  srcDir := "src"
