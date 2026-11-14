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
                        "keep_alive": settings.OLLAMA_KEEP_ALIVE
                    },
                    timeout=20.0
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
                    timeout=20.0
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
            print(f"[Embedding Error]: {e}")

        return []

    @staticmethod
    def split_text_chunks(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
        """将长日记切分为带重叠的语义分块，确保长文后半段也能被向量召回"""
        cleaned = re.sub(r'\n{3,}', '\n\n', (text or "").strip())
        if not cleaned:
            return []
        if len(cleaned) <= chunk_size:
            return [cleaned]

        chunks: List[str] = []
        start = 0
        step = max(1, chunk_size - overlap)
        while start < len(cleaned):
            end = min(len(cleaned), start + chunk_size)
            if end < len(cleaned):
                # 尽量在换行或句号处断开，避免截断词句
                split_pos = max(
                    cleaned.rfind('\n', start + chunk_size // 2, end),
                    cleaned.rfind('。', start + chunk_size // 2, end),
                    cleaned.rfind('！', start + chunk_size // 2, end),
                    cleaned.rfind('？', start + chunk_size // 2, end),
                )
                if split_pos > start:
                    end = split_pos + 1
            chunk = cleaned[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(cleaned):
                break
            start = max(start + 1, end - overlap)
        return chunks

    def extract_entities_and_relations(self, text: str, diary_date=None, raise_on_error: bool = False) -> Dict[str, Any]:
        """
        面向 qwen3:8b 等中大规模模型的日记语义理解与结构化提取：
        1. System/User 分离 + Few-shot 示例，提升 JSON 稳定性与实体粒度；
        2. 注入知识库已有实体/别名上下文，保持称谓一致并建立跨日记图谱关联；
        3. 自动提炼 10-20 字一句话摘要（summary）与心境情绪（mood）；
        4. 支持结合写作日期将相对回忆时间折算为绝对年份（如“三年前”→“2023年”）。
        """
        date_str = diary_date.strftime("%Y年%m月%d日") if diary_date else "未知时间"
        diary_year = str(diary_date.year) if diary_date else ""

        kb_data = knowledge_base.get_all()
        owner_name = knowledge_base.get_owner_name()
        known_names = list(kb_data.get("custom_entities", {}).keys())[:60]
        known_aliases = [f"{a}->{c}" for a, c in list(kb_data.get("aliases", {}).items())[:30]]
        kb_hint_lines = [f"日记中的第一人称“我”指代「{owner_name}」"]
        if known_names:
            kb_hint_lines.append(f"已知实体参考（若文中提及请优先沿用相同名称）：{', '.join(known_names)}")
        if known_aliases:
            kb_hint_lines.append(f"已知别名映射：{', '.join(known_aliases)}")
        kb_hint = "\n".join(kb_hint_lines)

        system_prompt = f"""你是私密日记语义理解与记忆图谱构建助手。请从日记中提取结构化记忆，严格输出合法 JSON（不要 Markdown 代码块或额外解释）。

输出 Schema：
{{
  "summary": "10-20字的一句话核心提炼，概括日记主要事件或感悟",
  "mood": "必填，2-4字心境情绪或基调词（如：怀念、释怀、烦躁、平静、欣慰、充实、惬意、日常），严禁留空或输出“无”",
  "entities": [
    {{"name": "实体名", "entity_type": "person|pet|place|time|concept"}}
  ],
  "relations": [
    {{"source": "主体实体名", "relation": "关系词", "target": "客体实体名"}}
  ]
}}

提取准则：
1. entities 仅提取文中真实出现或明确指代的具象要素：
   - person：具体人物姓名、称谓或昵称（如：阿哲、妈妈、李医生）
   - pet：宠物名或动物（如：团子、橘猫）
   - place：具体地点、城市、店铺或场景（如：西湖、老家、公司楼下咖啡馆）
   - concept：核心事件、物品、项目或意象（如：毕业旅行、吉他、考研、桂花树）
   - time：仅当回忆过去的特定年份时提取绝对年份（如“2019年”）。若文中出现“五年前”“前年”等可结合写作年份明确折算的表述，请折算为具体年份（如写于2026年且提“三年前”，则提取“2023年”）。严禁提取日记自身写作年份，严禁提取“小时候”“以前”“最近”等无法确定年份的模糊词。
   - 严禁将第一人称或泛指代词、虚词放入 entities（如：我、你、他、她、作者、用户、自己、大家、别人、一切、所有、东西、事情、今天、现在）。
2. relations 仅提取文中明确体现的实体间关系，优先使用规范关系词（朋友、家人、同事、恋人、位于、养了、喜欢、参与、发生于）：
   - 若关系涉及日记中的第一人称“我”，source 或 target 请统一填写「{owner_name}」（严禁输出“作者”或“用户”）。
   - 其他实体尽量对应 entities 或已知实体。

示例：
输入（写于 2026年05月10日）：
"今晚和阿哲在杭州西湖边散步，聊起2021年一起在成都租房的日子，我养的橘猫豆包现在胖了不少。想到下周又要加班，心里有点烦躁。"
输出：
{{
  "summary": "与阿哲在西湖散步怀念2021年成都合租时光",
  "mood": "烦躁",
  "entities": [
    {{"name": "阿哲", "entity_type": "person"}},
    {{"name": "杭州", "entity_type": "place"}},
    {{"name": "西湖", "entity_type": "place"}},
    {{"name": "成都", "entity_type": "place"}},
    {{"name": "2021年", "entity_type": "time"}},
    {{"name": "豆包", "entity_type": "pet"}}
  ],
  "relations": [
    {{"source": "{owner_name}", "relation": "养了", "target": "豆包"}},
    {{"source": "{owner_name}", "relation": "朋友", "target": "阿哲"}},
    {{"source": "西湖", "relation": "位于", "target": "杭州"}}
  ]
}}"""

        user_prompt = f"日记写作日期：{date_str}\n"
        if kb_hint:
            user_prompt += f"{kb_hint}\n"
        user_prompt += f"\n日记正文：\n\"\"\"{text[:4000]}\"\"\""

        clean_entities_map: Dict[str, Dict[str, Any]] = {}
        clean_relations: List[Dict[str, str]] = []
        mood_str = ""
        summary_str = ""

        try:
            base_url = self._resolve_base_url(settings.LLM_BASE_URL)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            if self._is_ollama(base_url, settings.LLM_API_KEY):
                ollama_root = self._ollama_root(base_url)
                ollama_payload: Dict[str, Any] = {
                    "model": settings.LLM_MODEL,
                    "messages": messages,
                    "stream": False,
                    "think": False,
                    "keep_alive": settings.OLLAMA_KEEP_ALIVE,
                    "format": "json",
                    "options": {
                        "temperature": 0.2,
                        "num_ctx": 8192
                    }
                }
                try:
                    res_obj = self._post_json(
                        f"{ollama_root}/api/chat",
                        "",
                        ollama_payload,
                        timeout=120.0
                    )
                except urllib.error.HTTPError as http_err:
                    if http_err.code == 400 and "think" in ollama_payload:
                        ollama_payload.pop("think", None)
                        res_obj = self._post_json(
                            f"{ollama_root}/api/chat",
                            "",
                            ollama_payload,
                            timeout=120.0
                        )
                    else:
                        raise
                raw = (res_obj.get("message", {}).get("content", "")).strip()
            else:
                payload: Dict[str, Any] = {
                    "model": settings.LLM_MODEL,
                    "messages": messages,
                    "temperature": 0.2,
                    "stream": False,
                    "response_format": {"type": "json_object"}
                }
                try:
                    res_obj = self._post_json(
                        f"{base_url}/chat/completions",
                        settings.LLM_API_KEY,
                        payload,
                        timeout=120.0
                    )
                except urllib.error.HTTPError as http_err:
                    if http_err.code == 400:
                        payload.pop("response_format", None)
                        res_obj = self._post_json(
                            f"{base_url}/chat/completions",
                            settings.LLM_API_KEY,
                            payload,
                            timeout=120.0
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
            raw_summary = str(parsed.get("summary") or "").strip()
            if raw_summary and len(raw_summary) >= 2:
                summary_str = raw_summary[:45]

            raw_mood = str(parsed.get("mood") or "").strip(" \t\r\n\"'“”‘’。，、")
            bad_mood_set = {
                "具体情绪词", "心境词", "情绪词", "心境", "情绪", "心情", "情绪词汇",
                "情绪词或空字符串", "null", "none", "未知", "无", "具体", "情感", "状态",
                "无情绪", "无明显情绪", "没有明显情绪", "暂无"
            }
            if raw_mood.lower() in bad_mood_set or any(b in raw_mood for b in ["心境词", "具体情绪词", "情绪词", "占位"]):
                mood_str = ""
            elif len(raw_mood) > 6:
                mood_str = raw_mood[:4]
            else:
                mood_str = raw_mood

            if not mood_str:
                mood_str = "平静"

            stop_words = {
                "你", "我", "他", "她", "它", "你们", "我们", "他们", "她们", "它们",
                "您", "谁", "大家", "别人", "某人", "对方", "自己", "所有人", "每个人",
                "作者", "用户", "本人", "日记主人",
                "有人", "无人", "那个", "这个", "这些", "那些", "某位", "一位", "一个",
                "一人", "俩人", "两人", "三人", "很多东西", "什么", "怎么", "之所以",
                "因为", "所以", "如果", "但是", "其实", "虽然", "只是", "感觉", "觉得",
                "好像", "似乎", "也许", "可能", "大概", "总之", "东西", "日记", "今天",
                "现在", "那天", "这时候", "那时候", "此时", "当时", "null", "none", "没有",
                "一切", "所有", "全部", "事情", "很多", "样子", "原因", "时候", "小时候",
                "去年", "前年", "以前", "当年", "最近", "多年", "几年前"
            }

            self_aliases = {"我", "作者", "用户", "本人", "自己", "日记主人"}
            rel_stop_words = stop_words - self_aliases

            for e in parsed.get("entities", []):
                raw_name = str(e.get("name") or "").strip()
                etype = str(e.get("entity_type") or "concept").strip()
                if etype not in {"person", "pet", "place", "time", "concept"}:
                    etype = "concept"
                if not raw_name or len(raw_name) > 15 or raw_name.lower() in stop_words:
                    continue

                if etype == "time":
                    year_match = re.search(r'(19\d\d|20\d\d)', raw_name)
                    if not year_match:
                        continue
                    extracted_year = year_match.group(1)
                    if diary_year and extracted_year == diary_year:
                        continue
                    raw_name = f"{extracted_year}年"

                canonical = knowledge_base.resolve_entity(raw_name)
                alias_target = knowledge_base.get_alias_mapping_for_name(raw_name)
                if alias_target and alias_target != raw_name:
                    clean_relations.append({
                        "source": raw_name,
                        "relation": "alias_of",
                        "target": canonical
                    })

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
                if (
                    s and rel and t
                    and s.lower() not in rel_stop_words
                    and t.lower() not in rel_stop_words
                    and len(s) <= 15 and len(t) <= 15 and len(rel) <= 12
                ):
                    rs = owner_name if s in self_aliases else knowledge_base.resolve_entity(s)
                    rt = owner_name if t in self_aliases else knowledge_base.resolve_entity(t)
                    if rs != rt:
                        clean_relations.append({
                            "source": rs,
                            "relation": rel,
                            "target": rt
                        })
        except Exception as e:
            print(f"[LLM extraction error]: {e}")
            if raise_on_error:
                raise

        # 结合知识库词典做保底扫描
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
        knowledge_base.auto_register_entities(final_entities)

        if not summary_str:
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            first_line = lines[0] if lines else text[:30]
            summary_str = first_line[:40]

        return {
            "summary": summary_str,
            "mood": mood_str,
            "entities": final_entities,
            "relations": clean_relations
        }

llm_service = LLMClient()
