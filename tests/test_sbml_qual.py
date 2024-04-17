import requests

from mira.sources.sbml.qual_api import template_model_from_sbml_qual_string
from mira.sources.biomodels import get_sbml_model

apoptosis_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Apoptosis_stable.sbml?ref_type=heads"
)

coagulation_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Coagulation-pathway_stable.sbml?ref_type=heads"
)

stress_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/ER_Stress_stable.sbml?ref_type=heads"
)

etc_stable_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/ETC_stable.sbml?ref_type=heads"
)

e_protein_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/E_protein_stable.sbml?ref_type=heads"
)

hmox1_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/HMOX1_Pathway_stable.sbml?ref_type=heads"
)

ifn_lambda_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/IFN-lambda_stable.sbml?ref_type=heads"
)

interferon_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Interferon1_stable.sbml?ref_type=heads"
)

jnk_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/JNK_pathway_stable.sbml?ref_type=heads"
)
kyu_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Kynurenine_pathway_stable.sbml?ref_type=heads"
)
nlrp3_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/NLRP3_Activation_stable.sbml?ref_type=heads"
)
nsp_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Nsp14_stable.sbml?ref_type=heads"
)
nsp4_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Nsp4_Nsp6_stable.sbml?ref_type=heads"
)
nsp9_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Nsp9_protein_stable.sbml?ref_type=heads"
)
orf10_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Orf10_Cul2_pathway_stable.sbml?ref_type=heads"
)
orf3a_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Orf3a_stable.sbml?ref_type=heads"
)
pamp_signal_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/PAMP_signaling_stable.sbml?ref_type=heads"
)
pyrimidine_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Pyrimidine_deprivation_stable.sbml?ref_type=heads"
)
rtc_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/RTC-and-transcription_stable.sbml?ref_type=heads"
)
renin_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Renin_angiotensin_stable.sbml?ref_type=heads"
)
tgfb_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/TGFB_pathway_stable.sbml?ref_type=heads"
)
virus_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Virus_replication_cycle_stable.sbml?ref_type=heads"
)

file_list = [
    apoptosis_file,
    stress_file,
    coagulation_file,
    etc_stable_file,
    e_protein_file,
    hmox1_file,
    ifn_lambda_file,
    jnk_file,
    kyu_file,
    nlrp3_file,
    nsp_file,
    nsp4_file,
    nsp9_file,
    orf10_file,
    orf3a_file,
    pamp_signal_file,
    pyrimidine_file,
    rtc_file,
    renin_file,
    tgfb_file,
    virus_file,
]


def test_qual_models_from_example_repo():
    for file in file_list:
        xml_string = file.text
        tm = template_model_from_sbml_qual_string(xml_string)


def test_qual_models_from_biomodels():
    model_ids = ["BIOMD0000000562", "BIOMD0000000592", "BIOMD0000000593"]
    for model_id in model_ids:
        model_text = get_sbml_model(model_id)
        tm = template_model_from_sbml_qual_string(model_text)
