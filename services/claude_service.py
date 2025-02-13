import requests
import base64
import json  # json 모듈 추가
from config import Config
from utils.prompt_utils import load_prompt

class ClaudeService:
    def __init__(self):
        self.api_key = Config.CLAUDE_API_KEY
        self.api_url = Config.CLAUDE_API_URL

    def encode_image(self, image_path):
        """이미지를 base64로 인코딩"""
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"이미지 인코딩 오류: {e}")
            return None

    def analyze_image(self, image_path, prompt_file='analysis_prompt.txt'):
        """이미지 분석 요청"""
        try:
            # 프롬프트 로드
            prompt = load_prompt(prompt_file)
            if not prompt:
                return None

            # 이미지 인코딩
            encoded_image = self.encode_image(image_path)
            if not encoded_image:
                return None

            # API 요청 헤더
            headers = {
                'x-api-key': self.api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            }

            # Sonnet 모델용 API 요청 데이터
            data = {
                'model': 'claude-3-5-sonnet-20241022',  # Sonnet 모델로 변경
                'max_tokens': 4096,
                'messages': [{
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': 'image/jpeg',
                                'data': encoded_image
                            }
                        },
                        {
                            'type': 'text',
                            'text': prompt
                        }
                    ]
                }]
            }

            # 디버깅용 로그
            print("Sending request to Claude API...")
            print(f"URL: {self.api_url}")
            print("Headers:", {k: v for k, v in headers.items() if k != 'x-api-key'})
            print("Using model:", data['model'])

            # API 요청
            response = requests.post(self.api_url, headers=headers, json=data)
            
            # 응답 상태 확인 및 상세 로깅
            if response.status_code != 200:
                print(f"API Error: {response.status_code}")
                print(f"Error Response: {response.text}")
                return None

            print("API request successful")
            print(response.json())
            return response.json()

        except Exception as e:
            print(f"Claude API 요청 중 예외 발생: {e}")
            import traceback
            print(traceback.format_exc())  # 상세한 에러 트레이스
            return None

    def send_to_server(self, analysis_result):
        """분석 결과를 특정 서버로 전송"""
        try:
            # API 응답에서 JSON 데이터만 추출
            if isinstance(analysis_result, dict) and 'content' in analysis_result:
                # content 배열의 첫 번째 항목에서 text 추출
                json_str = analysis_result['content'][0]['text']
                # JSON 문자열을 파싱하여 실제 데이터 얻기
                data_to_send = json.loads(json_str)
            else:
                data_to_send = analysis_result

            response = requests.post(
                Config.TARGET_SERVER_URL,
                json=data_to_send,  # 파싱된 JSON 데이터만 전송
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"\nServer Response Status: {response.status_code}")
            print(f"Server Response Headers: {response.headers}")
            print(f"Server Response Content: {response.text}")
            
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"\nServer Error Details:")
            print(f"Status Code: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
            print(f"Error Message: {e.response.text if hasattr(e, 'response') else str(e)}")
            return False
        except Exception as e:
            print(f"\nUnexpected Error: {str(e)}")
            return False