# Hackaton scenarios 2023 July

The notebooks and model files in this folder are produced by MIRA.
All model JSON files use the AMR schema defined in
https://github.com/DARPA-ASKEM/Model-Representations/tree/main/petrinet.

Notebooks

| Notebook    | Description |
| -------- | ------- |
| scenario1.ipynb  | Scenario 1 implementation notebook    |
| scenario1-2-wastewater.ipynb | Scenario 1 wastewater notebook |
| scenario2.ipynb | Scenario 2 implementation notebook    |

Models

|Model|Description|
|-----|-----------|
|scenario1_a.json|Scenario 1.1.a: base model|
|scenario1_c.json|Scenario 1.1.c: model with more complex beta|
|scenario1_d.json|Scenario 1.1.d: model with reinfection|
|scenario1_d_normalized.json| Scenario 1.1.d: model with unit normalization|
|scenario1_2c_age.json| Scenario 1.2.c: model with three age groups|
|scenario1_2c_age_diag.json| Scenario 1.2.c: model with three age groups and diagnosed/undiagnosed|
|scenario1_2c_age_diag_vax.json| Scenario 1.2.c: model with three age groups, diagnosed/undiagnosed and vaccination|
|scenario1_q2_fazli.json| Scenario1 Wasterwater Model by Fazli et al.|
|scenario1_q2_mcmahan.json| Scenario1 Wasterwater Model by McMahan et al.|
|scenario2_a_beta_scale_static.json| Scenario 2.1.a: simple base model (static beta\_scale)|
|scenario2_a_beta_scale_var.json| Scenario 2.1.a: simple base model (piecewise varying beta\_scale)|
|scenario2_2_b_multi_vax.json| Scenario 2.2.b: base model stratified for Pfizer and AZ vaccines|
|scenario2_2_b_multi_vax_multi_strain.json|Scenario 2.2.b: stratified for Pfizer and AZ vaccines and WT, Alpha, Delta variants|
|scenario2_4_a_multi_vax_delta_omicron.json|Scenario 2.4.a: stratified for Pfizer and AZ vaccines and Delta, Omicron variants|
|scenario2_5_c_multi_vax_delta_omicron_age.json|Scenario 2.5.c: stratified for Pfizer and AZ vaccines and Delta, Omicron variants, and 5 age groups|
