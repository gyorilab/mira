# GPU Acceleration Setup for PDF Processing

This module uses [MinerU](https://github.com/opendatalab/MinerU) for PDF equation extraction. For optimal performance, GPU acceleration is strongly recommended.

## Prerequisites

- **NVIDIA GPU**: 8GB+ VRAM for `vlm-vllm-engine` backend (otherwise `pipeline` backend will be used)
- **CUDA**: Version 11.8, 12.6, or 12.8 ([Documentation](https://docs.vllm.ai/en/stable/getting_started/installation/gpu.html#pre-built-wheels))

---

## Installation

### 1. Install CUDA (if not already installed)

#### Check if CUDA is already installed
```bash
nvidia-smi
nvcc --version
```

#### Install CUDA Toolkit

**Ubuntu/Debian:**
```bash
# Update package list
sudo apt update

# Install CUDA toolkit (replace 12-6 with your desired version: 11-8, 12-6, or 12-8)
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install cuda-toolkit-12-6
```

**Other systems:**  
Download the installer from [NVIDIA CUDA Downloads](https://developer.nvidia.com/cuda-downloads)

#### Verify installation
```bash
nvcc --version
nvidia-smi
```

---

### 2. Install MinerU

Install with VLM support:
```bash
pip install mineru[all]>=2.0.0
```

Or install from the root project directory (same directory as `setup.cfg`):
```bash
pip install .[ode]
```

---

### 3. Install vLLM

For automatic CUDA detection using `uv`:
```bash
# Install uv (if needed)
pip install uv

# Install vLLM with automatic CUDA backend detection
uv pip install vllm --torch-backend=auto
```

> **📚 More details:** See the [official vLLM GPU installation guide](https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html)

---

### 4. Configure MinerU

Create configuration file at `~/mineru.json`:
```bash
cat > ~/mineru.json << 'EOF'
{
    "models-dir": {
        "pipeline": "$HOME/.cache/mineru/pipeline",
        "vlm": "$HOME/.cache/mineru/vlm"
    },
    "device-mode": "cuda"
}
EOF
```

**Configuration options:**
- `models-dir` — Model weights cache location (created automatically on first run)
- `device-mode` — Hardware acceleration:
  - `"cuda"` — NVIDIA GPU (recommended)
  - `"cpu"` — CPU only (slower)
  - `"mps"` — Apple Silicon (M1/M2/M3)

---

### 5. Set CUDA Environment Variables

Add to `~/.bashrc`:
```bash
# Replace the CUDA path with the actual path to CUDA installation that includes the
# version number
export CUDA_HOME=/usr/local/cuda
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}
export PATH=/usr/local/cuda/bin:${PATH}
```

Reload configuration:
```bash
source ~/.bashrc
```

---

### 6. Verify GPU Setup
```bash
# Check CUDA accessibility
nvidia-smi

# Verify PyTorch CUDA support
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

---

## Backend Selection

The system automatically selects the optimal backend based on available VRAM:

| VRAM     | Backend | Performance |
|----------|---------|-------------|
| **8GB+** | `vlm-vllm-engine` | Fastest, highest accuracy |
| **<8GB** | `pipeline` with CUDA | GPU-accelerated |
| **GPU**  | `pipeline` with CPU | Slower |