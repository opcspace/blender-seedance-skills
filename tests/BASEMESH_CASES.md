# BaseMesh category regression

Fourteen representative BaseMesh cases were tested against the seven library categories. Each case used a named `BASE_<asset>_ROOT`, primitive blockout parts, explicit parent relationships, Bevel modifiers, an active camera and a 640×360 Workbench preview.

| Category | Cases | Result |
| --- | --- | --- |
| Character | realistic male, stylized Q-body | Pass with silhouette-quality follow-up |
| Creature | wolf, dragon | Pass with appendage-quality follow-up |
| Props and still life | chair, sword + shield | Pass; orientation check required |
| Architecture | traditional house, sci-fi module | Pass; module/camera check required |
| Hard surface and machines | car shell, mech shell | Pass with hard-surface refinement follow-up |
| Environment and terrain | rock cluster, tree base | Pass; full-height framing check required |
| Abstract forms | primitive set, irregular sculpture base | Pass |

## Evidence

Machine-readable results and all 14 PNGs are in [`assets/basemesh_cases/`](assets/basemesh_cases/). Representative previews:

- [Realistic character](assets/basemesh_cases/character_realistic_male.png)
- [Dragon base](assets/basemesh_cases/creature_dragon.png)
- [Sword and shield](assets/basemesh_cases/prop_sword_shield.png)
- [Sci-fi architecture](assets/basemesh_cases/architecture_sci_fi_module.png)
- [Mech shell](assets/basemesh_cases/machine_mech.png)
- [Tree base](assets/basemesh_cases/environment_tree_base.png)
- [Abstract sculpture](assets/basemesh_cases/abstract_sculpture.png)

## Known limits

The restricted MCP tool set can create and parent objects, but it cannot write custom properties, create collections, create an armature, or save the active `.blend`. Therefore `reference_confidence`, `rig_ready`, collection isolation and library checkpoint are reported as metadata/manual follow-ups rather than claimed as completed Blender data.

