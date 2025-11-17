# GPU Acceleration Setup for PDF Processing

This module uses [MinerU](https://github.com/opendatalab/MinerU) for PDF equation extraction. For optimal performance, GPU acceleration is strongly recommended.

## Prerequisites

- **NVIDIA GPU**: 8GB+ VRAM for `vlm-vllm-engine` backend (otherwise `pipeline` backend will be used)
- **CUDA**: Version 11.8, 12.6, or 12.8 ([Documentation](https://docs.vllm.ai/en/stable/getting_started/installation/gpu.html#pre-built-wheels))
- Compatible with distributions only released in 2019 or later if using Linux
- Requires macOs >= 15.1 to work with PyTorch's `Conv1D` class per [comment](https://github.com/pytorch/pytorch/issues/144445#issuecomment-2583452641) 

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
These commands show your CUDA driver version:
```bash
nvcc --version
nvidia-smi
```

---

### 2. Set CUDA Environment Variables

Add to `~/.bashrc` (replace version number with your installed CUDA version):
```bash
export CUDA_HOME=/usr/local/cuda-12.6
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:${LD_LIBRARY_PATH}
export PATH=/usr/local/cuda-12.6/bin:${PATH}
```

Reload configuration:
```bash
source ~/.bashrc
```

---

### 3. Install PyTorch with matching CUDA Version

**IMPORTANT**: Install PyTorch **first** with the correct CUDA version to avoid version conflicts.
PyTorch has a starter installation guide [here](https://pytorch.org/get-started/locally/?__hstc=76629258.724dacd2270c1ae797f3a62ecd655d50.1746547368336.1746547368336.1746547368336.1&__hssc=76629258.9.1746547368336&__hsfp=2230748894).

Check your CUDA version from step 1, then install the matching packages.
If you'd like to install an older version PyTorch with matching CUDA version, check 
[here](https://pytorch.org/get-started/previous-versions/).

**Verify PyTorch can see CUDA:**
```bash
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA available:', torch.cuda.is_available())"
```
You should see `CUDA available: True`. If not, restart your terminal and/or system
and try again.

---

### 4. Install MinerU

Install with VLM support:
```bash
# Versions 2 and above using the mineru config file discussed further below
pip install mineru[all]>=2.0.0
```

Or install from the root project directory (same directory as `setup.cfg`):
```bash
pip install -e .[ode]
```

#### ⚠️ Important: Fresh Installation Best Practices

If you're doing a fresh installation of this project, **install the `ode` extras separately** from other optional dependencies:
```bash
# First install base package with other extras (if needed)
pip install -e .[web,dkg-client]

# Then install ode extras separately
pip install -e .[ode]
```

**Do NOT do this on fresh installs:**
```bash
pip install -e .[web,ode,dkg-client]  # ❌ Will cause issues with installation
```


### 5. Install vLLM

**Using uv (recommended):**
```bash
# Install uv (if needed)
pip install uv

# Install vLLM matching your CUDA version (e.g., cu126 for CUDA 12.6)
uv pip install vllm --torch-backend=cu126
```

**Alternative - automatic detection (experimental):**
```bash
uv pip install vllm --torch-backend=auto
```

If the two installation commands above install incompatible
torch packages with your CUDA driver version, check the 
[PyTorch documentation](https://pytorch.org/get-started/previous-versions/) 
to find the correct torch package versions for your CUDA version.

> **📚 More details:** See the [official vLLM GPU installation guide](https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html#pre-built-wheels)

---

### 6. Configure MinerU

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
    - **Note**: The initial run will take time to download models
  - `"cpu"` — CPU only (slower)
  - `"mps"` — Apple Silicon (M1/M2/M3)

---

### 7. Verify GPU Setup

We check to see if PyTorch can connect to CUDA again as installing vllm can reinstall
incompatible torch packages with your CUDA driver version. 
```bash
# Check CUDA accessibility
nvidia-smi

# Verify PyTorch CUDA support (should show True)
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"

```

If CUDA is not showing as available after all steps, try restarting your terminal or system. After CUDA
is linked to torch, if a process that is using the GPU suddenly crashes or is killed by the user, CUDA may not be available. 
The easiest way to fix this is to restart your system. 

---

## Backend Selection

The system automatically selects the optimal backend based on available VRAM:

| VRAM | Backend | Performance |
|------|---------|-------------|
| **8GB+** | `vlm-vllm-engine` | Fastest, highest accuracy |
| **<8GB** | `pipeline` with CUDA | GPU-accelerated |
| **No GPU** | `pipeline` with CPU | Slower |