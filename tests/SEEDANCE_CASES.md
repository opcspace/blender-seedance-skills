# Seedance 2.5 official template regression

The six cases below were tested against the official Dreamina prompt templates. Each case created a minimal Blender blockout, an active camera, a Workbench preview at 640×360, and a prompt record. Dreamina generation itself remains an external/login-dependent step.

| Alias | Blender blockout | Preview |
| --- | --- | --- |
| `grey_city_cyberpunk` | Road plane, three building masses and alley block | [PNG](assets/seedance_cases/grey_city_cyberpunk.png) |
| `white_castle_fantasy` | Terrain, keep, two towers, wall and gate | [PNG](assets/seedance_cases/white_castle_fantasy.png) |
| `low_poly_car_chase` | Road, hero car, pursuer car and lane markers | [PNG](assets/seedance_cases/low_poly_car_chase.png) |
| `white_interior_walkthrough` | Floor, walls, sofa, table and stair proxy | [PNG](assets/seedance_cases/white_interior_walkthrough.png) |
| `character_pose_hero` | Head, torso, arms, hero prop and floor | [PNG](assets/seedance_cases/character_pose_hero.png) |
| `blockout_board_final` | Three storyboard boards, timeline and screen frame | [PNG](assets/seedance_cases/blockout_board_final.png) |

The machine-readable prompts and MCP results are in [`assets/seedance_cases/results.json`](assets/seedance_cases/results.json).

## Acceptance criteria

- Prompt contains 30-second duration, case title and transformation intent.
- Prompt identifies multimodal reference types.
- Prompt preserves core composition and subject intent.
- Prompt includes camera movement, timeline pacing, lighting and localized refinement.
- Prompt includes `no readable text` and `no watermark` constraints.
- Blender preview has a named blockout, active camera and a valid PNG artifact.

