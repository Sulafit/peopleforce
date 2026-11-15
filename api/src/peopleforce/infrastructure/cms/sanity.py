"""Sanity adapter: one GROQ query returns the whole published path in the `LearningPath` shape."""

from typing import Any

import httpx

# Field names in Sanity are camelCase; the projection renames them to the API's snake_case shape.
# `perspective=published` on the request guarantees drafts are never returned.
PATH_QUERY = """
*[_type == "learningPath" && domain->slug.current == $domain][0]{
  "id": slug.current,
  "domain": domain->slug.current,
  title,
  "avatars": avatars,
  "more_coming": moreComing,
  "daily_challenges": dailyChallenges[]{
    key, title, intro, xp,
    "action": action[0]{
      "type": _type, key, title, instructions,
      "confirm_label": confirmLabel,
      "submit_label": submitLabel,
      "passing_score": passingScore,
      "target_count": targetCount, unit, tips,
      "fields": fields[]{
        name, label, help, placeholder, multiline,
        "min_length": minLength, "max_length": maxLength,
        "examples": examples
      },
      "questions": questions[]{
        "id": key, prompt, explanation,
        "correct_option_id": correctOptionId,
        "options": options[]{ "id": key, label }
      }
    }
  },
  "achievements": achievements[]{
    key, title, description,
    "trigger": trigger{ type, "lesson_id": lesson->slug.current, count, "asset_type": assetType }
  },
  "chapters": chapters[]->{
    "id": slug.current, theme, tier, title, blurb,
    "lessons": lessons[]->{
      "id": slug.current, title, minutes, xp, summary, output,
      "parts": parts[]{ kind, title, minutes },
      "content": {
        "blocks": blocks[]{
          "type": _type, key, title, body, tone, intro,
          "body_by_specialization": bodyBySpecialization,
          "video_id": videoId,
          "links": links[]{ label, url, description },
          "action_keys": actionKeys
        },
        "actions": actions[]{
          "type": _type, key, title, instructions, required, capability,
          "depends_on": dependsOn,
          "confirm_label": confirmLabel,
          "submit_label": submitLabel,
          "source_action_key": sourceActionKey,
          "asset_type": assetType,
          "passing_score": passingScore,
      "target_count": targetCount, unit, tips,
          completion,
          "fields": fields[]{
            name, label, help, placeholder, multiline,
            "min_length": minLength, "max_length": maxLength,
            "examples": examples
          },
          "questions": questions[]{
            "id": key, prompt, explanation,
            "correct_option_id": correctOptionId,
            "options": options[]{ "id": key, label }
          }
        }
      }
    }
  }
}
"""


def _strip_nulls(value: Any) -> Any:
    """GROQ returns null for absent fields; drop them so Pydantic defaults apply."""
    if isinstance(value, dict):
        return {k: _strip_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_strip_nulls(v) for v in value]
    return value


def _key_value_list_to_dict(value: Any) -> Any:
    """Sanity has no map type: maps are stored as [{key, value}] arrays."""
    if isinstance(value, list) and all(isinstance(i, dict) and "key" in i and "value" in i for i in value):
        return {i["key"]: i["value"] for i in value}
    return value


# Sanity type names are global, so the Studio suffixes them ("quizBlock" vs "quizAction").
TYPE_NAMES = {
    "markdownBlock": "markdown",
    "youtubeBlock": "youtube",
    "calloutBlock": "callout",
    "resourcesBlock": "resources",
    "actionGroupBlock": "action_group",
    "quizBlock": "quiz",
    "aiFeedbackBlock": "ai_feedback",
    "acknowledgeAction": "acknowledge",
    "textSubmissionAction": "text_submission",
    "quizAction": "quiz",
    "aiReviewAction": "ai_review",
    "saveAssetAction": "save_asset",
    "externalTaskAction": "external_task",
}


def normalize(node: Any) -> Any:
    """Turn a GROQ result into the plain `LearningPath` shape (still unvalidated)."""
    return _normalize(_strip_nulls(node))


def _normalize(node: Any) -> Any:
    if isinstance(node, dict):
        out = {k: _normalize(v) for k, v in node.items()}
        if isinstance(out.get("type"), str):
            out["type"] = TYPE_NAMES.get(out["type"], out["type"])
        for map_field in ("examples", "body_by_specialization"):
            if map_field in out:
                out[map_field] = _key_value_list_to_dict(out[map_field])
        return out
    if isinstance(node, list):
        return [_normalize(v) for v in node]
    return node


class SanityContentSource:
    name = "sanity"

    def __init__(self, project_id: str, dataset: str, api_version: str, token: str = "") -> None:
        self._url = f"https://{project_id}.api.sanity.io/v{api_version}/data/query/{dataset}"
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

    async def fetch_path(self, domain: str) -> dict[str, Any] | None:
        params = {"query": PATH_QUERY, "$domain": f'"{domain}"', "perspective": "published"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self._url, params=params, headers=self._headers)
        response.raise_for_status()
        result = response.json().get("result")
        if not result:
            return None
        return normalize(result)
