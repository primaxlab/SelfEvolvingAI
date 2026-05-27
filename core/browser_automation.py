"""
浏览器自动化 - 网页操作、表单填写、数据抓取

依赖: pip install selenium (可选)
无依赖时使用标准库降级方案
"""

import json
import os
import time
import hashlib
import urllib.request
import urllib.parse
import re
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any


class BrowserAction(Enum):
    OPEN = "open"
    CLICK = "click"
    TYPE = "type"
    SUBMIT = "submit"
    SCREENSHOT = "screenshot"
    GET_TEXT = "get_text"
    GET_LINKS = "get_links"
    NAVIGATE = "navigate"


@dataclass
class PageInfo:
    url: str
    title: str = ""
    content_length: int = 0
    links: List[str] = field(default_factory=list)
    forms: List[Dict] = field(default_factory=list)
    timestamp: float = 0.0


class BrowserAutomationEngine:
    """浏览器自动化引擎"""

    def __init__(self, storage_dir: str = "data/browser"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.driver = None
        self.page_history: List[PageInfo] = []
        self.current_page: Optional[PageInfo] = None
        self._try_import_selenium()

    def _try_import_selenium(self):
        """尝试导入selenium"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            self._webdriver = webdriver
            self._Options = Options
        except ImportError:
            self._webdriver = None

    def start_browser(self, headless: bool = True) -> bool:
        """启动浏览器"""
        if not self._webdriver:
            return False

        try:
            options = self._Options()
            if headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

            self.driver = self._webdriver.Chrome(options=options)
            return True
        except Exception:
            return False

    def stop_browser(self):
        """停止浏览器"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def open_url(self, url: str) -> Dict[str, Any]:
        """打开URL"""
        if self.driver:
            return self._selenium_open(url)
        return self._stdlib_fetch(url)

    def _selenium_open(self, url: str) -> Dict[str, Any]:
        """Selenium打开"""
        try:
            self.driver.get(url)
            time.sleep(1)

            page = PageInfo(
                url=url,
                title=self.driver.title,
                timestamp=time.time(),
            )

            # 获取链接
            links = self.driver.find_elements("tag name", "a")
            page.links = [l.get_attribute("href") for l in links[:50] if l.get_attribute("href")]

            self.current_page = page
            self.page_history.append(page)

            return {
                "success": True,
                "title": page.title,
                "url": url,
                "links_count": len(page.links),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _stdlib_fetch(self, url: str) -> Dict[str, Any]:
        """标准库抓取"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode('utf-8', errors='replace')
                content_type = resp.headers.get('Content-Type', '')

            # 提取标题
            title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
            title = title_match.group(1) if title_match else ""

            # 提取链接
            links = re.findall(r'href=["\']([^"\']+)["\']', content)

            # 提取文本
            text = re.sub(r'<[^>]+>', ' ', content)
            text = re.sub(r'\s+', ' ', text).strip()

            page = PageInfo(
                url=url, title=title,
                content_length=len(content),
                links=list(set(links))[:50],
                timestamp=time.time(),
            )
            self.current_page = page
            self.page_history.append(page)

            return {
                "success": True,
                "title": title,
                "url": url,
                "content_length": len(content),
                "text_preview": text[:500],
                "links_count": len(links),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def click_element(self, selector: str, by: str = "css") -> bool:
        """点击元素"""
        if not self.driver:
            return False
        try:
            from selenium.webdriver.common.by import By
            by_map = {
                "css": By.CSS_SELECTOR,
                "id": By.ID,
                "xpath": By.XPATH,
                "class": By.CLASS_NAME,
                "tag": By.TAG_NAME,
            }
            element = self.driver.find_element(by_map.get(by, By.CSS_SELECTOR), selector)
            element.click()
            return True
        except Exception:
            return False

    def type_text(self, selector: str, text: str, by: str = "css") -> bool:
        """输入文字"""
        if not self.driver:
            return False
        try:
            from selenium.webdriver.common.by import By
            by_map = {
                "css": By.CSS_SELECTOR,
                "id": By.ID,
                "xpath": By.XPATH,
            }
            element = self.driver.find_element(by_map.get(by, By.CSS_SELECTOR), selector)
            element.clear()
            element.send_keys(text)
            return True
        except Exception:
            return False

    def get_page_text(self) -> str:
        """获取页面文本"""
        if self.driver:
            try:
                return self.driver.find_element("tag name", "body").text[:5000]
            except Exception:
                pass
        return ""

    def take_screenshot(self, path: str = "") -> str:
        """截图"""
        if not self.driver:
            return ""
        if not path:
            path = os.path.join(self.storage_dir, f"screenshot_{int(time.time())}.png")
        try:
            self.driver.save_screenshot(path)
            return path
        except Exception:
            return ""

    def get_page_source(self) -> str:
        """获取页面源码"""
        if self.driver:
            try:
                return self.driver.page_source[:10000]
            except Exception:
                pass
        return ""

    def search_web(self, query: str, engine: str = "google") -> Dict[str, Any]:
        """搜索网页"""
        encoded_query = urllib.parse.quote(query)
        urls = {
            "google": f"https://www.google.com/search?q={encoded_query}",
            "bing": f"https://www.bing.com/search?q={encoded_query}",
            "baidu": f"https://www.baidu.com/s?wd={encoded_query}",
        }
        url = urls.get(engine, urls["google"])

        if self.driver:
            return self._selenium_open(url)
        else:
            # 直接抓取搜索结果
            return self._stdlib_fetch(url)

    def fetch_content(self, url: str) -> str:
        """获取网页内容(纯文本)"""
        result = self._stdlib_fetch(url)
        if result.get("success"):
            return result.get("text_preview", "")
        return result.get("error", "")

    def extract_links(self, url: str) -> List[str]:
        """提取链接"""
        result = self._stdlib_fetch(url)
        return result.get("links", [])

    def get_history(self) -> List[Dict[str, Any]]:
        """获取浏览历史"""
        return [asdict(p) for p in self.page_history[-20:]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "selenium_available": self._webdriver is not None,
            "browser_running": self.driver is not None,
            "pages_visited": len(self.page_history),
        }


if __name__ == "__main__":
    print("=== 浏览器自动化测试 ===")
    engine = BrowserAutomationEngine()

    print(f"Selenium: {'可用' if engine._webdriver else '不可用(降级模式)'}")

    # 抓取网页
    result = engine.open_url("https://httpbin.org/html")
    print(f"\n打开网页: {result}")

    # 获取内容
    content = engine.fetch_content("https://httpbin.org/html")
    print(f"\n内容: {content[:200]}...")

    # 提取链接
    links = engine.extract_links("https://httpbin.org/links/5")
    print(f"\n链接: {links}")

    print(f"\n统计: {engine.get_stats()}")
    print("测试完成!")
