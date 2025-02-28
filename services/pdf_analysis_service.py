import PyPDF2
import requests
import json
from config import Config
from utils.prompt_utils import load_prompt
from bs4 import BeautifulSoup
import re
import os

class PDFAnalysisService:
    def __init__(self, pdf_dir):
            self.api_key = Config.CLAUDE_API_KEY
            self.api_url = Config.CLAUDE_API_URL
            self.pdf_dir = pdf_dir
            self.allowed_extensions = {'pdf'}
        
    # 확장자 검사
    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    # url로 pdf 업로드
    def download_pdf_from_url(self, url):
        try:
            session = requests.Session()
            
            # 초기 페이지 요청
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
            }
            
            response = session.get(url, headers=headers)
            if response.status_code != 200:
                return False, "페이지를 불러올 수 없습니다."

            soup = BeautifulSoup(response.text, 'html.parser')
            pdf_links = soup.find_all('a', {'class': 'doc_link'})
            
            for link in pdf_links:
                onclick = link.get('onclick', '')
                if '.pdf' in link.text and 'attachfileDownload' in onclick:
                    match = re.search(r"attachfileDownload\('([^']+)',\s*'([^']+)'\)", onclick)
                    if match:
                        _, attach_no = match.groups()
                        pdf_url = f"{Config.DOWNLOAD_URL}?attachNo={attach_no}"
                        
                        print(f"Attempting to download PDF from: {pdf_url}")
                        
                        # PDF 다운로드 요청
                        pdf_response = session.get(
                            pdf_url,
                            headers={
                                **headers,
                                'Accept': 'application/pdf',
                                'Referer': url
                            },
                            allow_redirects=True
                        )
                        
                        print(f"PDF Response Status: {pdf_response.status_code}")
                        print(f"PDF Response Headers: {dict(pdf_response.headers)}")
                        print(f"Response Content Length: {len(pdf_response.content)}")
                        
                        if pdf_response.status_code == 200 and len(pdf_response.content) > 0:
                            self.save_pdf(pdf_response.content)
                            return True, "PDF가 성공적으로 다운로드되었습니다."
                        else:
                            print(f"Download failed with status: {pdf_response.status_code}")
            
            return False, "PDF 파일을 찾을 수 없거나 다운로드할 수 없습니다."

        except Exception as e:
            print(f"Error details: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False, f"오류가 발생했습니다: {str(e)}"
       
    # pdf 직접 첨부 업로드 
    def upload_pdf(self, file):
        try:
            if file.filename == '':
                return False, "선택된 파일이 없습니다."
                
            if not file.filename.endswith('.pdf'):
                return False, "PDF 파일만 업로드 가능합니다."

            file_path = os.path.join(self.pdf_dir, 'protest-info-pdf.pdf')
            file.save(file_path)
            # 파일 권한 설정 (소유자만 읽기/쓰기)
            os.chmod(file_path, 0o600) 
            
            return True, "파일이 성공적으로 업로드되었습니다."
        except Exception as e:
            print(f"File upload error: {str(e)}")
            return False, f"파일 업로드 중 오류가 발생했습니다: {str(e)}"

    def save_pdf(self, content):
        pdf_path = os.path.join(self.pdf_dir, 'protest-info-pdf.pdf')
    
        # 디렉토리가 없으면 생성
        os.makedirs(self.pdf_dir, exist_ok=True)
        
        with open(pdf_path, 'wb') as f:
            f.write(content)

    # pdf 분석 + 텍스트 파일 분석
    def analyze_pdf(self, pdf_path, prompt_file='pdf_analysis_prompt.txt', news_file='static/text/news_info.txt'):
        try:
            prompt = load_prompt(prompt_file)
            if not prompt:
                return None
            
            
            # pdf 파일
            pdf_text = self._extract_pdf_text(pdf_path)
            if not pdf_text:
                return None
            
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
                'max_tokens': 4096,
                'messages': [{
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': f"{prompt}\n\nPDF Content:\n{pdf_text}\nText file Content:\n{news_text}"
                        }
                    ]
                }]
            }

            print("Sending request to Claude API...")

            response = requests.post(self.api_url, headers=headers, json=data)
            
            if response.status_code != 200:
                print(f"API Error: {response.status_code}")
                print(f"Error Response: {response.text}")
                return None

            print("API request successful")
            # 분석 결과, content의 text 내용만 확인
            response_data = response.json()
            text_content = response_data['content'][0]['text']
            # indent=2로 설정하여 들여쓰기를 적용하고, ensure_ascii=False로 한글이 깨지지 않도록 설정
            print(json.dumps(json.loads(text_content), indent=2, ensure_ascii=False))
            return response.json()
            

        except Exception as e:
            print(f"PDF 분석 중 예외 발생: {e}")
            import traceback
            print(traceback.format_exc())
            return None

    # pdf 텍스트 추출
    def _extract_pdf_text(self, pdf_path):
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = []
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
                return '\n'.join(text)
        except Exception as e:
            print(f"PDF 텍스트 추출 중 오류 발생: {e}")
            return None
        
    # 텍스트 파일 추출(구글 검색)    
    def _read_news_text(self, news_file):
        try:
            if not os.path.exists(news_file):
                print(f"Text file not found: {news_file}")
                return None
                
            with open(news_file, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except Exception as e:
            print(f"텍스트 파일 읽기 중 오류 발생: {e}")
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