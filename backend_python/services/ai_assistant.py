"""
Advanced AI Assistant with semantic understanding, context handling, and conversational flows
"""
import requests
import json
import re
import logging
from config import settings
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AIAssistant:
    def __init__(self):
        self.ollama_url = settings.OLLAMA_URL
        self.model = "mistral"
        self.last_mentioned_task = None  # For context handling like "the previous one"
        logger.info(f"AIAssistant initialized with Ollama ({self.model}) at {self.ollama_url}")
    
    def build_system_prompt(self, tasks: list) -> str:
        """Build intelligent system prompt with full requirements"""
        tasks_description = self._format_tasks_for_prompt(tasks)
        
        return f"""You are an exceptional AI voice assistant for task management. Your primary goal is to have natural, conversational interactions while helping users manage their tasks.

CURRENT USER TASKS:
{tasks_description}

=== CORE RESPONSIBILITIES ===

1. **UNDERSTAND USER INTENT**: Detect if the user wants to:
   - CREATE_TASK: Add new tasks
   - READ_TASKS: Check tasks (with time filters: morning, afternoon, evening, today, tomorrow)
   - UPDATE_TASK: Modify existing tasks
   - DELETE_TASK: Remove tasks
   - CLARIFY: Ask follow-up questions when unclear

2. **SEMANTIC TIME UNDERSTANDING**:
   - "morning" = 6 AM to 12 PM
   - "afternoon" = 12 PM to 5 PM
   - "evening" = 5 PM to 9 PM
   - "tonight" = 5 PM to 12 AM
   - "tomorrow" = next calendar day
   - "today" = current date

3. **CONTEXT & REFERENCE HANDLING**:
   - Understand "the previous one", "it", "the second one"
   - Remember tasks mentioned in conversation
   - Handle pronouns and task references naturally
   - Track conversation flow

4. **MULTIPLE TASK HANDLING**:
   - Parse requests like "Create gym at 7 AM, team sync at 9 AM, and LinkedIn post at 11 AM"
   - Extract all tasks with their respective times
   - Format as separate CREATE_TASK actions

5. **CONFIRMATION & SAFETY**:
   - ALWAYS ask confirmation before DELETE: "Should I delete [task name]?"
   - Validate ambiguous requests: "Did you mean the 9:15 task?" when unclear
   - Get user agreement before destructive actions

6. **NATURAL CONVERSATION**:
   - Don't list tasks robotically. Summarize conversationally.
   - Example WRONG: "1. Sync at 2 PM 2. Deadline at 5 PM"
   - Example RIGHT: "You have a sync at 2 PM and a deadline at 5 PM today"
   - Ask clarifying questions when requests are ambiguous
   - Maintain conversational context

7. **ERROR HANDLING & RECOVERY**:
   - Gracefully handle unclear commands
   - Suggest alternatives if task not found
   - Recover naturally from errors

=== RESPONSE FORMAT ===

Your response MUST follow this format EXACTLY:

[RESPONSE]: Your conversational reply here (what the user hears)
[ACTION]: ACTION_TYPE (CREATE_TASK | CREATE_MULTIPLE_TASKS | READ_TASKS | UPDATE_TASK | DELETE_TASK | CLARIFY | NONE)
[DETAILS]: {{"key": "value", ...}}

Examples:

User: "Create a task for lunch at 12 PM"
[RESPONSE]: Got it! I've created a task for lunch at noon.
[ACTION]: CREATE_TASK
[DETAILS]: {{"title": "lunch", "dueTime": "12:00 PM"}}

User: "What are my evening tasks?"
[RESPONSE]: You have a product sync at 6 PM and a LinkedIn post at 8 PM tonight.
[ACTION]: READ_TASKS
[DETAILS]: {{"filter": "evening", "day": "today"}}

User: "Delete the lunch task"
[RESPONSE]: Should I delete the lunch task?
[ACTION]: CLARIFY
[DETAILS]: {{"requiresConfirmation": true, "taskName": "lunch", "taskId": "..."}}

User: "Create gym at 7 AM, sync at 9 AM, and LinkedIn at 11 AM tomorrow"
[RESPONSE]: I've created three tasks for tomorrow morning: gym at 7 AM, team sync at 9 AM, and LinkedIn post at 11 AM.
[ACTION]: CREATE_MULTIPLE_TASKS
[DETAILS]: {{"tasks": [{{"title": "gym", "dueTime": "7:00 AM"}}, {{"title": "sync", "dueTime": "9:00 AM"}}, {{"title": "LinkedIn", "dueTime": "11:00 AM"}}]}}

User: "Change the LinkedIn task to 6 PM"
[RESPONSE]: I'll update the LinkedIn post to 6 PM.
[ACTION]: UPDATE_TASK
[DETAILS]: {{"taskName": "LinkedIn", "newTime": "6:00 PM"}}

=== IMPORTANT CONSTRAINTS ===
- Keep responses concise (1-2 sentences usually)
- Never ask for clarification unless genuinely ambiguous
- Always confirm before deleting
- Handle multiple tasks elegantly
- Be warm and helpful in tone
- Format times consistently (12:00 PM format)
- Remember task context from conversation"""

    def _format_tasks_for_prompt(self, tasks: list) -> str:
        """Format tasks for system prompt with time grouping"""
        if not tasks:
            return "No tasks scheduled"
        
        today_tasks = []
        other_tasks = []
        
        for t in tasks:
            time_str = ""
            if t.get('dueTime'):
                time_str = f" at {t['dueTime']}"
            
            task_str = f"- {t['title']}{time_str}"
            
            # Group by today vs other
            if t.get('dueDate') and self._is_today(t['dueDate']):
                today_tasks.append(task_str)
            else:
                other_tasks.append(task_str)
        
        result = ""
        if today_tasks:
            result += "TODAY:\n" + "\n".join(today_tasks) + "\n"
        if other_tasks:
            if result:
                result += "\nOTHER DAYS:\n"
            else:
                result = "OTHER DAYS:\n"
            result += "\n".join(other_tasks)
        
        return result or "No tasks scheduled"
    
    def _is_today(self, date_str: str) -> bool:
        """Check if date string represents today"""
        try:
            task_date = datetime.fromisoformat(date_str).date()
            today = datetime.now().date()
            return task_date == today
        except:
            return False
    
    def process_user_message(self, user_message: str, messages_history: list, tasks: list) -> Dict[str, Any]:
        """Process user message with advanced AI"""
        try:
            system_prompt = self.build_system_prompt(tasks)
            
            # Prepare conversation history
            conversation_history = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages_history[-8:]  # Keep more context
            ]
            conversation_history.append({"role": "user", "content": user_message})
            
            logger.debug(f"Processing message: {user_message}")
            
            # Call Ollama
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        *conversation_history
                    ],
                    "stream": False,
                    "temperature": 0.7,
                },
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code}")
            
            ai_response = response.json().get("message", {}).get("content", "")
            logger.debug(f"AI Response: {ai_response}")
            
            # Parse structured response
            response_text = self._extract_section(ai_response, "RESPONSE")
            action = self._extract_section(ai_response, "ACTION")
            details_str = self._extract_section(ai_response, "DETAILS")
            
            try:
                details = json.loads(details_str) if details_str else {}
            except json.JSONDecodeError:
                details = {}
            
            # Normalize action
            action = (action or "NONE").strip().upper()
            
            # Post-process to enhance action details based on context
            if action == "DELETE_TASK":
                self._enhance_delete_action(details, tasks)
            elif action == "UPDATE_TASK":
                self._enhance_update_action(details, tasks)
            
            # Post-process to extract missing times and other details
            details = self._post_process_details(action, details, user_message)
            
            return {
                "response": response_text or ai_response,
                "action": action,
                "actionDetails": details,
            }
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "response": "I had trouble processing that. Could you repeat?",
                "action": "NONE",
                "actionDetails": {},
            }
    
    def _extract_section(self, response: str, section: str) -> str:
        """Extract [SECTION]: content from response"""
        pattern = rf"\[{section}\]:\s*(.+?)(?=\[|$)"
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    def _extract_time_from_text(self, text: str) -> Optional[str]:
        """Extract time from text like 'at 12 pm', 'at noon', '12:30 AM', etc."""
        import re
        from datetime import datetime
        
        # Common time patterns (with optional periods for a.m./p.m.)
        patterns = [
            r'\bat\s+(\d{1,2}):?(\d{2})?\s*(a\.?m\.?|p\.?m\.?)',  # "at 12 pm", "at 12 p.m.", "at 12:30 AM"
            r'\b(noon|midnight)\b',  # "at noon"
            r'\b(\d{1,2}):?(\d{2})?\s*(a\.?m\.?|p\.?m\.?)',  # Just time like "5 PM"
            r'\b(morning|afternoon|evening|tonight)\b',  # "in the morning"
        ]
        
        text_lower = text.lower()
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                matched_text = match.group(0)
                
                # Handle specific keywords
                if 'noon' in matched_text:
                    return '12:00 PM'
                elif 'midnight' in matched_text:
                    return '12:00 AM'
                elif 'morning' in matched_text:
                    return '9:00 AM'
                elif 'afternoon' in matched_text:
                    return '2:00 PM'
                elif 'evening' in matched_text or 'tonight' in matched_text:
                    return '6:00 PM'
                else:
                    # Parse time groups
                    groups = match.groups()
                    hour = groups[0] if groups else None
                    minute = groups[1] if len(groups) > 1 else None
                    period = groups[2] if len(groups) > 2 else 'am'
                    
                    if hour:
                        hour = int(hour)
                        minute = int(minute) if minute else 0
                        period = period.lower()
                        
                        # Format as 12-hour time
                        return f"{hour:02d}:{minute:02d} {period.upper()}"
        
        return None

    def _post_process_details(self, action: str, details: dict, user_message: str) -> dict:
        """Post-process AI response details to extract missing times, etc."""
        # If CREATE_TASK and no time was extracted by AI, try to extract from user message
        if action == "CREATE_TASK" and "dueTime" not in details:
            extracted_time = self._extract_time_from_text(user_message)
            if extracted_time:
                details["dueTime"] = extracted_time
                logger.info(f"Post-processing extracted time: {extracted_time}")
        
        # If CREATE_MULTIPLE_TASKS and some tasks missing times
        if action == "CREATE_MULTIPLE_TASKS":
            tasks = details.get("tasks", [])
            for task_info in tasks:
                if "dueTime" not in task_info or not task_info["dueTime"]:
                    # Look for time in context around title
                    extracted_time = self._extract_time_from_text(user_message)
                    if extracted_time:
                        task_info["dueTime"] = extracted_time
        
        return details
    def _enhance_delete_action(self, details: dict, tasks: list):
        """Add task ID if only name provided"""
        if "taskName" in details and "taskId" not in details:
            for task in tasks:
                title = task.get('title') or ''
                if title.lower() == details['taskName'].lower():
                    details["taskId"] = task['id']
                    break

    def _enhance_update_action(self, details: dict, tasks: list):
        """Add task ID if only name provided"""
        if "taskName" in details and "taskId" not in details:
            for task in tasks:
                title = task.get('title') or ''
                if title.lower() == details['taskName'].lower():
                    details["taskId"] = task['id']
                    break
