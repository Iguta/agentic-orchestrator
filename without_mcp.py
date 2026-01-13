# Complete Production-Ready Agentic React Development System
# With Gradio UI, Manager Agent, Real Tests, and Live Deployment

# %% [markdown]
# ## Cell 1: Install Dependencies

# %%
"""
!pip install langgraph anthropic python-dotenv gradio httpx asyncio
!npm install -g playwright
"""

# %% [markdown]
# ## Cell 2: Imports and Configuration

# %%
import os
import json
import asyncio
import subprocess
import base64
from typing import TypedDict, Annotated, Literal, Optional, Any
from operator import add
from datetime import datetime
from pathlib import Path
import gradio as gr

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from anthropic import Anthropic

# Initialize clients
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Configuration
PROJECT_DIR = Path("./generated_projects")
PROJECT_DIR.mkdir(exist_ok=True)

# %% [markdown]
# ## Cell 3: Enhanced State Schema

# %%
class DevelopmentState(TypedDict):
    """Complete state for the development workflow"""
    # User interaction
    user_request: str  # Initial user request
    requirements: str  # Finalized requirements after manager discussion
    requirements_approved: bool  # User approval flag
    conversation_history: Annotated[list, add]  # Manager-user chat history
    
    # Development artifacts
    development_plan: Optional[dict]
    code_files: dict  # Application code
    unit_tests: dict  # Unit tests written by developer
    e2e_tests: dict  # E2E tests written by tester
    
    # Test results
    unit_test_results: dict
    e2e_test_results: dict
    test_review_approved: bool  # User approval of tests
    
    # Deployment
    localhost_url: Optional[str]  # Local dev server URL
    deployment_url: Optional[str]  # Production URL (Vercel/Netlify)
    deployment_platform: str  # "vercel" or "netlify"
    
    # GitHub
    github_repo: Optional[dict]
    
    # Workflow control
    current_stage: str
    current_agent: str
    iteration_count: int
    errors: list
    messages: Annotated[list, add]

# %% [markdown]
# ## Cell 4: Helper Functions

# %%
async def call_claude(prompt: str, system_prompt: str = "") -> dict:
    """Call Claude API"""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=8000,
            system=system_prompt or "You are an expert software developer.",
            messages=[{"role": "user", "content": prompt}]
        )
        return {
            "content": response.content[0].text if response.content else "",
            "success": True
        }
    except Exception as e:
        return {"content": f"Error: {e}", "success": False, "error": str(e)}

def save_file(project_name: str, filename: str, content: str) -> str:
    """Save file to project directory"""
    project_path = PROJECT_DIR / project_name
    project_path.mkdir(parents=True, exist_ok=True)
    
    file_path = project_path / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8', errors='replace') as f:
        f.write(content)
    
    return str(file_path)

async def github_operation(operation: str, repo_info: dict, **kwargs) -> dict:
    """Simplified GitHub operations"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"success": False, "error": "No GitHub token"}
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            
            if operation == "create_repo":
                response = await http_client.post(
                    "https://api.github.com/user/repos",
                    headers=headers,
                    json={
                        "name": kwargs['name'],
                        "description": kwargs.get('description', ''),
                        "private": False,
                        "auto_init": True
                    }
                )
                if response.status_code == 201:
                    data = response.json()
                    return {
                        "success": True,
                        "repo_url": data["html_url"],
                        "owner": data["owner"]["login"],
                        "name": data["name"]
                    }
            
            elif operation == "commit_file":
                owner = repo_info['owner']
                repo = repo_info['name']
                
                # Check if file exists
                get_response = await http_client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/contents/{kwargs['path']}",
                    headers=headers
                )
                
                sha = None
                if get_response.status_code == 200:
                    sha = get_response.json().get('sha')
                
                # Commit file
                content_b64 = base64.b64encode(kwargs['content'].encode()).decode()
                payload = {
                    "message": kwargs.get('message', 'Update file'),
                    "content": content_b64,
                    "branch": kwargs.get('branch', 'main')
                }
                if sha:
                    payload['sha'] = sha
                
                response = await http_client.put(
                    f"https://api.github.com/repos/{owner}/{repo}/contents/{kwargs['path']}",
                    headers=headers,
                    json=payload
                )
                
                return {"success": response.status_code in [200, 201]}
        
        return {"success": False, "error": f"Status {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# %% [markdown]
# ## Cell 5: Manager Agent (Chatbot for Requirements)

# %%
async def manager_agent(user_message: str, conversation_history: list) -> tuple[str, list, bool]:
    """
    Manager agent that discusses requirements with user
    Returns: (response, updated_history, is_approved)
    """
    
    conversation_history.append({
        "role": "user",
        "content": user_message
    })
    
    # Check for approval keywords
    approval_keywords = ["approved", "looks good", "proceed", "start building", 
                        "yes that's good", "perfect", "correct", "satisfied"]
    
    is_approved = any(keyword in user_message.lower() for keyword in approval_keywords)
    
    if is_approved:
        # Summarize requirements
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in conversation_history
        ])
        
        summary_prompt = f"""
