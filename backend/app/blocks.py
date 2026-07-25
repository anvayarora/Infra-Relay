from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable

@dataclass(frozen=True)
class BlockDefinition:
    type: str
    name: str
    category: str
    description: str
    icon: str
    accent: str
    settings: list[dict]
    inputs: list[str]
    outputs: list[str]

DEFINITIONS = [
    BlockDefinition("trigger.manual", "Start", "Start and input", "Begin when a person, connected app or API starts this automation.", "Play", "zinc", [], [], ["main"]),
    BlockDefinition("ui.payload.inbound", "Collect information", "Start and input", "Ask a person or connected app for the information needed to continue.", "PanelTopOpen", "violet", [
        {"key":"intent","label":"Request key","type":"text","default":"request_input"}, {"key":"title","label":"Title","type":"text","default":"Provide details"},
        {"key":"schema","label":"Form fields","type":"json","default":{"fields":[{"key":"name","label":"Name","type":"text","required":True}]}},
        {"key":"timeout_minutes","label":"Wait up to (minutes)","type":"number","default":1440}], ["main"], ["main"]),
    BlockDefinition("ui.payload.outbound", "Share an update", "Results and updates", "Send progress, results or errors to every connected screen or tool.", "RadioTower", "cyan", [
        {"key":"intent","label":"Request key","type":"text","default":"workflow_result"}, {"key":"title","label":"Title","type":"text","default":"Automation update"},
        {"key":"payload","label":"Information to send","type":"json","default":{"message":"Completed"}}], ["main"], ["main"]),
    BlockDefinition("ui.payload.bidirectional", "Ask and wait", "Start and input", "Share the current details and wait for a person or approved tool to choose what happens next.", "PanelsTopLeft", "amber", [
        {"key":"intent","label":"Request key","type":"text","default":"confirm_action"}, {"key":"title","label":"Title","type":"text","default":"Confirm action"},
        {"key":"schema","label":"Fields and actions","type":"json","default":{"fields":[],"actions":[{"id":"confirm","label":"Confirm"},{"id":"cancel","label":"Cancel"}]}},
        {"key":"allowed_actions","label":"Available choices","type":"json","default":["confirm","cancel"]}], ["main"], ["main"]),
    BlockDefinition("hitl.approval", "Request approval", "Approvals", "Pause here, notify the right person and continue after they approve or reject.", "UserCheck", "emerald", [
        {"key":"title","label":"Approval title","type":"text","default":"Approval required"}, {"key":"approver_email","label":"Approver email","type":"text","default":""},
        {"key":"message","label":"Message","type":"textarea","default":"Review this infrastructure action."}, {"key":"notify","label":"Send email notification","type":"boolean","default":False}], ["main"], ["approved","rejected"]),
    BlockDefinition("resource.search", "Find resources", "Resources", "Find available servers, virtual machines, GPUs or other shared infrastructure.", "Server", "blue", [
        {"key":"resource_type","label":"Resource type","type":"text","default":"physical_server"}, {"key":"status","label":"Status","type":"text","default":"available"},
        {"key":"tags","label":"Must include tags","type":"json","default":[]}], ["main"], ["main"]),
    BlockDefinition("resource.book", "Reserve resource", "Resources", "Reserve a shared resource and prevent overlapping bookings.", "CalendarCheck", "blue", [
        {"key":"resource_id","label":"Resource ID","type":"resource","default":"{{input.resource_id}}"}, {"key":"requested_by","label":"Requested by","type":"text","default":"{{input.requested_by}}"},
        {"key":"starts_at","label":"Starts at","type":"text","default":"{{input.starts_at}}"}, {"key":"ends_at","label":"Ends at","type":"text","default":"{{input.ends_at}}"},
        {"key":"purpose","label":"Purpose","type":"text","default":"Infrastructure reservation"}], ["main"], ["main"]),
    BlockDefinition("gpu.inspect", "Check GPU server", "GPU maintenance", "Check the operating system, GPU, driver, CUDA and container setup before making changes.", "ScanSearch", "green", [
        {"key":"resource_id","label":"Resource ID","type":"resource","default":"{{input.resource_id}}"}, {"key":"execute","label":"Apply to the server","type":"boolean","default":False}], ["main"], ["main"]),
    BlockDefinition("gpu.provision", "Update GPU software", "GPU maintenance", "Choose and apply the GPU driver, CUDA, container support and required system settings.", "Cpu", "green", [
        {"key":"resource_id","label":"Resource ID","type":"resource","default":"{{input.resource_id}}"}, {"key":"driver","label":"Driver version","type":"text","default":"latest_compatible"},
        {"key":"cuda","label":"CUDA version","type":"text","default":"latest_compatible"}, {"key":"container_toolkit","label":"Install container support","type":"boolean","default":True},
        {"key":"resolve_nouveau","label":"Fix Nouveau conflicts","type":"boolean","default":True}, {"key":"enable_iommu","label":"Enable IOMMU","type":"boolean","default":False},
        {"key":"allow_reboot","label":"Allow reboot","type":"boolean","default":False}, {"key":"execute","label":"Apply to the server","type":"boolean","default":False}], ["main"], ["main"]),
    BlockDefinition("ad.search_user", "Find directory user", "User accounts", "Find an existing user account in a connected company directory.", "Search", "indigo", [
        {"key":"credential_ref","label":"Directory connection","type":"credential","default":""}, {"key":"query","label":"Name or username","type":"text","default":"{{input.query}}"}], ["main"], ["main"]),
    BlockDefinition("ad.create_user", "Create directory user", "User accounts", "Create a new company account in the selected directory.", "UserPlus", "indigo", [
        {"key":"credential_ref","label":"Directory connection","type":"credential","default":""}, {"key":"username","label":"Username","type":"text","default":"{{input.username}}"},
        {"key":"display_name","label":"Display name","type":"text","default":"{{input.display_name}}"}, {"key":"email","label":"Email","type":"text","default":"{{input.email}}"},
        {"key":"target_ou","label":"Folder / organisational unit","type":"text","default":""}, {"key":"execute","label":"Create the account","type":"boolean","default":False}], ["main"], ["main"]),
    BlockDefinition("powershell.winrm", "Run PowerShell remotely", "Server actions", "Run an approved PowerShell task on a connected Windows server.", "TerminalSquare", "sky", [
        {"key":"credential_ref","label":"Windows server connection","type":"credential","default":""}, {"key":"host","label":"Host","type":"text","default":"{{input.host}}"},
        {"key":"script","label":"PowerShell script","type":"code","default":"Get-ComputerInfo | ConvertTo-Json -Depth 4"}, {"key":"execute","label":"Run on the server","type":"boolean","default":False}], ["main"], ["main"]),
    BlockDefinition("smtp.send", "Send email", "Messages", "Send an email through the mail service configured for this deployment.", "Mail", "rose", [
        {"key":"to","label":"Recipient","type":"text","default":"{{input.email}}"}, {"key":"subject","label":"Subject","type":"text","default":"InfraRelay automation update"},
        {"key":"html","label":"HTML body","type":"textarea","default":"<p>Your automation has completed.</p>"}, {"key":"execute","label":"Send email","type":"boolean","default":False}], ["main"], ["main"]),
    BlockDefinition("control.condition", "Choose a path", "Logic", "Continue down a different path based on a value or result.", "GitBranch", "orange", [
        {"key":"value","label":"Value","type":"text","default":"{{input.status}}"}, {"key":"operator","label":"Operator","type":"select","options":["equals","not_equals","truthy","contains"],"default":"equals"},
        {"key":"compare_to","label":"Expected value","type":"text","default":"approved"}], ["main"], ["true","false"]),
    BlockDefinition("data.set", "Prepare information", "Data", "Create or organise information for the next steps.", "Braces", "zinc", [
        {"key":"values","label":"Information","type":"json","default":{"status":"ready"}}], ["main"], ["main"]),
    BlockDefinition("http.request", "Connect to an API", "Connections", "Send or retrieve information from another application.", "Globe2", "purple", [
        {"key":"method","label":"Method","type":"select","options":["GET","POST","PUT","PATCH","DELETE"],"default":"POST"}, {"key":"url","label":"URL","type":"text","default":""},
        {"key":"headers","label":"Headers","type":"json","default":{}}, {"key":"body","label":"Information to send","type":"json","default":{}}, {"key":"execute","label":"Contact the API","type":"boolean","default":False}], ["main"], ["main"]),
]

BLOCKS = {item.type: item for item in DEFINITIONS}

def serialize_definition(item: BlockDefinition) -> dict:
    return {"type":item.type,"name":item.name,"category":item.category,"description":item.description,"icon":item.icon,"accent":item.accent,"settings":item.settings,"inputs":item.inputs,"outputs":item.outputs}
