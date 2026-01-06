#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Loader
工具配置加载器
"""

import os
import yaml
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any


class ToolConfig:
    """工具配置"""
    
    def __init__(self, tool_id: str, config: dict, base_path: Path):
        self.tool_id = tool_id  # 如 recon/port_scan
        self.config = config
        self.base_path = base_path
        
        # 基本信息
        self.name = config.get('name', tool_id.split('/')[-1])
        self.version = config.get('version', '1.0')
        self.category = config.get('category', tool_id.split('/')[0])
        
        # 描述
        desc = config.get('description', {})
        self.short_desc = desc.get('short', '')
        self.long_desc = desc.get('long', '')
        
        # 参数
        self.params = config.get('params', {})
        
        # 输出
        self.output = config.get('output', {})
        
        # 示例
        self.examples = config.get('examples', [])
        
        # 执行配置
        self.execution = config.get('execution', {})
        
        # 标签
        self.tags = config.get('tags', [])
    
    def get_param_schema(self) -> dict:
        """获取参数 JSON Schema"""
        properties = {}
        required = []
        
        for name, param in self.params.items():
            prop = {
                "type": param.get('type', 'string'),
                "description": param.get('description', '')
            }
            
            if 'default' in param:
                prop['default'] = param['default']
            if 'enum' in param:
                prop['enum'] = param['enum']
            if 'min' in param:
                prop['minimum'] = param['min']
            if 'max' in param:
                prop['maximum'] = param['max']
            if 'examples' in param:
                prop['examples'] = param['examples']
            
            properties[name] = prop
            
            if param.get('required', False):
                required.append(name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def to_llm_description(self) -> str:
        """生成 LLM 友好的描述"""
        lines = [
            f"## {self.tool_id}",
            f"**{self.short_desc}**",
            "",
            self.long_desc if self.long_desc else "",
            "",
            "### 参数",
        ]
        
        for name, param in self.params.items():
            required = "必填" if param.get('required') else "可选"
            default = f"，默认: {param.get('default')}" if 'default' in param else ""
            lines.append(f"- `{name}` ({required}{default}): {param.get('description', '')}")
        
        if self.examples:
            lines.extend(["", "### 示例"])
            for ex in self.examples[:2]:
                lines.append(f"- {ex.get('name')}: `{ex.get('params')}`")
        
        return "\n".join(lines)


class ToolLoader:
    """工具加载器"""
    
    def __init__(self, toolbox_path: str = None):
        self.toolbox_path = Path(toolbox_path) if toolbox_path else Path(__file__).parent.parent
        self.tools_path = self.toolbox_path / "tools"
        
        self._tools: Dict[str, ToolConfig] = {}
        self._registry: dict = {}
        self._modules: Dict[str, Any] = {}
        
        self._load_registry()
        self._load_tools()
    
    def _load_registry(self):
        """加载工具注册表"""
        registry_file = self.toolbox_path / "tools.yaml"
        if registry_file.exists():
            with open(registry_file, 'r', encoding='utf-8') as f:
                self._registry = yaml.safe_load(f)
    
    def _load_tools(self):
        """加载所有工具配置"""
        tools_config = self._registry.get('tools', {})
        
        for tool_id, tool_meta in tools_config.items():
            if not tool_meta.get('enabled', True):
                continue
            
            # 加载工具配置文件
            parts = tool_id.split('/')
            if len(parts) != 2:
                continue
            
            category, name = parts
            config_file = self.tools_path / category / f"{name}.yaml"
            
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                self._tools[tool_id] = ToolConfig(
                    tool_id=tool_id,
                    config=config,
                    base_path=self.tools_path / category
                )
    
    def list_tools(self) -> Dict[str, dict]:
        """列出所有工具"""
        result = {}
        for tool_id, tool in self._tools.items():
            result[tool_id] = {
                "name": tool.name,
                "category": tool.category,
                "description": tool.short_desc,
                "tags": tool.tags,
                "params": tool.get_param_schema()
            }
        return result
    
    def get_tool(self, tool_id: str) -> Optional[ToolConfig]:
        """获取工具配置"""
        return self._tools.get(tool_id)
    
    def get_tool_schema(self, tool_id: str) -> Optional[dict]:
        """获取工具 schema"""
        tool = self.get_tool(tool_id)
        if not tool:
            return None
        
        return {
            "name": tool.tool_id,
            "description": tool.short_desc,
            "parameters": tool.get_param_schema(),
            "output": tool.output,
            "examples": tool.examples
        }
    
    def get_tools_summary(self) -> str:
        """获取工具摘要（给 LLM 用）"""
        lines = ["# 可用工具列表", ""]
        
        # 按分类分组
        by_category = {}
        for tool_id, tool in self._tools.items():
            cat = tool.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(tool)
        
        categories = self._registry.get('categories', {})
        
        for cat, tools in by_category.items():
            cat_info = categories.get(cat, {})
            icon = cat_info.get('icon', '📦')
            name = cat_info.get('name', cat)
            lines.append(f"## {icon} {name}")
            
            for tool in tools:
                lines.append(f"- **{tool.tool_id}**: {tool.short_desc}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def load_tool_module(self, tool_id: str):
        """加载工具模块"""
        if tool_id in self._modules:
            return self._modules[tool_id]
        
        tool = self.get_tool(tool_id)
        if not tool:
            return None
        
        script = tool.execution.get('script')
        if not script:
            return None
        
        script_path = tool.base_path / script
        if not script_path.exists():
            return None
        
        try:
            spec = importlib.util.spec_from_file_location(tool_id.replace('/', '_'), script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._modules[tool_id] = module
            return module
        except Exception as e:
            print(f"加载工具模块失败 {tool_id}: {e}")
            return None


# 全局加载器
_loader: Optional[ToolLoader] = None


def get_loader() -> ToolLoader:
    """获取全局加载器"""
    global _loader
    if _loader is None:
        _loader = ToolLoader()
    return _loader
