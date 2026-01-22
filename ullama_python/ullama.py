import json
import os
import ctypes
from pathlib import Path
from typing import List, Tuple, Dict
import re

def list_files(folder_path: str) -> list[str]:
    return [
        os.path.join(folder_path, name)
        for name in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, name))
    ]

def split_think_and_json(text: str):
    think_match = re.search(r"<think>(.*?)</think>", text, re.DOTALL)

    think_block = None
    data = None

    if think_match:
        think_block = think_match.group(1).strip()
        json_part = text[think_match.end():].strip()
    else:
        think_block = None
        json_part = text.strip()
    try:
        data = json.loads(json_part)
    except json.decoder.JSONDecodeError as e:
        print("Error decoding json:", e)

    return think_block, data

class ULlamaWrapper:
    def __init__(self):
        base_path = os.path.dirname(__file__)
        dll_dir = os.path.join(base_path, "libs")
        dll_f_path = os.path.join(dll_dir, "ullama.dll")

        if not os.path.exists(dll_f_path):
            raise FileNotFoundError(f"Can't find dll: {dll_f_path}")

        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(dll_dir)
        os.environ['PATH'] = dll_dir + os.pathsep + os.environ['PATH']

        self.lib = ctypes.CDLL(dll_f_path, winmode=0)

        self._setup_api()

    def _setup_api(self):
        # Tools
        self.lib.ullama_loadModel.argtypes = [ctypes.c_char_p]
        self.lib.ullama_loadModel.restype = ctypes.c_void_p

        self.lib.ullama_freeModel.argtypes = [ctypes.c_void_p]

        self.lib.ullama_makeSystemPrompt.argtypes = [
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p
        ]
        self.lib.ullama_makeSystemPrompt.restype = ctypes.c_int

        # region LLM Worker
        self.lib.ullama_worker_make.restype = ctypes.c_void_p

        self.lib.ullama_worker_init.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p]
        self.lib.ullama_worker_init.restype = ctypes.c_bool

        self.lib.ullama_worker_run.argtypes = [ctypes.c_void_p]

        self.lib.ullama_worker_ask.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

        self.lib.ullama_worker_getToken.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        self.lib.ullama_worker_getToken.restype = ctypes.c_bool

        self.lib.ullama_worker_isSpeaking.argtypes = [ctypes.c_void_p]
        self.lib.ullama_worker_isSpeaking.restype = ctypes.c_bool

        self.lib.ullama_worker_dispose.argtypes = [ctypes.c_void_p]
        # endregion

        # region Knowledge Base
        self.lib.ullama_kb_make.restype = ctypes.c_void_p

        self.lib.ullama_kb_search.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_float)
        ]
        self.lib.ullama_kb_search.restype = ctypes.c_bool
        # endregion

    def generate_system_prompt(self, npc, user, actions, example):
        # Создаем буфер для строки
        buf = ctypes.create_string_buffer(2048)
        self.lib.ullama_makeSystemPrompt(
            buf, 2048,
            npc.encode('utf-8'), user.encode('utf-8'),
            actions.encode('utf-8'), example.encode('utf-8')
        )
        return buf.value.decode('utf-8')

    def search_knowledge_base(self, kb_ptr, query):
        idx = ctypes.c_int()
        score = ctypes.c_float()
        found = self.lib.ullama_kb_search(
            kb_ptr, query.encode('utf-8'), ctypes.byref(idx), ctypes.byref(score)
        )
        return (found, idx.value, score.value)

def load_ullm_config(path: str) -> dict:
    with open(path, 'r') as f:
        config = json.load(f)
        return config

def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
        return data

def read_dataset_file(path: str) -> List[Tuple[str, dict]]:
    dataset_pairs: List[Tuple[str, dict]] = []
    with open(path, "r", encoding="utf-8") as f:
        data_lines = f.readlines()
        for line in data_lines:
            json_data = json.loads(line)
            usr_request = json_data['messages'][1]['content']
            ai_response = json.loads(json_data['messages'][2]['content'])
            pair = (usr_request, ai_response)
            dataset_pairs.append(pair)
    return dataset_pairs

def make_system_prompt(
    root_dir_path: str,
    sp_path: str,
    npc_name: str,
    usr_desc_path: str
):
    sp = read_file(f'{root_dir_path}\\resources\\{sp_path}')
    if False:
        usr_desc = read_file(f'{root_dir_path}/{usr_desc_path}')
    else:
        usr_desc = ''
    npc_desc = read_file(f'{root_dir_path}\\resources\\{npc_name}/npc_description.md')
    actions = read_file(f'{root_dir_path}\\resources\\{npc_name}/actions.txt')
    chat_example = read_file(f'{root_dir_path}\\resources\\{npc_name}/chat_example.md')

    system_prompt = sp.replace('<user_description></user_description>', usr_desc)
    system_prompt = system_prompt.replace('<chat_example></chat_example>', chat_example)
    system_prompt = system_prompt.replace('<npc_description></npc_description>', npc_desc)
    system_prompt = system_prompt.replace('<actions></actions>', actions)

    return system_prompt


def build_grammar(emotions: List[str], actions: List[dict], use_thinking_mode: bool = True) -> str:
    header = r'root ::= ThinkOrNothing nl nl Response' if use_thinking_mode else r'root ::= Response'

    thinking_rules = r'''
ThinkOrNothing ::= ThinkBlock | ""
ThinkBlock ::= "<think>" ThinkText "</think>"
Sentence ::= ([^.<] | "<" [^/])* "."
ThinkText ::= Sentence | Sentence Sentence | Sentence Sentence Sentence
''' if use_thinking_mode else r''

    common_rules = r'''
nl ::= "\n"
Action ::= "{" ws "\"name\":" ws actions "," ws "\"parameters\":" ws stringlist "}"
Response ::= "{" ws "\"emotion\":" ws emotions "," ws "\"answer\":" ws string "," ws "\"action\":" ws Action "}"
string ::= "\"" ([^"]*) "\""
ws ::= [ \t\n]*
stringlist ::= "[" ws "]" | "[" ws string ("," ws string)* ws "]"
'''

    emotions_rule = "emotions ::= " + " | ".join([rf'"\"{e}\""' for e in emotions])
    actions_rule = "actions ::= " + " | ".join([rf'"\"{a["name"]}\""' for a in actions])

    result =  f"# GBNF Grammar\n{header}{thinking_rules}{common_rules}\n{emotions_rule}\n{actions_rule}"
    return result

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

emotions = [
    "Neutral",
    "Angry",
    "Happy",
    "Sad",
    "Surprise"
]