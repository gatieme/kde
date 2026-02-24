# Model Inference Module

## 项目介绍

Model Inference Module 是 KDE 项目的 AI 模型集成层，负责与 ModelScope API 交互，使用 Qwen3-235B-A22B 模型进行文本分析和推理。

## 项目架构

### 整体架构图

```
┌──────────────────────────────────────────────────────────────┐
│                 Model Inference Module                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              ModelRequest                             │  │
│  │  - set_request(type, content)                        │  │
│  │  - get_messages() → List[Dict]                       │  │
│  │                                                       │  │
│  │  类型:                                                │  │
│  │  - summary: 300 字限制摘要                            │  │
│  │  - analysis: 详细技术分析                            │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                  │
│                         ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              ModelInference                           │  │
│  │  - OpenAI Client (ModelScope API)                    │  │
│  │  - inference(messages) → str                         │  │
│  │  - Streaming with tqdm progress                      │  │
│  │                                                       │  │
│  │  配置:                                                │  │
│  │  - model: Qwen3-235B-A22B                            │  │
│  │  - temperature: 0 (greedy)                           │  │
│  │  - stream: True                                      │  │
│  │  - extra_body: {enable_thinking: False}              │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                  │
│                         ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          ModelScope API (Qwen3-235B-A22B)             │  │
│  │  https://api-inference.modelscope.cn/v1/              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 核心组件

```
model/
├── model_infer.py      # ModelScope 推理封装
├── model_request.py    # 请求构建器
├── model_api.py        # API 工具函数
├── __init__.py         # 模块初始化
└── README.md           # 本文件
```

## 功能说明

### 主要功能

- **模型推理** - 使用 ModelScope Qwen3-235B-A22B 模型进行文本推理
- **流式输出** - 支持流式响应，实时显示推理进度
- **进度条显示** - 使用 tqdm 显示模型推理进度
- **请求构建** - 提供便捷的请求构建接口
- **温度控制** - 支持温度参数调整（默认为 0，贪心解码）
- **思考控制** - 支持启用/禁用模型思考过程

### 技术实现

- **OpenAI 兼容客户端** - 使用 OpenAI SDK 客户端连接 ModelScope API
- **流式推理** - 启用流式响应，支持实时输出
- **贪心解码** - 默认 temperature=0，确保输出确定性
- **进度可视化** - 使用 tqdm 库显示推理进度条
- **日志控制** - 通过 verbose 级别控制日志输出

## 使用说明

### 基本使用

```python
from model import ModelInference, ModelRequest

# 创建模型实例
model = ModelInference(verbose=1)

# 构建请求
request = ModelRequest()
request.set_content("分析这段代码的功能...")

# 执行推理
response = model.infer(request.get_messages())

print(response)
```

### 流式推理

```python
from model import ModelInference

model = ModelInference(verbose=1)

# 流式推理会自动显示进度条
messages = [
    {"role": "system", "content": "你是一个代码分析助手"},
    {"role": "user", "content": "分析这段代码..."}
]
response = model.inference(messages)
```

### 配置参数

```python
from model import ModelInference

# 创建模型实例（verbose=1 显示进度条）
model = ModelInference(verbose=1)

# 模型配置
model.model = 'Qwen/Qwen3-235B-A22B'  # 模型 ID
model.extra_body = {
    "enable_thinking": False,  # 启用思考过程
    # " "thinking_budget": 4096  # 思考 token 预算
}
```

## 依赖关系

### 外部依赖

- **openai** - OpenAI SDK（用于 ModelScope API 兼容）
- **tqdm** - 用于显示进度条

## 配置说明

### 模型配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `model` | `Qwen/Qwen3-235B-A22B` | ModelScope 模型 ID |
| `base_url` | `https://api-inference.modelscope.cn/v1/` | ModelScope API 基础 URL |
| `temperature` | `0` | 温度参数（0 表示贪心解码） |
| `top_p` | `1` | 核采样参数 |
| `presence_penalty` | `0` | 存在惩罚 |
| `frequency_penalty` | `0` | 频率惩罚 |
| `enable_thinking` | `False` | 是否启用思考过程 |

### Verbose 级别

| 级别 | 行为 |
|------|------|
| `0` | 不显示进度条，显示 "模型思考中..." |
| `1` | 显示进度条和基本日志 |
| `2+` | 显示更详细的日志和推理过程 |

## API 说明

### ModelInference 类

```python
class ModelInference:
    def __init__(self, content=None, verbose=0):
        """初始化模型实例
        
        Args:
            content: 初始内容（可选）
            verbose: 详细级别（0-3）
        """
    
    def inference(self, messages):
        """执行模型推理
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
        
        Returns:
            str: 模型推理结果
        """
```

### ModelRequest 类

```python
class ModelRequest:
    def __init__(self):
        """初始化请求构建器"""
    
    def set_content(self, content):
        """设置请求内容
        
        Args:
            content: 请求内容字符串
        """
    
    def get_messages(self):
        """获取消息列表
        
        Returns:
            list: 消息列表
        """
```

## 注意事项

1. **API 密钥** - 当前使用硬编码的 ModelScope Token，建议改为环境变量配置
2. **网络连接** - 需要网络连接访问 ModelScope API
3. **推理时间** - 大型模型推理可能需要较长时间，建议使用进度条
4. **Token 限制** - 注意输入和输出的 token 限制
5. **温度设置** - 生产环境建议使用 temperature=0 确保输出确定性

## 扩展计划

### 功能扩展

- 支持更多模型选择
- 添加批量推理功能
- 支持自定义系统提示
- 添加结果缓存机制

### 性能优化

- 优化流式输出性能
- 添加请求重试机制
- 实现请求队列管理
- 添加并发推理支持

### 用户体验

- 添加更详细的错误处理
- 支持自定义进度条样式
- 添加推理时间统计
- 支持结果格式化输出

## 许可证

MIT License
