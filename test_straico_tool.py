
# import asyncio
# import os
# from google.genai import types as genai_types
# from google.adk.models.llm_request import LlmRequest
# from google.adk.tools.base_tool import BaseTool
# from email_orchestrator.tools.straico_llm import StraicoLLM

# # Mock a simple tool
# class WeatherTool(BaseTool):
#     def __init__(self):
#         super().__init__(name="get_weather", description="Get the current weather for a location")

#     def declaration(self):
#         return genai_types.FunctionDeclaration(
#             name="get_weather",
#             description="Get the current weather for a location",
#             parameters=genai_types.Schema(
#                 type="object",
#                 properties={
#                     "location": genai_types.Schema(
#                         type="string",
#                         description="The city and state, e.g. San Francisco, CA"
#                     )
#                 },
#                 required=["location"]
#             )
#         )

# async def main():
#     print("Initializing StraicoLLM...")
#     llm = StraicoLLM(model="openai/gpt-4o-2024-08-06")
    
#     tool = WeatherTool()
    
#     # Construct a request
#     req = LlmRequest(
#         model="openai/gpt-4o-2024-08-06",
#         contents=[
#             genai_types.Content(
#                 role="user",
#                 parts=[genai_types.Part(text="Call the get_weather tool for San Francisco. Output ONLY a JSON object like: {\"tool\": \"get_weather\", \"arguments\": {\"location\": \"San Francisco\"}}")]
#             )
#         ],
#         tools_dict={"get_weather": tool},
#         config=genai_types.GenerateContentConfig(
#             temperature=0.0
#         )
#     )
    
#     print("Sending request...")
#     async for response in llm.generate_content_async(req):
#         print("\nResponse received:")
#         print(response)
#         if response.content and response.content.parts:
#             for part in response.content.parts:
#                 if part.function_call:
#                     print(f"✅ Tool Call Detected: {part.function_call}")
#                 if part.text:
#                     print(f"Text: {part.text}")

# if __name__ == "__main__":
#     asyncio.run(main())
