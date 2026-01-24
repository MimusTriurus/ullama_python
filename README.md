#### python -m build

#### pip install dist/ullama_python-0.0.1-py3-none-any.whl

####  pip uninstall dist/ullama_python-0.0.1-py3-none-any.whl

#### pip install git+https://github.com/MimusTriurus/ullama_python.git@main

### LLM model configuration

```
{
  "model": "",
  "lora_adapter": "",
  "system_prompt": "",
  "antiprompts": ["User: ", "user: "],
  "n_gpu_layers": 9999,
  "temp": 0.9,
  "top_k": 40,
  "top_p": 0.949999988,
  "repeat_penalty": 1,
  "repeat_last_n": 64,
  "seed": -1,
  "use_mlock": false,
  "use_mmap": true,
  "reset_history": true
}
```

### Knowledge base embedding model configuration

```
{
  "model": ""
}
```