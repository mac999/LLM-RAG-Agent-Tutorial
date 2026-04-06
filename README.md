# LLM, RAG and AI agent development tutorial
This repository contains [Syllabus](https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/1-1.prepare/syllabus-llm-rag-agent.docx) for LLM(large language model), RAG(retrieval augmented generation), AI Agent and MCP(Model Context Protocol) class focusing on creative AI agent development, modeling, and computing as the viewpoint of usecase. The colab code, source, presentation and reference with AI tools like below can be used for developing LLM, RAG and AI Agent. If you want to know the LLM, RAG and AI Agent with MCP subjects and materials, refer to the below link.
- [Syllabus](https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/1-1.prepare/syllabus-llm-rag-agent.docx)
If you need AI deep learning foundation, refer the below link.
- [AI foundation and tutorial with code](https://github.com/mac999/AI_foundation_tutorial): This repository contains materials for an AI Foundation seminar, covering fundamental concepts of AI, Machine Learning, Deep Learning, Natural Language Processing, Transformers, and Large Language Models (LLMs), including agent-based approaches and related services. It is designed to provide hands-on experience, primarily utilizing Jupyter Notebooks.
- [Computer Vision with Deep Learning](https://github.com/mac999/computer_vision_deeplearning): This course goes beyond simply running pre-existing code. The core objective is to foster a deep understanding by having you implement the internal mechanisms of key deep learning models—such as CNN, ResNet, R-CNN, and YOLO—from the ground up. With hands-on exercises in PyTorch and Keras, you will gain proficiency in translating complex theories into functional code.
- [Multimodal AI Tutorial](https://github.com/mac999/multimodal_ai_tutorial): This repository provides a comprehensive, hands-on tutorial for learning multimodal artificial intelligence through progressive implementation of foundational and advanced AI architectures. The curriculum is designed to take learners from basic machine learning concepts through cutting-edge multimodal models including Vision Transformers, CLIP and Vision-Language Models.

In reference, the subjects are like below. 
- [Transformer encoder and decoder tutoring](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/1-2.transformer). [Transformer scratch source code](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/2-3.deep-tranformer)
- Token and Embedding for NLP (natural language process) using [huggingface](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/2-1.huggingface)
- [Multi-modal](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/3-3.multi-modal) like CLIP, LLaVA
- Stable Diffusion and prompt engineering using [text to image, video, audio, sound, document (word, presentation) and code (app, game) tools](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/2-2.genai-prompt) 
- LLM. [Train and Finetune](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/3-2.finetuning) for model like gemma, llama
- [Vector RAG](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/4-2.llm-rag) and [Langchain](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/4-1.langchain). [Vector DB](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/4-3.db) like [FAISS](https://engineering.fb.com/2017/03/29/data-infrastructure/faiss-a-library-for-efficient-similarity-search/), Chroma DB
- [Graph RAG](https://github.com/mac999/infra_ai_agent_tutorials/tree/main/08_AI_Agent/5_infra_graph_rag) using [FalkorDB](https://github.com/FalkorDB/FalkorDB), Neo4j
- [Chatbot](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/4-3.db) with [Ollama](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/4-5.ollama). Gradio and Streamlit for UX
- [AI Agent](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/5-1.agent) and [MCP](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/5-2.llm-mcp-app)
- LLM Internal Code Analysis like [Deepseek](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/2-4.deep-seek), Manus</br>
- [Vibe coding](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/5-3.vibe-coding) using Copilot, GPT etc
- [Project and documentation](https://github.com/mac999/LLM-RAG-Agent-Tutorial/tree/main/6.project)

<img src="https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/5-1.agent/streamlit-chatbot.PNG" height="230"/><img src="https://github.com/mac999/BIM_LLM_code_agent/raw/main/doc/img1.gif" height="230"/><img src="https://github.com/mac999/geo-llm-agent-dashboard/raw/main/doc/geo_llm_demo.gif" height="230"/>

# Preparation for LLM, RAG and AI Agent study
LLM uses deep learning model architecture like transformer which uses numerical analysis, linear algebra, so it's better to understand the below subjects before starting it.
- [linear algebra](https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/1-1.prepare/linear-algebra.pdf). Dataset like [Matrix, tensor handling and visualization cheat sheet](https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/1-1.prepare/data-visualization(numpy%2C%20pandas%2C%20pytorch%2C%20tensor).pdf) 
- [newton mathod for equation solution](https://www.intmath.com/applications-differentiation/newtons-method-interactive.php). In addition, [differential Calculus](https://www.geogebra.org/t/differential-calculus) includes newton method.
<img src="https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/1-1.prepare/numerical-analysis-newton.PNG" alt="newton method" width="400"/>

- [numerical analysis (youtube)](https://www.youtube.com/watch?v=bfoxcZYoGfQ)
- [numerical analysis reference](https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/1-1.prepare/numerical-analysis.pdf)

# Installation for LLM, RAG and AI agent development
First, clone this repository. 
```bash
git clone https://github.com/mac999/LLM-RAG-Agent-Tutorial.git
```
Second, check [syllabus](https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/1-1.prepare/syllabus-llm-rag-agent.docx) and [lesson plan](https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/1-1.prepare/lesson-plan.docx) to understand LLM, RAG and AI agent development courses.</br>
<img src="https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/1-1.prepare/lesson-plan.PNG" height="230" /><img src="https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/1-2.transformer/transformer-architecture.PNG" height="230" /><img src="https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/1-1.prepare/lesson-reference.PNG" height="230" />
</br>
Before running the example code, ensure you have Colab Pro, Python 3.10 or higher installed. Some tool or library use NVIDIA GPU, so if you want to use it, prepare notebook computer with NVIDIA GPU(recommend 8GB. minimum 4GB)
Follow the instructions below to set up your environment:
- [LLM development environment document(word file)](https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/1-1.prepare/dev-env.docx) [(English version)](https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/1-1.prepare/dev-env(english).pdf) 

In refernce, this lesson will use the below 
- **Colab Pro**: To run jupyter notebook, You need to create Colab account. For finetuning LLM, Colab Pro will be needed.
- **OpenAI**: To use ChatGPT LLM model and API, You need to create ChatGPT account and OpenAI API key
- **Huggingface**: For uisng LLM, Stable Diffusion-based model, You need to sign up Huggingface. In example, [Single Image-to-3D model](https://huggingface.co/spaces/stabilityai/stable-point-aware-3d)
- **Ollama**: For using AI tools in open source LLM projects. You need to install NVIDIA cuda for run it.
- **Generative AI service** like Sora, Runway, Dream machine, Kling AI, Canva etc: For prompt engineering practice. If you want to use it temporarily and don't share your private, use temp email like [Temp Mail](https://temp-mail.org/en/).
- **LangChain** with Vector DB: For RAG, langchain, chroma db etc will be used.

<img src="https://github.com/mac999/LLM-RAG-Agent-Tutorial/blob/main/4-2.llm-rag/rag-agent-chain.PNG" height="150" />

## NVIDIA Drivers (for Ollama. optional)
For GPU-accelerated tasks, you need to install the correct NVIDIA drivers for your GPU.

- **Download NVIDIA Drivers**: [NVIDIA Driver Downloads](https://www.nvidia.com/Download/index.aspx)
- **Steps**:
  1. Identify your GPU model using the NVIDIA Control Panel or the `nvidia-smi` command in the terminal.
  2. Download the latest driver for your GPU model.
  3. Install the driver and reboot your system.

To confirm installation:
```bash
nvidia-smi
```

## CUDA Toolkit (for NVIDIA. optional)
CUDA is required for running GPU-accelerated operations.

- **Download CUDA Toolkit**: [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads)
- During installation:
  - Match the CUDA version with your NVIDIA driver and GPU model. Refer to the compatibility chart on the download page.
  - Install the CUDA Toolkit with default options.
  - Add the CUDA binary paths to your environment variables.

## Python
Ensure that Python (safe version 3.10 or 3.12) is installed on your system. About macbook, please refer to [how to install python on mac](https://www.youtube.com/watch?v=u4xUUBTER4I).

- **Download Python**: [python.org](https://www.python.org/)
- During installation:
  - Check the box for **"Add Python to PATH"**.
  - Install Python along with **pip**.

To confirm installation in terminal(DOS command in windows. Shell terminal in linux):
```bash
python --version
```

## Anaconda
Ensure that Anaconda (version 24.0 or later) is installed on your system.

- **Download Anaconda**: [Anaconda](https://docs.anaconda.com/anaconda/install/)

### Huggingface, OpenAI (Optinnal) Account 
Make Accounts for OpenAI, Huggingface
- Sign up [Huggingface](https://huggingface.co/) and make [API token](https://huggingface.co/settings/tokens)to develop Open source LLM-base application
- Sign up [OpenAI API](https://platform.openai.com/) to develop ChatGPT-based application (*Note: don't check auto-subscription option)

## PyTorch library 

- If AI-related models or tools will be used (such as LLM model fine-tuning with Ollama), install stable [PyTorch](https://pytorch.org/get-started/locally/)(11.8 version) and additional packages:
   ```bash
   pip install openai
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

## Install Python Packages
Run the following command to install the required libraries:
```bash
pip install pandas numpy
pip install ollama openai transformers huggingface_hub langchain
```

## Install Ollama 
For examples that utilize Ollama, follow the installation instructions from the [Ollama website](https://www.ollama.com/).

## Install sublime and vscode (Recommend)
Install [Sublime](https://www.sublimetext.com/) for editing source code</br>
Install [vscode](https://code.visualstudio.com/download) for debuging code. Please refer to how to [install vscode](https://www.youtube.com/watch?v=vesxpfOAOCw).</br>

---

# **System Environment Checks**

After completing the installations, verify that the environment is set up correctly:

1. **Check Python Version**:
   ```bash
   python --version
   ```

2. **Verify NVIDIA Drivers**:
   ```bash
   nvidia-smi
   ```

3. **Confirm CUDA Version**:
   ```bash
   nvcc --version
   ```

4. **Test Python Libraries**:
   Create a test script and import the installed libraries:
   ```python
   import pandas as pd
   import numpy as np
   import torch
   print("Libraries are installed successfully!")
   print(f"torch version = {torch.__version__}")
   ```

# For media art
If you're interested in media art, refer to the below link. The repository includes examples to experiment with generative media art.</br>
- [Gen AI for Media Art](https://github.com/mac999/llm-media-art-demo)
<img src="https://github.com/mac999/blender-llm-addin/raw/main/doc/blender_gpt.gif" height="300"/>

For Blender using AI-Assisted Modeling, 
- **Download Blender**: [blender.org](https://www.blender.org/download/)
- After installation:
  - Enable the **Python Console** within Blender to run scripts directly.
  - Ensure Blender uses the same Python environment where required libraries are installed.

If you're interested in text to 3D model, you can find Text-to-3D model tool the below link. 
- [Text-to-3D model code](https://github.com/mac999/blender-llm-addin): Using Open-Source Models with Blender for AI-Assisted 3D Modeling: Comparative Study with OpenAI GPT

If you're interested in Arduino based generative AI, refer to the below. 
- [Chat with ChatGPT through Arduino IoT Cloud](https://projecthub.arduino.cc/dbeamonte_arduino/chat-with-chatgpt-through-arduino-iot-cloud-6b4ef0)
- [ChatGPT Arduino library](https://github.com/programming-electronics-academy/chatGPT-Arduino-library/tree/main)
- [ChatGPT_Client_For_Arduino](https://github.com/0015/ChatGPT_Client_For_Arduino)
- [ChatGPT for Arduino](https://blog.wokwi.com/learn-arduino-using-ai-chatgpt/)
- [Using ChatGPT to Write Code for Arduino and ESP32](https://dronebotworkshop.com/chatgpt/)

# Reference
- Lee Boonstra, Google, 2025, Prompt Engineering
- Julia Wiesinger, Patrick Marlow and Vladimir Vuskovic, Google, 2024, Agents
- OpenAI, A practical guide to building agents
- Keith Chugg, USC, 2020, Brief Introduction to Natural Language Processing
- Mustafa Degerli, Bilkent University, 2014, Software Processes and Software Development Process Models
- [NVIDIA cuda programming, open source and AI](https://www.slideshare.net/slideshow/nvidia-cuda-programming-open-source-and-ai/270372806?from_search=6)

# Collaboration & Research

This repository is part of my ongoing work on AI, LLMs, and Transformer-based architectures.
I am open to research collaboration, academic exchange, and joint projects with universities, public institutions, company and research labs.

For collaboration inquiries, please feel free to reach out:
[laputa99999@gmail.com] | [[LinkedIn or Personal Website](https://www.linkedin.com/feed/)]

# License
This repository is licensed under the MIT License. You are free to use, modify, and distribute the code for personal or commercial projects.

# Author
Ph.D, Taewook Kang(laputa99999@gmail.com)
