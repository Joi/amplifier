# Quick Start Guide

Get the demo running in 5 minutes!

## Option 1: vLLM Only (Fastest to Test)

### 1. Install vLLM

```bash
pip install vllm openai pydantic
```

### 2. Start vLLM Server

In a separate terminal:

```bash
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --guided-decoding-backend outlines
```

**Note**: First run will download the model (~8GB). This may take 5-10 minutes.

### 3. Run the Demo

```bash
cd amplifier/prob_tools/demos/agent_communication
python vllm_example.py
```

**Expected output**: Structured agent messages generated in ~100-500ms each.

## Option 2: LLaMPPL Only (Conceptual Demo)

### 1. Install Dependencies

```bash
pip install pydantic transformers torch
```

### 2. Run the Demo

```bash
python llamppl_example.py
```

**Expected output**: Conceptual demonstration of constraint-guided generation.

**Note**: Full LLaMPPL demo requires additional setup. See main README for details.

## Option 3: Side-by-Side Comparison

Requires both vLLM server running AND LLaMPPL installed.

```bash
python comparison.py
```

## Testing Without Full Setup

Just want to see the schemas?

```bash
python schemas.py
```

This will show example messages and validate the Pydantic models work correctly.

## Troubleshooting

### vLLM server won't start

**Error**: `CUDA out of memory`

**Solution**: The Llama-3.1-8B model needs ~16GB VRAM. Try a smaller model:

```bash
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3.2-3B-Instruct
```

### vLLM example fails with connection error

**Check**: Is the vLLM server running?

```bash
curl http://localhost:8000/health
```

Should return: `{"status": "ok"}`

### LLaMPPL import fails

LLaMPPL is a research library and may require manual installation from source:

```bash
git clone https://github.com/probcomp/llamppl.git
cd llamppl
pip install -e .
```

## Next Steps

Once you have the basic demo running:

1. **Modify schemas** in `schemas.py` to test your own message types
2. **Change prompts** in the examples to see different behaviors
3. **Run comparison.py** to benchmark both approaches
4. **Read the strategic vision** in `../STRATEGIC_VISION.md`

## Quick Command Reference

```bash
# Start vLLM server
python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-3.1-8B-Instruct

# Run vLLM demo
python vllm_example.py

# Run LLaMPPL demo
python llamppl_example.py

# Run comparison
python comparison.py

# Test schemas
python schemas.py
```

## Getting Help

- vLLM docs: https://docs.vllm.ai/
- LLaMPPL paper: https://arxiv.org/abs/2306.03081
- Strategic vision: `../STRATEGIC_VISION.md`
- System overview: `../SYSTEM_OVERVIEW.md`
