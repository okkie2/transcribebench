Below is a **complete updated README** incorporating:

* clearer onboarding
* the privacy motivation
* the relationship with **AutoTranscribe2**
* Mozilla Common Voice credit
* dataset reproducibility guidance
* improved structure

---

# TranscribeBench

**TranscribeBench** is a benchmarking tool for speech-to-text engines.

> This repo includes helper pages in `docs/` that can be used as GitHub Wiki content.

It runs multiple transcription engines on the same audio dataset and compares their output against ground-truth transcripts using objective metrics such as **Word Error Rate (WER)** and **Character Error Rate (CER)**.

The goal is simple: **determine which engine and model performs best for your language, dataset, and hardware.**

---

# Why this project exists

AI transcription has become widely used. Tools such as **Microsoft Teams** can automatically transcribe meetings, making conversations searchable and easier to review.

However, these systems typically rely on **cloud-based processing**, which means that recordings and transcripts are sent to external services. For many organisations and individuals this raises significant **privacy and data sovereignty concerns**.

Because of this, a growing number of **local transcription engines** are emerging that run entirely on personal hardware.

This concern is the reason I started building:

**[AutoTranscribe2](https://github.com/okkie2/AutoTranscribe2)**

AutoTranscribe2 aims to become a **fully local alternative to meeting transcription tools such as Microsoft Teams**, where audio never leaves the user's machine. The project is still in an early stage and not yet integrated as a plugin or meeting assistant, but it provides the foundation for a practical local transcription pipeline.

To select the best transcription engines for such a system, I needed a reliable way to compare them.
**TranscribeBench was created to solve that problem.**

Although it originated as a supporting tool for AutoTranscribe2, **TranscribeBench is designed to stand on its own as a general benchmarking framework for speech-to-text systems.**

---

# What TranscribeBench does

TranscribeBench runs a repeatable benchmark pipeline:

```
Audio dataset
      │
      ▼
Transcription engines
      │
      ▼
Generated transcripts
      │
      ▼
Evaluation against reference transcripts
      │
      ▼
Benchmark report (WER / CER / timing)
```

This allows transcription engines to be compared under **identical conditions**.

---

# Example output

Example comparison of two engines on the same dataset:

```
Dataset: benchmark-dataset-nl-v1

Engine              WER     CER     Speed
-------------------------------------------
mlx-whisper         7.8%    2.3%    1.4x realtime
whisper-cpp         9.5%    3.1%    0.9x realtime
```

The benchmark ensures that:

* each engine processes the **same audio**
* results are compared against the **same reference transcripts**
* metrics are calculated in a **consistent and reproducible way**

---

# Core concepts

TranscribeBench is built around three simple concepts.

## Dataset

A dataset contains:

* audio recordings
* reference transcripts

Example structure:

```
dataset/
  audio/
    sample1.wav
    sample2.wav

  transcripts/
    sample1.txt
    sample2.txt
```

The transcripts represent the **ground truth** used to measure transcription accuracy.

---

## Engine

An **engine** is a transcription system consisting of:

* a runtime
* a model

Examples include:

* MLX Whisper
* Faster-Whisper
* whisper.cpp
* OpenAI Whisper

Each engine converts audio into text, allowing results to be compared.

---

## Benchmark

A benchmark run:

1. loads a dataset
2. runs one or more transcription engines
3. generates transcripts
4. compares them with reference transcripts
5. calculates accuracy metrics

---

# Metrics

TranscribeBench currently focuses on standard speech recognition metrics.

### Word Error Rate (WER)

Measures the percentage of words that differ between the generated transcription and the reference transcript.

Lower values indicate better transcription accuracy.

### Character Error Rate (CER)

Measures character-level differences.

This is particularly useful for languages where word segmentation may be ambiguous.

---

# Dataset source

Example datasets used in this project are derived from **Mozilla Common Voice**.

Mozilla Common Voice is an open speech dataset designed to help build open and accessible speech recognition systems. It contains thousands of hours of recorded speech from volunteers worldwide.

Project page:
[https://commonvoice.mozilla.org](https://commonvoice.mozilla.org)

Repository:
[https://github.com/common-voice](https://github.com/common-voice)

Common Voice provides:

* high-quality **ground-truth transcripts**
* recordings in **many languages**
* an **open licence suitable for benchmarking**

TranscribeBench typically uses **small curated subsets** of the dataset to keep benchmark runs lightweight and reproducible.

---

# Dataset reproducibility

Benchmarks are only meaningful if they use the **same audio samples and transcripts**.

TranscribeBench therefore defines a **fixed dataset subset** for each benchmark run. Each dataset specification includes:

* dataset source
* dataset version
* language
* exact list of audio files used

Example dataset definition:

```
dataset:
  source: Mozilla Common Voice
  version: 17.0
  language: nl
  samples:
    - common_voice_nl_18765432.wav
    - common_voice_nl_18765433.wav
    - common_voice_nl_18765434.wav
```

This ensures that benchmark results are **fully reproducible** across machines and engines.

Benchmark results should always reference the dataset identifier used, for example:

```
Dataset: benchmark-dataset-nl-v1
```

---

# Project relationship

TranscribeBench and AutoTranscribe2 serve different roles:

| Project         | Purpose                                            |
| --------------- | -------------------------------------------------- |
| AutoTranscribe2 | Local transcription pipeline                       |
| TranscribeBench | Evaluation and comparison of transcription engines |

TranscribeBench helps determine **which engine AutoTranscribe2 should use**.

---

# Project status

This project is currently **experimental**.

Planned improvements include:

* support for additional transcription engines
* automated dataset downloading
* improved benchmarking metrics
* reproducible benchmark reports
* support for multiple languages

---

# Contributing

Contributions are welcome.

Areas where help would be particularly valuable:

* new engine integrations
* dataset adapters
* improved evaluation metrics
* benchmark visualisation and reporting

---

# License

See the repository licence for details.

