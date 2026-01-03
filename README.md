# pocket

`pocket` 是一个轻量级的 Python 工具包，用于沉淀和复用项目中常用的工具函数、装饰器以及可选的基础设施封装。  
设计目标是 **模块化、可选依赖、长期可维护**。

---

## 特性

- 📦 **工具集合**：将常用代码集中管理，避免项目间重复复制
- ⏱ **计时装饰器**：支持同步 / 异步函数执行时间统计
- 🔌 **可选模块设计**：如 `nats`，按需安装，不影响核心功能
- 🧩 **标准 logging**：基于 Python 标准库，避免日志库冲突

---

## 安装

### 基础安装（不包含可选模块）

```bash
uv add pocket
```
## 安装 NATS 模块（可选）

```
uv add pocket[nats]
```
nats 模块依赖官方客户端 nats-py，通过 extras 自动安装。

## 计时装饰器

### 同步函数
```python
from pocket.decorators.timing import get_time_sync

@get_time_sync
def compute(a: int, b: int) -> int:
    return a + b

compute(1, 2)

```

### 异步函数
```python
import asyncio
from pocket.decorators.timing import get_time_async

@get_time_async
async def async_compute(a: int, b: int) -> int:
    await asyncio.sleep(1)
    return a + b

asyncio.run(async_compute(1, 2))
```
## Nats
```python
import asyncio
from pocket.nats import NatsConnection, EventPublisher

async def main():
    conn = await NatsConnection.create("nats://127.0.0.1:4222")

    publisher = EventPublisher(conn)
    await publisher.publish("demo.subject", b"hello world")

    await conn.close()

asyncio.run(main())

```
## 项目结构
```
pocket/
├── src/
│   └── pocket/
│       ├── __init__.py
│       ├── logger.py
│       ├── decorators/
│       │   ├── __init__.py
│       │   └── timing.py
│       └── nats/
│           ├── __init__.py
│           └── client.py
```
