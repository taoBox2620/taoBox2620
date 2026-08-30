#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
西瓜影院 TVBox Python 爬虫
站点: https://www.xiguazx.cc
备用: www.xiguadh.com | www.bzzdyy.com
框架: maccms (苹果CMS) HTML 解析
继承: base.spider.Spider
兼容: FongMi TV / OK影视 / webhome
"""

import json
import re
import sys
import urllib.parse

sys.path.append("..")
sys.path.append(".")

# ---- requests 兜底（沙箱无 requests 时可用） ----
try:
    import requests
except ImportError:
    requests = None

# ---- Spider 基类: 优先框架注入, 沙箱兜底 ----
try:
    from base.spider import Spider as _BaseSpider
    HAS_BASE = True
except Exception:
    HAS_BASE = False

    class _BaseSpider:
        """沙箱兜底基类，保证脚本可独立运行"""

        def __init__(self):
            pass

        def post(self, url, **kwargs):
            if requests is None:
                raise RuntimeError("requests 未安装")
            return requests.post(url, **kwargs)

        def fetch(self, url, headers=None, **kwargs):
            if requests is None:
                raise RuntimeError("requests 未安装")
            hdrs = headers or {}
            return requests.get(url, headers=hdrs, **kwargs)


# ---- 常量 ----
HOST = "https://www.xiguazx.cc"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

# 分类结构: 6个大类，每个大类配置子分类筛选
CATEGORIES = [
    {"type_id": "20", "type_name": "电影"},
    {"type_id": "37", "type_name": "连续剧"},
    {"type_id": "43", "type_name": "动漫"},
    {"type_id": "45", "type_name": "综艺"},
    {"type_id": "47", "type_name": "B站"},
    {"type_id": "60", "type_name": "人人专区"},
]

FILTERS = {
    "20": [
        {
            "key": "class",
            "name": "类型",
            "value": [
                {"n": "全部", "v": "20"},
                {"n": "动作片", "v": "21"},
                {"n": "喜剧片", "v": "22"},
                {"n": "爱情片", "v": "23"},
                {"n": "科幻片", "v": "24"},
                {"n": "恐怖片", "v": "25"},
                {"n": "剧情片", "v": "26"},
                {"n": "战争片", "v": "27"},
                {"n": "惊悚片", "v": "28"},
                {"n": "犯罪片", "v": "29"},
                {"n": "冒险片", "v": "30"},
                {"n": "动画片", "v": "31"},
                {"n": "悬疑片", "v": "32"},
                {"n": "武侠片", "v": "33"},
                {"n": "奇幻片", "v": "34"},
                {"n": "纪录片", "v": "35"},
                {"n": "其他片", "v": "36"},
            ],
        },
    ],
    "37": [
        {
            "key": "class",
            "name": "类型",
            "value": [
                {"n": "全部", "v": "37"},
                {"n": "国产剧", "v": "38"},
                {"n": "港台剧", "v": "39"},
                {"n": "欧美剧", "v": "40"},
                {"n": "日韩剧", "v": "41"},
                {"n": "其他剧", "v": "42"},
            ],
        },
    ],
    "43": [
        {
            "key": "class",
            "name": "类型",
            "value": [
                {"n": "全部", "v": "43"},
                {"n": "动漫", "v": "44"},
            ],
        },
    ],
    "45": [
        {
            "key": "class",
            "name": "类型",
            "value": [
                {"n": "全部", "v": "45"},
                {"n": "综艺", "v": "46"},
            ],
        },
    ],
    "47": [
        {
            "key": "class",
            "name": "类型",
            "value": [
                {"n": "全部", "v": "47"},
                {"n": "番剧(B站)", "v": "48"},
                {"n": "国创(B站)", "v": "49"},
                {"n": "电影(B站)", "v": "50"},
                {"n": "电视剧(B站)", "v": "51"},
            ],
        },
    ],
    "60": [
        {
            "key": "class",
            "name": "类型",
            "value": [
                {"n": "全部", "v": "60"},
                {"n": "连续剧", "v": "61"},
                {"n": "电影", "v": "62"},
                {"n": "动漫", "v": "63"},
                {"n": "综艺", "v": "64"},
                {"n": "纪录片", "v": "66"},
            ],
        },
    ],
}


class Spider(_BaseSpider):
    """西瓜影院 TVBox 爬虫主类"""

    def init(self, ext=""):
        """框架初始化钩子（FongMi/OK影视/webhome 必须实现）"""
        pass

    def destroy(self):
        """框架销毁钩子，释放资源"""
        pass

    def getName(self):
        return "西瓜影院"

    def isVideoFormat(self, url):
        """判断 url 是否为可直接播放的视频流"""
        low = url.lower().split("?")[0]
        return low.endswith((".m3u8", ".mp4", ".flv", ".avi", ".mov", ".wmv", ".mkv"))

    def _clean_pic(self, url):
        """处理封面图代理 /img.php?url=xxx -> 提取实际地址"""
        if not url:
            return ""
        if "/img.php?url=" in url:
            raw = url.split("/img.php?url=", 1)[-1]
            return urllib.parse.unquote(raw)
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return HOST + url
        return url

    def _fetch(self, url):
        """统一请求方法，返回 HTML 文本。禁用 Brotli 防止乱码"""
        headers = {
            "User-Agent": UA,
            "Referer": HOST,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate",  # 禁用 br(Brotli)
        }
        try:
            if HAS_BASE:
                # 框架基类 fetch 方法
                try:
                    resp = self.fetch(url, headers=headers)
                except TypeError:
                    # 兼容基类 fetch 可能不接 headers 关键字
                    resp = self.fetch(url)
                return resp.text if hasattr(resp, "text") else str(resp)
            elif requests:
                resp = requests.get(url, headers=headers, timeout=15)
                return resp.text
        except Exception as e:
            print(f"[西瓜影院] 请求失败 {url}: {e}", file=sys.stderr)
            return ""

    def homeContent(self, filter=False):
        """首页分类栏 + 子分类筛选"""
        result = {"class": CATEGORIES}
        if filter:
            result["filters"] = FILTERS
        return result

    def homeVideoContent(self):
        """首页推荐视频（从首页抓取热播推荐）"""
        html = self._fetch(HOST + "/")
        videos = []
        # 匹配首页推荐区的视频卡片
        cards = re.findall(
            r'<div class="stui-vodlist__box">\s*'
            r'<a class="stui-vodlist__thumb[^"]*"[^>]*'
            r'href="/index\.php/vod/detail/id/(\d+)\.html"[^>]*'
            r'title="([^"]*)"[^>]*'
            r'data-original="([^"]*)"[^>]*>.*?'
            r'<span class="pic-text1[^"]*"><b>([^<]*)</b></span>\s*'
            r'<span class="pic-text[^"]*"><b>([^<]*)</b></span>.*?'
            r'<h4 class="title[^"]*">.*?</h4>\s*'
            r'<p class="text[^"]*">([^<]*)</p>',
            html,
            re.S,
        )
        for vid, title, pic, cat, remark, actor in cards:
            videos.append(
                {
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": self._clean_pic(pic),
                    "vod_remarks": remark,
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": actor.strip() if actor else "",
                }
            )
        return {"list": videos}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        """分类列表页 (兼容 FongMi 4参数 / webhome 3参数)"""
        page = int(pg) if pg else 1
        if extend is None:
            extend = {}

        # 筛选子分类: extend 中 class 的值优先，否则用 tid
        class_id = str(tid)
        if extend and isinstance(extend, dict):
            class_val = extend.get("class") or extend.get("cate")
            if class_val:
                class_id = str(class_val)

        url = f"{HOST}/index.php/vod/show/id/{class_id}/page/{page}.html"
        html = self._fetch(url)

        videos = []
        seen_ids = set()

        # 匹配列表页视频卡片
        cards = re.findall(
            r'<a class="stui-vodlist__thumb[^"]*"[^>]*'
            r'href="/index\.php/vod/detail/id/(\d+)\.html"[^>]*'
            r'title="([^"]*)"[^>]*'
            r'data-original="([^"]*)"[^>]*>.*?'
            r'<span class="pic-text1[^"]*"><b>([^<]*)</b></span>\s*'
            r'<span class="pic-text[^"]*"><b>([^<]*)</b></span>.*?'
            r'<h4 class="title[^"]*"><a[^>]*>([^<]*)</a></h4>\s*'
            r'<p class="text[^"]*text-muted[^"]*">([^<]*)</p>',
            html,
            re.S,
        )
        for vid, title, pic, cat, remark, _name, actor in cards:
            if vid in seen_ids:
                continue
            seen_ids.add(vid)
            videos.append(
                {
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": self._clean_pic(pic),
                    "vod_remarks": remark,
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": actor.strip() if actor else "",
                }
            )

        # 检测总页数
        page_match = re.findall(r"/page/(\d+)\.html", html)
        max_page = int(max(page_match)) if page_match else page
        limit = len(videos) if videos else 12
        total = max_page * limit

        return {
            "list": videos,
            "page": page,
            "pagecount": max_page,
            "limit": limit,
            "total": total,
        }

    def detailContent(self, ids):
        """视频详情页 - 封面海报/信息/播放线路/剧集"""
        vid = ids[0] if isinstance(ids, list) else str(ids)
        url = f"{HOST}/index.php/vod/detail/id/{vid}.html"
        html = self._fetch(url)

        if not html:
            return {"list": []}

        # 封面海报
        pic = ""
        pic_m = re.search(
            r'<a class="pic"[^>]*>\s*<img[^>]*data-original="([^"]*)"', html, re.S
        )
        if not pic_m:
            pic_m = re.search(
                r'<div class="stui-content__thumb">.*?data-original="([^"]*)"', html, re.S
            )
        if pic_m:
            pic = self._clean_pic(pic_m.group(1))

        # 标题
        name = ""
        name_m = re.search(r'<h1 class="title">([^<]*)</h1>', html)
        if name_m:
            name = name_m.group(1).strip()

        # 信息行: 类型/地区/年份
        vod_year = ""
        vod_area = ""
        vod_class = ""
        info_m = re.search(
            r'<p class="data[^"]*hidden-xs[^"]*">(.*?)</p>', html, re.S
        )
        if info_m:
            info_text = info_m.group(1)
            year_m = re.search(r"年份[：:]\s*(\S+)", info_text)
            area_m = re.search(r"地区[：:]\s*(\S+)", info_text)
            class_m = re.search(r"类型[：:]\s*(.+?)(?:\s*/|$)", info_text)
            if year_m:
                vod_year = year_m.group(1).strip()
            if area_m:
                vod_area = area_m.group(1).strip()
            if class_m:
                vod_class = class_m.group(1).strip()

        # 状态/备注
        remark = ""
        remark_m = re.search(
            r'<p class="data[^"]*">\s*状态[：:]\s*<span[^>]*>([^<]*)</span>', html, re.S
        )
        if remark_m:
            remark = remark_m.group(1).strip()

        # 导演
        director = ""
        dir_m = re.search(r'<p class="data[^"]*">\s*导演[：:]\s*([^<]*)</p>', html)
        if dir_m:
            director = dir_m.group(1).strip()

        # 主演
        actor = ""
        actor_m = re.search(r'<p class="data[^"]*">\s*主演[：:]\s*([^<]*)</p>', html)
        if actor_m:
            actor = actor_m.group(1).strip()

        # 简介（优先取完整版 detail-content，其次 detail-sketch）
        content = ""
        content_m = re.search(
            r'<span class="detail-content[^"]*"[^>]*>(.*?)</span>', html, re.S
        )
        if content_m:
            content = content_m.group(1).strip()
        if not content:
            sketch_m = re.search(
                r'<span class="detail-sketch[^"]*"[^>]*>(.*?)</span>', html, re.S
            )
            if sketch_m:
                content = sketch_m.group(1).strip()
        # 清理 HTML 标签
        content = re.sub(r"<[^>]+>", "", content).strip()

        # 播放线路 - 选项卡名称（按 HTML 出现顺序）
        play_from_names = []
        tab_matches = re.findall(
            r'<li><a href="#playlist(\d+)"[^>]*>([^<]+)</a></li>', html
        )
        tab_dict = {}
        for tab_id, tab_name in tab_matches:
            tab_dict[tab_id] = tab_name.strip()
            play_from_names.append(tab_name.strip())

        # 剧集列表 - 用 </ul>\s*</div> 匹配每个 playlist 的完整内容
        playlist_dict = {}
        playlist_matches = re.findall(
            r'<div id="playlist(\d+)" class="tab-pane[^"]*"[^>]*>(.*?)</ul>\s*</div>',
            html,
            re.S,
        )
        for p_id, p_content in playlist_matches:
            playlist_dict[p_id] = p_content

        # 按选项卡顺序组装播放线路和剧集
        play_url_list = []
        for tab_id, _ in tab_matches:
            p_content = playlist_dict.get(tab_id, "")
            if not p_content:
                continue
            episodes = re.findall(
                r'<a href="/index\.php/vod/play/id/\d+/sid/(\d+)/nid/(\d+)\.html"[^>]*>([^<]*)</a>',
                p_content,
            )
            if not episodes:
                continue
            # 按 nid 从小到大排序（源站可能倒序）
            episodes_sorted = sorted(episodes, key=lambda x: int(x[1]))
            ep_list = []
            for ep_sid, ep_nid, ep_name in episodes_sorted:
                # 播放ID格式: vid-sid-nid，playerContent 据此拼接播放页URL
                play_id = f"{vid}-{ep_sid}-{ep_nid}"
                ep_name_clean = ep_name.strip() or f"第{ep_nid}集"
                ep_list.append(f"{ep_name_clean}${play_id}")
            if ep_list:
                play_url_list.append("#".join(ep_list))

        play_from = "$$$".join(play_from_names) if play_from_names else "默认线路"
        play_url = "$$$".join(play_url_list) if play_url_list else ""

        vod = {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic,
            "vod_year": vod_year,
            "vod_area": vod_area,
            "vod_class": vod_class,
            "vod_remarks": remark,
            "vod_director": director,
            "vod_actor": actor,
            "vod_content": content,
            "vod_play_from": play_from,
            "vod_play_url": play_url,
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        """搜索视频"""
        page = int(pg) if pg else 1
        key_encoded = urllib.parse.quote(key)
        # 搜索分页URL: /index.php/vod/search/page/{page}/wd/{keyword}.html
        url = f"{HOST}/index.php/vod/search/page/{page}/wd/{key_encoded}.html"
        html = self._fetch(url)

        videos = []
        seen_ids = set()
        cards = re.findall(
            r'<a class="stui-vodlist__thumb[^"]*"[^>]*'
            r'href="/index\.php/vod/detail/id/(\d+)\.html"[^>]*'
            r'title="([^"]*)"[^>]*'
            r'data-original="([^"]*)"[^>]*>.*?'
            r'<span class="pic-text1[^"]*"><b>([^<]*)</b></span>\s*'
            r'<span class="pic-text[^"]*"><b>([^<]*)</b></span>.*?'
            r'<p class="text[^"]*text-muted[^"]*">([^<]*)</p>',
            html,
            re.S,
        )
        for vid, title, pic, cat, remark, actor in cards:
            if vid in seen_ids:
                continue
            seen_ids.add(vid)
            videos.append(
                {
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": self._clean_pic(pic),
                    "vod_remarks": remark,
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": actor.strip() if actor else "",
                }
            )

        return {"list": videos}

    def _resolve_m3u8(self, video_url):
        """通过站点解析器 hls.xiguadh.com 将第三方平台链接解析为直链
        流程: 1.请求解析器页面获取apiToken 2.调用resolve API获取m3u8/mp4
        """
        PARSE_HOST = "https://hls.xiguadh.com"
        try:
            if requests is None:
                return ""
            session = requests.Session()
            session.headers.update({
                "User-Agent": UA,
                "Referer": HOST + "/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "gzip, deflate",
            })
            # 步骤1: 获取解析器页面, 提取 apiToken
            parse_url = f"{PARSE_HOST}/?url={video_url}"
            resp = session.get(parse_url, timeout=15)
            token_m = re.search(r'apiToken:\s*"([^"]*)"', resp.text)
            if not token_m:
                print("[西瓜影院] 未找到 apiToken", file=sys.stderr)
                return ""
            api_token = token_m.group(1)

            # 步骤2: 调用 resolve API
            api_url = f"{PARSE_HOST}/api/resolve.php?token={urllib.parse.quote(api_token)}"
            resp2 = session.get(api_url, timeout=15)
            data = resp2.json()
            if data.get("code") == 200:
                return data.get("url", "")
            else:
                print(f"[西瓜影院] resolve 返回错误: {data.get('msg', '')}", file=sys.stderr)
                return ""
        except Exception as e:
            print(f"[西瓜影院] 解析直链失败: {e}", file=sys.stderr)
            return ""

    def playerContent(self, flag, id, vipFlags):
        """获取播放地址 (header 必须为 JSON 字符串)
        播放原理: player_aaaa.url 是第三方平台网页链接,
        通过站点解析器 hls.xiguadh.com/api/resolve.php 解析为 m3u8/mp4 直链,
        parse=0 让 TVBox 直接播放直链。
        """
        headers = {"User-Agent": UA, "Referer": HOST}

        # id 格式: vid-sid-nid
        parts = str(id).split("-")
        if len(parts) < 3:
            return {"parse": 0, "playUrl": "", "url": "", "header": json.dumps(headers)}

        vid, sid, nid = parts[0], parts[1], parts[2]
        url = f"{HOST}/index.php/vod/play/id/{vid}/sid/{sid}/nid/{nid}.html"
        html = self._fetch(url)

        if not html:
            return {"parse": 0, "playUrl": "", "url": "", "header": json.dumps(headers)}

        # 提取 player_aaaa JSON 对象
        player_m = re.search(r'player_aaaa\s*=\s*(\{[^}]*\})', html)

        if player_m:
            try:
                player_data = json.loads(player_m.group(1))
                play_url = player_data.get("url", "")
                play_from = player_data.get("from", "")

                # 1. 如果本身就是直链, 直接播放
                if self.isVideoFormat(play_url):
                    result = {"parse": 0, "playUrl": "", "url": play_url, "header": json.dumps(headers)}
                    if play_from:
                        result["from"] = play_from
                    return result

                # 2. 通过站点解析器获取直链
                direct_url = self._resolve_m3u8(play_url)
                if direct_url and self.isVideoFormat(direct_url):
                    # 解析成功, 获得了 m3u8/mp4 直链
                    result = {"parse": 0, "playUrl": "", "url": direct_url, "header": json.dumps(headers)}
                    if play_from:
                        result["from"] = play_from
                    return result

                # 3. 解析失败, 回退到嗅探模式
                result = {"parse": 2, "playUrl": "", "url": play_url, "header": json.dumps(headers)}
                if play_from:
                    result["from"] = play_from
                return result
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[西瓜影院] 解析 player_aaaa 失败: {e}", file=sys.stderr)

        # fallback: 嗅探播放页
        return {
            "parse": 2,
            "playUrl": "",
            "url": url,
            "header": json.dumps(headers),
        }

    # ---- 兼容 webhomeTV 三参数 searchContent ----
    def searchContentPage(self, key, quick, page):
        """搜索分页（兼容部分 TVBox 变体）"""
        result = self.searchContent(key, quick, str(page))
        return result


# ---- 测试入口（沙箱独立运行） ----
if __name__ == "__main__":
    spider = Spider()

    def test_home():
        print("=" * 60)
        print("[测试] homeContent - 首页分类栏")
        print("=" * 60)
        result = spider.homeContent(True)
        cats = result.get("class", [])
        print(f"分类数量: {len(cats)}")
        for c in cats:
            print(f"  {c['type_id']:>3s} | {c['type_name']}")
        filters = result.get("filters", {})
        print(f"\n筛选分类数: {len(filters)}")
        for tid, flist in filters.items():
            for f in flist:
                vals = f.get("value", [])
                print(f"  tid={tid} [{f['name']}] 子分类数: {len(vals)}")
        assert len(cats) >= 6, "分类数应>=6"
        assert len(filters) >= 6, "筛选数应>=6"
        print("[OK] homeContent\n")
        return result

    def test_category():
        print("=" * 60)
        print("[测试] categoryContent - 电影分类第1页")
        print("=" * 60)
        result = spider.categoryContent("20", "1", {})
        videos = result.get("list", [])
        print(f"视频数量: {len(videos)}")
        print(f"总页数: {result.get('pagecount')}")
        print(f"总条数: {result.get('total')}")
        for i, v in enumerate(videos[:5]):
            print(f"  [{i+1}] id={v['vod_id']} name={v['vod_name']} "
                  f"pic={'有' if v['vod_pic'] else '无'} remark={v['vod_remarks']}")
        assert len(videos) > 0, "列表应有视频"
        assert all(v["vod_pic"] for v in videos), "封面图不应为空"
        assert all(v["vod_name"] for v in videos), "标题不应为空"
        print("[OK] categoryContent\n")
        return result

    def test_category_subclass():
        print("=" * 60)
        print("[测试] categoryContent - 动作片子分类")
        print("=" * 60)
        result = spider.categoryContent("20", "1", {"class": "21"})
        videos = result.get("list", [])
        print(f"动作片视频数量: {len(videos)}")
        if videos:
            print(f"  [1] id={videos[0]['vod_id']} name={videos[0]['vod_name']}")
        assert len(videos) > 0, "动作片应有视频"
        print("[OK] 子分类筛选\n")
        return result

    def test_detail():
        print("=" * 60)
        print("[测试] detailContent - 视频详情")
        print("=" * 60)
        result = spider.detailContent(["137939"])
        vod = result.get("list", [{}])[0] if result.get("list") else {}
        print(f"  vod_id:    {vod.get('vod_id')}")
        print(f"  vod_name:  {vod.get('vod_name')}")
        print(f"  vod_pic:   {vod.get('vod_pic', '')[:80]}")
        print(f"  vod_year:  {vod.get('vod_year')}")
        print(f"  vod_area:  {vod.get('vod_area')}")
        print(f"  vod_class: {vod.get('vod_class')}")
        print(f"  vod_remarks: {vod.get('vod_remarks')}")
        print(f"  vod_director: {vod.get('vod_director')}")
        print(f"  vod_actor: {vod.get('vod_actor')}")
        print(f"  vod_content: {vod.get('vod_content', '')[:80]}...")
        print(f"  vod_play_from: {vod.get('vod_play_from')}")
        play_url = vod.get('vod_play_url', '')
        print(f"  vod_play_url: {play_url[:100]}...")
        assert vod.get("vod_name"), "标题不应为空"
        assert vod.get("vod_pic"), "封面图不应为空"
        assert vod.get("vod_play_url"), "播放地址不应为空"
        assert vod.get("vod_play_from"), "播放线路不应为空"
        print("[OK] detailContent\n")
        return result

    def test_search():
        print("=" * 60)
        print("[测试] searchContent - 搜索 '变形金刚'")
        print("=" * 60)
        result = spider.searchContent("变形金刚", "1")
        videos = result.get("list", [])
        print(f"搜索结果数量: {len(videos)}")
        for i, v in enumerate(videos[:5]):
            print(f"  [{i+1}] id={v['vod_id']} name={v['vod_name']} "
                  f"pic={'有' if v['vod_pic'] else '无'}")
        assert len(videos) > 0, "搜索应有结果"
        assert all(v["vod_pic"] for v in videos), "封面图不应为空"
        print("[OK] searchContent\n")
        return result

    def test_player():
        print("=" * 60)
        print("[测试] playerContent - 解析直链播放")
        print("=" * 60)
        # 先获取详情页中的播放ID
        detail = spider.detailContent(["137939"])
        vod = detail.get("list", [{}])[0] if detail.get("list") else {}
        play_url = vod.get("vod_play_url", "")
        if play_url:
            first_ep = play_url.split("#")[0]
            ep_name, play_id = first_ep.split("$")
            print(f"  剧集: {ep_name}, 播放ID: {play_id}")
            result = spider.playerContent("", play_id, [])
            parse_val = result.get('parse')
            url_val = result.get('url', '')
            print(f"  parse: {parse_val} (0=直链播放)")
            print(f"  url: {url_val[:80]}")
            print(f"  from: {result.get('from', '')}")
            hdr = result.get('header', '')
            print(f"  header type: {type(hdr).__name__}")
            assert url_val, "播放地址不应为空"
            assert isinstance(hdr, str), "header 应为 JSON 字符串"
            print("[OK] playerContent\n")
        else:
            print("[SKIP] 无播放地址\n")
        return None

    # 执行所有测试
    print("\n")
    print("#" * 60)
    print("#  西瓜影院 TVBox 爬虫 - 功能测试")
    print(f"#  站点: {HOST}")
    print("#" * 60)
    print("\n")

    tests = [
        ("homeContent", test_home),
        ("categoryContent", test_category),
        ("子分类筛选", test_category_subclass),
        ("detailContent", test_detail),
        ("searchContent", test_search),
        ("playerContent", test_player),
    ]

    passed = 0
    failed = 0
    for name, func in tests:
        try:
            func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"[FAIL] {name}: {e}\n")

    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