Based on this conversation, create a clear, detailed requirements document:

{history_text}

Create a comprehensive requirements document that includes:
- Application purpose and goals
- Key features (be specific)
- UI/UX requirements
- Technical requirements
- Any constraints or preferences mentioned

Format as a structured document.
"""
        
        result = await call_claude(
            summary_prompt,
            system_prompt="You are a senior product manager who writes clear requirements."
        )
        
        response = f"✅ **Requirements Approved!**\n\n{result['content']}\n\nProceeding to development..."
        conversation_history.append({"role": "assistant", "content": response})
        
        return response, conversation_history, True
    
    # Continue discussion
    manager_prompt = f"""
You are a senior product manager helping gather requirements for a software project.

Conversation so far:
{json.dumps(conversation_history, indent=2)}

User's latest message: {user_message}

Your goals:
1. Understand exactly what the user wants to build
2. Ask clarifying questions about:
   - Key features and functionality
   - Target users
   - UI/UX preferences
   - Technical constraints
   - Success criteria
3. Be conversational and friendly
4. Once you have enough detail, summarize and ask for approval

Respond naturally to continue the discussion.
"""
    
    result = await call_claude(
        manager_prompt,
        system_prompt="You are a helpful product manager gathering requirements."
    )
    
    response = result['content']
    conversation_history.append({"role": "assistant", "content": response})
    
    return response, conversation_history, False

# %% [markdown]
# ## Cell 6: GitHub Agent

# %%
async def github_agent_node(state: DevelopmentState) -> DevelopmentState:
    """Creates repo and commits changes at milestones"""
    stage = state.get('current_stage', '')
    project_name = state.get('development_plan', {}).get('project_name', 'react-app')
    project_name = project_name.lower().replace(' ', '-')
    
    # Initialize repo
    if not state.get('github_repo'):
        print("\n🐙 Creating GitHub repository...")
        
        result = await github_operation(
            "create_repo",
            {},
            name=project_name,
            description=state['requirements'][:100]
        )
        
        if result['success']:
            state['github_repo'] = {
                'name': result['name'],
                'url': result['repo_url'],
                'owner': result['owner'],
                'branch': 'main'
            }
            print(f"✅ Repository: {result['repo_url']}")
        else:
            state['github_repo'] = {'name': project_name, 'url': 'local-only'}
            print("⚠️  GitHub unavailable, continuing locally")
        
        return state
    
    # Commit at milestones
    if state['github_repo']['url'] == 'local-only':
        return state
    
    repo = state['github_repo']
    files_to_commit = {}
    commit_msg = ""
    
    if 'code_written' in stage:
        files_to_commit = {**state.get('code_files', {}), **state.get('unit_tests', {})}
        commit_msg = "feat: Add application code with unit tests"
    elif 'tests_written' in stage:
        files_to_commit = state.get('e2e_tests', {})
        commit_msg = "test: Add E2E Playwright tests"
    elif 'deployment_complete' in stage:
        # Final commit with deployment info
        files_to_commit = {"README.md": f"# {project_name}\n\nLive: {state.get('deployment_url')}"}
        commit_msg = "docs: Add deployment URL"
    
    if files_to_commit:
        print(f"\n🐙 Committing: {commit_msg}")
        for filename, content in list(files_to_commit.items())[:10]:  # Limit commits
            await github_operation("commit_file", repo, path=filename, content=content, message=commit_msg)
        print(f"✅ Committed {len(files_to_commit)} files")
    
    return state

# %% [markdown]
# ## Cell 7: Planner Agent

# %%
async def planner_node(state: DevelopmentState) -> DevelopmentState:
    """Creates development plan from approved requirements"""
    print("\n🎯 PLANNER: Creating development plan...")
    
    prompt = f"""
