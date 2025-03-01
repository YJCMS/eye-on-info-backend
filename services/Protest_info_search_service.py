from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import urllib.parse
import os
import logging
import time
import random

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ProtestInfoSearchService')

class ProtestInfoSearchService:
    def __init__(self):
        self.chrome_options = self._setup_chrome_options()
    #     self._setup_directories()

    # def _setup_directories(self):
    #     """필요한 디렉토리 구조 생성"""
    #     os.makedirs('static/text', exist_ok=True)

    def _setup_chrome_options(self):
        """크롬 드라이버 옵션 설정"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # 유저 에이전트 사용(잘되는거 1개만 사용 중)
        user_agents = [
            #'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            #'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        ]
        chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        # 추가 옵션으로 탐지 회피 향상
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        return chrome_options

    def _get_search_query(self, date=None):
        """검색 쿼리 생성"""
        if date is None:
            date = datetime.now()
        formatted_date = date.strftime("%Y %m월%d일")
        return f"[오늘의 주요일정]사회 + {formatted_date} + site:newsis.com"

    def _get_article_url_with_retry(self, max_retries=3):
        """Google 검색으로 기사 URL 가져오기 (재시도 로직 포함)"""
        driver = None
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            
            # 구글 검색 수행
            for attempt in range(max_retries):
                try:
                    date_offset = timedelta(days=-attempt) if attempt > 0 else timedelta()
                    search_date = datetime.now() + date_offset
                    search_query = self._get_search_query(search_date)
                    
                    logger.info(f"검색 시도 {attempt+1}/{max_retries}, 쿼리: {search_query}")
                    
                    encoded_query = urllib.parse.quote(search_query)
                    search_url = f"https://www.google.com/search?q={encoded_query}"
                    
                    driver.get(search_url)
                    
                    time.sleep(1 + random.random() * 2)  
                    
                    wait = WebDriverWait(driver, 5)  # 타임아웃 줄임
                    
                    # 검색 결과에서 뉴시스 링크 찾기
                    selectors = [
                        'a[jsname="UWckNb"]',
                        'div.g div.yuRUbf > a',
                        'div.tF2Cxc > div.yuRUbf > a',
                        'div.g a'
                    ]
                    
                    for selector in selectors:
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            for element in elements:
                                result_url = element.get_attribute('href')
                                if result_url and 'newsis.com' in result_url:
                                    logger.info(f"기사 URL 찾음: {result_url}")
                                    return result_url
                        except Exception as e:
                            logger.debug(f"선택자 {selector} 처리 중 오류: {e}")
                            continue
                    
                    logger.warning(f"시도 {attempt+1}: 결과 없음, 다른 날짜로 재시도")
                    
                except TimeoutException:
                    logger.warning(f"시도 {attempt+1}: 타임아웃")
                    
                if attempt < max_retries - 1:
                    # 재시도 전 무작위 지연
                    wait_time = 2 + random.random() * 3
                    logger.info(f"재시도 대기 중... ({wait_time:.1f}초)")
                    time.sleep(wait_time)
            
            logger.error("최대 재시도 횟수 초과, URL을 찾지 못함")
            return None
                
        except Exception as e:
            logger.error(f"기사 URL 검색 중 오류: {e}")
            return None
            
        finally:
            if driver:
                driver.quit()

    def _extract_triangle_texts(self, article_url):
        """기사에서 삼각형(▲) 포함 텍스트 추출"""
        driver = None
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            logger.info(f"기사 URL 접근: {article_url}")
            
            driver.get(article_url)
            
            # 페이지 로딩 대기
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
            
            # HTML 파싱
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            article = soup.find('article')
            
            if not article:
                logger.warning("기사 본문을 찾을 수 없음")
                return []

            # 삼각형(▲)이 포함된 문장들 추출
            triangle_texts = []
            
            # 방법 1: br 태그 다음 텍스트 확인
            for br in article.find_all('br'):
                text = br.next_sibling
                if text and isinstance(text, str) and "▲" in text:
                    triangle_texts.append(text.strip())
            
            # 방법 2: p 태그 내 텍스트 확인 (추가 방법)
            if not triangle_texts:
                for p in article.find_all('p'):
                    text = p.get_text()
                    if "▲" in text:
                        triangle_texts.append(text.strip())
            
            # 방법 3: 전체 텍스트에서 추출 (마지막 방법)
            if not triangle_texts:
                full_text = article.get_text()
                lines = full_text.split('\n')
                for line in lines:
                    if "▲" in line:
                        triangle_texts.append(line.strip())
            
            logger.info(f"삼각형 텍스트 {len(triangle_texts)}개 추출됨")
            return triangle_texts

        except Exception as e:
            logger.error(f"텍스트 추출 중 오류: {e}")
            return []
            
        finally:
            if driver:
                driver.quit()

    def save_protest_info_to_txt(self, filepath='static/text/news_info.txt'):
        """집회/시위 정보를 텍스트 파일로 저장하는 메서드"""
        start_time = time.time()
        logger.info(f"정보 수집 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. Google 검색으로 기사 URL 가져오기
        article_url = self._get_article_url_with_retry()
        
        if not article_url:
            logger.error("기사 URL을 찾지 못함")
            return False
        
        # 2. 기사에서 텍스트 추출
        triangle_texts = self._extract_triangle_texts(article_url)
        
        if not triangle_texts:
            logger.warning("기사에서 집회/시위 정보를 찾지 못함")
            return False
        
        # 3. 파일에 저장
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                for text in triangle_texts:
                    f.write(text + '\n')
        except Exception as e:
            logger.error(f"파일 저장 중 오류: {e}")
            return False
        
        elapsed_time = time.time() - start_time
        logger.info(f"정보 수집 완료 (소요시간: {elapsed_time:.2f}초)")
        return True