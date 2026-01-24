import json
import os
import ctypes
from pathlib import Path
from typing import List, Tuple, Dict
import re

from ullama_python.ullama_python.ullama import ULlamaWrapper, build_grammar, emotions, split_think_and_json
#from ullama_python.ullama import build_grammar, emotions, split_think_and_json, ULlamaWrapper

def list_files(folder_path: str) -> list[str]:
    return [
        os.path.join(folder_path, name)
        for name in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, name))
    ]

def load_ullm_config(path: str) -> dict:
    with open(path, 'r') as f:
        config = json.load(f)
        return config

def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
        return data

def read_dataset_file(path: str) -> List[dict]:
    requests: List[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        data_lines = f.readlines()
        for line in data_lines:
            json_data = json.loads(line)
            requests.append(json_data)
    return requests

def make_system_prompt(sp_path: str):
    sp = read_file(sp_path)

    system_prompt = sp

    return system_prompt

def read_kb_file(path: str) -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        triggers = f.readlines()
        knowledge_base = {}
        for trigger in triggers:
            t, v = trigger.split('|')
            t = t.strip()
            v = v.strip()
            knowledge_base[t] = v
        return knowledge_base

def parse_actions_from_file(path: str):
    actions = []

    pattern = re.compile(r"-\s*([A-Za-z_][A-Za-z0-9_]*)\s*")

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            match = pattern.search(line)
            if match:
                action_name = match.group(1)
                actions.append({"name": action_name})

    return actions

BUFFER_SIZE = 512
ENCODING = "utf-8"

if __name__ == "__main__":
    # region ENV vars
    llm_model_f_path = os.getenv('LLM_MODEL_F_PATH', '')
    lora_adapter_f_path = os.getenv('LORA_ADAPTER_F_PATH', '')
    actions_f_path = os.getenv('ACTIONS_F_PATH', '')
    emb_model_f_path = os.getenv('EMB_MODEL_F_PATH', 'bge-base-en-v1.5-f16')
    requests_count = int(os.getenv('MAX_REQUESTS_COUNT', 10))
    use_thinking = os.getenv('USE_THINKING', 'false').lower() in ("1", "true", "yes", "on")
    system_prompt_f_path = os.getenv('SYSTEM_PROMPT_F_PATH', '')

    llm_cfg_f_path = os.getenv('LLM_CFG_F_PATH', '')
    kb_cfg_f_path = os.getenv('KB_CFG_F_PATH', '')

    kb_triggers_f_path = os.getenv('KB_TRIGGERS_F_PATH', '')

    dataset_f_path = os.getenv("DATASET_F_PATH", '')
    kb_threshold = float(os.getenv('KB_THRESHOLD', 0.6))
    # endregion

    if not os.path.isfile(dataset_f_path):
        print(f"No validation dataset path provided: {dataset_f_path}")
        exit(1)

    if not os.path.isfile(llm_cfg_f_path):
        print(f"No cfg file for ullama provided: {llm_cfg_f_path}")
        exit(2)

    if not os.path.isfile(llm_model_f_path):
        print(f"No llm model file provided: {llm_model_f_path}")
        exit(3)

    if not os.path.isfile(actions_f_path):
        print(f"No npc actions file provided: {actions_f_path}")
        exit(3)

    api = ULlamaWrapper()

    emb_model = None
    kb_worker_ptr = None
    kb_init_result = False
    kb = {}
    if os.path.isfile(kb_cfg_f_path) and os.path.isfile(emb_model_f_path):
        emb_model = api.lib.ullama_loadModel(emb_model_f_path.encode(ENCODING))
        kb_worker_ptr = api.lib.ullama_kb_make()
        kb_cfg = json.loads(read_file(kb_cfg_f_path))
        kb_cfg['model'] = emb_model_f_path
        kb_cgf_str = json.dumps(kb_cfg).encode(ENCODING)
        kb_init_result = api.lib.ullama_kb_init(kb_worker_ptr, kb_cgf_str, emb_model)
        if kb_init_result:
            kb = read_kb_file(kb_triggers_f_path)
            if kb:
                for k, v in kb.items():
                    api.lib.ullama_kb_addChunk(kb_worker_ptr, k.encode(ENCODING))
                api.lib.ullama_kb_update(kb_worker_ptr)

    ullm_config = load_ullm_config(f'{llm_cfg_f_path}')

    ullm_config['model'] = llm_model_f_path
    ullm_config['lora_adapter'] = lora_adapter_f_path
    ullm_config['system_prompt'] = make_system_prompt(system_prompt_f_path)
    actions = parse_actions_from_file(actions_f_path)
    grammar_string = build_grammar(emotions, actions, use_thinking)
    ullm_config['grammar'] = grammar_string

    ullama_cfg_json_str = json.dumps(ullm_config).encode(ENCODING)

    try:
        model = api.lib.ullama_loadModel(ullama_cfg_json_str)
        worker = api.lib.ullama_worker_make()
        if api.lib.ullama_worker_init(worker, ullama_cfg_json_str, model):
            token_buf = ctypes.create_string_buffer(BUFFER_SIZE)

            api.lib.ullama_worker_run(worker)

            file_name = Path(dataset_f_path).stem

            kb_chunk_idx = ctypes.c_int()
            kb_chunk_score = ctypes.c_float()

            user_requests = read_dataset_file(dataset_f_path)
            for request_dict in user_requests[:requests_count]:
                request_of_user = request_dict['request_of_user']

                if kb_init_result:
                    request = json.dumps(request_dict)
                    chunk_found = api.lib.ullama_kb_search(
                        kb_worker_ptr,
                        request.encode(ENCODING),
                        ctypes.byref(kb_chunk_idx),
                        ctypes.byref(kb_chunk_score)
                    )
                    if chunk_found:
                        kb_content = list(kb.values())
                        context = kb_content[kb_chunk_idx.value]
                        if not request_dict['context'] and kb_chunk_score.value >= kb_threshold:
                            request_dict['context'] = context
                        #print(f"==> KB chunk. Score: {kb_chunk_score.value} Context: {context}")

                request = json.dumps(request_dict)

                api.lib.ullama_worker_ask(worker, request.encode(ENCODING))
                response = ''
                while api.lib.ullama_worker_isSpeaking(worker):
                    if api.lib.ullama_worker_getToken(worker, token_buf, BUFFER_SIZE):
                        response += token_buf.value.decode(ENCODING)

                think_block = None
                response_dict = {}
                try:
                    think_block, response_dict = split_think_and_json(response)
                except Exception as e:
                    print(e)
                    continue

                if response_dict is None:
                    print(f"==> Error! Can't parse response: {response}")
                    continue

                if 'answer' not in response_dict or 'action' not in response_dict or 'name' not in response_dict['action'] or 'parameters' not in response_dict['action']:
                    print(f"==> Error!. Json has incorrect structure: {response}")
                    continue

                answer = response_dict.get('answer')
                action_name = response_dict['action']['name']
                action_args = response_dict['action']['parameters']

                print(f'--------------------')
                print(f"User: {request_of_user}")
                if request_dict['context']:
                    print(f"Context: {request_dict['context']}")
                print('')
                print(f"Assistant: {answer}")
                print(f"Action: {action_name}")
                print(f"Parameters: {action_args}")
                print('')

        else:
            api.lib.ullama_worker_dispose(worker)
            api.lib.ullama_freeModel(model)

        api.lib.ullama_worker_dispose(worker)
        api.lib.ullama_freeModel(model)

        if emb_model:
            api.lib.ullama_freeModel(emb_model)
        if kb_worker_ptr:
            api.lib.ullama_kb_dispose(kb_worker_ptr)

    except Exception as e:
        print(f"Error: {e}")

    print('=== end ===')