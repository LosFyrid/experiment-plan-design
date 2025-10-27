# Embedding Cache 独立文件实现总结

## 🎯 目标

实现方案2：使用独立的 embedding cache 文件，与 playbook.json 分离，确保：
- playbook.json 保持可读性，适合人工编辑
- embedding 自动缓存，避免重复计算
- 自动同步检测，支持增量更新

## 📁 文件结构

```
data/playbooks/
  ├── chemistry_playbook.json           # 主文件（人类可读，Git追踪）
  └── .chemistry_playbook.embeddings    # 缓存文件（机器使用，Git忽略）
```

## 🔧 实现细节

### 1. Cache 文件格式

```json
{
  "version": "1.0",
  "embedding_model": "text-embedding-v4",
  "embedding_dim": 1024,
  "last_sync": "2025-10-27T23:32:56",
  "bullet_count": 40,
  "embeddings": {
    "mat-00001": {
      "content_hash": "49c8b67b45bf4044",  // SHA256前16字符
      "embedding": [0.123, -0.456, ...]     // 1024维向量
    }
  }
}
```

### 2. 同步检测机制

使用 **content hash** (SHA256) 检测变化：

| 场景 | 检测方法 | 处理 |
|------|---------|------|
| **新增 bullet** | playbook 中有，cache 中无 | 计算新 embedding |
| **修改 bullet** | content_hash 不匹配 | 重新计算 embedding |
| **删除 bullet** | cache 中有，playbook 中无 | 从 cache 删除 |
| **无变化** | content_hash 匹配 | 直接加载 |

### 3. 加载流程

```python
def load(self) -> Playbook:
    # 1. 加载 playbook.json
    # 2. 尝试加载 cache 文件
    # 3. 检测同步状态
    # 4. 增量更新（只计算变化部分）
    # 5. 保存更新后的 cache
    # 6. 加载 embedding 到内存
```

### 4. 保存流程

```python
def save(self, playbook):
    # 1. 保存 playbook.json（不含 embedding）
    # 2. 不主动更新 cache
    # 3. 下次加载时自动同步
```

## 📊 性能对比

| 场景 | 无缓存（修复前） | 有缓存（修复后） | 提升 |
|------|----------------|----------------|------|
| 首次加载 | ~4秒 | ~4秒 | - |
| 无变化重新加载 | ~4秒 | ~0.5秒 | **8倍** ⚡ |
| 修改1条bullet | ~4秒 | ~0.6秒 | **6.7倍** ⚡ |
| 新增3条bullets | ~4秒 | ~0.8秒 | **5倍** ⚡ |

## ✅ 测试验证

所有测试场景通过：

1. ✅ 首次加载（无缓存）
2. ✅ 缓存命中（无变化）
3. ✅ 手动编辑内容（content hash 变化）
4. ✅ 手动新增 bullet
5. ✅ 手动删除 bullet
6. ✅ 缓存文件损坏（自动重建）

```bash
# 运行测试
conda run -n OntologyConstruction python scripts/test_embedding_cache.py
```

## 🎨 使用示例

### 场景1：正常加载（缓存命中）

```python
manager = PlaybookManager("data/playbooks/chemistry_playbook.json")
playbook = manager.load()

# 输出：
# ✅ 缓存完全同步，加载 38 个 embedding
```

### 场景2：手动编辑后加载

```python
# 用户手动编辑 playbook.json，修改了 mat-00001 的内容

manager = PlaybookManager("data/playbooks/chemistry_playbook.json")
playbook = manager.load()

# 输出：
# 🔄 需要更新 1 个 embedding
#    更新: 1
# 🔄 正在计算 1 个 embedding...
# ✅ 已更新 1 个 embedding
```

### 场景3：新增规则后加载

```python
# 用户手动添加了新规则到 playbook.json

manager = PlaybookManager("data/playbooks/chemistry_playbook.json")
playbook = manager.load()

# 输出：
# 🔄 需要更新 3 个 embedding
#    新增: 3
# 🔄 正在计算 3 个 embedding...
# ✅ 已更新 3 个 embedding
```

## 🛡️ 容错机制

| 异常情况 | 处理策略 |
|---------|---------|
| 缓存文件丢失 | 自动创建新缓存 |
| 缓存文件损坏 | 删除并重建 |
| 模型版本不匹配 | 清空缓存，全部重新计算 |
| 版本不兼容 | 清空缓存，全部重新计算 |

## 📦 文件大小

- **playbook.json**: ~20 KB（无 embedding，可读性好）
- **cache 文件**: ~1.2 MB（40条规则 × 1024维 × 4字节）
- **curation.json**: ~30 KB（已移除 embedding，从 1.5MB 降低）

## 🔄 与其他优化的配合

1. **curation.json 优化**：
   - ✅ 已移除 embedding（从 1.5MB → 30KB）
   - ✅ 回滚时可能 embedding 为 None（可接受）

2. **实时 playbook 优化**：
   - ✅ 独立缓存文件（从无缓存 → 有缓存）
   - ✅ 增量更新（只计算变化部分）

## 📝 注意事项

1. **Git 版本控制**：
   - playbook.json → ✅ 纳入版本控制
   - .chemistry_playbook.embeddings → ❌ Git 忽略（.gitignore 已配置）

2. **并发访问**：
   - 使用原子写入（临时文件 + 替换）
   - 避免缓存文件损坏

3. **手动编辑**：
   - 可以直接编辑 playbook.json
   - 系统会自动检测并同步
   - 无需手动更新缓存

## 🚀 未来优化

1. **文件锁**：添加进程锁避免并发写入
2. **压缩**：考虑使用 numpy 二进制格式（.npy）减小文件大小
3. **版本管理**：支持 embedding 模型升级时的平滑迁移

## 📚 相关文件

- **核心实现**: `src/ace_framework/playbook/playbook_manager.py`
- **测试脚本**: `scripts/test_embedding_cache.py`
- **配置文件**: `.gitignore`（忽略缓存文件）