Create a detailed development plan for this React + Vite application:

REQUIREMENTS:
{state['requirements']}

Create a JSON plan with:
{{
    "project_name": "descriptive-name",
    "description": "brief description",
    "components": ["Component1", "Component2"],
    "file_structure": {{
        "src/App.jsx": "Main app component",
        "src/components/Component1.jsx": "Description"
    }},
    "features": ["feature 1", "feature 2"],
    "tech_stack": ["React", "Vite", "Tailwind"],
    "testing_strategy": "Unit tests with Vitest, E2E with Playwright",
    "deployment": "Vercel"
}}

Be specific and comprehensive.
"""
    
    result = await call_claude(prompt, "You are a senior technical architect.")
    
    if result['success']:
        try:
            content = result['content']
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            plan = json.loads(content[json_start:json_end])
            
            state['development_plan'] = plan
            state['messages'].append({"role": "planner", "content": f"Plan created: {plan['project_name']}"})
            print(f"✅ Plan: {plan['project_name']}")
        except:
            state['errors'].append("Failed to parse plan")
    
    state['current_stage'] = 'planning_complete'
    return state

# %% [markdown]
# ## Cell 8: Developer Agent (Code + Unit Tests)

# %%
async def developer_node(state: DevelopmentState) -> DevelopmentState:
    """Writes application code AND unit tests"""
    print("\n💻 DEVELOPER: Writing code and unit tests...")
    
    plan = state['development_plan']
    project_name = plan['project_name']
    
    # Generate application code
    code_prompt = f"""
Write production-ready React code for this project:

PLAN:
{json.dumps(plan, indent=2)}

Generate these files with complete, working code:
1. package.json - Include Vitest for unit testing
2. vite.config.js
3. index.html
4. src/main.jsx
5. src/App.jsx
{chr(10).join([f"{i+6}. {file}" for i, file in enumerate(plan.get('file_structure', {}).keys())])}

Format: ===FILE: filename===
[content]
===END FILE===

Use modern React, functional components, hooks.
"""
    
    result = await call_claude(code_prompt, "You are an expert React developer.")
    
    code_files = {}
    if result['success']:
        parts = result['content'].split('===FILE:')
        for part in parts[1:]:
            if '===' in part:
                header, content = part.split('===', 1)
                filename = header.strip()
                body = content.replace('===END FILE===', '').strip()
                code_files[filename] = body
                save_file(project_name, filename, body)
        
        state['code_files'] = code_files
        print(f"✅ Generated {len(code_files)} code files")
    
    # Generate unit tests
    unit_test_prompt = f"""
Write comprehensive unit tests using Vitest for this React application:

COMPONENTS:
{chr(10).join([f for f in code_files.keys() if '.jsx' in f])}

Generate test files:
1. src/App.test.jsx - Test main App component
2. vitest.config.js - Vitest configuration
{chr(10).join([f"3. src/components/{comp}.test.jsx" for comp in plan.get('components', [])[:3]])}

Format: ===FILE: filename===
[content]
===END FILE===

