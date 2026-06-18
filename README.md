# FFH-Dataset-and-Code

This repository provides a representative dataset subset, evaluation scripts, and core algorithm implementation associated with the following manuscript:

**A Data-Driven Real-Time Fall-from-Height Detection Method for On-Device Worker Safety Wearables**

## Overview

The proposed method is a lightweight on-device Fall-from-Height (FFH) detection approach designed for wearable worker safety systems. The method combines acceleration- and pressure-based features within a unified score-based framework to achieve real-time FFH detection on resource-constrained embedded devices.

## Repository Structure

```text
dataset/

evaluation/
├── evaluate.py
└── ...

algorithm/
├── peak_detection.c
├── feature_extraction.c
├── score_calculation.c
└── ...
```

## Dataset

The repository contains a representative subset of the dataset used in the study, including:

- Fall-from-Height (FFH) events
- Running activities
- Fast sitting activities
- Stair ascent/descent
- Elevator usage
- Escalator usage

These samples are provided to support reproducibility and facilitate future research on wearable FFH detection.

## Evaluation Scripts

The evaluation scripts reproduce the performance metrics reported in the manuscript, including:

- Accuracy
- Precision
- Recall
- F1-score

## Core Algorithm Implementation

The original wearable firmware was implemented on the Nordic nRF5340 platform using Zephyr RTOS.

To improve clarity and reproducibility, this repository provides only the algorithmic components directly related to FFH detection, including:

- Peak detection
- Feature extraction
- Score calculation
- FFH decision logic

Platform-specific components such as sensor drivers, BLE communication, storage management, and RTOS task scheduling are not included.

## Citation

If you use this dataset or code in your research, please cite the corresponding publication.

```bibtex
@article{Kang2026FFH,
  title={A Data-Driven Real-Time Fall-from-Height Detection Method for On-Device Worker Safety Wearables},
  author={Kang, Sanghyeok and others},
  journal={BDCC},
  year={2026}
}
```

## License

This repository is released under the MIT License.
