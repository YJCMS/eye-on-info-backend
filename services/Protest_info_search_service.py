from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import urllib.parse
import os

class ProtestInfoSearchService:
    def __init__(self):
        self.chrome_options = self._setup_chrome_options()

    def _setup_chrome_options(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
        return chrome_options

    def _get_search_query(self):
        today = datetime.now().strftime("%Y.%m.%d")
        return f"[오늘의 주요일정]사회 뉴시스 + {today}"

    def get_today_schedule_url(self):
        driver = None
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            
            search_query = self._get_search_query()
            encoded_query = urllib.parse.quote(search_query)
            url = f"https://www.google.com/search?q={encoded_query}"
            
            driver.get(url)
            wait = WebDriverWait(driver, 10)
            
            selectors = [
                'a[jsname="UWckNb"]',
                'div.g div.yuRUbf > a',
                'div.tF2Cxc > div.yuRUbf > a',
                'div.g a'
            ]
            
            result_url = None
            for selector in selectors:
                try:
                    element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    result_url = element.get_attribute('href')
                    if 'newsis.com' in result_url:
                        break
                except:
                    continue

            return result_url

        except Exception as e:
            print(f"Error occurred: {e}")
            return None
            
        finally:
            if driver:
                driver.quit()
                
    def save_protest_info_to_txt(self, filepath='static/text/news_info.txt'):
        """집회/시위 정보를 텍스트 파일로 저장하는 메서드"""
        driver = None
        try:
            # 디렉토리 생성
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # 먼저 URL 가져오기
            url = self.get_today_schedule_url()
            if not url:
                return False

            # 새로운 드라이버로 뉴시스 페이지 접근
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get(url)
            
            # 페이지 로딩 대기
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "article")))
            
            # HTML 파싱
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            article = soup.find('article')
            
            if not article:
                return False

            # 삼각형(▲)이 포함된 문장들 추출
            triangle_texts = []
            for br in article.find_all('br'):
                text = br.next_sibling
                if text and isinstance(text, str) and "▲" in text:
                    triangle_texts.append(text.strip())

            # 텍스트 파일로 저장
            if triangle_texts:
                with open(filepath, 'w', encoding='utf-8') as f:
                    for text in triangle_texts:
                        f.write(text + '\n')
                return True

            return False

        except Exception as e:
            print(f"Error occurred while saving protest info: {e}")
            return False

        finally:
            if driver:
                driver.quit()