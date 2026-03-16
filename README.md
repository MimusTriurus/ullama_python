#### python -m build

#### pip install dist/ullama_python-0.0.1-py3-none-any.whl

####  pip uninstall dist/ullama_python-0.0.1-py3-none-any.whl

#### pip install git+https://github.com/MimusTriurus/ullama_python.git@main

### LLM model configuration

### Params description:
- **temp** - регулирует степень случайности при выборе следующего токена [0.1 - 1.2+]. Чем больше, тем более "творческий" ответ
- **top_k** - > 99 == больше разнообразия, выше риск разъезжания смысла [10 - 200+]
- **top_p** - > 0.8 == больше разнообразия, меньше строгий вывод [0.4-0.98]
- **repeat_penalty** - штрафует повторяющиеся токены, чтобы модель не зацикливалась (1.0 - выключено) [1.0-1.6+].
- **repeat_last_n** - Малое значение [16–32] - штрафует только недавние повторы; Большое значение [64–256] - модель избегает повторов на длинных дистанциях
- **seed** - -1 - вывод будет каждый раз немного разный

### Knowledge base embedding model configuration

#### Максимум выразительности
```
{
  "temp": 1.1,
  "top_k": 80,
  "top_p": 0.95,
  "repeat_penalty": 1.05,
  "repeat_last_n": 128,
  "seed": -1
}
```

#### Точные ответы
```
{
  "temp": 0.2,
  "top_k": 20,
  "top_p": 0.5,
  "repeat_penalty": 1.15,
  "repeat_last_n": 64,
  "seed": 123
}

```

#### Относительно стабильный чат бот
```
{
  "temp": 0.7,
  "top_k": 40,
  "top_p": 0.9,
  "repeat_penalty": 1.1,
  "repeat_last_n": 128,
  "seed": -1
}
```

## Mlops
- Prefect