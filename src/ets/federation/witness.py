class WitnessFederation:
    def __init__(self):
        self.roots = {}

    def observe(self, log_id, tree_size, root_hash, verifier_id):
        key = (log_id, tree_size)

        existing = self.roots.get(key)

        if existing and existing != root_hash:
            return {
                "status": "ForkDetected",
                "expected": existing,
                "observed": root_hash,
                "verifier": verifier_id,
            }

        self.roots[key] = root_hash

        return {
            "status": "OK",
            "root": root_hash,
        }
