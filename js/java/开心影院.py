# coding=utf-8
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import json
import time
import urllib.parse
import requests
from urllib.parse import quote
from lxml import etree
import html as html_module

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider(object):
        pass

try:
    requests.packages.urllib3.disable_warnings()
except Exception:
    pass


class Spider(Spider):

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.name = "开心影院"
        self.host = "https://www.kxyy2.cc"
        self.parse_api = "https://kk123.seesee.sbs/player/?url="
        self.header = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                           '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': self.host + '/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        self._session = None
        self._last = {}

    # ================= 基础 =================

    def getName(self):
        return self.name

    def init(self, extend=""):
        return

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.split('?')[0].split('#')[0].lower()
        return any(u.endswith(x) for x in
                   ['.m3u8', '.mp4', '.flv', '.ts', '.mkv', '.avi', '.mov', '.webm', '.mpd'])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return

    def localProxy(self, params):
        return [200, "video/MP2T", {}, ""]

    # ================= 工具 =================

    def _sess(self):
        if self._session is None:
            s = requests.Session()
            s.trust_env = False
            # 设置默认headers
            s.headers.update(self.header)
            self._session = s
        return self._session

    def _get(self, url, timeout=15, headers=None, retry=3):
        for i in range(retry + 1):
            try:
                headers = headers or self.header.copy()
                headers['Referer'] = self.host + '/'
                
                r = self._sess().get(url, headers=headers,
                                     timeout=timeout, verify=False,
                                     allow_redirects=True)
                r.encoding = 'utf-8'
                
                print(f"[{self.name}] 请求: {url[:80]}...")
                print(f"[{self.name}] 状态码: {r.status_code}, 长度: {len(r.text) if r.text else 0}")
                
                if r.status_code == 200 and r.text and len(r.text) > 100:
                    return r.text
                elif r.status_code in [301, 302]:
                    # 重定向
                    redirect_url = r.headers.get('Location', '')
                    if redirect_url:
                        print(f"[{self.name}] 重定向到: {redirect_url}")
                        r = self._sess().get(redirect_url, headers=headers, timeout=timeout, verify=False)
                        r.encoding = 'utf-8'
                        if r.status_code == 200 and r.text and len(r.text) > 100:
                            return r.text
            except Exception as e:
                print(f"[{self.name}] 请求异常: {e}")
            if i < retry:
                time.sleep(0.5 * (i + 1))
        return ''

    def _get_json(self, url, timeout=15, retry=2):
        for i in range(retry + 1):
            try:
                r = self._sess().get(url, headers=self.header, timeout=timeout, verify=False)
                r.encoding = 'utf-8'
                if r.status_code == 200 and r.text:
                    return json.loads(r.text)
            except Exception:
                pass
            if i < retry:
                time.sleep(0.5 * (i + 1))
        return {}

    def _fix(self, url):
        if not url:
            return ''
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            return self.host + url
        return url

    def _txt(self, el):
        if el is None:
            return ''
        try:
            text = ''.join(el.itertext()).strip()
            return html_module.unescape(text) if text else ''
        except:
            return ''

    def _parse_list(self, html):
        out, seen = [], set()
        if not html:
            return out
        try:
            root = etree.HTML(html)
            # 匹配各种卡片样式
            nodes = root.xpath('//div[contains(@class,"card-link")]')
            if not nodes:
                nodes = root.xpath('//div[contains(@class,"module-card-item")]')
            if not nodes:
                nodes = root.xpath('//div[contains(@class,"item")]//a[contains(@href,"/voddetail/")]/..')
            if not nodes:
                nodes = root.xpath('//a[contains(@href,"/voddetail/")]')

            for node in nodes:
                try:
                    a = None
                    if node.tag == 'a' and 'voddetail' in node.get('href', ''):
                        a = node
                    else:
                        a = node.xpath('.//a[contains(@href,"/voddetail/")]')
                        a = a[0] if a else None

                    if a is None:
                        continue

                    href = a.get('href', '')
                    m = re.search(r'/voddetail/(\d+)\.html', href)
                    if not m:
                        m = re.search(r'voddetail/(\d+)', href)
                    if not m:
                        continue
                    vid = m.group(1)

                    name = (a.get('title') or '').strip()
                    if not name:
                        title = node.xpath('.//h3[contains(@class,"card-title")]')
                        if title:
                            name = self._txt(title[0])
                    if not name:
                        img = a.xpath('.//img')
                        if img:
                            name = (img[0].get('alt') or '').strip()
                    if not name:
                        continue

                    pic = ''
                    img = a.xpath('.//img')
                    if img:
                        pic = (img[0].get('data-src') or img[0].get('src') or '')
                        if pic and 'load' in pic:
                            pic = img[0].get('data-src') or ''
                        pic = self._fix(pic)

                    badge = node.xpath('.//span[contains(@class,"badge")]')
                    remark = self._txt(badge[0]) if badge else ''

                    if vid not in seen:
                        seen.add(vid)
                        out.append({
                            "vod_id": vid,
                            "vod_name": name,
                            "vod_pic": pic,
                            "vod_remarks": remark
                        })
                except Exception as e:
                    print(f"[{self.name}] 解析单个条目异常: {e}")
                    continue
        except Exception as e:
            print(f"[{self.name}] 解析列表异常: {e}")
        return out

    def _pagecount(self, html, default=1):
        total = 0
        try:
            for m in re.finditer(r'/vodshow/[\d\-]+-(\d+)\.html', html):
                total = max(total, int(m.group(1)))
            root = etree.HTML(html)
            for a in root.xpath('//a'):
                text = self._txt(a)
                if text == '尾页':
                    href = a.get('href', '')
                    m = re.search(r'/vodshow/[\d\-]+-(\d+)\.html', href)
                    if m:
                        total = max(total, int(m.group(1)))
        except Exception:
            pass
        return total or default

    def _build_category_url(self, tid, pg, extend=None):
        if extend is None:
            extend = {}
        pg = pg or 1
        area = extend.get('area', '')
        by = extend.get('by', '')
        cls = extend.get('class', '')
        year = extend.get('year', '')
        segs = [tid, area, by, cls, '', '', '', '', str(pg), '', '', year]
        segs = [quote(str(s)) for s in segs]
        return f'{self.host}/vodshow/{"-".join(segs)}.html'

    # ================= 首页 =================

    def homeContent(self, filter):
        classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "26", "type_name": "短剧"}
        ]
        result = {
            "class": classes,
            "filters": self.FILTERS,
            "list": self.homeVideoContent().get('list', []),
            "parse": 0,
            "jx": 0
        }
        return result

    def homeVideoContent(self):
        html = self._get(self.host + '/')
        vlist = self._parse_list(html)
        if not vlist:
            html = self._get(self.host + '/vodshow/1-----------.html')
            vlist = self._parse_list(html)
        return {"list": vlist[:30], "parse": 0, "jx": 0}

    # ================= 分类 =================

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if str(pg).isdigit() and int(pg) > 0 else 1
        try:
            if isinstance(extend, str) and extend:
                try:
                    extend = json.loads(extend)
                except Exception:
                    extend = {}
            if not isinstance(extend, dict):
                extend = {}

            url = self._build_category_url(tid, page, extend)
            html = self._get(url)
            vlist = self._parse_list(html)
            pc = self._pagecount(html, 1 if not vlist else page)

            return {
                'list': vlist,
                'page': page,
                'pagecount': pc,
                'limit': len(vlist) or 40,
                'total': (pc * len(vlist)) if vlist else 0
            }
        except Exception as e:
            print(f"[{self.name}] 分类获取失败: {e}")
            return {'list': [], 'page': page, 'pagecount': 1, 'limit': 40, 'total': 0}

    # ================= 详情 =================

    def detailContent(self, ids):
        try:
            if isinstance(ids, (list, tuple)):
                vid = ids[0] if ids else ''
            else:
                vid = ids
                
            vid = str(vid).strip()
            print(f"[{self.name}] 原始ID: {vid}")
            
            # 提取数字ID
            m = re.search(r'(\d+)', vid)
            if not m:
                print(f"[{self.name}] 无法提取数字ID")
                return {'list': [], 'parse': 0, 'jx': 0}
            
            vid = m.group(1)
            
            # 尝试多种URL格式
            urls_to_try = [
                f'{self.host}/voddetail/{vid}.html',
                f'{self.host}/voddetail/{vid}/',
                f'{self.host}/detail/{vid}.html',
            ]
            
            html = ''
            for url in urls_to_try:
                print(f"[{self.name}] 尝试URL: {url}")
                html = self._get(url)
                if html:
                    print(f"[{self.name}] 成功获取HTML，长度: {len(html)}")
                    # 检查是否是详情页
                    if 'vodplay' in html or '播放' in html:
                        print(f"[{self.name}] 确认是详情页")
                        break
                    else:
                        print(f"[{self.name}] 可能不是详情页，继续尝试...")
                        html = ''
            
            if not html:
                print(f"[{self.name}] 所有URL尝试失败")
                return {'list': [], 'parse': 0, 'jx': 0}

            # 从HTML中提取播放链接（这是关键）
            # 开心影院是聚合站，详情页直接包含播放链接
            play_links = []
            # 提取所有vodplay链接
            for match in re.finditer(r'href="([^"]*vodplay[^"]*)"', html):
                play_url = match.group(1)
                if not play_url.startswith('http'):
                    play_url = self._fix(play_url)
                play_links.append(play_url)
                print(f"[{self.name}] 找到播放链接: {play_url}")
            
            # 如果没有vodplay链接，尝试提取iframe
            if not play_links:
                for match in re.finditer(r'<iframe[^>]*src="([^"]*)"', html):
                    iframe_url = match.group(1)
                    if 'player' in iframe_url or 'play' in iframe_url:
                        if not iframe_url.startswith('http'):
                            iframe_url = self._fix(iframe_url)
                        play_links.append(iframe_url)
                        print(f"[{self.name}] 找到iframe: {iframe_url}")
            
            # 提取标题
            title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            if not title_match:
                title_match = re.search(r'<title>([^<]+)</title>', html)
            name = title_match.group(1).strip() if title_match else f"影片{vid}"
            # 清理标题
            name = re.sub(r'\s*[-_|]\s*开心影院.*$', '', name)
            name = re.sub(r'\s*\(\d{4}\)\s*$', '', name)
            name = name.strip()
            
            # 提取海报
            pic = ''
            pic_match = re.search(r'<img[^>]*data-src="([^"]*)"[^>]*class="[^"]*poster[^"]*"', html)
            if not pic_match:
                pic_match = re.search(r'<img[^>]*src="([^"]*)"[^>]*class="[^"]*poster[^"]*"', html)
            if pic_match:
                pic = self._fix(pic_match.group(1))
            
            # 提取简介
            content = ''
            content_match = re.search(r'<div[^>]*class="[^"]*introduction[^"]*"[^>]*>([^<]*(?:<[^>]+>[^<]*</[^>]+>)*[^<]*)</div>', html, re.DOTALL)
            if content_match:
                content = re.sub(r'<[^>]+>', '', content_match.group(1)).strip()
            if content:
                content = content[:500]
            
            # 构建播放数据
            if play_links:
                lines = ['默认线路']
                # 将所有播放链接合并为一条线路
                eps = []
                for idx, url in enumerate(play_links):
                    ep_name = f'第{idx+1}集' if len(play_links) > 1 else '正片'
                    eps.append(f'{ep_name}${url}')
                playlists = ['#'.join(eps)]
                play_from = '$$$'.join(lines)
                play_url = '$$$'.join(playlists)
            else:
                # 没有找到播放链接，使用原始ID
                play_from = '默认线路'
                play_url = f'暂无播放地址${vid}'

            detail = {
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_content": content or "暂无简介",
                "vod_play_from": play_from,
                "vod_play_url": play_url
            }
            
            print(f"[{self.name}] 详情解析成功: {name}, 播放链接数: {len(play_links)}")
            return {'list': [detail], 'parse': 0, 'jx': 0}
            
        except Exception as e:
            print(f"[{self.name}] 详情解析异常: {e}")
            import traceback
            traceback.print_exc()
            return {'list': [], 'parse': 0, 'jx': 0}

    # ================= 播放 =================

    def playerContent(self, flag, id, vipFlags):
        play_url = id if str(id).startswith('http') else self._fix(id)
        headers = {
            'User-Agent': self.header['User-Agent'],
            'Referer': self.host + '/'
        }

        print(f"[{self.name}] 播放请求: {play_url}")

        # 直链直接返回
        if self.isVideoFormat(play_url):
            print(f"[{self.name}] 直链播放: {play_url}")
            return {
                'parse': 0,
                'url': play_url,
                'playUrl': '',
                'header': json.dumps(headers)
            }

        # 对于聚合站的播放链接，直接返回让播放器处理
        # 因为开心影院的播放链接会重定向到真实播放地址
        result = {
            'parse': 1,
            'url': play_url,
            'playUrl': '',
            'header': json.dumps(headers)
        }
        
        try:
            # 尝试获取播放页，提取真实地址
            html = self._get(play_url, timeout=10)
            if html:
                # 查找m3u8
                m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
                if m3u8_match:
                    print(f"[{self.name}] 找到m3u8: {m3u8_match.group(1)}")
                    return {
                        'parse': 0,
                        'url': m3u8_match.group(1),
                        'playUrl': '',
                        'header': json.dumps(headers)
                    }
                
                # 查找mp4
                mp4_match = re.search(r'(https?://[^\s"\']+\.mp4[^\s"\']*)', html)
                if mp4_match:
                    print(f"[{self.name}] 找到mp4: {mp4_match.group(1)}")
                    return {
                        'parse': 0,
                        'url': mp4_match.group(1),
                        'playUrl': '',
                        'header': json.dumps(headers)
                    }
                
                # 查找player_aaaa配置
                player_match = re.search(r'player_aaaa\s*=\s*({[^}]+})', html)
                if player_match:
                    try:
                        config = json.loads(player_match.group(1).replace("'", '"'))
                        url = config.get('url', '')
                        if url:
                            print(f"[{self.name}] 从player_aaaa提取: {url}")
                            if self.isVideoFormat(url):
                                return {
                                    'parse': 0,
                                    'url': url,
                                    'playUrl': '',
                                    'header': json.dumps(headers)
                                }
                            else:
                                result['url'] = url
                    except:
                        pass
        except Exception as e:
            print(f"[{self.name}] 播放解析异常: {e}")

        print(f"[{self.name}] 交给播放器处理: {play_url}")
        return result

    # ================= 搜索 =================

    def searchContent(self, key, quick, pg='1'):
        page = int(pg) if str(pg).isdigit() and int(pg) > 0 else 1
        try:
            kw = str(key).strip()
            if not kw:
                return {'list': [], 'page': page, 'pagecount': 1, 'limit': 20, 'total': 0}

            self._throttle('search', 2)
            url = f'{self.host}/index.php/ajax/suggest?mid=1&wd={quote(kw)}&limit=20&page={page}'
            print(f"[{self.name}] 搜索URL: {url}")
            data = self._get_json(url)

            vlist = []
            for it in data.get('list', []):
                vlist.append({
                    "vod_id": f"voddetail/{it.get('id', '')}.html",
                    "vod_name": it.get('name', ''),
                    "vod_pic": self._fix(it.get('pic', '')),
                    "vod_remarks": ''
                })

            pc = data.get('pagecount', 1 if vlist else 0)
            return {
                'list': vlist,
                'page': page,
                'pagecount': pc,
                'limit': len(vlist) or 20,
                'total': pc * (len(vlist) or 20)
            }
        except Exception as e:
            print(f"[{self.name}] 搜索异常: {e}")
            return {'list': [], 'page': page, 'pagecount': 1, 'limit': 20, 'total': 0}

    # ================= 筛选器 =================

    FILTERS = json.loads(r'''{"1": [{"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "科幻", "v": "科幻"}, {"n": "剧情", "v": "剧情"}, {"n": "惊悚", "v": "惊悚"}, {"n": "爱情", "v": "爱情"}, {"n": "古装", "v": "古装"}, {"n": "动作", "v": "动作"}, {"n": "悬疑", "v": "悬疑"}, {"n": "犯罪", "v": "犯罪"}, {"n": "谍战", "v": "谍战"}, {"n": "历史", "v": "历史"}, {"n": "喜剧", "v": "喜剧"}, {"n": "奇幻", "v": "奇幻"}, {"n": "家庭", "v": "家庭"}, {"n": "青春", "v": "青春"}, {"n": "冒险", "v": "冒险"}, {"n": "纪录", "v": "纪录"}, {"n": "动画", "v": "动画"}, {"n": "人物", "v": "人物"}, {"n": "文化", "v": "文化"}, {"n": "其他", "v": "其他"}]}, {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "中国香港", "v": "中国香港"}, {"n": "中国台湾", "v": "中国台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}, {"n": "泰国", "v": "泰国"}, {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"}, {"n": "意大利", "v": "意大利"}, {"n": "印度", "v": "印度"}, {"n": "马来西亚", "v": "马来西亚"}]}, {"key": "year", "name": "年份", "value": [{"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"}, {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"}, {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"}, {"n": "2009", "v": "2009"}, {"n": "2008", "v": "2008"}, {"n": "2007", "v": "2007"}, {"n": "2006", "v": "2006"}, {"n": "2005", "v": "2005"}, {"n": "2004", "v": "2004"}, {"n": "2003", "v": "2003"}, {"n": "2002", "v": "2002"}, {"n": "2001", "v": "2001"}, {"n": "2000", "v": "2000"}, {"n": "90年代", "v": "90年代"}, {"n": "80年代", "v": "80年代"}, {"n": "70年代", "v": "70年代"}, {"n": "更早", "v": "其他"}]}, {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "time"}, {"n": "最热", "v": "hits_week"}, {"n": "评分", "v": "douban_score"}]}], "2": [{"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "爱情", "v": "爱情"}, {"n": "古装", "v": "古装"}, {"n": "悬疑", "v": "悬疑"}, {"n": "都市", "v": "都市"}, {"n": "喜剧", "v": "喜剧"}, {"n": "战争", "v": "战争"}, {"n": "剧情", "v": "剧情"}, {"n": "青春", "v": "青春"}, {"n": "历史", "v": "历史"}, {"n": "网剧", "v": "网剧"}, {"n": "奇幻", "v": "奇幻"}, {"n": "冒险", "v": "冒险"}, {"n": "励志", "v": "励志"}, {"n": "犯罪", "v": "犯罪"}, {"n": "商战", "v": "商战"}, {"n": "恐怖", "v": "恐怖"}, {"n": "穿越", "v": "穿越"}, {"n": "农村", "v": "农村"}, {"n": "人物", "v": "人物"}, {"n": "商业", "v": "商业"}, {"n": "生活", "v": "生活"}, {"n": "其他", "v": "其他"}]}, {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "中国香港", "v": "中国香港"}, {"n": "中国台湾", "v": "中国台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}, {"n": "泰国", "v": "泰国"}, {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"}, {"n": "意大利", "v": "意大利"}]}, {"key": "year", "name": "年份", "value": [{"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"}, {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"}, {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"}, {"n": "2009", "v": "2009"}, {"n": "2008", "v": "2008"}, {"n": "2007", "v": "2007"}, {"n": "2006", "v": "2006"}, {"n": "2005", "v": "2005"}, {"n": "2004", "v": "2004"}, {"n": "2003", "v": "2003"}, {"n": "2002", "v": "2002"}, {"n": "2001", "v": "2001"}, {"n": "2000", "v": "2000"}, {"n": "90年代", "v": "90年代"}, {"n": "80年代", "v": "80年代"}, {"n": "70年代", "v": "70年代"}, {"n": "更早", "v": "其他"}]}, {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "time"}, {"n": "最热", "v": "hits_week"}, {"n": "评分", "v": "douban_score"}]}], "3": [{"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "真人秀", "v": "真人秀"}, {"n": "脱口秀", "v": "脱口秀"}, {"n": "喜剧", "v": "喜剧"}, {"n": "音乐", "v": "音乐"}, {"n": "爱情", "v": "爱情"}, {"n": "家庭", "v": "家庭"}, {"n": "歌舞", "v": "歌舞"}]}, {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "港台", "v": "港台"}, {"n": "韩国", "v": "韩国"}, {"n": "欧美", "v": "欧美"}, {"n": "其他", "v": "其他"}]}, {"key": "year", "name": "年份", "value": [{"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"}, {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"}, {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"}, {"n": "2009", "v": "2009"}, {"n": "2008", "v": "2008"}, {"n": "2007", "v": "2007"}, {"n": "2006", "v": "2006"}, {"n": "2005", "v": "2005"}, {"n": "2004", "v": "2004"}, {"n": "2003", "v": "2003"}, {"n": "2002", "v": "2002"}, {"n": "2001", "v": "2001"}, {"n": "2000", "v": "2000"}, {"n": "90年代", "v": "90年代"}, {"n": "80年代", "v": "80年代"}, {"n": "70年代", "v": "70年代"}, {"n": "更早", "v": "其他"}]}, {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "time"}, {"n": "最热", "v": "hits_week"}, {"n": "评分", "v": "douban_score"}]}], "4": [{"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "少年", "v": "少年"}, {"n": "热血", "v": "热血"}, {"n": "科幻", "v": "科幻"}, {"n": "冒险", "v": "冒险"}, {"n": "动画", "v": "动画"}, {"n": "爱情", "v": "爱情"}, {"n": "奇幻", "v": "奇幻"}, {"n": "武侠", "v": "武侠"}, {"n": "悬疑", "v": "悬疑"}, {"n": "惊悚", "v": "惊悚"}, {"n": "剧情", "v": "剧情"}, {"n": "音乐", "v": "音乐"}, {"n": "恐怖", "v": "恐怖"}, {"n": "喜剧", "v": "喜剧"}, {"n": "儿童", "v": "儿童"}]}, {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "日本", "v": "日本"}]}, {"key": "year", "name": "年份", "value": [{"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"}, {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"}, {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"}, {"n": "2009", "v": "2009"}, {"n": "2008", "v": "2008"}, {"n": "2007", "v": "2007"}, {"n": "2006", "v": "2006"}, {"n": "2005", "v": "2005"}, {"n": "2004", "v": "2004"}, {"n": "2003", "v": "2003"}, {"n": "2002", "v": "2002"}, {"n": "2001", "v": "2001"}, {"n": "2000", "v": "2000"}, {"n": "90年代", "v": "90年代"}, {"n": "80年代", "v": "80年代"}, {"n": "70年代", "v": "70年代"}, {"n": "更早", "v": "其他"}]}, {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "time"}, {"n": "最热", "v": "hits_week"}, {"n": "评分", "v": "douban_score"}]}], "26": [{"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "短剧", "v": "短剧"}]}, {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}]}, {"key": "year", "name": "年份", "value": [{"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"}, {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}]}, {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "time"}, {"n": "最热", "v": "hits_week"}, {"n": "评分", "v": "douban_score"}]}]}''')