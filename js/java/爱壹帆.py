# -*- coding: utf-8 -*-
# 爱壹帆 - https://www.iyf.lv/
import re
import sys
import json
import time
from urllib.parse import quote, unquote
from pyquery import PyQuery as pq
sys.path.append('..')
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        pass

    def getName(self):
        return "爱壹帆"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host = 'https://www.iyf.lv'

    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,ko;q=0.5",
        # 以下安全头建议保留，很多网站会检查
        "sec-ch-ua": "\"Chromium\";v=\"142\", \"Microsoft Edge\";v=\"142\", \"Not_A Brand\";v=\"99\"",
        "sec-ch-ua-mobile": "?0", 
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none"
    }


    def homeContent(self, filter):
        """获取首页内容和分类"""
        try:
            response = self.fetch_with_encoding(self.host, headers=self.headers)
            doc = self.getpq(response.text)

            result = {}
            classes = []

            # 获取分类导航 - 基于浏览器分析，分类链接包含/t/
            nav_items = doc('.swiper-slide a[href*="/t/"]')

            for item in nav_items.items():
                text = item.text().strip()
                href = item.attr('href')
                if text and href and '/t/' in href:
                    # 提取分类ID
                    type_id = href.split('/t/')[-1].rstrip('/')
                    if type_id.isdigit():
                        classes.append({
                            'type_name': text,
                            'type_id': type_id
                        })

            # 获取首页视频列表 - 优先查找包含图片的视频链接
            videos = []
            seen_ids = set()  # 用于去重

            # 优先查找包含图片的视频链接（主要的视频项）
            video_links = doc('a[href*="/iyftv/"]').filter(lambda _, e: pq(e).find('img').length > 0)

            for link in video_links.items():
                try:
                    href = link.attr('href') or ''
                    if not href:
                        continue

                    # 提取视频ID
                    vod_id = href.split('/iyftv/')[-1].rstrip('/')
                    if not vod_id or vod_id in seen_ids:
                        continue

                    seen_ids.add(vod_id)  # 添加到已见集合

                    # 获取标题 - 优先从图片alt属性获取（最准确）
                    title = ''
                    img_elem = link.find('img')
                    if img_elem:
                        title = img_elem.attr('alt') or ''

                    # 如果图片alt为空，尝试其他方式
                    if not title:
                        title = link.attr('title') or ''
                    if not title:
                        # 从链接文本获取，但要过滤掉无关文本
                        link_text = link.text().strip()
                        if link_text and link_text not in ['正片', '详情', '播放', '观看']:
                            title = link_text

                    if not title:
                        continue

                    # 获取图片 - 优先获取data-original（真实图片），避免懒加载占位图
                    pic = ''
                    if img_elem:
                        pic = img_elem.attr('data-original') or img_elem.attr('data-src') or img_elem.attr('src') or ''
                        if pic and not pic.startswith('http'):
                            pic = self.host + pic if pic.startswith('/') else ''

                    # 获取备注信息 - 查找可能的备注元素
                    remarks = ''
                    # 查找父容器中的备注信息
                    parent = link.parent()
                    if parent:
                        # 查找集数信息
                        episode_elem = parent.find('.episode, .status, .note')
                        if episode_elem:
                            remarks = episode_elem.text().strip()
                        else:
                            # 查找包含"第"、"集"、"期"等关键字的文本
                            parent_text = parent.text()
                            import re
                            episode_match = re.search(r'第\d+[集期]|更新至|完结|正片', parent_text)
                            if episode_match:
                                remarks = episode_match.group()

                    videos.append({
                        'vod_id': vod_id,
                        'vod_name': self.fix_encoding(title),
                        'vod_pic': pic,
                        'vod_year': '',
                        'vod_remarks': self.fix_encoding(remarks)
                    })
                except Exception as e:
                    self.log(f"解析视频项时出错: {e}")
                    continue

            result['class'] = classes
            result['list'] = videos
            return result

        except Exception as e:
            self.log(f"获取首页内容时出错: {e}")
            return {'class': [], 'list': []}

    def homeVideoContent(self):
        """获取推荐视频"""
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        """获取分类内容"""
        try:
            # 构建分类URL
            url = f"{self.host}/t/{tid}/"
            if int(pg) > 1:
                url = f"{self.host}/t/{tid}/page/{pg}/"

            response = self.fetch_with_encoding(url, headers=self.headers)
            doc = self.getpq(response.text)

            # 获取视频列表 - 优先查找包含图片的视频链接
            videos = []
            seen_ids = set()  # 用于去重

            # 优先查找包含图片的视频链接（主要的视频项）
            video_links = doc('a[href*="/iyftv/"]').filter(lambda _, e: pq(e).find('img').length > 0)

            for link in video_links.items():
                try:
                    href = link.attr('href') or ''
                    if not href:
                        continue

                    # 提取视频ID
                    vod_id = href.split('/iyftv/')[-1].rstrip('/')
                    if not vod_id or vod_id in seen_ids:
                        continue

                    seen_ids.add(vod_id)  # 添加到已见集合

                    # 获取标题 - 优先从图片alt属性获取（最准确）
                    title = ''
                    img_elem = link.find('img')
                    if img_elem:
                        title = img_elem.attr('alt') or ''

                    # 如果图片alt为空，尝试其他方式
                    if not title:
                        title = link.attr('title') or ''
                    if not title:
                        # 从链接文本获取，但要过滤掉无关文本
                        link_text = link.text().strip()
                        if link_text and link_text not in ['正片', '详情', '播放', '观看']:
                            title = link_text

                    if not title:
                        continue

                    # 获取图片 - 优先获取data-original（真实图片），避免懒加载占位图
                    pic = ''
                    if img_elem:
                        pic = img_elem.attr('data-original') or img_elem.attr('data-src') or img_elem.attr('src') or ''
                        if pic and not pic.startswith('http'):
                            pic = self.host + pic if pic.startswith('/') else ''

                    # 获取备注信息 - 查找集数或状态信息
                    remarks = ''
                    parent = link.parent()
                    if parent:
                        # 查找集数信息
                        episode_elem = parent.find('.episode, .status, .note')
                        if episode_elem:
                            remarks = episode_elem.text().strip()
                        else:
                            # 查找包含"第"、"集"、"期"等关键字的文本
                            parent_text = parent.text()
                            import re
                            episode_match = re.search(r'第\d+[集期]|更新至|完结|正片', parent_text)
                            if episode_match:
                                remarks = episode_match.group()

                    videos.append({
                        'vod_id': vod_id,
                        'vod_name': self.fix_encoding(title),
                        'vod_pic': pic,
                        'vod_year': '',
                        'vod_remarks': self.fix_encoding(remarks)
                    })
                except Exception as e:
                    self.log(f"解析分类视频项时出错: {e}")
                    continue

            result = {
                'list': videos,
                'page': pg,
                'pagecount': 1,  # 设置一个较大的值
                'limit': 80,
                'total': 999999
            }
            return result

        except Exception as e:
            self.log(f"获取分类内容时出错: {e}")
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 80, 'total': 0}

    
    def detailContent(self, ids):
        """获取视频详情"""
        try:
            vod_id = ids[0]
            url = f"{self.host}/iyftv/{vod_id}/"

            response = self.fetch_with_encoding(url, headers=self.headers)
            doc = self.getpq(response.text)

            # 获取标题
            title_elem = doc('h1')
            title = self.fix_encoding(title_elem.text()) if title_elem else ''

            # 获取图片
            pic = ''
            img_elem = doc('.module-item-pic img')
            if img_elem:
                pic = img_elem.attr('data-original') or img_elem.attr('src') or ''
                if pic and not pic.startswith('http'):
                    pic = self.host + pic if pic.startswith('/') else ''

            # 获取基本信息
            year = ''
            region = ''
            genres = []
            director = []
            actors = []
            duration = ''
            language = ''
            release_date = ''
            update_date = ''
            remark = ''
            douban_link = ''

            # 提取标签信息
            tag_div = doc('.module-info-tag')
            if tag_div:
                tag_links = tag_div.find('a')
                if tag_links.length >= 1:
                    year = tag_links.eq(0).text().strip()
                if tag_links.length >= 2:
                    region = tag_links.eq(1).text().strip()
                if tag_links.length >= 3:
                    # 类型可能有多个，用斜杠分隔
                    genre_text = tag_links.eq(2).parent().text()
                    genres = [g.strip() for g in genre_text.split('/') if g.strip()]

            # 提取详细信息项
            info_items = doc('.module-info-item')
            for item in info_items.items():
                label_span = item.find('.module-info-item-title')
                if not label_span:
                    continue
                    
                label = label_span.text().strip().replace('：', '')
                content_div = item.find('.module-info-item-content')
                
                if not content_div:
                    continue
                    
                if label == '导演':
                    director_links = content_div.find('a')
                    director = [self.fix_encoding(link.text().strip()) for link in director_links.items() if link.text().strip()]
                elif label == '主演':
                    actor_links = content_div.find('a')
                    actors = [self.fix_encoding(link.text().strip()) for link in actor_links.items() if link.text().strip()]
                elif label == '片长':
                    duration = content_div.text().strip()
                elif label == '语言':
                    language = content_div.text().strip()
                elif label == '上映':
                    release_date = content_div.text().strip()
                elif label == '更新':
                    update_date = content_div.text().strip()
                elif label == '备注':
                    remark = content_div.text().strip()
                elif label == '豆瓣':
                    douban_link_elem = content_div.find('a')
                    if douban_link_elem:
                        douban_link = douban_link_elem.attr('href') or ''

            # 获取剧情简介
            content = ''
            intro_div = doc('.module-info-introduction-content')
            if intro_div:
                intro_p = intro_div.find('p')
                if intro_p:
                    content = self.fix_encoding(intro_p.text().strip())

            # 保持原来的播放源解析方式
            play_from = []
            play_url = []

            # 查找播放源标签 - 基于浏览器分析，可能是.module-tab-item
            tab_selectors = ['.module-tab-item', '.tab-item', '.play-source', '.source-tab']
            playlist_selectors = ['.module-play-list', '.play-list', '.episode-list']

            tabs = None
            playlists = None

            for selector in tab_selectors:
                tabs = doc(selector)
                if tabs:
                    break

            for selector in playlist_selectors:
                playlists = doc(selector)
                if playlists:
                    break

            if tabs and playlists:
                for i, tab in enumerate(tabs.items()):
                    # 获取播放源名称
                    source_name = self.fix_encoding(tab.text().strip())

                    if source_name:
                        play_from.append(source_name)

                        # 获取对应的播放列表
                        episodes = []
                        if i < len(playlists):
                            episode_items = playlists.eq(i).find('a')
                            for ep in episode_items.items():
                                ep_title = self.fix_encoding(ep.text().strip())
                                ep_href = ep.attr('href')
                                if ep_title and ep_href:
                                    episodes.append(f"{ep_title}${ep_href}")

                        play_url.append('#'.join(episodes))
            else:
                # 如果没有找到播放源，使用默认播放按钮
                play_buttons = doc('.main-btn, .play-btn, a[href*="/iyfplay/"]')
                for btn in play_buttons.items():
                    btn_href = btn.attr('href') or ''
                    if '/iyfplay/' in btn_href:
                        play_from.append('播放源1')
                        play_url.append(f"立即播放${btn_href}")
                        break

            # 构建返回数据 - 保持原来的播放字段格式
            vod = {
                'vod_id': vod_id,
                'vod_name': title,
                'vod_pic': pic,
                'vod_year': year,
                'vod_area': region,
                'vod_remarks': remark,
                'vod_actor': ','.join(actors),
                'vod_director': ','.join(director),
                'vod_content': content,
                'vod_play_from': '$$$'.join(play_from) if play_from else '播放源1',
                'vod_play_url': '$$$'.join(play_url) if play_url else f"立即播放${url}"
            }

            return {'list': [vod]}

        except Exception as e:
            self.log(f"获取视频详情时出错: {e}")
            # 返回基本详情
            return {'list': [{
                'vod_id': ids[0],
                'vod_name': '未知',
                'vod_pic': '',
                'vod_play_from': '播放源1',
                'vod_play_url': f"立即播放${self.host}/iyftv/{ids[0]}/"
            }]}

            
    def searchContent(self, key, quick, pg="1"):
        """搜索内容"""
        try:
            # 使用正确的搜索URL格式
            search_url = f"{self.host}/s/-------------/"
            params = {'wd': key}

            response = self.fetch_with_encoding(search_url, params=params, headers=self.headers)
            doc = self.getpq(response.text)

            # 获取搜索结果 - 基于搜索页面的实际结构
            videos = []
            seen_ids = set()  # 用于去重

            # 搜索页面的结构：每个视频在一个容器中，包含图片链接和标题链接
            # 优先查找包含图片的视频链接（主要的视频项）
            video_containers = doc('a[href*="/iyftv/"]').filter(lambda _, e: pq(e).find('img').length > 0)

            for link in video_containers.items():
                try:
                    href = link.attr('href') or ''
                    if not href:
                        continue

                    # 提取视频ID
                    vod_id = href.split('/iyftv/')[-1].rstrip('/')
                    if not vod_id or vod_id in seen_ids:
                        continue

                    seen_ids.add(vod_id)  # 添加到已见集合

                    # 获取标题 - 优先从图片alt属性获取
                    title = ''
                    img_elem = link.find('img')
                    if img_elem:
                        title = img_elem.attr('alt') or ''

                    # 如果图片alt为空，查找同级或父级的标题链接
                    if not title:
                        # 查找父容器中的标题链接
                        parent_container = link.parent()
                        if parent_container:
                            title_link = parent_container.find(f'a[href="/iyftv/{vod_id}/"] strong')
                            if title_link:
                                title = title_link.text().strip()
                            else:
                                # 查找其他可能的标题元素
                                title_elem = parent_container.find(f'a[href="/iyftv/{vod_id}/"]').not_(link)
                                if title_elem:
                                    title = title_elem.text().strip()

                    if not title:
                        continue

                    # 获取图片 - 优先获取data-original（真实图片），避免懒加载占位图
                    pic = ''
                    if img_elem:
                        pic = img_elem.attr('data-original') or img_elem.attr('data-src') or img_elem.attr('src') or ''
                        if pic and not pic.startswith('http'):
                            pic = self.host + pic if pic.startswith('/') else ''

                    # 获取备注信息 - 查找集数或状态信息
                    remarks = ''
                    parent_container = link.parent()
                    if parent_container:
                        # 查找集数信息（通常在图片上方的标签中）
                        episode_elem = parent_container.find('.episode, .status, .note')
                        if episode_elem:
                            remarks = episode_elem.text().strip()
                        else:
                            # 查找包含"第"、"集"、"期"等关键字的文本
                            parent_text = parent_container.text()
                            import re
                            episode_match = re.search(r'第\d+[集期]|更新至|完结|正片', parent_text)
                            if episode_match:
                                remarks = episode_match.group()

                    videos.append({
                        'vod_id': vod_id,
                        'vod_name': self.fix_encoding(title),
                        'vod_pic': pic,
                        'vod_year': '',
                        'vod_remarks': self.fix_encoding(remarks)
                    })
                except Exception as e:
                    self.log(f"解析搜索结果时出错: {e}")
                    continue

            return {'list': videos, 'page': pg}

        except Exception as e:
            self.log(f"搜索时出错: {e}")
            return {'list': [], 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        """获取播放地址"""
        try:
            # 播放页面URL
            play_url = f"{self.host}{id}"

            response = self.fetch_with_encoding(play_url, headers=self.headers)
            doc = self.getpq(response.text)

            # 查找播放器配置
            scripts = doc('script')
            for script in scripts.items():
                script_text = script.text()
                if 'player' in script_text and ('url' in script_text):
                    # 尝试提取播放地址
                    url_match = re.search(r'"url"\s*:\s*"([^"]+)"', script_text)
                    if url_match:
                        video_url = url_match.group(1)
                        return {
                            'parse': 0,
                            'url': video_url,
                            'header': self.headers
                        }

            # 如果没有找到直接播放地址，返回播放页面让系统解析
            return {
                'parse': 1,
                'url': play_url,
                'header': self.headers
            }

        except Exception as e:
            self.log(f"获取播放地址时出错: {e}")
            return {
                'parse': 1,
                'url': f"{self.host}{id}",
                'header': self.headers
            }

    def localProxy(self, param):
        pass

    def fix_encoding(self, text):
        """修复UTF-8编码问题 - 加强版"""
        if not text:
            return text

        try:
            # 扩展的乱码特征检测
            garbled_patterns = [
                # 常见的UTF-8乱码模式
                '\u00e4\u00b8', '\u00e5', '\u00e6', '\u00e7', '\u00e8', '\u00e9',
                '\u00c3\u00a4', '\u00c3\u00a5', '\u00c3\u00a6', '\u00c3\u00a7',
                '\u00ef\u00bc', '\u00e2\u0080', '\u00e2\u0084',
                # 更多乱码模式
                '\u00c2\u00a0', '\u00c2\u00b7', '\u00c2\u00bb',
                '\u00e2\u0082', '\u00e2\u0086', '\u00e2\u0088',
                # 特殊字符乱码
                '\u00c3\u0097', '\u00c3\u00b7', '\u00c2\u00b1'
            ]

            has_garbled = any(pattern in text for pattern in garbled_patterns)

            # 额外检查：如果文本包含大量非ASCII字符但没有中文，可能是乱码
            if not has_garbled:
                non_ascii_count = sum(1 for c in text if ord(c) > 127)
                chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
                if non_ascii_count > 0 and chinese_count == 0 and non_ascii_count > len(text) * 0.3:
                    has_garbled = True

            if has_garbled:
                self.log(f"检测到编码问题，尝试修复: {text[:50]}...")

                # 方法1: 尝试Latin1->UTF-8转换
                try:
                    fixed = text.encode('latin1').decode('utf-8')
                    # 检查是否修复成功（包含中文字符且减少了乱码字符）
                    if re.search(r'[\u4e00-\u9fff]', fixed):
                        self.log("使用Latin1->UTF-8修复成功")
                        return fixed
                except Exception as e:
                    self.log(f"Latin1->UTF-8修复失败: {e}")

                # 方法2: 尝试其他编码转换
                encodings = ['cp1252', 'iso-8859-1', 'windows-1252']
                for encoding in encodings:
                    try:
                        fixed = text.encode(encoding).decode('utf-8')
                        if re.search(r'[\u4e00-\u9fff]', fixed):
                            self.log(f"使用{encoding}->UTF-8修复成功")
                            return fixed
                    except:
                        continue

                # 方法3: 尝试直接处理常见的乱码替换
                try:
                    # 常见乱码字符替换表
                    replacements = {
                        '\u00e4\u00b8\u00ad': '中',
                        '\u00e6\u0096\u0087': '文',
                        '\u00e5\u00bd\u00b1': '影',
                        '\u00e8\u00a7\u0086': '视',
                        '\u00e9\u00a2\u0091': '频',
                    }

                    fixed = text
                    for garbled, correct in replacements.items():
                        fixed = fixed.replace(garbled, correct)

                    if fixed != text and re.search(r'[\u4e00-\u9fff]', fixed):
                        self.log("使用字符替换修复成功")
                        return fixed
                except:
                    pass

                self.log("编码修复失败，返回原文本")

            return text

        except Exception as e:
            self.log(f"编码修复异常: {e}")
            return text

    def fetch_with_encoding(self, url, **kwargs):
        """带编码处理的请求方法"""
        try:
            response = self.fetch(url, **kwargs)
            # 确保使用UTF-8编码
            response.encoding = 'utf-8'
            return response
        except Exception as e:
            self.log(f"请求失败: {e}")
            raise

    def getpq(self, text):
        """安全的pyquery解析"""
        try:
            return pq(text)
        except Exception as e:
            self.log(f"pyquery解析出错: {e}")
            try:
                return pq(text.encode('utf-8'))
            except:
                return pq('')