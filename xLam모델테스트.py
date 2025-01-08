from typing import Dict, List
import json
from autogen import ConversableAgent, UserProxyAgent

def call_openweather_api(location: str, unit: str = "fahrenheit") -> str:
    print(f"OpenWeather API 실행: {location}, {unit}")
    return f"현재 {location}의 날씨는 맑음, 기온 {20 if unit == 'celsius' else 68}도입니다."

def call_calendar_api() -> str:
    print("Google Calendar API 실행")
    return "오늘의 일정: 회의 2건이 있습니다."

class XLamAgent(ConversableAgent):
    def __init__(self, name: str, llm_config: dict):
        system_message = self._get_system_message()
        super().__init__(
            name=name,
            llm_config=llm_config,
            system_message=system_message
        )
        self._register_functions()
    
    def _register_functions(self):
        self._function_map = {
            "get_weather": call_openweather_api,
            "get_calendar": call_calendar_api
        }

    def _get_system_message(self) -> str:
        tools = [
            {
                "name": "get_weather",
                "description": "Get current weather information for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name (e.g., New York, Seoul)"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Temperature unit"
                        }
                    },
                    "required": ["location"]
                }
            },
            {
                "name": "get_calendar",
                "description": "Get today's calendar events",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]
        return f"""You are an AI assistant that helps with function calling.
Available functions: {json.dumps(tools, indent=2)}

Rules:
1. ONLY use the functions listed above
2. If a function requires parameters, make sure to provide them
3. Return response in this exact JSON format:
{{
    "tool_calls": [
        {{
            "name": "function_name",
            "arguments": {{
                "param1": "value1",
                "param2": "value2"
            }}
        }}
    ]
}}
"""

    def run_function(self, func_name: str, arguments: dict) -> str:
        """실제 함수를 실행하고 결과를 반환하는 메서드"""
        if func_name not in self._function_map:
            return f"Error: Function {func_name} not found"
        return self._function_map[func_name](**arguments)

    async def _process_message(self, message: str) -> str:
        try:
            # LLM에 메시지 전송
            response = await self.llm.create_chat_completion(
                messages=[{
                    'role': 'system',
                    'content': self.system_message
                }, {
                    'role': 'user',
                    'content': message
                }]
            )
            
            # ChatResult에서 content 추출
            if hasattr(response, 'chat_history'):
                response_text = response.chat_history[-1]['content']
            else:
                response_text = response

            # JSON 파싱
            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError:
                return "Error: Invalid response format from LLM"

            # tool_calls 처리
            tool_calls = response_data.get('tool_calls', [])
            if not tool_calls:
                return "No valid function call found in response"

            # 첫 번째 tool call 실행
            tool_call = tool_calls[0]
            func_name = tool_call.get('name')
            arguments = tool_call.get('arguments', {})

            # 함수 실행
            result = self.run_function(func_name, arguments)
            print(f"Function Result: {result}")  # 디버깅을 위한 출력
            return result

        except Exception as e:
            return f"Error occurred: {str(e)}"

def main():
    # LLM 설정
    llm_config = {
        "config_list": [{
            "model": "xLAM",
            "base_url": "http://localhost:4000",
            "api_key": "not-needed"
        }],
        "cache_seed": None
    }

    # 에이전트 생성
    assistant = XLamAgent("assistant", llm_config=llm_config)
    user_proxy = UserProxyAgent(
        name="user",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1,
        is_termination_msg=lambda x: "TERMINATE" in str(x.get("content", ""))
    )

    # 테스트 실행
    test_queries = [
        "What's the weather like in New York in fahrenheit?",
        "What's my schedule for today?",
        "What's the weather like in Seoul in celsius?",
        "TERMINATE"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            chat_response = assistant.initiate_chat(user_proxy, message=query)
            print(f"Chat Response: {chat_response}")
            
            # 채팅 히스토리에서 마지막 응답 확인
            if hasattr(chat_response, 'chat_history') and chat_response.chat_history:
                last_response = chat_response.chat_history[-1]['content']
                try:
                    response_data = json.loads(last_response)
                    if 'tool_calls' in response_data:
                        tool_call = response_data['tool_calls'][0]
                        func_name = tool_call['name']
                        arguments = tool_call['arguments']
                        result = assistant.run_function(func_name, arguments)
                        print(f"Function Execution Result: {result}")
                except json.JSONDecodeError:
                    pass
                
        except Exception as e:
            print(f"Error: {str(e)}")
        print("-" * 50)

if __name__ == "__main__":
    main()