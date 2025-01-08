from autogen import AssistantAgent
from autogen.coding import LocalCommandLineCodeExecutor


'''
User 정보 기입
- 메일을 보낼 사용자와 받을 사용자의 정보를 기입하세요.
- sender_email : 구글 이메일을 기입하세요
- password : 구글 앱 비밀번호를 입력하세요 (참고: https://myaccount.google.com/apppasswords)
- receiver_email : 결과 보고를 받을 이메일을 기입하세요. 
'''
### 변경필요
sender_email = "aaa@gmail.com"
password = "xxxx xxxx xxxx xxxx"
receiver_email = "bbb@xxx.xxx"
###

llm_config={
    "config_list": [
        {
            "model": "Korean", 
            "api_key": "ollama", 
            "base_url": "http://localhost:11434/v1"  
        }
    ],
    "cache_seed": None
}

executor = LocalCommandLineCodeExecutor( 
    timeout=3600,
    work_dir="./"
)


'''
사용된 Agent 종류 
1. docker_log_collector : docker 실행 결과에 대한 로그를 가져옵니다.
2. email_writer : 로그 결과를 분석하여 이메일 내용을 작성합니다.
3. email_sender : 관리자에게 이메일을 전송합니다. 
'''


docker_executor = AssistantAgent(
    name="docker executor",
    system_message="""Log Search""",
    llm_config=False, 
    code_execution_config={"executor": executor, "verbose": True},
    human_input_mode="NEVER"
)

email_writer = AssistantAgent(
    name="email writer",
    llm_config=llm_config,
    system_message="""
    당신은 개발팀의 시스템 모니터링 담당자입니다. 
    당신은 컨테이너에 오류가 발생했을때 오류내용을 판별하여 이메일을 작성합니다. 

    ## 컨테이너 오류가 발생했을 때
    
        개발자에게 명확하고 전문적인 에러 리포트 이메일을 작성해야 합니다.
    
        아래 형식으로 에러 내용을 분석하여 이메일을 작성해주세요:
        
        입력된 에러 로그:

        [실패] 일부 컨테이너에서 오류가 발생했습니다.

        발생 시간: {timestamp}

        발생한 오류:

        {container_name} | {error_message}

        비정상 종료된 컨테이너:

        {container_status}
        
        요구사항:

        1. 이메일 제목은 "[오류 보고]"로 시작하고 핵심 문제를 간단히 포함할 것

        2. 다음 섹션들을 반드시 포함할 것:

        - 오류 발견 내용: 영향받은 컨테이너, 오류 유형, 구체적 오류 메시지

        - 예상되는 원인: 기술적 관점에서 가능성 있는 원인 설명

        - 권장 해결 방안: numbered list로 구체적인 해결 단계 제시

        3. 전문적이고 명확한 어조를 유지할 것

        4. 긴급성을 암시하되 정중한 톤을 유지할 것

        5. 추가 지원 가능함을 언급하며 마무리할 것
        
        위 요구사항에 맞춰 전문적인 에러 리포트 이메일을 작성해주세요.
    """
)

email_sender = AssistantAgent(
    name="email sender",
    system_message="You are an agent who execute an email transfer code.",
    llm_config=False, 
    code_execution_config={
        "executor": executor, 
        "verbose": True,
    },
    human_input_mode="NEVER",
    default_auto_reply="Please continue. If everything is done, reply 'TERMINATE'."
)

# 1. 로그 확인
docker_executor_message = """This is a message with code block.
The code block is below:
```python
import subprocess
result = subprocess.run(["cat", "prophet-container.log"], capture_output=True, text=True)
print("stdout:", result.stdout.split("Process Result:")[-1])
```
This is the end of the message."""
execution_result = docker_executor.generate_reply(messages=[{"role": "user", "content": docker_executor_message}])

# 2. 이메일 작성
writer_result = email_writer.generate_reply(messages=[{"content": execution_result, "role": "user"}])
email = str(writer_result)
title = email[0:80].replace('\n', ' ').strip()
content = email

# 3. 이메일 전송
email_code = f"""This is a message with code block.
The code block is below:
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

message = MIMEMultipart()
message["From"] = "{sender_email}"
message["To"] = "{receiver_email}"
message["Subject"] = f'''{title}'''

body = '''{content}'''
message.attach(MIMEText(body, "plain"))

try:
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login("{sender_email}", "{password}")
        server.send_message(message)
        print("Email sent successfully!")
except Exception as e:
    print(f"Error occurred: {{e}}")
```
This is the end of the message."""

reply = email_sender.generate_reply(messages=[{"role": "user", "content": email_code}])
print("send_result---------", reply)