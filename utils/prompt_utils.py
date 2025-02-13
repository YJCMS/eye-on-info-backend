import os
from config import Config

def load_prompt(prompt_file):
    # 프롬프트 파일 읽기
    prompt_path = os.path.join(Config.PROMPT_DIR, prompt_file)
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"프롬프트 파일 읽기 오류: {e}")
        return None