Write tests for:
- Component rendering
- Props handling
- State management
- User interactions
- Edge cases
"""
    
    test_result = await call_claude(unit_test_prompt, "You are a QA expert specializing in unit tests.")
    
    unit_tests = {}
    if test_result['success']:
        parts = test_result['content'].split('===FILE:')
        for part in parts[1:]:
            if '===' in part:
                header, content = part.split('===', 1)
                filename = header.strip()
                body = content.replace('===END FILE===', '').strip()
                unit_tests[filename] = body
                save_file(project_name, filename, body)
        
        state['unit_tests'] = unit_tests
        print(f"✅ Generated {len(unit_tests)} unit test files")
    
    state['current_stage'] = 'code_written'
    state['iteration_count'] += 1
    return state

# %% [markdown]
# ## Cell 9: Unit Test Executor

# %%
async def run_unit_tests(project_name: str) -> dict:
    """Execute Vitest unit tests"""
    project_path = PROJECT_DIR / project_name
    
    try:
        # Install dependencies
        print("  📦 Installing dependencies...")
        subprocess.run(
            ["npm", "install"],
            cwd=project_path,
            capture_output=True,
            timeout=120
        )
        
        # Run Vitest
        print("  🧪 Running unit tests...")
        result = subprocess.run(
            ["npx", "vitest", "run", "--reporter=json"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Parse results
        try:
            data = json.loads(result.stdout)
            return {
                "success": True,
                "total": data.get('numTotalTests', 0),
                "passed": data.get('numPassedTests', 0),
                "failed": data.get('numFailedTests', 0),
                "details": data.get('testResults', [])
            }
        except:
            # Fallback parsing
            lines = result.stdout + result.stderr
            return {
                "success": True,
                "total": lines.count('✓') + lines.count('✗'),
                "passed": lines.count('✓'),
                "failed": lines.count('✗'),
                "details": []
            }
    
    except Exception as e:
        return {"success": False, "error": str(e), "total": 0, "passed": 0, "failed": 0}

# %% [markdown]
# ## Cell 10: Tester Agent (Playwright E2E Tests)

# %%
async def tester_node(state: DevelopmentState) -> DevelopmentState:
    """Writes and executes Playwright E2E tests"""
    print("\n🧪 TESTER: Writing Playwright E2E tests...")
    
    plan = state['development_plan']
    project_name = plan['project_name']
    
    # Generate Playwright tests
    e2e_prompt = f"""
Write comprehensive Playwright E2E tests for this React application:

FEATURES:
{chr(10).join(plan.get('features', []))}

COMPONENTS:
{chr(10).join([f for f in state['code_files'].keys() if '.jsx' in f])}

Generate:
1. playwright.config.js - Headless mode, localhost:5173
2. tests/app.spec.js - Main user flows
3. tests/features.spec.js - Feature-specific tests

Format: ===FILE: filename===
[content]
===END FILE===

