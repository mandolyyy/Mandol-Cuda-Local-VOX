# Mandol-Cuda-Local-VOX · Local AI Voice Studio
A high-performance, local AI Voice Studio optimized for NVIDIA CUDA hardware. This tool allows for instant voice cloning and descriptive voice design without cloud fees, subscriptions, or privacy concerns. Developed as a specialized module for the MyTRACE Network ecosystem.

# Overview
Mandol-Cuda-Local-VOX is a professional-grade interface for generating cinematic narration. Tired of robotic, pay-walled online generators? This engine runs entirely on your local GPU, giving you full control over the "vibe," pace, and tone of your project's voiceovers.

# Key Features:
-Zero-Shot Voice Cloning: Drop a 10-second .wav clip to mimic any voice style instantly.
-Descriptive Voice Design: Influence the output using natural language prompts (e.g., "Deep, glacially slow, cinematic bass").
-RTX Optimized: Leverages CUDA for fast, high-fidelity audio generation.
-Studio UI: A modern, dark-themed interface designed for efficient production workflows.

# Installation (A-to-Z Guide)
Follow these steps exactly to ensure the CUDA environment is configured correctly.

Prerequisites:
-Python 3.11.9 (Mandatory for library compatibility).
-NVIDIA GPU with 8GB+ VRAM (Recommended for smooth performance).

1. Open cmd in the project folder, initialize the environment: py -3.11 -m venv venv
2. Activate the environment: venv\Scripts\activate
3. Install all the dependencies: pip install -r requirements.txt
4. Launch the studio: python gui.py



# License & Credits
Software License: MIT License.


Engine: This project utilizes the VoxCPM model developed by OpenBMB.
