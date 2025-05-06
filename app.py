import datetime
import requests
from bs4 import BeautifulSoup
import os
import json
from utils.prompt_utils import load_prompt
from config import Config

class ProtestInfoPostService:
    
    def __init__(self):
        self.api_key = Config.CLAUDE_API_KEY
        self.api_url = Config.CLAUDE_API_URL

    @staticmethod
    def fetch_triangle_sentences():
        list_url = "https://news.nate.com/hissue/list?isq=9890&mid=n0412&type=c"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }

        try:
            # 1. 뉴스 목록 페이지에서 첫 번째 링크 추출
            res = requests.get(list_url, headers=headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            first_link_tag = soup.select_one('.mduSubjectList .mlt01 a')
            if not first_link_tag:
                return [], "뉴스 링크를 찾을 수 없습니다."

            first_link = first_link_tag['href']
            news_url = "https:" + first_link if first_link.startswith("//") else first_link

            # 2. 뉴스 본문 요청
            news_res = requests.get(news_url, headers=headers)
            news_soup = BeautifulSoup(news_res.text, 'html.parser')
            content_div = news_soup.select_one('#realArtcContents')

            if not content_div:
                return [], "본문을 찾을 수 없습니다."

            lines = [line.strip() for line in content_div.stripped_strings]
            triangle_lines = [line for line in lines if '▲' in line]

            if not triangle_lines:
                return [], "▲ 문자가 포함된 문장을 찾지 못했습니다."

            # 3. 파일 저장
            filepath='static/text/news_info.txt'
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                for line in triangle_lines:
                    f.write(line + "\n")

            return triangle_lines, None

        except Exception as e:
            return [], str(e)
    
    def _read_news_text(self, file_path):
        """뉴스 텍스트 파일을 읽어 내용을 반환하는 메서드"""
        try:
            if not os.path.exists(file_path):
                print(f"Warning: File does not exist: {file_path}")
                return ""
                
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading news text: {e}")
            return ""
        
    def analyze_protest_info(self, prompt_file='pdf_analysis_prompt.txt', news_file='static/text/news_info.txt'):
        """시위 정보를 분석하는 메서드"""
        try:
            prompt = load_prompt(prompt_file)
            if not prompt:
                return None
            
            current_date = datetime.datetime.now().strftime('%Y년 %m월 %d일')
            
            # 텍스트 파일
            news_text = self._read_news_text(news_file)
            if not news_text:
                print(f"Warning: Could not read news text from {news_file}")
                news_text = "No news information available."

            headers = {
                'x-api-key': self.api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            }

            data = {
                'model': 'claude-3-5-sonnet-20241022',
                'max_tokens': 8192,
                'messages': [{
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': f"시위 날짜는 {current_date}이야\n{news_text}\n{prompt}"
                        }
                    ]
                }]
            }
            
            print("API 요청 데이터:", json.dumps(data, ensure_ascii=False, indent=2))
            print("Claude API에 요청을 보내는 중...")

            response = requests.post(self.api_url, headers=headers, json=data)
            
            if response.status_code != 200:
                print(f"API 오류: {response.status_code}")
                print(f"오류 응답: {response.text}")
                return None

            print("API 요청 성공")
            # 분석 결과, content의 text 내용만 확인
            response_data = response.json()
            text_content = response_data['content'][0]['text']
            # indent=2로 설정하여 들여쓰기를 적용하고, ensure_ascii=False로 한글이 깨지지 않도록 설정
            print(json.dumps(json.loads(text_content), indent=2, ensure_ascii=False))
            return response_data
            
        except Exception as e:
            print(f"시위 정보 분석 중 예외 발생: {e}")
            import traceback
            print(traceback.format_exc())
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

# 사용 예시
if __name__ == "__main__":
    service = ProtestInfoPostService()
    
    # 1. 뉴스에서 삼각형(▲) 포함된 문장 추출
    triangle_sentences, error = ProtestInfoPostService.fetch_triangle_sentences()
    if error:
        print(f"Error fetching triangle sentences: {error}")
    else:
        print(f"Found {len(triangle_sentences)} triangle sentences")
        
    # 2. 시위 정보 분석
    analysis_result = service.analyze_protest_info()
    
    # 3. 분석 결과 서버 전송
    if analysis_result:
        success = service.send_to_server(analysis_result)
        print(f"Server transmission {'successful' if success else 'failed'}")
    else:
        print("No analysis result to send")