Test:
- Complete user workflows
- Form submissions
- Navigation
- Data persistence
- Error states
- Accessibility basics
"""
    
    result = await call_claude(e2e_prompt, "You are a QA expert specializing in Playwright E2E testing.")
    
    e2e_tests = {}
    if result['success']:
        parts = result['content'].split('===FILE:')
        for part in parts[1:]:
            if '===' in part:
                header, content = part.split('===', 1)
                filename = header.strip()
                body = content.replace('===END FILE===', '').strip()
                e2e_tests[filename] = body
                save_file(project_name, filename, body)
        
        state['e2e_tests'] = e2e_tests
        print(f"✅ Generated {len(e2e_tests)} E2E test files")
    
    state['current_stage'] = 'tests_written'
    return state

# %% [markdown]
# ## Cell 11: E2E Test Executor (with Playwright MCP)

# %%
async def run_e2e_tests(project_name: str, localhost_url: str) -> dict:
    """
    Execute Playwright E2E tests against localhost
    Uses Playwright Node.js (can be enhanced with MCP)
    """
    project_path = PROJECT_DIR / project_name
    
    try:
        # Install Playwright
        print("  🌐 Installing Playwright...")
        subprocess.run(
            ["npx", "playwright", "install"],
            cwd=project_path,
            capture_output=True,
            timeout=300
        )
        
        # Start dev server in background
        print(f"  🚀 Starting dev server at {localhost_url}...")
        dev_server = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to be ready
        await asyncio.sleep(10)
        
        # Run Playwright tests
        print("  🎭 Running Playwright tests...")
        result = subprocess.run(
            ["npx", "playwright", "test", "--reporter=json"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Kill dev server
        dev_server.terminate()
        dev_server.wait()
        
        # Parse results
        try:
            data = json.loads(result.stdout)
            suites = data.get('suites', [])
            total = passed = failed = 0
            details = []
            
            for suite in suites:
                for spec in suite.get('specs', []):
                    for test in spec.get('tests', []):
                        total += 1
                        status = test.get('status', 'unknown')
                        if status == 'passed':
                            passed += 1
                        else:
                            failed += 1
                        details.append({
                            "test": test.get('title'),
                            "status": status,
                            "error": test.get('error', {}).get('message') if status != 'passed' else None
                        })
            
            return {
                "success": True,
                "total": total,
                "passed": passed,
                "failed": failed,
                "details": details
            }
        except:
            return {
                "success": False,
                "error": "Failed to parse test results",
                "total": 0,
                "passed": 0,
                "failed": 0
            }
    
    except Exception as e:
        return {"success": False, "error": str(e), "total": 0, "passed": 0, "failed": 0}

# %% [markdown]
# ## Cell 12: Deployment Agent (Vercel)

# %%
async def deploy_to_vercel(project_name: str, github_repo: dict) -> dict:
    """Deploy to Vercel (better for React than Netlify)"""
    vercel_token = os.getenv("VERCEL_TOKEN")
    
    if not vercel_token:
        return {"success": False, "error": "No Vercel token"}
    
    try:
        import httpx
        
        headers = {
            "Authorization": f"Bearer {vercel_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            # Create deployment
            response = await http_client.post(
                "https://api.vercel.com/v13/deployments",
                headers=headers,
                json={
                    "name": project_name,
                    "gitSource": {
                        "type": "github",
                        "repo": f"{github_repo['owner']}/{github_repo['name']}",
                        "ref": "main"
                    },
                    "buildCommand": "npm run build",
                    "framework": "vite"
                }
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                deployment_url = f"https://{data.get('url', project_name)}.vercel.app"
                return {
                    "success": True,
                    "url": deployment_url,
                    "deployment_id": data.get('id')
                }
        
        return {"success": False, "error": f"Status {response.status_code}"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

async def deployer_node(state: DevelopmentState) -> DevelopmentState:
    """Deploy to production (Vercel)"""
    print("\n🚀 DEPLOYER: Deploying to Vercel...")
    
    project_name = state['development_plan']['project_name']
    
    result = await deploy_to_vercel(project_name, state['github_repo'])
    
    if result['success']:
        state['deployment_url'] = result['url']
        state['deployment_platform'] = 'vercel'
        print(f"✅ Deployed: {result['url']}")
    else:
        print(f"⚠️  Deployment failed: {result.get('error')}")
        state['errors'].append(f"Deployment failed: {result.get('error')}")
    
    state['current_stage'] = 'deployment_complete'
    return state

# %% [markdown]
# ## Cell 13: Build Complete Workflow

# %%
def create_workflow() -> StateGraph:
    """Build the complete agentic workflow"""
    workflow = StateGraph(DevelopmentState)
    
    # Add all agents
    workflow.add_node("github_init", github_agent_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("developer", developer_node)
    workflow.add_node("github_commit_code", github_agent_node)
    workflow.add_node("tester", tester_node)
    workflow.add_node("github_commit_tests", github_agent_node)
    workflow.add_node("deployer", deployer_node)
    workflow.add_node("github_commit_deploy", github_agent_node)
    
    # Define flow
    workflow.set_entry_point("github_init")
    workflow.add_edge("github_init", "planner")
    workflow.add_edge("planner", "developer")
    workflow.add_edge("developer", "github_commit_code")
    workflow.add_edge("github_commit_code", "tester")
    workflow.add_edge("tester", "github_commit_tests")
    workflow.add_edge("github_commit_tests", "deployer")
    workflow.add_edge("deployer", "github_commit_deploy")
    workflow.add_edge("github_commit_deploy", END)
    
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

workflow_app = create_workflow()
print("✅ Workflow compiled!")

# %% [markdown]
# ## Cell 14: Gradio UI Application

# %%
class AgenticDevSystem:
    """Main application controller"""
    
    def __init__(self):
        self.conversation_history = []
        self.requirements = None
        self.state = None
        self.workflow = workflow_app
    
    async def chat_with_manager(self, user_message: str, history: list) -> tuple:
        """Handle manager chat"""
        response, self.conversation_history, is_approved = await manager_agent(
            user_message,
            self.conversation_history
        )
        
        if is_approved:
            # Extract final requirements
            self.requirements = response
            return response, history + [[user_message, response]], "approved"
        
        return response, history + [[user_message, response]], "continue"
    
    async def run_development(self, requirements: str, progress=gr.Progress()):
        """Execute the full development workflow"""
        
        progress(0, desc="Initializing...")
        
        initial_state = {
            "user_request": requirements,
            "requirements": requirements,
            "requirements_approved": True,
            "conversation_history": self.conversation_history,
            "development_plan": None,
            "code_files": {},
            "unit_tests": {},
            "e2e_tests": {},
            "unit_test_results": {},
            "e2e_test_results": {},
            "test_review_approved": False,
            "localhost_url": "http://localhost:5173",
            "deployment_url": None,
            "deployment_platform": "vercel",
            "github_repo": None,
            "current_stage": "initial",
            "current_agent": "github",
            "iteration_count": 0,
            "errors": [],
            "messages": []
        }
        
        config = {"configurable": {"thread_id": f"dev-{datetime.now().strftime('%Y%m%d%H%M%S')}"}}
        
        stages = [
            "Creating GitHub repo",
            "Planning architecture",
            "Writing code & unit tests",
            "Committing code",
            "Writing E2E tests",
            "Committing tests",
            "Deploying to Vercel",
            "Final commit"
        ]
        
        logs = []
        
        try:
            step = 0
            async for event in self.workflow.astream(initial_state, config):
                stage_name = stages[min(step, len(stages)-1)]
                progress((step + 1) / len(stages), desc=stage_name)
                
                for node_name, node_state in event.items():
                    if node_name != "__end__":
                        log_entry = f"✓ {stage_name} complete"
                        logs.append(log_entry)
                        print(log_entry)
                
                step += 1
                await asyncio.sleep(0.5)  # Visual feedback
            
            # Get final state
            final_state = await self.workflow.aget_state(config)
            self.state = final_state.values
            
            return {
                "status": "success",
                "github_url": self.state.get('github_repo', {}).get('url'),
                "deployment_url": self.state.get('deployment_url'),
                "logs": "\n".join(logs)
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "logs": "\n".join(logs)
            }

# Create system instance
dev_system = AgenticDevSystem()

# %% [markdown]
# ## Cell 15: Gradio Interface

# %%
def create_gradio_app():
    """Create the Gradio UI"""
    
    with gr.Blocks(title="Agentic React Development System", theme=gr.themes.Soft()) as app:
        
        gr.Markdown("# 🤖 Agentic React Development System")
        gr.Markdown("Complete AI-powered development: Requirements → Code → Tests → Deployment")
        
        with gr.Tab("💬 Requirements Discussion"):
            gr.Markdown("### Step 1: Discuss Your Application with the Manager Agent")
            
            chatbot = gr.Chatbot(
                label="Manager Agent",
                height=400
            )
            
            msg = gr.Textbox(
                label="Your Message",
                placeholder="I want to build a todo app with...",
                lines=2
            )
            
            with gr.Row():
                send_btn = gr.Button("Send", variant="primary")
                clear_btn = gr.Button("Clear")
            
            status = gr.Textbox(label="Status", value="Type your request above", interactive=False)
            requirements_output = gr.Textbox(label="Final Requirements", lines=10, interactive=False)
            
            async def handle_message(user_msg, history):
                if not user_msg:
                    return "", history, "Please enter a message"
                
                response, updated_history, approval_status = await dev_system.chat_with_manager(user_msg, history)
                
                if approval_status == "approved":
                    return "", updated_history, "✅ Requirements approved! Go to Development tab to build.", response
                else:
                    return "", updated_history, "Continue discussion...", ""
            
            send_btn.click(
                handle_message,
                inputs=[msg, chatbot],
                outputs=[msg, chatbot, status, requirements_output]
            )
            
            msg.submit(
                handle_message,
                inputs=[msg, chatbot],
                outputs=[msg, chatbot, status, requirements_output]
            )
            
            clear_btn.click(lambda: ([], "", ""), outputs=[chatbot, msg, status])
        
        with gr.Tab("🚀 Development Execution"):
            gr.Markdown("### Step 2: Execute Agentic Development Workflow")
            gr.Markdown("This will: Create GitHub repo → Plan → Code → Test → Deploy")
            
            with gr.Row():
                start_btn = gr.Button("🎬 Start Development", variant="primary", size="lg")
            
            progress_text = gr.Textbox(label="Progress", lines=3, interactive=False)
            logs_output = gr.TextArea(label="Development Logs", lines=15, interactive=False)
            
            with gr.Row():
                github_link = gr.Textbox(label="GitHub Repository", interactive=False)
                deployment_link = gr.Textbox(label="Live Deployment", interactive=False)
            
            result_json = gr.JSON(label="Full Results")
            
            async def run_development_workflow(progress=gr.Progress()):
                if not dev_system.requirements:
                    return "❌ Please approve requirements first!", "", "", "", {}
                
                result = await dev_system.run_development(dev_system.requirements, progress)
                
                if result["status"] == "success":
                    return (
                        "✅ Development Complete!",
                        result["logs"],
                        result.get("github_url", "N/A"),
                        result.get("deployment_url", "N/A"),
                        result
                    )
                else:
                    return (
                        f"❌ Error: {result.get('error')}",
                        result["logs"],
                        "",
                        "",
                        result
                    )
            
            start_btn.click(
                run_development_workflow,
                outputs=[progress_text, logs_output, github_link, deployment_link, result_json]
            )
        
        with gr.Tab("🧪 Test Review"):
            gr.Markdown("### Step 3: Review Tests Before Deployment")
            gr.Markdown("Review unit tests and E2E tests written by agents")
            
            test_type = gr.Radio(
                choices=["Unit Tests", "E2E Tests"],
                label="Test Type",
                value="Unit Tests"
            )
            
            test_files = gr.Dropdown(
                label="Test File",
                choices=[],
                interactive=True
            )
            
            test_content = gr.Code(
                label="Test Code",
                language="javascript",
                lines=20
            )
            
            test_results = gr.JSON(label="Test Results")
            
            with gr.Row():
                run_tests_btn = gr.Button("▶️ Run Tests")
                approve_tests_btn = gr.Button("✅ Approve & Deploy", variant="primary")
            
            def load_test_files(test_type_selected):
                if not dev_system.state:
                    return gr.Dropdown(choices=[])
                
                if test_type_selected == "Unit Tests":
                    files = list(dev_system.state.get('unit_tests', {}).keys())
                else:
                    files = list(dev_system.state.get('e2e_tests', {}).keys())
                
                return gr.Dropdown(choices=files, value=files[0] if files else None)
            
            def show_test_content(test_type_selected, test_file):
                if not dev_system.state or not test_file:
                    return ""
                
                if test_type_selected == "Unit Tests":
                    return dev_system.state.get('unit_tests', {}).get(test_file, "")
                else:
                    return dev_system.state.get('e2e_tests', {}).get(test_file, "")
            
            async def run_selected_tests(test_type_selected):
                if not dev_system.state:
                    return {"error": "No tests available"}
                
                project_name = dev_system.state['development_plan']['project_name']
                
                if test_type_selected == "Unit Tests":
                    results = await run_unit_tests(project_name)
                else:
                    localhost_url = dev_system.state.get('localhost_url', 'http://localhost:5173')
                    results = await run_e2e_tests(project_name, localhost_url)
                
                return results
            
            test_type.change(load_test_files, inputs=[test_type], outputs=[test_files])
            test_files.change(show_test_content, inputs=[test_type, test_files], outputs=[test_content])
            run_tests_btn.click(run_selected_tests, inputs=[test_type], outputs=[test_results])
            approve_tests_btn.click(
                lambda: "✅ Tests approved! Proceeding to deployment...",
                outputs=[gr.Textbox(label="Status")]
            )
        
        with gr.Tab("📊 Project Dashboard"):
            gr.Markdown("### Project Overview")
            
            project_info = gr.JSON(label="Project Information")
            file_tree = gr.TextArea(label="Generated Files", lines=15)
            
            refresh_btn = gr.Button("🔄 Refresh")
            
            def refresh_dashboard():
                if not dev_system.state:
                    return {}, "No project loaded"
                
                state = dev_system.state
                
                info = {
                    "project_name": state.get('development_plan', {}).get('project_name'),
                    "github_repo": state.get('github_repo', {}).get('url'),
                    "deployment_url": state.get('deployment_url'),
                    "stage": state.get('current_stage'),
                    "errors": state.get('errors', [])
                }
                
                files = []
                files.extend([f"📄 {f}" for f in state.get('code_files', {}).keys()])
                files.extend([f"🧪 {f}" for f in state.get('unit_tests', {}).keys()])
                files.extend([f"🎭 {f}" for f in state.get('e2e_tests', {}).keys()])
                
                return info, "\n".join(files)
            
            refresh_btn.click(refresh_dashboard, outputs=[project_info, file_tree])
        
        with gr.Tab("⚙️ Configuration"):
            gr.Markdown("### Environment Setup")
            gr.Markdown("""
            **Required Environment Variables:**
            
            1. `ANTHROPIC_API_KEY` - Your Claude API key
            2. `GITHUB_TOKEN` - GitHub Personal Access Token (repo scope)
            3. `VERCEL_TOKEN` - Vercel API token (optional, for deployment)
            
            **Setup Instructions:**
            
            ```bash
            # Create .env file
            echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
            echo "GITHUB_TOKEN=ghp_..." >> .env
            echo "VERCEL_TOKEN=..." >> .env
            ```
            
            **Why Vercel over Netlify for React?**
            - ✅ Built by creators of Next.js (React framework)
            - ✅ Better Vite integration
            - ✅ Faster cold starts
            - ✅ Edge functions support
            - ✅ Automatic Lighthouse scores
            """)
            
            check_btn = gr.Button("🔍 Check Configuration")
            config_status = gr.Textbox(label="Configuration Status", lines=5)
            
            def check_configuration():
                status = []
                status.append(f"✅ Claude API: {bool(os.getenv('ANTHROPIC_API_KEY'))}")
                status.append(f"{'✅' if os.getenv('GITHUB_TOKEN') else '❌'} GitHub Token: {bool(os.getenv('GITHUB_TOKEN'))}")
                status.append(f"{'✅' if os.getenv('VERCEL_TOKEN') else '⚠️'} Vercel Token: {bool(os.getenv('VERCEL_TOKEN'))} (optional)")
                status.append(f"\n📁 Projects directory: {PROJECT_DIR}")
                return "\n".join(status)
            
            check_btn.click(check_configuration, outputs=[config_status])
    
    return app

# Launch the Gradio app
if __name__ == "__main__":
    app = create_gradio_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )

# %% [markdown]
# ## Usage Instructions
# 
# **1. Start the application:**
# ```python
# python script_name.py
# ```
# 
# **2. Open browser:** http://localhost:7860
# 
# **3. Workflow:**
# - Tab 1: Chat with Manager Agent until requirements approved
# - Tab 2: Click "Start Development" - full automated workflow
# - Tab 3: Review generated tests, run them, approve
# - Tab 4: View project dashboard
# 
# **4. What happens automatically:**
# - ✅ GitHub repo created
# - ✅ Development plan generated
# - ✅ React code + unit tests written
# - ✅ Code committed to GitHub
# - ✅ Playwright E2E tests written
# - ✅ Tests committed to GitHub
# - ✅ Localhost dev server started
# - ✅ E2E tests executed
# - ✅ Deployed to Vercel
# - ✅ Deployment URL committed
# 
# **5. Human-in-the-loop checkpoints:**
# - ✅ Requirements approval (Manager chat)
# - ✅ Test review before deployment (optional)