import requests
from bs4 import BeautifulSoup
import os
from utils.image_utils import ensure_directory_exists, get_headers
from config import Config

class CrawlService:
    @staticmethod
    def get_bcontent_image(url):
        try:
            print(f"페이지 요청: {url}")
            response = requests.get(url, headers=get_headers(), verify=False)
            response.raise_for_status
            
            soup = BeautifulSoup(response.text, 'html.parser')
            bcontent = soup.find('div', class_='bcontent')
            
            if bcontent:
                print("bcontent div를 찾았습니다.")
                img_tag = bcontent.find('img')
                if img_tag:
                    src = img_tag.get('src')
                    print(f"찾은 이미지 src: {src}")
                    
                    if src:
                        if not src.startswith(('http://', 'http://')):
                            if src.startswith('//'):
                                src = 'htts:' + src
                            else:
                                src = Config.BASE_URL + src
                        return src
            else:
                print("bcontent div를 찾을 수 없습니다.")
            
            return None
                    
        except Exception as e:
            print(f"이미지 찾기 중 오류 발생: {e}")
            return None
            
    @staticmethod
    def download_image(img_url, filename):
        try:
            print(f"다운로드 시도할 이미지 URL: {img_url}")
            ensure_directory_exists()
            save_path = os.path.join(Config.SAVE_DIR, filename)
            
            response = requests.get(img_url, stream=True, verify=False)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"이미지 저장 완료: {save_path}")
            return True, save_path
        except Exception as e:
            print(f"이미지 다운로드 중 오류 발생: {e}")
            return False, None
