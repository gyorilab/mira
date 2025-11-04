# GPU Acceleration Setup for PDF Processing

This module uses [MinerU](https://github.com/opendatalab/MinerU) for PDF equation extraction. For optimal performance, GPU acceleration is strongly recommended.

## Prerequisites

- NVIDIA GPU (8GB+ for `vlm-vllm-engine` backend)
    - Otherwise, the `pipeline` backend will be used
- CUDA 12.1+ drivers installed

## Installation

### 1. Install MinerU with VLM support
```bash
pip install mineru[all]>=2.0.0
```

or 

```bash
pip install .[ode]
```

in the same directory as `setup.cfg`
### 2. Install vLLM with automatic CUDA detection

For NVIDIA CUDA GPUs, we recommend using `uv` to automatically detect and install the correct PyTorch version:
```bash
# Install uv if you don't have it
pip install uv

# Install vLLM with automatic CUDA backend detection
uv pip install vllm --torch-backend=auto
```

For detailed vLLM installation instructions, see the [official vLLM GPU installation guide](https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html#create-a-new-python-environment).

### 3. Configure MinerU

Create a configuration file at `~/mineru.json`. 
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

**Configuration fields:**
- `models-dir`: Where model weights are cached (will be created automatically on first run)
- `device-mode`: Hardware acceleration mode
  - `"cuda"` - NVIDIA GPU (recommended)
  - `"cpu"` - CPU only (slower)
  - `"mps"` - Apple Silicon (Mac M1/M2/M3)

### 4. Set CUDA environment variables

Add to your `~/.bashrc`:
```bash
export CUDA_HOME=/usr/local/cuda
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}
export PATH=/usr/local/cuda/bin:${PATH}
```

Then reload:
```bash
source ~/.bashrc
```

### 5. Verify GPU setup
```bash
# Check CUDA is accessible
nvidia-smi

# Verify PyTorch can use CUDA
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

## Backend Selection

The code automatically selects the optimal backend based on available VRAM:

- **8GB+ VRAM**: Uses `vlm-vllm-engine` (faster, higher accuracy)
- **4-8GB VRAM**: Uses `pipeline` with CUDA acceleration
- **No GPU**: Falls back to `pipeline` with CPU (slower)
