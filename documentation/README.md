# Submission Guidelines for TREC AutoJudge

We encourage [code submissions](#submission-variant-2-code-submissions) so that AutoJudge systems can be re-executed by others.
Organizing code so that it runs on machines that are not under your control requires more effort (please consider to add the code of your approach via a pull request to this repository as this allows us to provide help and maintain everything in one place).
We also allow to [manually upload submissions](#submission-variant-1-upload-of-submissions).

<details>
<summary>Prerequisite: Create an Account at TIRA.io and register a team to TREC AutoJudge in TIRA</summary>

### Step 1: Create an Account at TIRA

Please go to [https://www.tira.io/](https://www.tira.io/) and click on "Sign Up" to create a new account or "Log In" if you already have an account. You can either create an new account or Log in via GitHub or Google.

<img width="1042" height="965" alt="Screenshot_20251210_074005" src="https://github.com/user-attachments/assets/6f05d18d-3b03-4314-94b4-b1136613b362" />

### Step 2: Register Your Team to TREC AutoJudge

After you have logged in to TIRA, please navigate to the TREC AutoJudge task at [https://www.tira.io/task-overview/trec-auto-judge](https://www.tira.io/task-overview/trec-auto-judge). There, please click on "Register".

<img width="1726" height="554" alt="Screenshot_20251210_074553" src="https://github.com/user-attachments/assets/cb30f158-c62f-4201-9805-42dc1c0d64bb" />

### Step 3 (Optional): Manage your team

If you want to add others to your team, please navigate to your groups (under the hamburger menu) at [https://www.tira.io/g?type=my](https://www.tira.io/g?type=my)

</details>

## Submission Variant 1: Upload of Submissions

In cases where [code submissions](#submission-variant-2-code-submissions) do not make sense (e.g., for manually curated leaderboards, when systems are very experimental, or when deadlines are close), we encourage to upload your submissions manually.

A manual submission has the following two files:

```
├── ir-metadata.yml
└── trec-leaderboard.txt
```

where `ir-metadata.yml` describes the approach in the [ir_metadata format](https://www.ir-metadata.org/) (**attention: we still need to discuss which fields we want to make mandatory, currently nothing is mandatory**) and `trec-leaderboard.txt` is in a [format congruent to trec_eval -q](https://github.com/trec-auto-judge/auto-judge-code/tree/main/trec25/datasets/spot-check-dataset#formats).

The directory [leaderboard-upload-skeleton](leaderboard-upload-skeleton) contains an example that you can use as starter.

<details>
<summary>Step 1: Authentication and Login</summary>

We assume you have created an account at TIRA.io and have registered a team to TREC AutoJudge following the prerequisite above.

The preferred way to upload a submission to TIRA is via the command line interface, as this already can check that everything is in the correct format on your side.

Please install the TIRA cli via:

```
pip3 install --upgrade tira
```

Next, you need an authentication token:

- Navigate to the TREC AutoJudge task in TIRA [https://www.tira.io/task-overview/trec-auto-judge](https://www.tira.io/task-overview/trec-auto-judge)
- Click on "submit" => "Run Uploads" => "I want to upload runs via the command line". The UI shows your authentication token:

<img width="1964" height="503" alt="Screenshot_20251210_095119" src="https://github.com/user-attachments/assets/12e55ed2-a670-473c-ac4d-748a169afefa" />

Assuming your authentication token is AUTH-TOKEN, please authenticate via:

```
tira-cli login --token AUTH-TOKEN
```

Lastly, to verify that everything is correct, please run `tira-cli verify-installation`. Outputs might look like:

<img width="821" height="180" alt="Screenshot_20251210_095410" src="https://github.com/user-attachments/assets/51160132-eb19-4da3-8892-8a53adb41c71" />

</details>


<details>
<summary>Step 2: Upload your Submission</summary>

An complete overview of all dataset IDs for which you can upload submissions is available at [https://www.tira.io/datasets?query=trec-auto-judge](https://www.tira.io/datasets?query=trec-auto-judge). **Attention, some datasets that have missing responses or duplicated IDs are not yet available, as we first wanted to discuss how to handle them, this is ongoing in [this issue](https://github.com/trec-auto-judge/auto-judge-code/issues/2).**


Assuming you have your results in the `leaderboard-upload-skeleton` directory for the dataset id `spot-check-dataset-20251202-training`, then please first ensure that everything is valid via:

```
tira-cli upload --dataset spot-check-dataset-20251202-training --directory leaderboard-upload-skeleton --dry-run
```

The output should look like:

<img width="1074" height="131" alt="Screenshot_20251210_123926" src="https://github.com/user-attachments/assets/18c7f1d7-12d2-4ecc-9d2e-73cf31ec3582" />

If everything looks good, you can re-run the command and remove the `--dry-run` argument to upload your submission.

</details>

<details>
<summary>Alternative: Upload your Submission via the UI</summary>
TBD ...
</details>

## Submission Variant 2: Code Submissions

### Our Goal

**We want to make a reasonable set of LLM Judges easily accessible so that they can be easily re-executed.**

We would like to collect approaches via pull requests into this repository via this structure:

<img width="232" height="271" alt="Screenshot_20251210_134435" src="https://github.com/user-attachments/assets/2e60977f-1478-4750-b6fe-ac8399d890ba" />

I.e., we aim that for each year, we collect the systems in an "append only" mono repository. Please note: You can also work in a private repository, so it is not required that you contribute your code to this repository, but in cases where contributing code to this repository makes sense, please do not hesitate to do so.

### Requirements to Code Submissions

Each system (i.e., a directory like `trec25/my-judge-system` in the structure above) is developed inside its directory as a stand-alone solution. To allow for a maximum flexibility, we aim to make as few requirements to each system as possible. We still have some requirements to ensure that everything is easily maintainable and submittable to TIRA, but it is totally fine when you do not take care on this yourself, and we take care of this (e.g., you can just add the code as you like it, and we add the additional stuff that is required). Our requirements to a code submission (we can help to meet them) are:

- All code must be organized in the repository
- The repository must be clean (i.e., git status indicates no uncommitted chages
- The code must be compatible with the [dev-container standard](https://containers.dev/)

As soon as those requirements are met, a code submission to TIRA performs the following steps:

- The code is compiled into the Docker image as specified by the dev-container
- This image is tested on the local machine on the spot-check dataset to ensure that the software produces valid outputs
- If the outputs are valid, the docker image is uploaded to TIRA
- Within TIRA, we/you run the docker image on all datasets

### Step-by-Step Example

In the following, we will use the Naive AutoJudge system in [../trec25/judges/naive](../trec25/judges/naive) as an hello world example. You can perform all steps below and just re-submit this system to TIRA to ensure everything works on your side and then switch to your system. (Alternatively, you can also add your code to this repository via a pull request and we conduct the steps for doing the code submissions, as long as there is enough time to the deadline we should always be able to help with this.)



<details>
<summary>Step 1: the structure of a system</summary>

The Naive AutoJudge system has the following files in its directory:

```
├── .devcontainer.json
├── Dockerfile
├── naive-baseline.py
├── README.md
└── requirements.txt
```

The `.devcontainer.json` and the `Dockerfile` configure the dev-container. Many IDEs (e.g., VS-Code, but also [Github Codespaces in your browser](https://github.com/features/codespaces)) can directly boot into the dev-container, so that they also help to simplify the development as one can develop directly in an environment where everything is installed.  The `requirements.txt` file describes the requirements and the `naive-baseline.py` provides the actual code (a simple judge that provides random/naive judgments). The judge has to process RAG responses as inputs and produce a leaderboard in a format congruent to `trec_eval -q` outputs. Please see the [minimal spot check dataset](https://github.com/trec-auto-judge/auto-judge-code/tree/main/trec25/datasets/spot-check-dataset#minimal-spot-check-dataset) for a detailed description of inputs and outputs to your system.

</details>

<details>
<summary>Step 2: Authentication and Login</summary>

We assume you have created an account at TIRA.io and have registered a team to TREC AutoJudge following the prerequisite above.

The preferred way to upload a submission to TIRA is via the command line interface, as this already can check that everything is in the correct format on your side.

Please install the TIRA cli via:

```
pip3 install --upgrade tira
```

Next, you need an authentication token:

- Navigate to the TREC AutoJudge task in TIRA [https://www.tira.io/task-overview/trec-auto-judge](https://www.tira.io/task-overview/trec-auto-judge)
- Click on "submit" => "Code Submissions" => "I want to submit from my local machine". The UI shows your authentication token (alternatively, you can upload via Github Actions, the UI guides you through this and we also offer help, please do not hesitate to reach out, we plan to incorporate corresponding github actions to this repository):

<img width="1839" height="929" alt="Screenshot_20251210_215021" src="https://github.com/user-attachments/assets/e2ab77e7-4818-4d55-abb7-c374b62db945" />


Assuming your authentication token is AUTH-TOKEN, please authenticate via:

```
tira-cli login --token AUTH-TOKEN
```

Lastly, to verify that everything is correct, please run `tira-cli verify-installation`. Outputs might look like:

<img width="821" height="180" alt="Screenshot_20251210_095410" src="https://github.com/user-attachments/assets/51160132-eb19-4da3-8892-8a53adb41c71" />

</details>

<details>
<summary>Step 3: Test your system on the spot-check Dataset</summary>


Assuming you are in the [../trec25/judges](../trec25/judges) directory we use the `code-submission` command of TIRA against the `spot-check-dataset-20251202-training` dataset to ensure that everything is valid via:

```
tira-cli code-submission \
    --path naive \
    --task trec-auto-judge \
    --dry-run \
    --dataset spot-check-dataset-20251202-training \
    --command '/naive-baseline.py --rag-responses ${inputDataset} --output ${outputDir}/trec-leaderboard.txt'
```

In this command,
- `--path naive` indicates that the code that is to be submitted is in the [corresponding directory](../trec25/judges/naive)
- `--task trec-auto-judge` indicates hat we want to submit to the TREC AutoJudge task
- `--dry-run` indicates that we want to test that everything works without actually uploading the submission
- `--command` indicates the to-be-executed command that is to be executed. Every submission is intended to read its inputs from the directory to which the `inputDataset` variable points to and write its results to the directory specified by the `outputDir` variable.
- `--dataset` indicates that we want to run the code on the spot-check dataset

The output should look like:

<img width="1227" height="154" alt="Screenshot_20251210_215910" src="https://github.com/user-attachments/assets/4aaef384-8ed8-412f-a714-2117eefa19c8" />

</details>

<details>
<summary>Step 4: Upload Your System to TIRA</summary>

Please re-execute the command above but remove the `--dry-run` flag, this will additionaly upload the system to TIRA. The output should look like:

<img width="1230" height="336" alt="Screenshot_20251210_220112" src="https://github.com/user-attachments/assets/0a53a83c-954d-46cf-8c92-60e61907edbf" />

</details

.

<details>
<summary>Step 5: Run Your System in TIRA</summary>

Please navigate to the TREC AutoJudge task in TIRA [https://www.tira.io/task-overview/trec-auto-judge](https://www.tira.io/task-overview/trec-auto-judge) and click on "submit" and "Code Submissions". Then select your submission. You can select on datasets using which resources your approach should be executed within TIRA. This looks like:

<img width="1851" height="733" alt="Screenshot_20251210_220656" src="https://github.com/user-attachments/assets/e33e270a-bed9-4b48-9ac7-338d6e6fa4b1" />

We aim to run every submitted system on all datasets.

</details>
