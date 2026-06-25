# gpu_engine.py
import torch
import os

def get_gpu_info():
    info = {
        "available":    False,
        "name":         "None",
        "vram_total":   0,
        "vram_free":    0,
        "cuda_version": "None",
    }

    if torch.cuda.is_available():
        info["available"]    = True
        info["name"]         = torch.cuda.get_device_name(0)
        info["cuda_version"] = torch.version.cuda
        props = torch.cuda.get_device_properties(0)
        info["vram_total"] = props.total_memory // (1024 ** 2)
        info["vram_free"]  = (
            props.total_memory - torch.cuda.memory_allocated(0)
        ) // (1024 ** 2)

    return info

def print_gpu_status():
    info = get_gpu_info()
    print("=" * 45)
    print("  GPU STATUS")
    print("=" * 45)
    if info["available"]:
        print(f"  GPU  : {info['name']}")
        print(f"  CUDA : {info['cuda_version']}")
        print(f"  VRAM : {info['vram_total']} MB total")
        print(f"  Free : {info['vram_free']} MB free")
    else:
        print("  No CUDA GPU — running on CPU")
    print("=" * 45)
    return info

def set_gpu_env():
    os.environ["CUDA_VISIBLE_DEVICES"]       = "0"
    os.environ["PYTORCH_CUDA_ALLOC_CONF"]    = "max_split_size_mb:512"
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark           = True
        torch.backends.cuda.matmul.allow_tf32   = True
        