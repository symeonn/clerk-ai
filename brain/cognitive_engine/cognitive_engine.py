"""
Cognitive Engine - LLM-Powered Reasoning Component

Receives structured input, performs cognitive analysis using OpenAI API, outputs JSON only.
No file I/O. No scheduling. No orchestration. No side effects.

Core Principle: All cognitive work done by OpenAI model with temperature=0 for determinism.
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))


class CognitiveEngineError(Exception):
    """Base exception for cognitive engine errors."""
    pass


class ValidationError(CognitiveEngineError):
    """Raised when output validation fails."""
    pass


def normalize_time_format(time_input) -> str:
    """
    Normalize time to HH:MM:SS format (Obsidian format).
    
    Handles common format issues:
    - 660 (minutes) -> "11:00:00"
    - "1320" -> "13:20:00" (missing colon)
    - "13:20:00" -> "13:20:00" (already correct)
    - "13:20" -> "13:20:00" (add seconds)
    - Validates final format
    
    Args:
        time_input: Time as int (minutes), or string in various formats
        
    Returns:
        Normalized time in HH:MM:SS format
        
    Raises:
        ValueError: If time cannot be normalized to valid HH:MM:SS format
    """
    if not time_input and time_input != 0:
        return time_input
    
    # Handle integer input (minutes since midnight)
    if isinstance(time_input, int):
        if 0 <= time_input <= 1440:  # Valid range: 0-1440 minutes (0-24 hours)
            hours = time_input // 60
            minutes = time_input % 60
            time_str = f"{hours:02d}:{minutes:02d}:00"
            return time_str
        else:
            raise ValueError(f"Invalid minutes value: {time_input} (must be 0-1440)")
    
    # Convert to string for remaining validations
    time_str = str(time_input).strip()
    
    # If already in HH:MM:SS format, return as-is
    if re.match(r'^\d{2}:\d{2}:\d{2}$', time_str):
        return time_str
    
    # If in HH:MM format, add seconds
    if re.match(r'^\d{2}:\d{2}$', time_str):
        return time_str + ":00"
    
    # Try to handle HHMM format (no colon) - convert to HH:MM:SS
    if re.match(r'^\d{4}$', time_str):
        hours = time_str[:2]
        minutes = time_str[2:4]
        time_str = f"{hours}:{minutes}:00"
    
    # Validate final format
    if not re.match(r'^\d{2}:\d{2}:\d{2}$', time_str):
        raise ValueError(f"Cannot normalize time format: {time_str}")
    
    return time_str


class CognitiveEngine:
    """
    Stateless, deterministic cognitive engine powered by OpenAI API.
    
    All cognitive tasks (classification, summarization, confidence, scoring,
    routing, tap detection) are performed by a single LLM call with structured output.
    """
    
    def __init__(self):
        """Initialize the cognitive engine with OpenAI client."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise CognitiveEngineError("OPENAI_API_KEY environment variable not set")
        
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    def process(self, input_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for cognitive processing.
        
        Input:
        {
            "id": "string",
            "text": "string",
            "source": "string",
            "timestamp": "ISO-8601 string",
            "existing_projects": ["project_name_1", ...],
            "recent_context": [{"text": "...", "project": "..."}],  # Optional
            "available_tags": ["tag_1", "tag_2", ...],  # Optional
            "today": "YYYY-MM-DD"
        }
        
        Output: Validated JSON conforming to schema
        """
        # Extract input fields
        item_id = input_json.get('id', '')
        text = input_json.get('text', '')
        existing_projects = input_json.get('existing_projects', [])
        recent_context = input_json.get('recent_context', [])
        available_tags = input_json.get('available_tags', [])
        today = input_json.get('today', datetime.now().strftime('%Y-%m-%d'))
        
        # Call LLM for all cognitive tasks
        llm_output = self._call_llm(text, existing_projects, recent_context, available_tags, today)
        
        # Add ID to output
        llm_output['id'] = item_id
        
        # Validate output
        self._validate_output(llm_output)
        
        return llm_output
    
    def _call_llm(self, text: str, existing_projects: List[str], recent_context: List[Dict[str, str]], available_tags: List[str], today: str) -> Dict[str, Any]:
        """
        Call OpenAI API with structured output for all cognitive tasks.
        
        Temperature = 0 for determinism.
        Uses JSON schema enforcement.
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(text, existing_projects, recent_context, available_tags, today)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0  # Deterministic
            )
            
            content = response.choices[0].message.content
            if content is None:
                raise CognitiveEngineError("LLM returned empty response")
            
            result = json.loads(content)
            return result
            
        except json.JSONDecodeError as e:
            raise CognitiveEngineError(f"Failed to parse LLM JSON output: {e}")
        except Exception as e:
            raise CognitiveEngineError(f"LLM API call failed: {e}")
    
    def _build_system_prompt(self) -> str:
        """Load the system prompt from SYSTEM_PROMPT.md file."""
        prompt_path = os.path.join(os.path.dirname(__file__), 'SYSTEM_PROMPT.md')
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise CognitiveEngineError(f"System prompt file not found: {prompt_path}")
        except Exception as e:
            raise CognitiveEngineError(f"Failed to load system prompt: {e}")
    
    def _build_user_prompt(self, text: str, existing_projects: List[str], recent_context: List[Dict[str, str]], available_tags: List[str], today: str) -> str:
        """Build the user prompt with input data and schema."""
        existing_projects_str = json.dumps(existing_projects)
        recent_context_str = json.dumps(recent_context) if recent_context else "[]"
        available_tags_str = json.dumps(available_tags) if available_tags else "[]"
        
        return f"""Analyze this input:
        
        TEXT: "{text}"
        EXISTING_PROJECTS: {existing_projects_str}
        RECENT_CONTEXT: {recent_context_str}
        AVAILABLE_TAGS: {available_tags_str}
        TODAY: {today}
        
        Return a JSON object with this EXACT schema:
        
        {{
          "classification": "project | note | event | review",
          "summary": "string (1-2 sentences)",
          "confidence": 0.0,
          "score": 0.0,
          "tags": ["tag1", "tag2", "tag3"],
          "routing": {{
            "type": "project | note | event | review",
            "project": {{
              "name": "string",
              "is_new": true,
              "next_action": "string"
            }},
            "event": {{
              "due_date": "YYYY-MM-DD or null",
              "time": "HH:MM:SS or null",
              "all_day": false
            }}
          }},
          "tap_on_the_shoulder": {{
            "date": "{today}",
            "candidates": [
              {{
                "reason": "string",
                "score": 0.0
              }}
            ]
          }}
        }}
        
        IMPORTANT:
        - Generate maximum 3 Obsidian tags based on context in the "tags" field
        - Prefer reusing tags from AVAILABLE_TAGS when appropriate
        - Create new tags only when existing tags don't fit the content
        - Tags should be lowercase, use underscores for multi-word tags (e.g., "machine_learning")
        - If no suitable tags, use empty array []
        - If routing.type == "project", include "project" field with name, is_new, and next_action
        - If routing.type == "event", include "event" field with due_date, time, and all_day
          * If time is present in message: extract time in HH:MM:SS format (Obsidian format), set all_day to false
          * If time is NOT present: set time to null, set all_day to true
        - If routing.type is "note" or "review", omit both "project" and "event" fields
        - tap_on_the_shoulder.candidates max length is 3
        - If no tap candidates, use empty array []
        - confidence < 0.6 means classification AND routing.type must be "review"
        - Use RECENT_CONTEXT to identify related messages and group them under the same project name
        - For events: parse relative dates like "tomorrow", "next week" using TODAY as reference
        
        Return ONLY the JSON object, nothing else."""
    
    def _validate_output(self, output: Dict[str, Any]) -> None:
        """
        Validate LLM output against schema and business rules.
        Raises ValidationError if invalid.
        """
        # Required top-level fields
        required_fields = ['classification', 'summary', 'confidence', 'score', 'tags', 'routing', 'tap_on_the_shoulder']
        for field in required_fields:
            if field not in output:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate tags
        tags = output['tags']
        if not isinstance(tags, list):
            raise ValidationError("tags must be an array")
        
        if len(tags) > 3:
            raise ValidationError(f"tags has {len(tags)} items, max is 3")
        
        for i, tag in enumerate(tags):
            if not isinstance(tag, str):
                raise ValidationError(f"Tag {i} must be a string")
        
        # Validate classification
        valid_classifications = ['project', 'note', 'event', 'review']
        if output['classification'] not in valid_classifications:
            raise ValidationError(f"Invalid classification: {output['classification']}")
        
        # Validate confidence range
        confidence = output['confidence']
        if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
            raise ValidationError(f"Invalid confidence value: {confidence}")
        
        # Validate score range
        score = output['score']
        if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
            raise ValidationError(f"Invalid score value: {score}")
        
        # Validate routing
        if 'type' not in output['routing']:
            raise ValidationError("Missing routing.type")
        
        routing_type = output['routing']['type']
        if routing_type not in valid_classifications:
            raise ValidationError(f"Invalid routing.type: {routing_type}")
        
        # Validate confidence threshold rule
        if confidence < 0.6 and routing_type != 'review':
            raise ValidationError(f"Confidence {confidence} < 0.6 but routing is not 'review'")
        
        # Validate project object consistency
        if routing_type == 'project':
            if 'project' not in output['routing']:
                raise ValidationError("routing.type is 'project' but project object missing")
            
            project = output['routing']['project']
            if 'name' not in project or 'is_new' not in project:
                raise ValidationError("project object missing required fields (name, is_new)")
            
            if not isinstance(project['is_new'], bool):
                raise ValidationError("project.is_new must be boolean")
            
            # next_action is optional but should be a string if present
            if 'next_action' in project and project['next_action'] is not None:
                if not isinstance(project['next_action'], str):
                    raise ValidationError("project.next_action must be string or null")
        else:
            # If not routing to project, project field should not exist
            if 'project' in output['routing'] and output['routing']['project'] is not None:
                # Remove it to enforce schema
                output['routing']['project'] = None
        
        # Validate event object consistency
        if routing_type == 'event':
            if 'event' not in output['routing']:
                raise ValidationError("routing.type is 'event' but event object missing")
            
            event = output['routing']['event']
            if 'due_date' not in event:
                raise ValidationError("event object missing required field (due_date)")
            
            # due_date can be null or a string in YYYY-MM-DD format
            due_date = event['due_date']
            if due_date is not None and not isinstance(due_date, str):
                raise ValidationError("event.due_date must be string or null")
            
            # time is optional, can be null or HH:MM:SS format
            if 'time' in event:
                time = event['time']
                if time is not None:
                    # Normalize and validate time format (handles int, HH:MM, HH:MM:SS, etc.)
                    try:
                        normalized_time = normalize_time_format(time)
                        event['time'] = normalized_time
                    except ValueError as e:
                        raise ValidationError(f"Invalid time format '{time}': {e}")
            else:
                # Set default value if not provided by LLM
                event['time'] = None
            
            # all_day is optional, defaults based on time presence
            if 'all_day' in event:
                all_day = event['all_day']
                if not isinstance(all_day, bool):
                    raise ValidationError("event.all_day must be boolean")
            else:
                # Set default: true if no time, false if time exists
                event['all_day'] = event.get('time') is None
        else:
            # If not routing to event, event field should not exist
            if 'event' in output['routing'] and output['routing']['event'] is not None:
                # Remove it to enforce schema
                output['routing']['event'] = None
        
        # Validate tap_on_the_shoulder
        tap = output['tap_on_the_shoulder']
        if 'date' not in tap or 'candidates' not in tap:
            raise ValidationError("tap_on_the_shoulder missing required fields")
        
        candidates = tap['candidates']
        if not isinstance(candidates, list):
            raise ValidationError("tap_on_the_shoulder.candidates must be array")
        
        if len(candidates) > 3:
            raise ValidationError(f"tap_on_the_shoulder.candidates has {len(candidates)} items, max is 3")
        
        # Validate each candidate
        for i, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                raise ValidationError(f"Candidate {i} is not an object")
            
            if 'reason' not in candidate or 'score' not in candidate:
                raise ValidationError(f"Candidate {i} missing required fields")
            
            cand_score = candidate['score']
            if not isinstance(cand_score, (int, float)) or not (0.0 <= cand_score <= 1.0):
                raise ValidationError(f"Candidate {i} has invalid score: {cand_score}")


# Legacy function-based interface for backward compatibility
def process_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy function interface for backward compatibility.
    Creates engine instance and processes input.
    """
    engine = CognitiveEngine()
    return engine.process(input_data)


def main():
    """
    CLI entry point: read JSON from stdin, output JSON to stdout.
    """
    import sys
    
    try:
        input_data = json.load(sys.stdin)
        engine = CognitiveEngine()
        output = engine.process(input_data)
        print(json.dumps(output, indent=2))
    except json.JSONDecodeError as e:
        error_output = {
            "error": "Invalid JSON input",
            "details": str(e)
        }
        print(json.dumps(error_output, indent=2), file=sys.stderr)
        sys.exit(1)
    except CognitiveEngineError as e:
        error_output = {
            "error": "Cognitive engine error",
            "details": str(e)
        }
        print(json.dumps(error_output, indent=2), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        error_output = {
            "error": "Processing error",
            "details": str(e)
        }
        print(json.dumps(error_output, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
