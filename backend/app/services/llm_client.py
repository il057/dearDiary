import json
import re
import urllib.request
import urllib.error
from typing import List, Dict, Any
from app.config import settings
from app.services.knowledge_base import knowledge_base

class LLMClient:
    def __init__(self):
        # 确保直连本地或 Tailscale 100.x 远端 IP，不走本机科学代理
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @staticmethod
    def _resolve_base_url(configured_url: str) -> str:
        url = (configured_url or "").strip().rstrip("/")
        ollama_host = (settings.OLLAMA_HOST or "").strip().rstrip("/")
        if (not url or url == "http://localhost:11434/v1") and ollama_host and ollama_host != "http://localhost:11434":
            return f"{ollama_host}/v1"
        return url or "http://localhost:11434/v1"

    @staticmethod
    def _is_ollama(base_url: str, api_key: str) -> bool:
        return ":11434" in base_url or (api_key or "").lower() == "ollama"

    @staticmethod
    def _ollama_root(base_url: str) -> str:
        return base_url[:-3] if base_url.endswith("/v1") else base_url

    def _post_json(self, url: str, api_key: str, payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )
        with self.opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_embedding(self, text: str) -> List[float]:
        cleaned_text = re.sub(r'[ \t\r\f]+', ' ', text)
        cleaned_text = re.sub(r'\n+', '\n', cleaned_text).strip()
        if not cleaned_text:
            cleaned_text = "日记"

        try:
            base_url = self._resolve_base_url(settings.EMBEDDING_BASE_URL)
            if self._is_ollama(base_url, settings.EMBEDDING_API_KEY):
                ollama_root = self._ollama_root(base_url)
                result = self._post_json(
                    f"{ollama_root}/api/embed",
                    "",
                    {
                        "model": settings.EMBEDDING_MODEL,
                        "input": cleaned_text[:2000],
                        "keep_alive": 0
                    },
                    timeout=15.0
                )
                embeddings = result.get("embeddings") or []
                vec = embeddings[0] if embeddings else result.get("embedding", [])
            else:
                result = self._post_json(
                    f"{base_url}/embeddings",
                    settings.EMBEDDING_API_KEY,
                    {
                        "model": settings.EMBEDDING_MODEL,
                        "input": cleaned_text[:2000]
                    },
                    timeout=15.0
                )
                data = result.get("data") or []
                vec = data[0].get("embedding", []) if data else result.get("embedding", [])
            if len(vec) == settings.EMBEDDING_DIM:
                return vec
            elif len(vec) > settings.EMBEDDING_DIM:
                return vec[:settings.EMBEDDING_DIM]
            elif len(vec) > 0:
                return vec + [0.0] * (settings.EMBEDDING_DIM - len(vec))
        except Exception as e:
            print(f"[Embedding Info]: {e}")

        import hashlib
        seed = int(hashlib.md5(cleaned_text.encode('utf-8')).hexdigest(), 16)
        import random
        rng = random.Random(seed)
        return [rng.uniform(-0.1, 0.1) for _ in range(settings.EMBEDDING_DIM)]

    def extract_entities_and_relations(self, text: str, diary_date=None, raise_on_error: bool = False) -> Dict[str, Any]:
        """
        开源通用级日记语义理解：
        1. 结合写作日期进行【回忆回溯时间绝对化】（如把过去的年份折算为绝对年份，严禁日记自身的记录年份，严禁“小时候/以前”等模糊词）；
        2. 严格排除代词（你/我/她/他/别人）与“一切/所有/东西”等抽象虚词；
        3. 联动知识库实现用户专属词典保底扫描与实体别名对齐。
        """
        date_str = diary_date.strftime("%Y年%m月%d日") if diary_date else "未知时间"
        diary_year = str(diary_date.year) if diary_date else ""

        prompt = f"""你是一个私密日记语义理解助手。
日记写于：{date_str}

请仔细阅读日记正文，提取作者心境情绪（2-4字，如：怀念、困惑、释怀、烦躁，若无法判断请留空""），以及正文中实际提及的具象人物称谓/昵称、宠物、地点场景或核心事物意象。

【严格负面约束与时间规范】：
1. 严禁代词与虚词：绝对严禁提取“你”、“我”、“他”、“她”、“别人”、“某人”、“大家”、“自己”、“一切”、“所有”、“东西”、“事情”等代词或抽象词！
2. 严禁提取日记自身写作日期：绝不要把日记写于的这一天（{date_str}）当做实体提取！
3. 严禁回显占位提示词：严禁输出“具体情绪词”、“心境词”、“情绪”、“心情”等占位符；若有多种情绪仅选一个最核心的2字词（如“烦躁”或“痛苦”，严禁拼接为“烦痛苦”）。
4. 仅当作者在回忆过去的特定年份时，才提取该过去的绝对年份（如“2019年”）。严禁提取“小时候”、“四五年前”、“去年”、“最近”、“以前”等模糊词；若文中无确切过去年份，严禁提取任何时间标签！

日记正文：
\"\"\"{text[:2500]}\"\"\"

请严格输出纯 JSON（无需多余解释）：
{{
  "mood": "情绪词或空字符串",
  "entities": [
    {{"name": "实体名", "entity_type": "person/pet/place/time/concept"}}
  ],
  "relations": [
    {{"source": "主体", "relation": "关系词", "target": "客体"}}
  ]
}}"""
        clean_entities_map: Dict[str, Dict[str, Any]] = {}
        clean_relations: List[Dict[str, str]] = []
        mood_str = ""

        try:
            base_url = self._resolve_base_url(settings.LLM_BASE_URL)
            if self._is_ollama(base_url, settings.LLM_API_KEY):
                ollama_root = self._ollama_root(base_url)
                ollama_payload: Dict[str, Any] = {
                    "model": settings.LLM_MODEL,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "think": False,
                    "keep_alive": 0,
                    "format": "json",
                    "options": {
                        "temperature": 0.2,
                        "num_ctx": 4096
                    }
                }
                try:
                    res_obj = self._post_json(
                        f"{ollama_root}/api/chat",
                        "",
                        ollama_payload,
                        timeout=90.0
                    )
                except urllib.error.HTTPError as http_err:
                    if http_err.code == 400 and "think" in ollama_payload:
                        ollama_payload.pop("think", None)
                        res_obj = self._post_json(
                            f"{ollama_root}/api/chat",
                            "",
                            ollama_payload,
                            timeout=90.0
                        )
                    else:
                        raise
                raw = (res_obj.get("message", {}).get("content", "")).strip()
            else:
                payload: Dict[str, Any] = {
                    "model": settings.LLM_MODEL,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "stream": False,
                    "response_format": {"type": "json_object"}
                }
                try:
                    res_obj = self._post_json(
                        f"{base_url}/chat/completions",
                        settings.LLM_API_KEY,
                        payload,
                        timeout=90.0
                    )
                except urllib.error.HTTPError as http_err:
                    if http_err.code == 400:
                        payload.pop("response_format", None)
                        res_obj = self._post_json(
                            f"{base_url}/chat/completions",
                            settings.LLM_API_KEY,
                            payload,
                            timeout=90.0
                        )
                    else:
                        raise
                choices = res_obj.get("choices") or []
                raw = (choices[0].get("message", {}).get("content", "") if choices else "").strip()

            if "</think>" in raw:
                raw = raw.split("</think>")[-1].strip()
            if raw.startswith("```"):
                raw = re.sub(r'^```(?:json)?\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw).strip()

            parsed = json.loads(raw)
            raw_mood = str(parsed.get("mood") or "").strip()
            # 严格过滤模板占位符回显与生硬拼接词
            bad_mood_set = {
                "具体情绪词", "心境词", "情绪词", "心境", "情绪", "心情", "情绪词汇",
                "情绪词或空字符串", "null", "none", "未知", "无", "具体", "情感", "状态", "无情绪"
            }
            if raw_mood in bad_mood_set or any(b in raw_mood for b in ["心境词", "具体情绪词", "情绪词", "占位"]):
                mood_str = ""
            elif raw_mood == "烦痛苦":
                mood_str = "烦躁"
            elif len(raw_mood) > 6:
                mood_str = raw_mood[:4]
            else:
                mood_str = raw_mood

            # 严格代词、抽象代名词与虚词黑名单（彻底阻止“你/她/一切”等被错提）
            stop_words = {
                "你", "我", "他", "她", "它", "你们", "我们", "他们", "她们", "它们",
                "您", "谁", "大家", "别人", "某人", "对方", "自己", "所有人", "每个人",
                "有人", "无人", "那个", "这个", "这些", "那些", "某位", "一位", "一个",
                "一人", "俩人", "两人", "三人", "很多东西", "什么", "怎么", "之所以",
                "因为", "所以", "如果", "但是", "其实", "虽然", "只是", "感觉", "觉得",
                "好像", "似乎", "也许", "可能", "大概", "总之", "东西", "日记", "今天",
                "现在", "那天", "这时候", "那时候", "此时", "当时", "null", "none", "没有",
                "一切", "所有", "全部", "事情", "很多", "样子", "原因", "时候", "小时候",
                "去年", "前年", "以前", "当年", "最近", "多年", "几年前"
            }

            for e in parsed.get("entities", []):
                raw_name = str(e.get("name") or "").strip()
                etype = str(e.get("entity_type") or "concept").strip()
                if not raw_name or len(raw_name) > 15 or raw_name.lower() in stop_words:
                    continue

                # 时间类型严格校验
                if etype == "time":
                    year_match = re.search(r'(19\d\d|20\d\d)', raw_name)
                    if not year_match:
                        # 舍弃所有模糊时间词（如“小时候”、“前些年”）
                        continue
                    extracted_year = year_match.group(1)
                    # 严禁将日记自身写作年份作为回忆时间提取
                    if diary_year and extracted_year == diary_year:
                        continue
                    raw_name = f"{extracted_year}年"

                # 非时间类型必须在正文中实际存在
                if etype != "time" and (raw_name not in text and raw_name.lower() not in text.lower()):
                    continue

                canonical = knowledge_base.resolve_entity(raw_name)
                alias_target = knowledge_base.get_alias_mapping_for_name(raw_name)
                if alias_target and alias_target != raw_name:
                    clean_relations.append({
                        "source": raw_name,
                        "relation": "alias_of",
                        "target": canonical
                    })

                # 用户在知识库已设定的类型为最高优先准则
                user_saved_type = knowledge_base.custom_entities.get(canonical)
                final_type = user_saved_type if user_saved_type else etype

                clean_entities_map[canonical] = {
                    "name": canonical,
                    "entity_type": final_type,
                    "description": f"文中提及: {raw_name}" if canonical != raw_name else ""
                }

            for r in parsed.get("relations", []):
                s = str(r.get("source") or "").strip()
                rel = str(r.get("relation") or "").strip()
                t = str(r.get("target") or "").strip()
                if s and rel and t and s not in stop_words and t not in stop_words:
                    clean_relations.append({
                        "source": knowledge_base.resolve_entity(s),
                        "relation": rel,
                        "target": knowledge_base.resolve_entity(t)
                    })
        except Exception as e:
            print(f"[LLM extraction error]: {e}")
            if raise_on_error:
                raise

        # 结合知识库词典做 100% 保底扫描（确保单字人名、朋友昵称绝不漏采）
        scanned_custom = knowledge_base.scan_custom_entities(text)
        for c in scanned_custom:
            c_name = c["name"]
            if c_name not in clean_entities_map:
                clean_entities_map[c_name] = c
            if c.get("alias_source"):
                clean_relations.append({
                    "source": c["alias_source"],
                    "relation": "alias_of",
                    "target": c_name
                })

        final_entities = list(clean_entities_map.values())
        # 自动学习沉淀：将 AI 提取的有效标签持久化到知识库中
        knowledge_base.auto_register_entities(final_entities)

        return {
            "summary": text[:40],
            "mood": mood_str,
            "entities": final_entities,
            "relations": clean_relations
        }

llm_service = LLMClient()
