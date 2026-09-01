# EXAMPLE ONLY - Workflow Action Plugin Demonstration
from plugins.contracts.workflow_contract import BaseWorkflowActionPlugin
from typing import Dict, Any, Optional

class ExampleWorkflowPlugin(BaseWorkflowActionPlugin):
    async def execute(self, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "status": "success",
            "executed_action": self.action_name,
            "received_payload": payload,
            "message": "Custom workflow action executed successfully."
        }
