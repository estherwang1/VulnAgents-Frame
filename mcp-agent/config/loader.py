# -*- coding: utf-8 -*-
"""
Config Loader
MCP Server 配置加载器
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


def resolve_env_vars(value: Any) -> Any:
    """解析环境变量 ${VAR:default}"""
    if isinstance(value, str):
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replace(match):
            var_name = match.group(1)
            default = match.group(2) or ""
            return os.getenv(var_name, default)
        
        return re.sub(pattern, replace, value)
    elif isinstance(value, dict):
        return {k: resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [resolve_env_vars(item) for item in value]
    return value


@dataclass
class ParamSchema:
    """参数 Schema"""
    name: str
    type: str
    required: bool = False
    default: Any = None
    description: str = ""
    enum: List[str] = field(default_factory=list)
    items: str = None  # for array type
    
    def to_json_schema(self) -> dict:
        """转换为 JSON Schema"""
        schema = {
            "type": self.type,
            "description": self.description
        }
        
        if self.default is not None:
            schema["default"] = self.default
        
        if self.enum:
            schema["enum"] = self.enum
        
        if self.type == "array" and self.items:
            schema["items"] = {"type": self.items}
        
        return schema


@dataclass
class ToolConfig:
    """工具配置"""
    name: str
    group: str
    handler: str
    description: str
    params: Dict[str, ParamSchema] = field(default_factory=dict)
    security: Dict[str, Any] = field(default_factory=dict)
    
    def get_input_schema(self) -> dict:
        """生成 MCP inputSchema"""
        properties = {}
        required = []
        
        for name, param in self.params.items():
            properties[name] = param.to_json_schema()
            if param.required:
                required.append(name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def to_mcp_definition(self) -> dict:
        """生成 MCP 工具定义"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.get_input_schema()
        }


class MCPConfig:
    """MCP Server 配置"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent / "tools.yaml"
        
        self.config_path = Path(config_path)
        self._raw_config: Dict = {}
        self._tools: Dict[str, ToolConfig] = {}
        self._groups: Dict[str, dict] = {}
        self._security: Dict = {}
        
        self._load()
    
    def _load(self):
        """加载配置"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._raw_config = yaml.safe_load(f)
        
        # 解析环境变量
        self._raw_config = resolve_env_vars(self._raw_config)
        
        # 加载分组
        self._groups = self._raw_config.get('groups', {})
        
        # 加载安全配置
        self._security = self._raw_config.get('security', {})
        
        # 加载工具
        self._load_tools()
    
    def _load_tools(self):
        """加载工具配置"""
        tools_config = self._raw_config.get('tools', {})
        
        for name, tool_data in tools_config.items():
            params = {}
            params_config = tool_data.get('params', {})
            
            for param_name, param_data in params_config.items():
                if isinstance(param_data, dict):
                    params[param_name] = ParamSchema(
                        name=param_name,
                        type=param_data.get('type', 'string'),
                        required=param_data.get('required', False),
                        default=param_data.get('default'),
                        description=param_data.get('description', ''),
                        enum=param_data.get('enum', []),
                        items=param_data.get('items')
                    )
            
            self._tools[name] = ToolConfig(
                name=name,
                group=tool_data.get('group', 'default'),
                handler=tool_data.get('handler', ''),
                description=tool_data.get('description', ''),
                params=params,
                security=tool_data.get('security', {})
            )
    
    # === 属性访问 ===
    
    @property
    def server(self) -> dict:
        """服务器配置"""
        return self._raw_config.get('server', {})
    
    @property
    def paths(self) -> dict:
        """路径配置"""
        return self._raw_config.get('paths', {})
    
    @property
    def execution(self) -> dict:
        """执行配置"""
        return self._raw_config.get('execution', {})
    
    @property
    def tools(self) -> Dict[str, ToolConfig]:
        """所有工具"""
        return self._tools
    
    @property
    def groups(self) -> Dict[str, dict]:
        """工具分组"""
        return self._groups
    
    @property
    def security(self) -> dict:
        """安全配置"""
        return self._security
    
    # === 工具方法 ===
    
    def get_tool(self, name: str) -> Optional[ToolConfig]:
        """获取工具配置"""
        return self._tools.get(name)
    
    def get_mcp_definitions(self) -> List[dict]:
        """获取所有工具的 MCP 定义"""
        return [tool.to_mcp_definition() for tool in self._tools.values()]
    
    def get_tools_by_group(self, group: str) -> List[ToolConfig]:
        """按分组获取工具"""
        return [t for t in self._tools.values() if t.group == group]
    
    def is_command_safe(self, command: str) -> tuple:
        """检查命令是否安全"""
        # 检查黑名单
        blacklist = self._security.get('command_blacklist', [])
        for pattern in blacklist:
            if pattern in command:
                return False, f"命令匹配黑名单: {pattern}"
        
        # 检查白名单
        whitelist = self._security.get('command_whitelist', [])
        if whitelist:
            cmd_base = command.split()[0] if command else ""
            if cmd_base not in whitelist:
                return False, f"命令不在白名单中: {cmd_base}"
        
        return True, "OK"
    
    def validate_params(self, tool_name: str, args: dict) -> tuple:
        """验证参数"""
        tool = self.get_tool(tool_name)
        if not tool:
            return False, f"工具不存在: {tool_name}"
        
        # 检查必填参数
        for name, param in tool.params.items():
            if param.required and name not in args:
                return False, f"缺少必填参数: {name}"
            
            # 检查枚举值
            if name in args and param.enum:
                if args[name] not in param.enum:
                    return False, f"参数 {name} 的值必须是 {param.enum} 之一"
        
        return True, "OK"
    
    def fill_defaults(self, tool_name: str, args: dict) -> dict:
        """填充默认值"""
        tool = self.get_tool(tool_name)
        if not tool:
            return args
        
        filled = dict(args)
        for name, param in tool.params.items():
            if name not in filled and param.default is not None:
                filled[name] = param.default
        
        return filled


# 全局配置实例
_config: Optional[MCPConfig] = None


def get_config() -> MCPConfig:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = MCPConfig()
    return _config


def reload_config():
    """重新加载配置"""
    global _config
    _config = None
    return get_config()
