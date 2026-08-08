# Commercial use and high-precision delivery policy

## What is commercially usable

The OPCspace Skill and `precision-mcp` source code are released under the repository MIT License.
Commercial users may run, modify, integrate and redistribute this code while preserving the copyright
notice and license text.

The precision workflow is intended for dimension-driven white models and editable BaseMeshes. A
commercial delivery should include the model specification, `.blend` checkpoint, measurement report,
preview render and a list of unresolved assumptions.

## What is not automatically licensed

- Blender itself and its bundled components.
- CAD Sketcher, if installed; it is a separate GPL-3.0 dependency and is not vendored here.
- Jimeng/Dreamina/Seedance and Volcengine services, accounts, APIs and generated results.
- The supplied Jimeng uploader ZIP, whose redistribution rights must be confirmed with its provider.
- Reference images, AI-generated references, scans, trademarks, likenesses and downloaded models.

The repository license does not grant rights to any of those third-party assets or services.

## Precision claim policy

Use the following wording in a commercial handoff:

- **L0**: blockout; visual composition only.
- **L1**: measured structured white model; dimensions and contact points passed the declared tolerance.
- **L2**: high-precision editable BaseMesh; typed precision MCP runtime, geometry QA, checkpoint and
  reference/constraint report all passed.

Do not call an image-only reconstruction, a primitive-only smoke test or an unverified background
render “CAD-level”, “production topology” or “watertight”.

## Minimum evidence bundle

1. `model_spec.json` with units, dimensions, tolerance and category.
2. `.blend` checkpoint before the first destructive change and final editable file.
3. Geometry report containing bounds, dimensions, non-manifold count and ground contact.
4. White-model preview with an uncropped silhouette.
5. Reference-confidence and unresolved-assumptions notes.
6. Third-party asset/license inventory when external references or plugins were used.
