# coding=utf-8
"""
目标站: 牛剧影院 (niuju.net)
站点: https://niuju.net/
海洋CMS架构 - 完整爬虫插件
"""
import re
import sys
import json
import urllib.parse
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.site_url = "https://niuju.net"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        self.categories = self._fetch_categories()

    def _fetch_categories(self):
        """从首页导航获取分类"""
        try:
            resp = self.fetch(self.site_url, headers=self.headers)
            if not resp:
                return self._default_categories()
            soup = BeautifulSoup(resp.text, 'html.parser')
            categories = []
            seen = set()
            
            # 牛剧影院导航在 .nav 中，链接指向 /hot.html, /new.html, /duanju.html, /score.html
            # 但实际分类可能是 /vodtype/ 或 /vodshow/ 格式
            # 检查导航链接
            nav_links = soup.select('.nav a, nav a, .top a')
            exclude = ['牛剧影院', '搜索', '首页']
            
            for a in nav_links:
                href = a.get('href', '')
                name = a.get_text(strip=True)
                if not name or name in exclude:
                    continue
                # 尝试匹配分类链接
                match = re.search(r'/(hot|new|duanju|score)\.html', href)
                if match:
                    type_map = {
                        'hot': {'id': 'hot', 'name': '热榜'},
                        'new': {'id': 'new', 'name': '上新'},
                        'duanju': {'id': 'duanju', 'name': '短剧'},
                        'score': {'id': 'score', 'name': '高分'}
                    }
                    info = type_map.get(match.group(1))
                    if info and info['id'] not in seen:
                        seen.add(info['id'])
                        categories.append({"type_id": info['id'], "type_name": info['name']})
                        continue
                # 尝试匹配 /vodtype/ 格式
                match2 = re.search(r'/vodtype/(\d+)\.html', href)
                if match2:
                    tid = match2.group(1)
                    if tid not in seen:
                        seen.add(tid)
                        categories.append({"type_id": tid, "type_name": name})
            
            # 如果没抓到分类，使用默认的
            if categories:
                return categories
        except Exception as e:
            print(f"[牛剧影院] 获取分类失败: {e}")
        return self._default_categories()

    def _default_categories(self):
        return [
            {"type_id": "hot", "type_name": "热榜"},
            {"type_id": "new", "type_name": "上新"},
            {"type_id": "duanju", "type_name": "短剧"},
            {"type_id": "score", "type_name": "高分"},
        ]

    def _fix_url(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if not url.startswith("http"):
            return urllib.parse.urljoin(self.site_url + "/", url)
        return url

    def _parse_video_list(self, html):
        """解析视频列表，适配牛剧影院的 .grid .card 结构"""
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        seen = set()
        
        # 牛剧影院卡片结构: .card 包裹，内部 h3 是标题，.poster img 是封面
        for card in soup.select('.grid .card, .card'):
            # 提取链接
            link = card if card.name == 'a' else card.select_one('a')
            if not link:
                continue
            href = link.get('href', '')
            
            # 提取 vod_id
            vod_id = None
            match = re.search(r'/voddetail/(\d+)\.html', href)
            if match:
                vod_id = match.group(1)
            else:
                # 也可能是 /voddetail/xxx.html 格式
                match2 = re.search(r'/voddetail/([^/]+)\.html', href)
                if match2:
                    vod_id = match2.group(1)
            
            if not vod_id or vod_id in seen:
                continue
            seen.add(vod_id)
            
            # 标题
            title_elem = card.select_one('h3')
            title = title_elem.get_text(strip=True) if title_elem else ''
            if not title:
                title = link.get('title', '')
            if not title:
                continue
            
            # 封面图
            pic = ''
            img = card.select_one('.poster img, img')
            if img:
                pic = img.get('data-original') or img.get('src') or ''
            if not pic:
                # 检查 background-image
                style = card.get('style', '')
                bg = re.search(r'url\(([^)]+)\)', style)
                if bg:
                    pic = bg.group(1).strip('"').strip("'")
            
            # 备注（年份、集数等）
            remark = ''
            # 牛剧影院的卡片里有 p 和 span 标签
            p_elem = card.select_one('p')
            if p_elem:
                remark = p_elem.get_text(strip=True)
            span_elem = card.select_one('span')
            if span_elem and not remark:
                remark = span_elem.get_text(strip=True)
            elif span_elem:
                remark += ' ' + span_elem.get_text(strip=True)
            
            results.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": self._fix_url(pic),
                "vod_remarks": remark
            })
        
        return results

    def homeContent(self, filter):
        """首页内容"""
        url = self.site_url + "/"
        resp = self.fetch(url, headers=self.headers)
        video_list = []
        if resp:
            video_list = self._parse_video_list(resp.text)
            video_list = video_list[:30]
        return {"class": self.categories, "list": video_list, "filters": {}}

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        """分类/列表页内容"""
        page = int(pg) if pg else 1
        
        # 根据分类ID构建URL
        # 牛剧影院: /hot.html, /new.html, /duanju.html, /score.html
        type_map = {
            'hot': 'hot',
            'new': 'new', 
            'duanju': 'duanju',
            'score': 'score'
        }
        # 如果是数字ID，尝试用 /vodtype/ 格式
        if tid.isdigit():
            base_url = f"{self.site_url}/vodtype/{tid}"
        else:
            base_name = type_map.get(tid, tid)
            base_url = f"{self.site_url}/{base_name}"
        
        if page == 1:
            url = base_url + ".html"
        else:
            url = base_url + f"-{page}.html"
            # 如果上面不行，尝试带参数
            if page > 1:
                url = base_url + f".html?page={page}"
        
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            # 尝试备用URL
            alt_url = f"{self.site_url}/vodshow/{tid}-{page}.html"
            resp = self.fetch(alt_url, headers=self.headers)
            if not resp:
                return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}
        
        video_list = self._parse_video_list(resp.text)
        
        # 计算总页数
        pagecount = page
        soup = BeautifulSoup(resp.text, 'html.parser')
        pagination = soup.select('.page a, .pagination a, .page-link, .modhd .more')
        if pagination:
            nums = []
            for a in pagination:
                text = a.get_text(strip=True)
                if text.isdigit():
                    nums.append(int(text))
            if nums:
                pagecount = max(nums)
            else:
                # 检查是否有 "更多" 链接，如果有说明可能不止一页
                more_link = soup.select_one('.modhd .more')
                if more_link:
                    # 尝试从 more 链接提取页数
                    more_href = more_link.get('href', '')
                    page_match = re.search(r'-(\d+)\.html', more_href)
                    if page_match:
                        pagecount = int(page_match.group(1))
        
        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount if pagecount >= page else page + 1,
            "limit": 24,
            "total": len(video_list) * pagecount
        }

    def detailContent(self, ids):
        """详情页"""
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/voddetail/{vod_id}.html"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": []}
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 标题
        title_elem = soup.select_one('.hero h1, h1, .vod-title')
        vod_name = title_elem.get_text(strip=True) if title_elem else vod_id
        
        # 封面
        vod_pic = ''
        img_elem = soup.select_one('.poster img, .vod-pic img, .detail-pic img')
        if img_elem:
            vod_pic = img_elem.get('data-original') or img_elem.get('src')
            vod_pic = self._fix_url(vod_pic)
        
        # 简介
        vod_content = ''
        content_elem = soup.select_one('.vod-content, .detail-content, .desc, .hero p.muted')
        if content_elem:
            vod_content = content_elem.get_text(' ', strip=True)
        
        # 演员
        vod_actor = ''
        actor_elem = soup.select_one('.vod-actor, .actor')
        if actor_elem:
            vod_actor = actor_elem.get_text(strip=True).replace('主演：', '').strip()
        
        # 导演
        vod_director = ''
        director_elem = soup.select_one('.vod-director, .director')
        if director_elem:
            vod_director = director_elem.get_text(strip=True).replace('导演：', '').strip()
        
        # 年份
        vod_year = ''
        year_elem = soup.select_one('.vod-year, .year')
        if year_elem:
            vod_year = year_elem.get_text(strip=True).replace('年份：', '').strip()
        
        # 播放列表
        play_from_list = []
        play_url_list = []
        
        # 查找播放列表
        play_blocks = soup.select('.play-list, .vod-play-list, .episode-list, .playlist, ul.playlist')
        if not play_blocks:
            play_blocks = soup.select('.stui-play__list, .module-play-list')
        
        for idx, block in enumerate(play_blocks):
            line_name = f"线路{idx+1}"
            name_elem = block.select_one('.play-title, .line-name, .playlist-title')
            if name_elem:
                line_name = name_elem.get_text(strip=True)
            episodes = []
            for a in block.select('a'):
                href = a.get('href', '')
                if not href or 'javascript:' in href:
                    continue
                ep_name = a.get_text(strip=True) or f"第{len(episodes)+1}集"
                full_url = self._fix_url(href)
                episodes.append(f"{ep_name}${full_url}")
            if episodes:
                play_from_list.append(line_name)
                play_url_list.append('#'.join(episodes))
        
        # 如果没找到播放列表，尝试查找所有 /vodplay/ 链接
        if not play_url_list:
            all_links = soup.select('a[href*="/vodplay/"]')
            if all_links:
                episodes = []
                for a in all_links:
                    href = a.get('href', '')
                    ep_name = a.get_text(strip=True) or f"第{len(episodes)+1}集"
                    full_url = self._fix_url(href)
                    episodes.append(f"{ep_name}${full_url}")
                if episodes:
                    play_from_list.append('默认线路')
                    play_url_list.append('#'.join(episodes))
        
        # 如果还是没有，尝试从 .card 或其他地方提取
        if not play_url_list:
            # 查找所有可能的播放链接
            all_play_links = soup.select('a[href*="/play/"], a[href*="/vodplay/"]')
            if all_play_links:
                episodes = []
                for a in all_play_links[:30]:
                    href = a.get('href', '')
                    ep_name = a.get_text(strip=True) or f"第{len(episodes)+1}集"
                    full_url = self._fix_url(href)
                    episodes.append(f"{ep_name}${full_url}")
                if episodes:
                    play_from_list.append('播放源')
                    play_url_list.append('#'.join(episodes))
        
        vod_play_from = '$$$'.join(play_from_list) if play_from_list else '默认源'
        vod_play_url = '$$$'.join(play_url_list) if play_url_list else f"播放${vod_id}"
        
        result = [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": vod_director,
            "vod_area": "",
            "vod_year": vod_year,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }]
        return {"list": result}

    def searchContent(self, key, quick, pg="1"):
        """搜索"""
        page = int(pg) if pg else 1
        encoded_key = urllib.parse.quote(key)
        
        # 尝试搜索接口
        search_urls = [
            f"{self.site_url}/vodsearch/-------------.html?wd={encoded_key}",
            f"{self.site_url}/search.php?wd={encoded_key}",
            f"{self.site_url}/index.php?m=vod-search&wd={encoded_key}",
        ]
        
        if page > 1:
            for i in range(len(search_urls)):
                search_urls[i] += f"&page={page}"
        
        html_text = ""
        for url in search_urls:
            resp = self.fetch(url, headers=self.headers)
            if resp:
                html_text = resp.text
                break
        
        if not html_text:
            return {"list": [], "page": page, "pagecount": 1}
        
        video_list = self._parse_video_list(html_text)
        return {"list": video_list, "page": page, "pagecount": 1}

    def playerContent(self, flag, id, vipFlags):
        """
        播放解析 - 增强版
        递归解析播放地址
        """
        play_url = self._fix_url(id)
        
        # 如果已经是直链，直接返回
        if re.search(r'\.(m3u8|mp4|flv)(\?|$)', play_url, re.I):
            return {"parse": 0, "url": play_url, "header": self.headers}
        
        headers = dict(self.headers)
        headers['Referer'] = self.site_url + '/'
        max_depth = 8

        def _extract(url, depth):
            if depth > max_depth:
                return None
            if re.search(r'\.(m3u8|mp4|flv)(\?|$)', url, re.I):
                return url

            resp = self.fetch(url, headers=headers)
            if not resp:
                return None
            html = resp.text

            # 1. 提取 player_aaaa 变量
            match = re.search(r'var\s+player_aaaa\s*=\s*({[^;]+});', html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    link = data.get('link', '')
                    if link:
                        next_url = self._fix_url(link)
                        if next_url != url:
                            return _extract(next_url, depth + 1)
                    url_val = data.get('url', '')
                    if url_val:
                        if re.search(r'\.(m3u8|mp4|flv)', url_val, re.I):
                            return url_val
                        next_url = self._fix_url(url_val)
                        if next_url != url:
                            return _extract(next_url, depth + 1)
                except Exception as e:
                    print(f"[牛剧影院] 解析 player_aaaa 失败: {e}")

            # 2. 查找 iframe
            iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html)
            if iframe:
                iframe_url = self._fix_url(iframe.group(1))
                if iframe_url != url:
                    return _extract(iframe_url, depth + 1)

            # 3. video 标签
            video_src = re.search(r'<video[^>]+src="([^"]+)"', html)
            if video_src:
                return video_src.group(1)

            # 4. source 标签
            source_src = re.search(r'<source[^>]+src="([^"]+)"', html)
            if source_src:
                return source_src.group(1)

            # 5. 直接匹配 m3u8/mp4
            direct = re.search(r'(https?://[^\s"\']+\.(m3u8|mp4|flv)[^\s"\']*)', html)
            if direct:
                return direct.group(1)

            # 6. 常见播放变量
            var_patterns = [
                r'var\s+playurl\s*=\s*["\']([^"\']+)["\']',
                r'var\s+url\s*=\s*["\']([^"\']+)["\']',
                r'var\s+video\s*=\s*["\']([^"\']+)["\']',
                r'var\s+src\s*=\s*["\']([^"\']+)["\']',
                r'var\s+playUrl\s*=\s*["\']([^"\']+)["\']',
            ]
            for pat in var_patterns:
                match = re.search(pat, html, re.I)
                if match:
                    p = match.group(1)
                    if re.search(r'\.(m3u8|mp4|flv)', p, re.I):
                        return p
                    # 也可能是链接
                    if p.startswith('http'):
                        next_url = self._fix_url(p)
                        if next_url != url:
                            return _extract(next_url, depth + 1)

            # 7. 查找 /vodplay/ 链接
            next_links = re.findall(r'<a[^>]+href="([^"]*\/vodplay\/[^"]+)"', html)
            for nl in next_links[:5]:
                next_url = self._fix_url(nl)
                if next_url != url:
                    result = _extract(next_url, depth + 1)
                    if result:
                        return result

            return None

        final_url = _extract(play_url, 0)

        if final_url:
            final_url = self._fix_url(final_url)
            if re.search(r'\.(m3u8|mp4|flv)', final_url, re.I):
                return {"parse": 0, "url": final_url, "header": headers}
            else:
                return self.playerContent(flag, final_url, vipFlags)

        # 兜底：交给客户端解析
        return {"parse": 1, "url": play_url, "header": headers}