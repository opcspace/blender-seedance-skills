# BaseMesh scale policy

Use metric Blender units: 1 Blender unit = 1 meter. These are target envelopes for the first white-model pass, not rigid production dimensions.

| Category | Asset | Target envelope / primary scale |
| --- | --- | --- |
| Character | realistic adult | height 1.7–1.9 m; feet on Z=0 |
| Character | Q-style body | height 1.0–1.3 m; head 35–50% of total height |
| Creature | wolf / mammal | length 1.8–2.5 m; shoulder height 0.8–1.3 m |
| Creature | dragon / fantasy | length 3–6 m; feet/contact on Z=0; wings fit the camera envelope |
| Props | chair / furniture | height 0.8–1.1 m |
| Props | sword / shield | sword length 0.9–1.2 m; shield diameter 0.6–0.9 m |
| Architecture | house module | 3–8 m high; door/opening around 2 m |
| Architecture | city / sci-fi module | 6–30 m high; camera must show the complete module |
| Hard surface | car | length 4–5 m; width 1.7–2.1 m; height 1.3–1.8 m |
| Hard surface | mech shell | height 3–8 m; feet and major joints readable |
| Environment | rock cluster | 1–4 m dominant height; ground context included |
| Environment | tree base | 4–8 m total height; canopy and trunk both inside frame |
| Abstract | sculpture base | 1–3 m dominant height; negative space preserved |

## Normalization algorithm

1. Build the blockout under a named root.
2. Query every mesh's location and dimensions.
3. Compute `min_z`, `max_z` and the X/Y/Z envelope.
4. Choose the target height from this table and apply one uniform root scale factor `target_height / (max_z - min_z)`.
5. Translate the root by `-min_z * factor` so the lowest support touches Z=0.
6. Re-query the envelope and place the camera from the envelope center and maximum span. Use a wider distance for architecture and environment, and a closer distance for props and character portraits.
7. Render a test still. If any major mass is cropped or the object occupies less than roughly half the frame, adjust camera distance and repeat.

This pass is required before declaring a BaseMesh preview usable. If MCP cannot edit a root or query dimensions, report the measured bounds and leave scale normalization as a manual Blender step.
