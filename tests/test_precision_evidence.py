import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "precision-mcp"))

from precision_mcp.evidence import EvidenceBundle, JobState


class PrecisionEvidenceTests(unittest.TestCase):
    def test_bundle_writes_canonical_utf8_json_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = EvidenceBundle(Path(directory), "desk-001")
            path = bundle.write_contract("scene_spec", {"label": "杏团", "b": 2, "a": 1})
            expected = '{\n  "a": 1,\n  "b": 2,\n  "label": "杏团"\n}\n'
            self.assertEqual(path.read_text(encoding="utf-8"), expected)
            digest = bundle.sha256(path)
            self.assertEqual(len(digest), 64)
            self.assertEqual(digest, hashlib.sha256(expected.encode("utf-8")).hexdigest())

    def test_invalid_state_transition_is_rejected(self):
        state = JobState("desk-001")
        with self.assertRaisesRegex(
            ValueError, "invalid transition: planned -> committed"
        ):
            state.transition("committed")

    def test_bundle_writes_assumptions(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = EvidenceBundle(Path(directory), "desk-001")
            path = bundle.write_assumptions(
                ["hidden rear fasteners inferred from the front view"]
            )
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# Unresolved assumptions\n\n"))
            self.assertIn("hidden rear fasteners", text)

    def test_valid_transition_sequence_reaches_committed(self):
        state = JobState("desk-001")
        for target in (
            "active",
            "external_pending",
            "external_failed",
            "active",
            "validating",
            "failed_qa",
            "active",
            "validating",
            "committed",
        ):
            state.transition(target)
        self.assertEqual(state.value, "committed")

    def test_checkpoint_and_preview_paths_are_allowlisted_and_contained(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = EvidenceBundle(Path(directory), "desk-001")
            checkpoint = bundle.checkpoint_path("before")
            preview = bundle.preview_path("orthographic")
            self.assertEqual(checkpoint, bundle.root / "checkpoints" / "before.blend")
            self.assertEqual(preview, bundle.root / "previews" / "orthographic.png")
            self.assertTrue(checkpoint.resolve().is_relative_to(bundle.root))
            self.assertTrue(preview.resolve().is_relative_to(bundle.root))

            for invalid in ("after", "../final", "final/../../escape"):
                with self.subTest(checkpoint=invalid):
                    with self.assertRaises(ValueError):
                        bundle.checkpoint_path(invalid)
            for invalid in ("front", "../perspective", "perspective/../../escape"):
                with self.subTest(preview=invalid):
                    with self.assertRaises(ValueError):
                        bundle.preview_path(invalid)

    def test_job_id_rejects_path_traversal_before_creating_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            workdir = Path(directory)
            for job_id in ("../escape", "Desk-001", "bad_name", "a" * 65):
                with self.subTest(job_id=job_id):
                    with self.assertRaisesRegex(ValueError, "invalid job_id"):
                        EvidenceBundle(workdir, job_id)
            self.assertFalse((workdir / "evidence").exists())


if __name__ == "__main__":
    unittest.main()
