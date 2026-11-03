# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import math
import os
import re
import time
from functools import lru_cache
from urllib.parse import quote

from base.spider import Spider

try:
    from Crypto.Cipher import AES as _CryptoAES
except Exception:
    _CryptoAES = None

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM
except Exception:
    _AESGCM = None


_SBOX = (
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
)
_RCON = (0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


@lru_cache(maxsize=8)
def _aes_round_keys(key):
    words = [int.from_bytes(key[i:i + 4], "big") for i in range(0, 16, 4)]
    for index in range(4, 44):
        value = words[index - 1]
        if index % 4 == 0:
            value = ((value << 8) & 0xFFFFFFFF) | (value >> 24)
            value = sum(_SBOX[(value >> shift) & 0xFF] << shift for shift in (24, 16, 8, 0))
            value ^= _RCON[index // 4] << 24
        words.append(words[index - 4] ^ value)
    return tuple(b"".join(words[round_index * 4 + i].to_bytes(4, "big") for i in range(4)) for round_index in range(11))


def _xtime(value):
    return ((value << 1) ^ (0x11B if value & 0x80 else 0)) & 0xFF


def _aes_block(key, block):
    keys = _aes_round_keys(key)
    state = [value ^ keys[0][index] for index, value in enumerate(block)]
    for round_index in range(1, 11):
        state = [_SBOX[value] for value in state]
        state = [state[4 * ((column + row) % 4) + row] for column in range(4) for row in range(4)]
        if round_index < 10:
            mixed = []
            for column in range(4):
                a0, a1, a2, a3 = state[column * 4:column * 4 + 4]
                mixed.extend((
                    _xtime(a0) ^ (_xtime(a1) ^ a1) ^ a2 ^ a3,
                    a0 ^ _xtime(a1) ^ (_xtime(a2) ^ a2) ^ a3,
                    a0 ^ a1 ^ _xtime(a2) ^ (_xtime(a3) ^ a3),
                    (_xtime(a0) ^ a0) ^ a1 ^ a2 ^ _xtime(a3),
                ))
            state = mixed
        state = [value ^ keys[round_index][index] for index, value in enumerate(state)]
    return bytes(state)


def _gf_mul(left, right):
    result, value = 0, right
    for index in range(128):
        if left & (1 << (127 - index)):
            result ^= value
        value = (value >> 1) ^ (0xE1000000000000000000000000000000 if value & 1 else 0)
    return result


def _ghash(key_hash, aad, data):
    value = 0
    payload = aad + b"\0" * (-len(aad) % 16) + data + b"\0" * (-len(data) % 16)
    payload += (len(aad) * 8).to_bytes(8, "big") + (len(data) * 8).to_bytes(8, "big")
    for offset in range(0, len(payload), 16):
        value = _gf_mul(value ^ int.from_bytes(payload[offset:offset + 16], "big"), key_hash)
    return value.to_bytes(16, "big")


def _ctr_crypt(key, nonce, data):
    counter = bytearray(nonce + b"\0\0\0\1")
    output = bytearray()
    for offset in range(0, len(data), 16):
        number = (int.from_bytes(counter[12:], "big") + 1) & 0xFFFFFFFF
        counter[12:] = number.to_bytes(4, "big")
        stream = _aes_block(key, bytes(counter))
        output.extend(a ^ b for a, b in zip(data[offset:offset + 16], stream))
    return bytes(output)


def _pure_gcm_encrypt(key, nonce, data, aad):
    encrypted = _ctr_crypt(key, nonce, data)
    key_hash = int.from_bytes(_aes_block(key, b"\0" * 16), "big")
    tag = bytes(a ^ b for a, b in zip(_aes_block(key, nonce + b"\0\0\0\1"), _ghash(key_hash, aad, encrypted)))
    return encrypted + tag


def _pure_gcm_decrypt(key, nonce, data, aad):
    encrypted, tag = data[:-16], data[-16:]
    key_hash = int.from_bytes(_aes_block(key, b"\0" * 16), "big")
    expected = bytes(a ^ b for a, b in zip(_aes_block(key, nonce + b"\0\0\0\1"), _ghash(key_hash, aad, encrypted)))
    if not hmac.compare_digest(tag, expected):
        raise ValueError("Invalid GCM tag")
    return _ctr_crypt(key, nonce, encrypted)


def _gcm_encrypt(key, data, aad=b""):
    nonce = os.urandom(12)
    if _CryptoAES is not None:
        cipher = _CryptoAES.new(key, _CryptoAES.MODE_GCM, nonce=nonce, mac_len=16)
        cipher.update(aad)
        encrypted, tag = cipher.encrypt_and_digest(data)
        return nonce + encrypted + tag
    if _AESGCM is not None:
        return nonce + _AESGCM(key).encrypt(nonce, data, aad)
    return nonce + _pure_gcm_encrypt(key, nonce, data, aad)


def _gcm_decrypt(key, payload, aad=b""):
    if len(payload) <= 28:
        raise ValueError("Invalid encrypted payload")
    nonce, data = payload[:12], payload[12:]
    if _CryptoAES is not None:
        cipher = _CryptoAES.new(key, _CryptoAES.MODE_GCM, nonce=nonce, mac_len=16)
        cipher.update(aad)
        return cipher.decrypt_and_verify(data[:-16], data[-16:])
    if _AESGCM is not None:
        return _AESGCM(key).decrypt(nonce, data, aad)
    return _pure_gcm_decrypt(key, nonce, data, aad)


class Spider(Spider):
    def getName(self):
        return "闪剧"

    def init(self, extend=""):
        self.nodes = [
            "http://156.238.228.37:894/v1",
            "http://124.221.108.97:894/v1",
            "http://110.42.56.152:894/v1",
        ]
        self.device_id = os.urandom(16).hex()
        self.timeout = 15
        if extend:
            try:
                config = json.loads(extend) if isinstance(extend, str) else extend
                nodes = config.get("nodes") or config.get("node")
                if isinstance(nodes, str):
                    nodes = [nodes]
                if isinstance(nodes, list) and nodes:
                    self.nodes = [str(node).rstrip("/") for node in nodes if str(node).strip()]
                self.device_id = str(config.get("deviceId", self.device_id))
                self.timeout = max(5, int(config.get("timeout", self.timeout)))
            except Exception:
                pass
        self.classes = [
            {"type_id": "22", "type_name": "电视剧"},
            {"type_id": "21", "type_name": "电影"},
            {"type_id": "23", "type_name": "综艺"},
            {"type_id": "24", "type_name": "动漫"},
            {"type_id": "27", "type_name": "少儿"},
            {"type_id": "26", "type_name": "短剧"},
            {"type_id": "28", "type_name": "直播"},
        ]
        self.api_key = b"n7X2pQ9sL4vT1mZ8"
        self.resolve_key = b"Y8rQ3mV1sT5kL9xZ"
        self.path_key = b"u1bCw4Qy7nF9rZ3Vt8K2pX6mS0D5hA9Jc4L7eR2tY1wQ8u3I"
        self.alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
        self.package = "com.qwtt.taiyue"
        self.version = "1.0.1"
        self.csrf = "Uq3vZp8nR2sK4tX1y7"
        self.ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"

    def _ensure(self):
        if not hasattr(self, "nodes"):
            self.init("")

    def _put_bits(self, target, value, size, position):
        for index in range(size - 1, -1, -1):
            if (value >> index) & 1:
                target[position // 8] |= 1 << (7 - position % 8)
            position += 1
        return position

    def _action_path(self, action):
        if not re.fullmatch(r"[a-z_]{1,21}", action):
            return action
        packed = bytearray(14)
        position = self._put_bits(packed, len(action), 5, 0)
        for char in action:
            position = self._put_bits(packed, 26 if char == "_" else ord(char) - 97, 5, position)
        raw = bytearray(16)
        bucket = int(time.time() // 30) & 0xFFFF
        raw[0], raw[1], raw[2:] = bucket >> 8, bucket & 0xFF, packed
        nonce = os.urandom(4)
        mask = hmac.new(self.path_key, nonce, hashlib.sha256).digest()
        payload = nonce + bytes(left ^ right for left, right in zip(raw, mask))
        bits = "".join(format(value, "08b") for value in payload)
        return "".join(self.alphabet[int(bits[index:index + 5], 2)] for index in range(0, 160, 5))

    def _canonical(self, params):
        values = []
        for key in sorted(params):
            value = params[key]
            if value is None:
                continue
            if isinstance(value, bool):
                value = "1" if value else "0"
            elif not isinstance(value, (str, int, float)):
                continue
            values.append(quote(str(key), safe="~") + "=" + quote(str(value), safe="~"))
        return "&".join(values)

    def _csrf_token(self, action, query, body=""):
        digest = hashlib.md5((query + "\n" + body).encode("utf-8")).hexdigest()
        fields = [
            action,
            self.device_id,
            "android",
            self.csrf,
            self.package,
            self.version,
            str(int(time.time() * 1000)),
            digest,
        ]
        encrypted = _gcm_encrypt(self.api_key, "|".join(fields)[::-1].encode("utf-8"), action.encode("utf-8"))
        return base64.b64encode(encrypted).decode("ascii")

    def _decoded(self, value, key, aad=b""):
        payload = base64.b64decode(value)
        plain = _gcm_decrypt(key, payload, aad).decode("utf-8").strip()
        try:
            return json.loads(plain)
        except Exception:
            return plain

    def _decode_api(self, data, action):
        if str(data.get("encoding", "")).lower() != "encoded" or not isinstance(data.get("data"), str):
            return data
        for aad in (action.encode("utf-8"), b""):
            try:
                result = dict(data)
                result["data"] = self._decoded(data["data"], self.api_key, aad)
                return result
            except Exception:
                continue
        return {}

    def _api(self, action, params=None):
        self._ensure()
        query = self._canonical(params or {})
        headers = {
            "User-Agent": self.ua,
            "X-Device-Model": "Android TV",
            "X-OS-Version": "13",
        }
        for index, node in enumerate(list(self.nodes)):
            try:
                headers["X-Csrf-Token"] = self._csrf_token(action, query)
                url = node + "/" + self._action_path(action) + ("?" + query if query else "")
                response = self.fetch(url, headers=headers, timeout=self.timeout)
                result = self._decode_api(response.json(), action)
                if result and int(result.get("code", response.status_code)) == 200:
                    if index:
                        self.nodes.remove(node)
                        self.nodes.insert(0, node)
                    return result
            except Exception:
                continue
        return {}

    def _video(self, item):
        if not isinstance(item, dict):
            return None
        vod_id = item.get("vod_id", item.get("vodId", item.get("id", item.get("req_content", ""))))
        name = item.get("vod_name", item.get("vodName", item.get("name", item.get("title", ""))))
        if not vod_id or not str(name).strip():
            return None
        result = {
            "vod_id": str(vod_id),
            "vod_name": str(name).strip(),
            "vod_pic": str(item.get("vod_pic", item.get("vodPic", item.get("pic", item.get("content", "")))) or ""),
            "vod_remarks": str(item.get("vod_remarks", item.get("vodRemarks", item.get("remarks", item.get("vod_sub", "")))) or ""),
        }
        if item.get("type_id", item.get("typeId")) is not None:
            result["type_id"] = str(item.get("type_id", item.get("typeId")))
        return result

    def _videos(self, items):
        result, seen = [], set()
        for item in items or []:
            video = self._video(item)
            if not video or video["vod_id"] in seen:
                continue
            seen.add(video["vod_id"])
            result.append(video)
        return result

    def _search(self, keyword, page, type_id=None, extend=None):
        extend = extend or {}
        return self._api("search", {
            "keyword": keyword,
            "page": page,
            "limit": 20,
            "type_id": type_id,
            "vod_class": extend.get("class"),
            "vod_area": extend.get("area"),
            "vod_year": extend.get("year"),
            "order_by": extend.get("order_by", "vod_time"),
        })

    def homeContent(self, filter):
        data = (self._api("index_video", {"limit": 20}).get("data") or {})
        items = []
        for key in ("search_hot", "hot", "list", "videos"):
            if isinstance(data.get(key), list):
                items.extend(data[key])
        for section in data.get("recommend_sections", []) or []:
            if isinstance(section, dict) and isinstance(section.get("videos"), list):
                items.extend(section["videos"])
        return {"class": self.classes, "list": self._videos(items), "filters": {}}

    def homeVideoContent(self):
        return {"list": self.homeContent(False).get("list", [])}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        result = self._search("", page, int(tid), extend if isinstance(extend, dict) else {})
        data = result.get("data") or {}
        videos = self._videos(data.get("list", []))
        limit = int(data.get("limit") or 20)
        total = int(data.get("total") or 0)
        pagecount = int(data.get("pagecount") or (math.ceil(total / limit) if total else page + (1 if len(videos) >= limit else 0)))
        return {"page": page, "pagecount": max(page, pagecount), "limit": limit, "total": total, "list": videos}

    def searchContent(self, key, quick, pg="1"):
        page = max(1, int(pg or 1))
        result = self._search(str(key), page)
        data = result.get("data") or {}
        videos = self._videos(data.get("list", []))
        if not videos:
            result = self._search(str(key), page, 0)
            data = result.get("data") or {}
            videos = self._videos(data.get("list", []))
        limit = int(data.get("limit") or 20)
        total = int(data.get("total") or 0)
        pagecount = int(data.get("pagecount") or (math.ceil(total / limit) if total else page))
        return {"page": page, "pagecount": max(page, pagecount), "limit": limit, "total": total, "list": videos}

    def detailContent(self, ids):
        result = []
        for value in ids:
            match = re.search(r"\d+", str(value))
            if not match:
                continue
            vod_id = int(match.group())
            data = self._api("video_detail", {"id": vod_id}).get("data") or {}
            vod = data.get("vod_info") or data.get("vodInfo") or data
            if not isinstance(vod, dict) or not vod:
                continue
            detail = {
                "vod_id": str(vod.get("vod_id", vod_id)),
                "vod_name": str(vod.get("vod_name", vod.get("vodName", vod_id))),
                "vod_pic": str(vod.get("vod_pic", vod.get("vodPic", "")) or ""),
                "vod_play_from": str(vod.get("vod_play_from", vod.get("vodPlayFrom", "")) or ""),
                "vod_play_url": str(vod.get("vod_play_url", vod.get("vodPlayUrl", "")) or ""),
            }
            for field in ("vod_remarks", "vod_year", "vod_area", "vod_actor", "vod_director", "vod_content", "vod_class", "vod_score", "vod_pubdate"):
                camel = "".join(part.capitalize() if index else part for index, part in enumerate(field.split("_")))
                value = vod.get(field, vod.get(camel))
                if value is not None:
                    detail[field] = str(value)
            result.append(detail)
        return {"list": result}

    def _headers(self, data):
        for key in ("header", "headers", "Header", "useHeaders", "use_headers"):
            value = data.get(key) if isinstance(data, dict) else None
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except Exception:
                    value = None
            if isinstance(value, dict):
                return {str(name): str(content) for name, content in value.items() if str(name).strip() and str(content).strip()}
        return {}

    def _valid_play(self, data, encoded=False):
        if not isinstance(data, dict):
            return None
        url = str(data.get("url", "")).strip()
        if not re.match(r"https?://", url, re.I):
            return None
        if encoded:
            try:
                timestamp = float(data.get("ts"))
                timestamp = timestamp / 1000 if timestamp > 1000000000000 else timestamp
                if abs(time.time() - timestamp) > 60:
                    return None
            except Exception:
                return None
        match = re.search(r"[?&]x-expires=(\d+)", url, re.I)
        if match and int(match.group(1)) <= int(time.time()) + 10:
            return None
        return {"url": url, "headers": self._headers(data) or {"User-Agent": self.ua}}

    def _local_resolve(self, token):
        try:
            payload = token.replace("-", "+").replace("_", "/")
            payload += "=" * (-len(payload) % 4)
            plain = _gcm_decrypt(self.resolve_key, base64.b64decode(payload), b"").decode("utf-8").strip()
            if re.match(r"https?://", plain, re.I):
                return {"url": plain, "headers": {"User-Agent": self.ua}}
            return self._valid_play(json.loads(plain))
        except Exception:
            return None

    def _resolve(self, token):
        direct = self._local_resolve(token)
        if direct:
            return direct
        for node in self.nodes:
            try:
                url = node + "/resolve?url=" + quote(token, safe="")
                response = self.fetch(url, headers={"User-Agent": self.ua}, timeout=self.timeout)
                result = response.json()
                if int(result.get("code", response.status_code)) != 200:
                    continue
                encoded = str(result.get("encoding", "")).lower() == "encoded"
                data = result.get("data")
                if encoded and isinstance(data, str):
                    data = self._decoded(data, self.resolve_key, b"")
                resolved = self._valid_play(data, encoded)
                if resolved:
                    return resolved
            except Exception:
                continue
        return None

    def playerContent(self, flag, id, vipFlags):
        self._ensure()
        value = str(id or "").strip()
        if re.match(r"https?://", value, re.I) and re.search(r"\.(?:m3u8|mp4|flv)(?:\?|$)", value, re.I):
            return {"parse": 0, "url": value, "header": {"User-Agent": self.ua}}
        resolved = self._resolve(value)
        if not resolved:
            return {"parse": 0, "url": "", "header": {"User-Agent": self.ua}, "msg": "播放地址解析失败"}
        return {"parse": 0, "url": resolved["url"], "header": resolved["headers"]}
